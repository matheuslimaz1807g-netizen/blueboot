"""add session_string_enc column to client_configs

Revision ID: 004
Revises: 003
Create Date: 2026-05-05 16:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "client_configs",
        sa.Column("session_string_enc", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_configs", "session_string_enc")
