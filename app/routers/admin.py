"""
AEGIS SaaS — Admin endpoints for tenant and API key management.
These are internal/admin endpoints (not exposed to end customers).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tenant, ApiKey
from app.services.billing_service import billing_service

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


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
def create_tenant(req: CreateTenantRequest, db: Session = Depends(get_db)):
    """Create a new tenant and generate an API key."""
    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == req.slug).first()
    if existing:
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
    db: Session = Depends(get_db),
):
    """Generate a new API key for an existing tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    full_key, key_hash = ApiKey.generate_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        prefix=full_key[:10],
        key_hash=key_hash,
        name=name,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyResponse(
        api_key_id=api_key.id,
        prefix=api_key.prefix,
        name=api_key.name,
        full_key=full_key,
    )


@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
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
def get_tenant_usage(tenant_id: str, db: Session = Depends(get_db)):
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