"""add note and pending machines

Revision ID: 003
Revises: 002
Create Date: 2026-05-03 13:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Adicionar coluna note na tabela licenses
    op.add_column('licenses', sa.Column('note', sa.String(length=256), nullable=True))
    
    # Criar tabela pending_machines se não existir
    op.create_table('pending_machines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('machine_id', sa.String(length=128), nullable=False),
        sa.Column('hostname', sa.String(length=256), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('platform', sa.String(length=64), nullable=True),
        sa.Column('label', sa.String(length=256), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_machines_machine_id'), 'pending_machines', ['machine_id'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_pending_machines_machine_id'), table_name='pending_machines')
    op.drop_table('pending_machines')
    op.drop_column('licenses', 'note')
