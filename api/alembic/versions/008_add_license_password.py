"""add license password

Revision ID: 008
Revises: 007
Create Date: 2026-05-06 16:17:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password column to licenses table
    op.add_column('licenses', sa.Column('password', sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column('licenses', 'password')
