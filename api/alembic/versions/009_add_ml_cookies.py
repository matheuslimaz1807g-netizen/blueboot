"""add ml_cookies_enc to client_configs

Revision ID: 009
Revises: 008
Create Date: 2026-05-13 10:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('client_configs', sa.Column('ml_cookies_enc', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('client_configs', 'ml_cookies_enc')
