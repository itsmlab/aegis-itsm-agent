"""Alembic environment configuration for ITSMLab SaaS.

Uses the same database connection logic as the application:
PostgreSQL first, with automatic fallback to SQLite.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Add the project root to sys.path so we can import app modules
# This is needed because Alembic runs from the alembic/ directory
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Alembic Config object
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.database import Base
from app.models import Tenant, ApiKey, UsageRecord  # noqa: F401

target_metadata = Base.metadata


def get_url() -> str:
    """
    Get the database URL with the same fallback logic as the application.

    Tries PostgreSQL first. If it fails, falls back to SQLite.
    This mirrors the logic in app/database.py.
    """
    from app.config import settings

    # Try PostgreSQL
    pg_url = str(settings.DATABASE_URL)
    try:
        from sqlalchemy import create_engine as _ce
        test_engine = _ce(pg_url)
        test_engine.connect().close()
        test_engine.dispose()
        return pg_url
    except Exception:
        pass

    # Fallback to SQLite
    db_path = os.path.join(_project_root, "aegis_dev.db")
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()

    # SQLite needs check_same_thread=False for Alembic
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
