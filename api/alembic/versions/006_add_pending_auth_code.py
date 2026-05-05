"""add pending_auth_code columns to licenses

Revision ID: 006
Revises: 005
Create Date: 2026-05-05 20:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("licenses", sa.Column("pending_code", sa.String(32), nullable=True))
    op.add_column("licenses", sa.Column("pending_password", sa.String(256), nullable=True))
    op.add_column("licenses", sa.Column("pending_code_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("licenses", "pending_code_at")
    op.drop_column("licenses", "pending_password")
    op.drop_column("licenses", "pending_code")
