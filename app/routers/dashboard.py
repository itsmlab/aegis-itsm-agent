"""
AEGIS SaaS — Web dashboard for tenants.
Serves an HTML page with usage stats, health check, recent activity,
category distribution, and accuracy metrics (if available).

Access: GET /dashboard
Auth:   Requires X-API-Key header (same as API endpoints)
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_tenant
from app.models import Tenant, UsageRecord
from app.services.classifier_service import classifier_service
from app.services.orchestrator_service import orchestrator_service
from app.services.billing_service import billing_service

router = APIRouter(tags=["Dashboard"])

# ── Templates ─────────────────────────────────────────────────

templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# ── Accuracy file path ────────────────────────────────────────
# Optional: if an accuracy report JSON exists, show it on the dashboard
ACCURACY_REPORT_PATH = settings.PROJECT_ROOT / "scripts" / "accuracy_report.json"


def load_accuracy_report() -> dict | None:
    """Load accuracy metrics from a JSON report file, if it exists."""
    if ACCURACY_REPORT_PATH.exists():
        import json
        try:
            with open(ACCURACY_REPORT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


# ── Dashboard endpoint ────────────────────────────────────────


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Serve the AEGIS web dashboard for the authenticated tenant.

    Shows:
      - Usage statistics (total, monthly, tokens)
      - System health check
      - Category distribution (bar chart)
      - Recent activity (last 20 requests)
      - Accuracy metrics (if available)
    """
    # ── Usage stats ───────────────────────────────────────────
    usage = billing_service.get_usage(db, tenant.id)

    # Plan limit display
    plan_limit = None
    if tenant.plan == "shield":
        plan_limit = settings.SHIELD_MAX_INCIDENTS_PER_MONTH

    # ── Health check ──────────────────────────────────────────
    patterns_ok = settings.PATTERNS_FILE.exists()
    health = {
        "status": "healthy",
        "tenant": tenant.slug,
        "plan": tenant.plan,
        "classifier_tickets": classifier_service.get_global_stats()["total_tickets"],
        "patterns_file": "found" if patterns_ok else "missing",
        "llm_provider": orchestrator_service.get_provider_name(),
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ── Classifier stats ──────────────────────────────────────
    try:
        classifier_stats = classifier_service.get_stats(tenant.id)
    except Exception:
        # Fallback if get_stats fails (e.g., collection not ready)
        classifier_stats = {"total": 0, "categories": {}}

    # ── Recent activity (last 20) ─────────────────────────────
    recent_records = (
        db.query(UsageRecord)
        .filter(UsageRecord.tenant_id == tenant.id)
        .order_by(desc(UsageRecord.timestamp))
        .limit(20)
        .all()
    )
    recent_activity = [
        {
            "timestamp": r.timestamp.isoformat(),
            "endpoint": r.endpoint,
            "tokens_used": r.tokens_used,
            "status_code": r.status_code,
        }
        for r in recent_records
    ]

    # ── Accuracy metrics (optional) ───────────────────────────
    accuracy = load_accuracy_report()

    # ── Render template ───────────────────────────────────────
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "tenant": tenant,
            "usage": usage,
            "plan_limit": plan_limit,
            "health": health,
            "classifier_stats": classifier_stats,
            "recent_activity": recent_activity,
            "accuracy": accuracy,
        },
    )
