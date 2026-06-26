"""
AEGIS SaaS — Alert processing endpoints.
Replaces the legacy integration_module.py endpoints with multi-tenant versions.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_tenant, rate_limit_check, UsageContext
from app.models import Tenant
from app.services.classifier_service import classifier_service
from app.services.orchestrator_service import orchestrator_service
from app.services.billing_service import billing_service
from app.services.rate_limit_service import rate_limit_service
from app.logging_config import get_logger


router = APIRouter(tags=["Alerts"])
logger = get_logger(__name__)


# ── Request / Response models ─────────────────────────────────


class AlertRequest(BaseModel):
    """Incoming alert or ticket from any source."""
    source: str = "api"
    severity: Optional[str] = None
    title: str
    description: str
    metadata: Optional[dict] = {}


class DiagnosisResponse(BaseModel):
    """AEGIS diagnosis result."""
    timestamp: str
    source: str
    severity: str
    level: str
    pattern_id: str
    pattern_name: str
    diagnosis: str
    script: str
    confidence: Optional[str] = None
    similar_tickets: Optional[list] = None


# ── Category mapping (same as integration_module.py) ──────────

CATEGORY_MAP = {
    "ACCESS": {
        "id": "L1-001", "name": "Access / Authentication Issue",
        "diagnosis": "User authentication or authorization failure detected.",
        "script": "1. Verify user account is active\n2. Reset password if needed\n3. Check group/role assignments\n4. Clear browser cache and cookies"
    },
    "DATABASE": {
        "id": "L1-005", "name": "Database Issue",
        "diagnosis": "Database connection, query, or performance issue detected.",
        "script": "1. Check database connection pool and active connections\n2. Review slow query log\n3. Verify replication status\n4. Escalate to DBA team if persists"
    },
    "LICENSE": {
        "id": "L1-003", "name": "License / Quota Issue",
        "diagnosis": "License expiration or quota exceeded detected.",
        "script": "1. Check license expiration date in admin panel\n2. Renew or extend license\n3. Review quota usage and increase if needed"
    },
    "API": {
        "id": "L1-006", "name": "API / Integration Issue",
        "diagnosis": "API endpoint or webhook failure detected.",
        "script": "1. Check API endpoint availability\n2. Verify authentication tokens\n3. Review rate limit quotas\n4. Check upstream service status"
    },
    "PERFORMANCE": {
        "id": "L1-002", "name": "Performance Degradation",
        "diagnosis": "Application performance issue detected. Likely caused by resource contention or network latency.",
        "script": "1. Check CPU and memory usage\n2. Review active database queries\n3. Verify CDN and cache status\n4. Escalate to L3/L4 if persists > 15 min"
    },
    "NETWORK": {
        "id": "L1-007", "name": "Network / Connectivity Issue",
        "diagnosis": "Network connectivity or DNS resolution issue detected.",
        "script": "1. Test connectivity with ping/traceroute\n2. Check DNS resolution\n3. Verify firewall rules\n4. Check VPN status if applicable"
    },
    "SECURITY": {
        "id": "L1-008", "name": "Security / Certificate Issue",
        "diagnosis": "Security vulnerability, certificate expiry, or threat detected.",
        "script": "1. Verify SSL/TLS certificate validity\n2. Run antivirus scan if malware suspected\n3. Apply required security patches\n4. Review security group and firewall rules"
    },
    "HOWTO": {
        "id": "L1-004", "name": "How-To / Configuration Request",
        "diagnosis": "User needs guidance on setup or configuration.",
        "script": "1. Direct user to documentation portal\n2. Share relevant runbook or KB article\n3. Schedule walkthrough session if needed"
    },
    "UNKNOWN": {
        "id": "L1-UNKNOWN", "name": "Unclassified Ticket",
        "diagnosis": "No matching L1/L2 pattern found. Routing to human agent for triage.",
        "script": "1. Review ticket manually\n2. Assign to appropriate team\n3. Update knowledge base with resolution"
    }
}


# ── Severity router ───────────────────────────────────────────


def route_severity(severity: Optional[str], description: str) -> str:
    """Determine if this is L1/L2 (routine) or L3/L4 (critical)."""
    if severity:
        sev = severity.lower()
        if sev in ("critical", "high"):
            return "L3/L4"
        if sev in ("low", "medium"):
            return "L1/L2"

    critical_keywords = [
        "outage", "down", "unavailable", "timeout", "cascad",
        "failover", "crash", "error 5", "500", "503", "504",
        "latency spike", "memory", "cpu", "disk full", "replication"
    ]
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in critical_keywords):
        return "L3/L4"

    return "L1/L2"


# ── L1/L2 handler ─────────────────────────────────────────────


def handle_l1_l2(alert: AlertRequest, tenant_id: str) -> dict:
    """Handle routine tickets using the ChromaDB vector classifier."""
    input_text = f"{alert.title} {alert.description}" if alert.title else alert.description

    result = classifier_service.classify(tenant_id, input_text)

    predicted_category = result["category"]
    confidence = result["confidence"]
    similar_tickets = result.get("similar_tickets", [])
    suggested_resolution = result.get("suggested_resolution", "")
    method = result.get("method", "unknown")
    all_scores = result.get("all_category_scores", {})

    pattern = CATEGORY_MAP.get(predicted_category, CATEGORY_MAP["UNKNOWN"])

    diagnosis = pattern["diagnosis"]
    if predicted_category != "UNKNOWN":
        diagnosis += f" (classified via {method}, confidence {confidence:.1%})"

    script = pattern["script"]
    if suggested_resolution and predicted_category != "UNKNOWN":
        script = f"Suggested resolution: {suggested_resolution}\n\n---\n\nStandard procedure:\n{pattern['script']}"

    confidence_label = "HIGH" if confidence >= 0.75 else "MEDIUM" if confidence >= 0.50 else "LOW"

    response = {
        "level": "L1/L2",
        "pattern_id": pattern["id"],
        "pattern_name": pattern["name"],
        "diagnosis": diagnosis,
        "script": script,
        "confidence": confidence_label,
    }

    if all_scores:
        response["category_scores"] = {
            cat: round(score * 100, 1)
            for cat, score in sorted(all_scores.items(), key=lambda x: -x[1])
        }

    return response


# ── L3/L4 handler ─────────────────────────────────────────────


def handle_l3_l4(alert: AlertRequest) -> dict:
    """Handle critical incidents using the configured LLM provider."""
    input_text = f"{alert.title} {alert.description}" if alert.title else alert.description
    result = orchestrator_service.diagnose(input_text)

    return {
        "level": "L3/L4",
        "pattern_id": str(result.get("id", "UNKNOWN")),
        "pattern_name": str(result.get("name", "Unknown Pattern")),
        "diagnosis": str(result.get("diagnosis", "")),
        "script": str(result.get("script", "")),
        "confidence": None,
    }


def handle_l3_l4_degraded(alert: AlertRequest) -> dict:
    """Handle critical incidents when LLM is not configured (degraded mode)."""
    input_text = f"{alert.title} {alert.description}" if alert.title else alert.description
    result = orchestrator_service.diagnose(input_text)

    return {
        "level": "L3/L4",
        "pattern_id": str(result.get("id", "LLM-UNAVAILABLE")),
        "pattern_name": str(result.get("name", "LLM Provider Not Configured")),
        "diagnosis": str(result.get("diagnosis", "")),
        "script": str(result.get("script", "")),
        "confidence": None,
    }


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/v1/alert", response_model=DiagnosisResponse)
def process_alert(
    alert: AlertRequest,
    request: Request,
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Main endpoint. Receives any alert or ticket and returns diagnosis + script.
    Requires X-API-Key header when AUTH_REQUIRED=true.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Check rate limit
    allowed, rate_headers = rate_limit_service.check_rate_limit(tenant.id, tenant.plan)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Limit: {rate_headers['X-RateLimit-Limit']} requests per hour.",
                "rate_limit": rate_headers,
            },
            headers=rate_headers,
        )

    # Add rate limit headers to response
    for key, value in rate_headers.items():
        response.headers[key] = value

    # Check quota
    billing_service.check_quota(db, tenant)

    # Route to L1/L2 or L3/L4
    level = route_severity(alert.severity, alert.description)

    logger.info("Processing alert", extra={
        "request_id": request_id,
        "tenant_id": tenant.id,
        "level": level,
        "severity": alert.severity,
        "source": alert.source,
        "title": alert.title[:80],
    })

    if level == "L1/L2":
        result = handle_l1_l2(alert, tenant.id)
    else:
        # Check if LLM is available (graceful degradation)
        if orchestrator_service.is_degraded:
            result = handle_l3_l4_degraded(alert)
            logger.warning("Alert processed in degraded mode — LLM not configured", extra={
                "request_id": request_id,
                "tenant_id": tenant.id,
                "level": level,
            })
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service Unavailable",
                    "message": "LLM provider not configured. Please set DEEPSEEK_API_KEY in .env",
                    "level": level,
                    **result,
                },
            )
        result = handle_l3_l4(alert)

    # Record usage
    billing_service.record_usage(
        db=db,
        tenant=tenant,
        endpoint="/v1/alert",
        status_code=200,
    )

    logger.info("Alert processed successfully", extra={
        "request_id": request_id,
        "tenant_id": tenant.id,
        "level": level,
        "pattern_id": result.get("pattern_id", "unknown"),
        "confidence": result.get("confidence"),
    })

    return DiagnosisResponse(
        timestamp=datetime.utcnow().isoformat(),
        source=alert.source,
        severity=alert.severity or "not specified",
        **result,
    )


@router.get("/v1/health")
def health(
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Health check endpoint."""
    patterns_ok = settings.PATTERNS_FILE.exists()

    # Add rate limit headers
    allowed, rate_headers = rate_limit_service.check_rate_limit(tenant.id, tenant.plan)
    for key, value in rate_headers.items():
        response.headers[key] = value

    llm_provider = orchestrator_service.get_provider_name()
    llm_available = not orchestrator_service.is_degraded

    return {
        "status": "healthy",
        "tenant": tenant.slug,
        "plan": tenant.plan,
        "classifier_tickets": classifier_service.get_global_stats()["total_tickets"],
        "patterns_file": "found" if patterns_ok else "missing",
        "llm_provider": llm_provider,
        "llm_available": llm_available,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/v1/stats")
def stats(
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get classifier and usage statistics for the current tenant."""
    classifier_stats = classifier_service.get_stats(tenant.id)
    usage_stats = billing_service.get_usage(db, tenant.id)

    # Add rate limit headers
    allowed, rate_headers = rate_limit_service.check_rate_limit(tenant.id, tenant.plan)
    for key, value in rate_headers.items():
        response.headers[key] = value

    return {
        "tenant": tenant.slug,
        "plan": tenant.plan,
        "classifier": classifier_stats,
        "usage": usage_stats,
    }
