"""add bot enabled flag

Revision ID: 011
Revises: 010
Create Date: 2026-05-25 20:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_configs",
        sa.Column("bot_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("client_configs", "bot_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("client_configs", "bot_enabled")
