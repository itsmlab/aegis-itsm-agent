"""
AEGIS SaaS — Metrics endpoint.

Provides:
  - GET /metrics: JSON snapshot of system and business metrics
    (request counts, latencies, classification stats, LLM usage, per-tenant data)

Access:  GET /metrics
Auth:    Optional (uses get_current_tenant if available, but works without auth)
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_current_tenant
from app.models import Tenant
from app.logging_config import metrics_collector, get_logger

router = APIRouter(tags=["Metrics"])
logger = get_logger(__name__)


@router.get("/metrics")
def get_metrics(tenant: Tenant = Depends(get_current_tenant)):
    """
    Return a JSON snapshot of system and business metrics.

    Includes:
      - Uptime
      - Request counts, error rates, and average latencies per endpoint
      - Classification counts and average confidence per category
      - LLM call counts, token usage, and average latency
      - Per-tenant request and error counts
    """
    metrics = metrics_collector.snapshot()
    metrics["tenant"] = tenant.slug

    logger.info("Metrics requested", extra={
        "tenant_id": tenant.id,
        "total_requests": metrics["total_requests"],
    })

    return JSONResponse(content=metrics)
