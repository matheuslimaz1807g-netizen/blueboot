"""Add schedule_rules column to licenses table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "licenses",
        sa.Column("schedule_rules", JSONB(), nullable=True, default=dict),
    )


def downgrade() -> None:
    op.drop_column("licenses", "schedule_rules")
