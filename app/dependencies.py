"""
AEGIS SaaS — FastAPI dependencies for multi-tenant authentication and rate limiting.

Provides:
  - get_current_tenant: extracts API key from X-API-Key header, resolves tenant
  - get_admin_tenant: validates admin API key for admin endpoints
  - rate_limit_check: checks per-tenant rate limits and adds X-RateLimit-* headers
  - get_llm: returns the configured LLMProvider singleton
"""

import uuid
from fastapi import Header, HTTPException, Depends, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Tenant, ApiKey
from app.services.rate_limit_service import rate_limit_service


async def get_current_tenant(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Dependency that resolves the tenant from the X-API-Key header.

    If AUTH_REQUIRED is False (dev mode), returns the default tenant.
    If AUTH_REQUIRED is True, validates the API key and returns the tenant.

    Raises 401 if the key is invalid, inactive, or missing when auth is required.
    """
    # ── Dev mode: skip auth ──────────────────────────────────
    if not settings.AUTH_REQUIRED:
        tenant = db.query(Tenant).filter(
            Tenant.slug == settings.DEFAULT_TENANT_ID
        ).first()
        if not tenant:
            # Auto-create default tenant on first run
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Default Tenant",
                slug=settings.DEFAULT_TENANT_ID,
                plan="guard",
                is_active=True,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        return tenant

    # ── Auth mode: validate API key ──────────────────────────
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. Provide a valid API key.",
        )

    key_hash = ApiKey.hash_key(x_api_key)
    api_key_record = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True,
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key.",
        )

    tenant = db.query(Tenant).filter(
        Tenant.id == api_key_record.tenant_id,
        Tenant.is_active == True,
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Tenant is inactive or not found.",
        )

    # Update last_used_at
    from datetime import datetime
    api_key_record.last_used_at = datetime.utcnow()
    db.commit()

    return tenant


async def get_admin_tenant(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Dependency for admin-only endpoints.

    In dev mode (AUTH_REQUIRED=False), returns the default tenant without checks.
    In production mode, validates that the API key exists, is active, and has
    role='admin'. Also accepts the master ADMIN_API_KEY from settings for
    bootstrapping. Raises 401 if any check fails.
    """
    # ── Dev mode: skip auth ──────────────────────────────────
    if not settings.AUTH_REQUIRED:
        tenant = db.query(Tenant).filter(
            Tenant.slug == settings.DEFAULT_TENANT_ID
        ).first()
        if not tenant:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Default Tenant",
                slug=settings.DEFAULT_TENANT_ID,
                plan="guard",
                is_active=True,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        return tenant

    # ── Auth mode: validate admin API key ────────────────────
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. Admin access requires a valid admin API key.",
        )

    # Check master admin key first (for bootstrapping)
    if settings.ADMIN_API_KEY and x_api_key == settings.ADMIN_API_KEY:
        # Return a pseudo-tenant for the admin bootstrap flow
        tenant = db.query(Tenant).filter(
            Tenant.slug == settings.DEFAULT_TENANT_ID
        ).first()
        if not tenant:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Default Tenant",
                slug=settings.DEFAULT_TENANT_ID,
                plan="guard",
                is_active=True,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        return tenant

    key_hash = ApiKey.hash_key(x_api_key)
    api_key_record = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True,
        ApiKey.role == "admin",
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid, inactive, or non-admin API key.",
        )

    tenant = db.query(Tenant).filter(
        Tenant.id == api_key_record.tenant_id,
        Tenant.is_active == True,
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Tenant is inactive or not found.",
        )

    # Update last_used_at
    from datetime import datetime
    api_key_record.last_used_at = datetime.utcnow()
    db.commit()

    return tenant


async def rate_limit_check(
    tenant: Tenant = Depends(get_current_tenant),
) -> tuple[Tenant, dict]:
    """
    Dependency that checks per-tenant rate limits.

    Must be used AFTER get_current_tenant (or get_admin_tenant).
    Returns a tuple of (tenant, rate_limit_headers) so the endpoint
    can add the headers to the response.

    Raises 429 Too Many Requests if the rate limit is exceeded.
    """
    allowed, headers = rate_limit_service.check_rate_limit(tenant.id, tenant.plan)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Limit: {headers['X-RateLimit-Limit']} requests per hour. Try again after the reset time.",
                "rate_limit": headers,
            },
            headers=headers,
        )

    return tenant, headers


class UsageContext:
    """Holds information about the current request context."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.tenant_id = tenant.id
        self.plan = tenant.plan
