"""add offer_filter_enabled column to client_configs

Revision ID: 013
Revises: 012
Create Date: 2026-06-11 10:46:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client_configs",
        sa.Column("offer_filter_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade():
    op.drop_column("client_configs", "offer_filter_enabled")