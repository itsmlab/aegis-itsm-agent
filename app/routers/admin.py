"""
ITSMLab — Admin endpoints for tenant and API key management.
These are internal/admin endpoints (not exposed to end customers).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_admin_tenant
from app.models import Tenant, ApiKey
from app.services.billing_service import billing_service
from app.logging_config import get_logger

router = APIRouter(prefix="/v1/admin", tags=["Admin"])
logger = get_logger(__name__)


# ── Request / Response models ─────────────────────────────────


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    plan: str = "shield"  # shield, guard, fortress


class CreateTenantResponse(BaseModel):
    tenant_id: str
    name: str
    slug: str
    plan: str
    api_key: str  # shown only once


class ApiKeyResponse(BaseModel):
    api_key_id: str
    prefix: str
    name: str
    full_key: str  # shown only once


class UsageResponse(BaseModel):
    tenant_id: str
    slug: str
    plan: str
    total_incidents: int
    monthly_incidents: int
    total_tokens_used: int


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/tenants", response_model=CreateTenantResponse)
def create_tenant(
    req: CreateTenantRequest,
    request: Request,
    db: Session = Depends(get_db),
    _admin: Tenant = Depends(get_admin_tenant),
):
    """Create a new tenant and generate an API key."""
    request_id = getattr(request.state, "request_id", "unknown")

    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == req.slug).first()
    if existing:
        logger.warning("Tenant slug already exists", extra={
            "request_id": request_id,
            "slug": req.slug,
        })
        raise HTTPException(status_code=409, detail=f"Tenant slug '{req.slug}' already exists")

    if req.plan not in ("shield", "guard", "fortress"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan '{req.plan}'. Must be: shield, guard, or fortress"
        )

    # Create tenant
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=req.name,
        slug=req.slug,
        plan=req.plan,
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    # Generate API key
    full_key, key_hash = ApiKey.generate_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        prefix=full_key[:10],
        key_hash=key_hash,
        name="default",
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(tenant)

    logger.info("Tenant created", extra={
        "request_id": request_id,
        "tenant_id": tenant.id,
        "slug": tenant.slug,
        "plan": tenant.plan,
    })

    return CreateTenantResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        api_key=full_key,
    )


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(
    tenant_id: str,
    name: str = "default",
    role: str = "api",
    request: Request = None,
    db: Session = Depends(get_db),
    _admin: Tenant = Depends(get_admin_tenant),
):
    """Generate a new API key for an existing tenant.

    Args:
        tenant_id: UUID of the tenant.
        name: Human-readable name for the key.
        role: "api" for regular API access, "admin" for admin-level access.
    """
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"

    if role not in ("api", "admin"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Must be 'api' or 'admin'.",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        logger.warning("Tenant not found for API key creation", extra={
            "request_id": request_id,
            "tenant_id": tenant_id,
        })
        raise HTTPException(status_code=404, detail="Tenant not found")

    full_key, key_hash = ApiKey.generate_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        prefix=full_key[:10],
        key_hash=key_hash,
        name=name,
        role=role,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info("API key created", extra={
        "request_id": request_id,
        "tenant_id": tenant.id,
        "prefix": api_key.prefix,
        "role": role,
    })

    return ApiKeyResponse(
        api_key_id=api_key.id,
        prefix=api_key.prefix,
        name=api_key.name,
        full_key=full_key,
    )


@router.get("/tenants")
def list_tenants(
    db: Session = Depends(get_db),
    _admin: Tenant = Depends(get_admin_tenant),
):
    """List all tenants."""
    tenants = db.query(Tenant).all()
    return {
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "plan": t.plan,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
            }
            for t in tenants
        ]
    }


@router.get("/usage/{tenant_id}", response_model=UsageResponse)
def get_tenant_usage(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: Tenant = Depends(get_admin_tenant),
):
    """Get usage statistics for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    usage = billing_service.get_usage(db, tenant_id)
    return UsageResponse(
        tenant_id=tenant.id,
        slug=tenant.slug,
        plan=tenant.plan,
        **usage,
    )
