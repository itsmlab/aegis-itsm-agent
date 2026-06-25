"""
AEGIS SaaS — Billing and usage tracking service.
Tracks incident count per tenant and enforces plan limits.
"""

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models import Tenant, UsageRecord
from app.logging_config import get_logger

logger = get_logger(__name__)


class BillingService:
    """
    Tracks API usage per tenant and enforces plan limits.

    Plans:
      - shield:   up to SHIELD_MAX_INCIDENTS_PER_MONTH (default 50)
      - guard:    unlimited
      - fortress: unlimited
    """

    def record_usage(
        self,
        db: Session,
        tenant: Tenant,
        endpoint: str,
        tokens_used: int = 0,
        status_code: int = 200,
    ):
        """Record a usage event for the given tenant."""
        record = UsageRecord(
            tenant_id=tenant.id,
            timestamp=datetime.utcnow(),
            endpoint=endpoint,
            incident_count=1,
            tokens_used=tokens_used,
            status_code=status_code,
        )
        db.add(record)
        db.commit()

        logger.debug("Usage recorded", extra={
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "endpoint": endpoint,
            "tokens_used": tokens_used,
            "status_code": status_code,
        })

    def check_quota(self, db: Session, tenant: Tenant):
        """
        Check if the tenant has exceeded their monthly quota.
        Raises HTTPException 429 if quota is exceeded.
        """
        if tenant.plan == "fortress" or tenant.plan == "guard":
            return  # Unlimited

        if tenant.plan == "shield":
            max_incidents = settings.SHIELD_MAX_INCIDENTS_PER_MONTH
        else:
            return  # Unknown plan, allow

        # Count incidents this month
        now = datetime.utcnow()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        count = db.query(func.count(UsageRecord.id)).filter(
            UsageRecord.tenant_id == tenant.id,
            UsageRecord.timestamp >= first_of_month,
        ).scalar() or 0

        if count >= max_incidents:
            logger.warning("Monthly quota exceeded", extra={
                "tenant_id": tenant.id,
                "tenant_slug": tenant.slug,
                "plan": tenant.plan,
                "count": count,
                "max": max_incidents,
            })
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Monthly incident limit reached ({count}/{max_incidents}). "
                    f"Upgrade from Shield to Guard for unlimited incidents."
                ),
            )

    def get_usage(self, db: Session, tenant_id: str) -> dict:
        """Get usage statistics for a tenant."""
        now = datetime.utcnow()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = db.query(func.count(UsageRecord.id)).filter(
            UsageRecord.tenant_id == tenant_id,
        ).scalar() or 0

        monthly = db.query(func.count(UsageRecord.id)).filter(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.timestamp >= first_of_month,
        ).scalar() or 0

        total_tokens = db.query(func.sum(UsageRecord.tokens_used)).filter(
            UsageRecord.tenant_id == tenant_id,
        ).scalar() or 0

        return {
            "total_incidents": total,
            "monthly_incidents": monthly,
            "total_tokens_used": int(total_tokens),
        }


# Singleton
billing_service = BillingService()
