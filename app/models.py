"""
AEGIS SaaS — SQLAlchemy ORM models for multi-tenant operational data.

Models:
  - Tenant: each customer organization
  - ApiKey: authentication keys per tenant
  - UsageRecord: billing/usage tracking per request
"""

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="shield")  # shield, guard, fortress
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.slug} ({self.plan})>"


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True)  # UUID
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    prefix = Column(String(10), nullable=False)  # e.g. "aeg_live_" — first chars of key
    key_hash = Column(String(128), nullable=False)  # SHA-256 hash of full key
    name = Column(String(255), nullable=False, default="default")
    role = Column(String(20), nullable=False, default="api")  # "admin" or "api"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="api_keys")

    @staticmethod
    def generate_key() -> tuple[str, str]:
        """
        Generate a new API key and return (full_key, key_hash).
        The full key is shown only once to the user.
        """
        raw = secrets.token_hex(32)  # 64 hex chars
        prefix = "aeg_live_"
        full_key = f"{prefix}{raw}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, key_hash

    @staticmethod
    def hash_key(full_key: str) -> str:
        """Hash a full API key for comparison."""
        return hashlib.sha256(full_key.encode()).hexdigest()

    def __repr__(self):
        return f"<ApiKey {self.prefix}... ({self.tenant_id})>"


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    incident_count = Column(Integer, default=1, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    status_code = Column(Integer, nullable=True)

    tenant = relationship("Tenant", back_populates="usage_records")

    def __repr__(self):
        return f"<UsageRecord {self.tenant_id} @ {self.timestamp}>"