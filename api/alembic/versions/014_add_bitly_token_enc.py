"""add bitly_token_enc column

Revision ID: 014
Revises: 013
Create Date: 2026-06-11 16:02:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client_configs",
        sa.Column("bitly_token_enc", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("client_configs", "bitly_token_enc")
