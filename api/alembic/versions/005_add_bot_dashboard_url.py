"""add bot_dashboard_url column to client_configs

Revision ID: 005
Revises: 004
Create Date: 2026-05-05 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "client_configs",
        sa.Column("bot_dashboard_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_configs", "bot_dashboard_url")
