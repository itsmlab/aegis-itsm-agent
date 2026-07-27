"""
ITSMLab — Database connection and session management.
Uses PostgreSQL (via psycopg2) by default, with automatic SQLite fallback
for local development when PostgreSQL is not available.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger("itsmlab.database")

# ── Engine creation with automatic fallback ────────────────────

_engine = None
_SessionLocal = None
Base = declarative_base()


def _create_postgres_engine():
    """Create a PostgreSQL engine."""
    return create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


def _create_sqlite_engine():
    """Create a SQLite engine for local development."""
    sqlite_path = settings.PROJECT_ROOT / "itsmlab_dev.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    logger.info(f"📁 Using SQLite fallback: {sqlite_path}")
    return create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
    )


def get_engine():
    """Get the database engine, creating it on first access with fallback."""
    global _engine
    if _engine is not None:
        return _engine

    # Try PostgreSQL first
    try:
        _engine = _create_postgres_engine()
        # Test connection
        with _engine.connect() as conn:
            conn.execute(conn.default_schema_name or "SELECT 1")
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL not available ({e}), falling back to SQLite")
        _engine = _create_sqlite_engine()

    return _engine


def get_session_local():
    """Get the sessionmaker, creating it on first access."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db():
    """FastAPI dependency — yields a database session."""
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call on startup."""
    Base.metadata.create_all(bind=get_engine())
