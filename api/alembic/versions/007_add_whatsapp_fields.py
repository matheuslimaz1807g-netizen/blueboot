"""add whatsapp fields

Revision ID: add_whatsapp_fields
Revises: 
Create Date: 2026-05-06 13:56:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    # Adiciona as colunas se elas não existirem
    # Usamos batch_alter_table para compatibilidade
    op.add_column('licenses', sa.Column('whatsapp_status', sa.String(length=32), nullable=True))
    op.add_column('licenses', sa.Column('whatsapp_qr', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('licenses', 'whatsapp_qr')
    op.drop_column('licenses', 'whatsapp_status')
