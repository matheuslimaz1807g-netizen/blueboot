"""add amazon fields to client configs

Revision ID: 012
Revises: 011
Create Date: 2026-05-27 21:38:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_configs",
        sa.Column("conv_amz", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("client_configs", "conv_amz", server_default=None)

    op.add_column(
        "client_configs",
        sa.Column("amz_cookies_enc", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_configs", "amz_cookies_enc")
    op.drop_column("client_configs", "conv_amz")
