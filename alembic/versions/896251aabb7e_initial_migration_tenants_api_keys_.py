"""Initial migration: tenants, api_keys, usage_records

Revision ID: 896251aabb7e
Revises: 
Create Date: 2026-06-25 18:07:16.246991
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '896251aabb7e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tenants table ─────────────────────────────────────────
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='shield'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── API Keys table ────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('prefix', sa.String(10), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False),
        sa.Column('name', sa.String(255), nullable=False, server_default='default'),
        sa.Column('role', sa.String(20), nullable=False, server_default='api'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )

    # ── Usage Records table ───────────────────────────────────
    op.create_table(
        'usage_records',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(36),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True,
                  server_default=sa.func.now()),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('incident_count', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status_code', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('usage_records')
    op.drop_table('api_keys')
    op.drop_table('tenants')
