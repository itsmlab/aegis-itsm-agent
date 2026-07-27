"""
ITSMLab — Pytest configuration and shared fixtures.

Provides:
  - test_client: FastAPI TestClient with a temporary SQLite database
  - test_db: SQLAlchemy session for direct DB access in tests
  - default_tenant: a pre-created Tenant for use in tests
  - admin_api_key: a pre-created admin API key
  - sample_alert: a standard L1/L2 alert payload
  - sample_critical_alert: a standard L3/L4 alert payload
"""

import os
import uuid
import tempfile
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ── Override database BEFORE importing app modules ────────────
# We need to monkey-patch the database module so that tests use
# a temporary SQLite database instead of the configured one.

from app import database as db_module

# Create a temporary file for the test database so that all connections
# (including those from different threads/sessions) see the same data.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
_test_engine = create_engine(
    f"sqlite:///{_db_path}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Single connection, shared across all sessions
)

# Replace the global engine and sessionmaker
db_module._engine = _test_engine
db_module._SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)

# Import models so SQLAlchemy knows about them, then create all tables
from app.models import Tenant, ApiKey, UsageRecord  # noqa: E402, F401
from app.database import Base  # noqa: E402
Base.metadata.create_all(bind=_test_engine)


# ── Helpers ───────────────────────────────────────────────────


def _clear_tables():
    """Delete all rows from all tables (but keep the tables)."""
    with _test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_db():
    """Automatically clean all tables before each test."""
    _clear_tables()
    yield


@pytest.fixture
def test_db():
    """Provide a clean database session for each test."""
    session = db_module._SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient with the temporary database."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def default_tenant(test_db: Session):
    """Create and return a default tenant."""
    from app.models import Tenant
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant",
        slug="test-tenant",
        plan="guard",
        is_active=True,
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant


@pytest.fixture
def shield_tenant(test_db: Session):
    """Create and return a Shield-plan tenant (limited quota)."""
    from app.models import Tenant
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Shield Tenant",
        slug="shield-tenant",
        plan="shield",
        is_active=True,
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant


@pytest.fixture
def admin_api_key(test_db: Session, default_tenant):
    """Create and return an admin API key for the default tenant."""
    from app.models import ApiKey
    full_key, key_hash = ApiKey.generate_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=default_tenant.id,
        prefix=full_key[:10],
        key_hash=key_hash,
        name="test-admin-key",
        role="admin",
        is_active=True,
    )
    test_db.add(api_key)
    test_db.commit()
    return full_key


@pytest.fixture
def regular_api_key(test_db: Session, default_tenant):
    """Create and return a regular API key for the default tenant."""
    from app.models import ApiKey
    full_key, key_hash = ApiKey.generate_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        tenant_id=default_tenant.id,
        prefix=full_key[:10],
        key_hash=key_hash,
        name="test-api-key",
        role="api",
        is_active=True,
    )
    test_db.add(api_key)
    test_db.commit()
    return full_key


@pytest.fixture
def sample_alert() -> dict:
    """Standard L1/L2 alert payload."""
    return {
        "source": "manual",
        "severity": "low",
        "title": "User cannot log in",
        "description": "User gets 403 error when accessing the application",
    }


@pytest.fixture
def sample_critical_alert() -> dict:
    """Standard L3/L4 critical alert payload."""
    return {
        "source": "pagerduty",
        "severity": "critical",
        "title": "Database failover failure",
        "description": "Primary database is down, failover to replica failed. Error 500 on all write operations.",
    }


# ── Cleanup ───────────────────────────────────────────────────


def pytest_unconfigure(config):
    """Remove the temporary database file after all tests."""
    global _db_fd, _db_path
    try:
        os.close(_db_fd)
    except OSError:
        pass
    try:
        os.unlink(_db_path)
    except OSError:
        pass
