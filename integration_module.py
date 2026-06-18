# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
AEGIS Integration Module v2.0
Universal webhook adapter — receives alerts and routes to L1/L2 classifier or L3/L4 orchestrator
Now supports Slack Bot (via slack_bot.py) and PagerDuty (via /pagerduty webhook).
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# ── Import Aegis Classifier ────────────────────────────────────
# The classifier module loads the embedding model + ChromaDB client on import.
# The menu only runs when __name__ == "__main__", so importing is safe.
import sys
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# Suppress the classifier init print statements during import
import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()  # capture init prints

from classifier import (
    load_dataset_from_csv, create_collection, load_tickets_to_db,
    classify_ticket, get_statistics, DATASET_PATH, SAMPLE_TICKETS
)

# Restore stdout and print our own header
sys.stdout = _old_stdout

# ── Load environment ──────────────────────────────────────────
load_dotenv()

# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(
    title="AEGIS Integration Module v2",
    description="Universal webhook adapter — L1/L2 with ChromaDB classifier, L3/L4 with DeepSeek",
    version="2.0.0"
)

# ── Paths ─────────────────────────────────────────────────────
PATTERNS_FILE = Path(__file__).parent / "AEGIS_PATTERNS.md"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ── Initialize ChromaDB classifier collection ─────────────────
print("🛡️ AEGIS Integration Module v2.0 - Initializing ChromaDB classifier...")
dataset = load_dataset_from_csv(DATASET_PATH)
if not dataset:
    print("⚠️ Using built-in sample tickets (CSV not found)")
    dataset = SAMPLE_TICKETS

collection = create_collection()
load_tickets_to_db(dataset, collection)

# Show stats
stats = get_statistics(collection)
print(f"📊 Classifier ready: {stats['total']} tickets in {len(stats['categories'])} categories")

# ── Category mapping ──────────────────────────────────────────
# Maps classifier categories to L1 pattern IDs/names for the API response

CATEGORY_MAP = {
    "ACCESS": {
        "id": "L1-001",
        "name": "Access / Authentication Issue",
        "diagnosis": "User authentication or authorization failure detected.",
        "script": "1. Verify user account is active\n2. Reset password if needed\n3. Check group/role assignments\n4. Clear browser cache and cookies"
    },
    "DATABASE": {
        "id": "L1-005",
        "name": "Database Issue",
        "diagnosis": "Database connection, query, or performance issue detected.",
        "script": "1. Check database connection pool and active connections\n2. Review slow query log\n3. Verify replication status\n4. Escalate to DBA team if persists"
    },
    "LICENSE": {
        "id": "L1-003",
        "name": "License / Quota Issue",
        "diagnosis": "License expiration or quota exceeded detected.",
        "script": "1. Check license expiration date in admin panel\n2. Renew or extend license\n3. Review quota usage and increase if needed"
    },
    "API": {
        "id": "L1-006",
        "name": "API / Integration Issue",
        "diagnosis": "API endpoint or webhook failure detected.",
        "script": "1. Check API endpoint availability\n2. Verify authentication tokens\n3. Review rate limit quotas\n4. Check upstream service status"
    },
    "PERFORMANCE": {
        "id": "L1-002",
        "name": "Performance Degradation",
        "diagnosis": "Application performance issue detected. Likely caused by resource contention or network latency.",
        "script": "1. Check CPU and memory usage\n2. Review active database queries\n3. Verify CDN and cache status\n4. Escalate to L3/L4 if persists > 15 min"
    },
    "NETWORK": {
        "id": "L1-007",
        "name": "Network / Connectivity Issue",
        "diagnosis": "Network connectivity or DNS resolution issue detected.",
        "script": "1. Test connectivity with ping/traceroute\n2. Check DNS resolution\n3. Verify firewall rules\n4. Check VPN status if applicable"
    },
    "SECURITY": {
        "id": "L1-008",
        "name": "Security / Certificate Issue",
        "diagnosis": "Security vulnerability, certificate expiry, or threat detected.",
        "script": "1. Verify SSL/TLS certificate validity\n2. Run antivirus scan if malware suspected\n3. Apply required security patches\n4. Review security group and firewall rules"
    },
    "HOWTO": {
        "id": "L1-004",
        "name": "How-To / Configuration Request",
        "diagnosis": "User needs guidance on setup or configuration.",
        "script": "1. Direct user to documentation portal\n2. Share relevant runbook or KB article\n3. Schedule walkthrough session if needed"
    },
    "UNKNOWN": {
        "id": "L1-UNKNOWN",
        "name": "Unclassified Ticket",
        "diagnosis": "No matching L1/L2 pattern found. Routing to human agent for triage.",
        "script": "1. Review ticket manually\n2. Assign to appropriate team\n3. Update knowledge base with resolution"
    }
}

# ── Request / Response models ─────────────────────────────────

class AlertRequest(BaseModel):
    """Incoming alert or ticket from any source."""
    source: str                    # e.g. "pagerduty", "slack", "jira", "manual"
    severity: Optional[str] = None # "low", "medium", "high", "critical"
    title: str                     # short description
    description: str               # full alert text / ticket body
    metadata: Optional[dict] = {}  # any extra fields from the source system

class DiagnosisResponse(BaseModel):
    """AEGIS diagnosis result."""
    timestamp: str
    source: str
    severity: str
    level: str                     # "L1/L2" or "L3/L4"
    pattern_id: str
    pattern_name: str
    diagnosis: str
    script: str
    confidence: Optional[str] = None
    similar_tickets: Optional[list] = None

# ── Severity router ───────────────────────────────────────────

def route_severity(severity: Optional[str], description: str) -> str:
    """
    Determine if this is an L1/L2 (routine) or L3/L4 (critical) incident.
    Uses severity field if provided, otherwise infers from description.
    """
    if severity:
        sev = severity.lower()
        if sev in ("critical", "high"):
            return "L3/L4"
        if sev in ("low", "medium"):
            return "L1/L2"

    # Infer from keywords in description
    critical_keywords = [
        "outage", "down", "unavailable", "timeout", "cascad",
        "failover", "crash", "error 5", "500", "503", "504",
        "latency spike", "memory", "cpu", "disk full", "replication"
    ]
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in critical_keywords):
        return "L3/L4"

    return "L1/L2"

# ── L1/L2 handler (now uses ChromaDB classifier) ──────────────

def handle_l1_l2(alert: AlertRequest) -> dict:
    """
    Handle routine tickets using the ChromaDB vector classifier.
    Uses the hybrid approach: vector search + weighted voting + keyword fallback.
    """
    # Use description as the main classification input (combine with title for more context)
    input_text = f"{alert.title} {alert.description}" if alert.title else alert.description

    # Classify using the vector + keyword hybrid classifier
    result = classify_ticket(input_text, collection)

    predicted_category = result["category"]
    confidence = result["confidence"]
    similar_tickets = result.get("similar_tickets", [])
    suggested_resolution = result.get("suggested_resolution", "")
    method = result.get("method", "unknown")
    all_scores = result.get("all_category_scores", {})

    # Map category to L1 pattern info
    pattern = CATEGORY_MAP.get(predicted_category, CATEGORY_MAP["UNKNOWN"])

    # Build diagnosis with confidence and method info
    diagnosis = pattern["diagnosis"]
    if predicted_category != "UNKNOWN":
        diagnosis += f" (classified via {method}, confidence {confidence:.1%})"

    # Build script: use suggested resolution if available, otherwise use pattern default
    script = pattern["script"]
    if suggested_resolution and predicted_category != "UNKNOWN":
        script = f"Suggested resolution: {suggested_resolution}\n\n---\n\nStandard procedure:\n{pattern['script']}"

    # Format confidence level for API response
    confidence_label = "HIGH" if confidence >= 0.75 else "MEDIUM" if confidence >= 0.50 else "LOW"

    # Build response
    response = {
        "level": "L1/L2",
        "pattern_id": pattern["id"],
        "pattern_name": pattern["name"],
        "diagnosis": diagnosis,
        "script": script,
        "confidence": confidence_label
    }

    # Include category distribution if available (for diagnostics)
    if all_scores:
        response["category_scores"] = {
            cat: round(score * 100, 1)
            for cat, score in sorted(all_scores.items(), key=lambda x: -x[1])
        }

    return response

# ── L3/L4 handler ─────────────────────────────────────────────

def handle_l3_l4(alert: AlertRequest) -> dict:
    """
    Handle critical incidents using DeepSeek + RAG over AEGIS_PATTERNS.md.
    This calls orchestrator.py logic directly.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY not configured. Add it to your .env file."
        )

    if not PATTERNS_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"AEGIS_PATTERNS.md not found at {PATTERNS_FILE}"
        )

    patterns_kb = PATTERNS_FILE.read_text(encoding="utf-8")
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    system_prompt = """You are Aegis, an autonomous incident triage agent.
Given a user alert and the AEGIS patterns knowledge base, identify the single closest matching pattern.

Rules:
- Compare symptoms, error codes, metrics, and context from the alert against each pattern.
- Pick the best match only if there is reasonable confidence; otherwise use UNKNOWN.
- Use the matched pattern's diagnosis and remediation script from the knowledge base.
- For "script", return the bash remediation commands from the matched pattern.
- Respond with valid JSON only, no markdown fences.

JSON schema:
{
  "id": "AEGIS-XXX or UNKNOWN",
  "name": "pattern name",
  "diagnosis": "root cause explanation tailored to the alert",
  "script": "remediation commands as a single string"
}"""

    user_prompt = f"""ALERT TITLE: {alert.title}
ALERT SOURCE: {alert.source}
ALERT SEVERITY: {alert.severity or 'not specified'}

ALERT DESCRIPTION:
{alert.description}

KNOWLEDGE BASE (AEGIS_PATTERNS.md):
{patterns_kb}

Find the closest matching pattern and return the JSON response."""

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content
        result = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse LLM response as JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek API error: {str(e)}")

    return {
        "level": "L3/L4",
        "pattern_id": str(result.get("id", "UNKNOWN")),
        "pattern_name": str(result.get("name", "Unknown Pattern")),
        "diagnosis": str(result.get("diagnosis", "")),
        "script": str(result.get("script", "")),
        "confidence": None
    }

# ── Routes ────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "AEGIS Integration Module",
        "version": "2.0.0",
        "status": "operational",
        "classifier_tickets": stats["total"],
        "classifier_categories": list(stats["categories"].keys()),
        "endpoints": {
            "POST /alert": "Submit an alert or ticket for diagnosis",
            "GET /health": "Health check",
            "GET /docs": "Interactive API documentation"
        }
    }

@app.get("/health")
def health():
    patterns_ok = PATTERNS_FILE.exists()
    api_key_ok = bool(os.getenv("DEEPSEEK_API_KEY"))
    classifier_ok = stats["total"] > 0
    return {
        "status": "healthy" if patterns_ok and api_key_ok and classifier_ok else "degraded",
        "classifier": f"{stats['total']} tickets, {len(stats['categories'])} categories" if classifier_ok else "empty",
        "patterns_file": "found" if patterns_ok else "missing",
        "deepseek_api_key": "configured" if api_key_ok else "missing",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/alert", response_model=DiagnosisResponse)
def process_alert(alert: AlertRequest):
    """
    Main endpoint. Receives any alert or ticket and returns diagnosis + script.

    Example payload:
    {
        "source": "manual",
        "severity": "low",
        "title": "User cannot log in",
        "description": "User gets 403 error when accessing the application"
    }
    """
    # Route to L1/L2 or L3/L4
    level = route_severity(alert.severity, alert.description)

    if level == "L1/L2":
        result = handle_l1_l2(alert)
    else:
        result = handle_l3_l4(alert)

    return DiagnosisResponse(
        timestamp=datetime.utcnow().isoformat(),
        source=alert.source,
        severity=alert.severity or "not specified",
        **result
    )

# ── PagerDuty webhook endpoint ──────────────────────────────────
# PagerDuty sends alerts via its webhook (Events API v2 format).
# This endpoint normalizes PagerDuty payloads into AEGIS alerts.

class PagerDutyWebhookPayload(BaseModel):
    """PagerDuty Events API v2 webhook payload."""
    event: Optional[str] = None
    event_type: Optional[str] = None
    incident: Optional[dict] = None
    messages: Optional[list] = None  # PagerDuty v3 webhook uses "messages"

class PagerDutyIncident(BaseModel):
    """Normalized PagerDuty incident."""
    id: str = ""
    title: str = ""
    severity: str = "critical"
    description: str = ""
    url: str = ""

def parse_pagerduty_payload(payload: PagerDutyWebhookPayload) -> list[PagerDutyIncident]:
    """Parse a PagerDuty webhook payload into one or more incidents."""
    incidents = []

    # PagerDuty v3 webhook format (messages array)
    if payload.messages:
        for msg in payload.messages:
            incident_data = msg.get("incident", msg)
            pd_id = incident_data.get("id", "") or incident_data.get("incident_number", "")
            pd_title = incident_data.get("title", "") or incident_data.get("summary", "")
            pd_severity = incident_data.get("severity", "critical") or incident_data.get("urgency", "high")
            # Map PagerDuty severity
            if pd_severity in ("low", "info"):
                pd_severity = "low"
            elif pd_severity in ("high", "urgent", "critical"):
                pd_severity = "critical"
            else:
                pd_severity = "medium"

            # Build description from available fields
            pd_desc = incident_data.get("description", "") or incident_data.get("body", {}).get("details", "")
            if not pd_desc:
                pd_desc = incident_data.get("details", "") or incident_data.get("trigger_summary_data", {}).get("subject", "")

            pd_url = incident_data.get("html_url", "") or incident_data.get("url", "")

            incidents.append(PagerDutyIncident(
                id=str(pd_id),
                title=str(pd_title),
                severity=str(pd_severity),
                description=str(pd_desc),
                url=str(pd_url)
            ))

    # PagerDuty v2 webhook format (top-level event)
    elif payload.incident:
        inc = payload.incident
        pd_id = inc.get("id", "") or inc.get("incident_number", "")
        pd_title = inc.get("title", "") or inc.get("summary", "")
        pd_severity = inc.get("severity", "critical") or inc.get("urgency", "high")
        if pd_severity in ("low", "info"):
            pd_severity = "low"
        elif pd_severity in ("high", "urgent", "critical"):
            pd_severity = "critical"
        else:
            pd_severity = "medium"
        pd_desc = inc.get("description", "") or inc.get("body", {}).get("details", "")
        pd_url = inc.get("html_url", "") or inc.get("url", "")

        incidents.append(PagerDutyIncident(
            id=str(pd_id),
            title=str(pd_title),
            severity=str(pd_severity),
            description=str(pd_desc),
            url=str(pd_url)
        ))

    return incidents


@app.post("/pagerduty")
def pagerduty_webhook(payload: PagerDutyWebhookPayload):
    """
    Webhook endpoint for PagerDuty.
    Receives PagerDuty alerts and returns AEGIS diagnosis.

    Configure in PagerDuty:
      1. Go to Integrations → Generic Webhooks (v3)
      2. Add webhook URL: https://your-server.com/pagerduty
      3. Select "incident.triggered" event
    """
    incidents = parse_pagerduty_payload(payload)
    if not incidents:
        raise HTTPException(status_code=400, detail="No incidents found in PagerDuty payload")

    results = []
    for inc in incidents:
        # Create an AlertRequest from the PagerDuty incident
        alert = AlertRequest(
            source="pagerduty",
            severity=inc.severity,
            title=inc.title or f"PagerDuty Incident #{inc.id}",
            description=inc.description or inc.title,
            metadata={"pagerduty_id": inc.id, "pagerduty_url": inc.url}
        )

        # Route and diagnose
        level = route_severity(alert.severity, alert.description)
        if level == "L1/L2":
            result = handle_l1_l2(alert)
        else:
            result = handle_l3_l4(alert)

        results.append(DiagnosisResponse(
            timestamp=datetime.utcnow().isoformat(),
            source="pagerduty",
            severity=alert.severity,
            **result
        ).model_dump())

    return {"incidents": results}

# ── Stats endpoint (for debugging) ────────────────────────────

@app.get("/stats")
def classifier_stats():
    """Show classifier statistics (for debugging)."""
    return {
        "total_tickets": stats["total"],
        "categories": stats["categories"],
        "classifier_info": {
            "model": "all-MiniLM-L6-v2",
            "database": "./tickets_db",
            "dataset": DATASET_PATH,
            "threshold": 0.45,
            "method": "hybrid (vector + keyword fallback)"
        }
    }

# ── Run ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🛡️ AEGIS Integration Module v2.0")
    print("=" * 50)
    print(f"ChromaDB classifier: {stats['total']} tickets in {len(stats['categories'])} categories")
    print(f"L3/L4 patterns: AEGIS_PATTERNS.md")
    print(f"Starting server on http://localhost:8000")
    print(f"API docs available at http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)