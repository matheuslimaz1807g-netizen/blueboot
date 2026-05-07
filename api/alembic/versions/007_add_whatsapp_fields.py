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
    # Verifica se as colunas já existem antes de tentar adicionar
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('licenses')]
    
    if 'whatsapp_status' not in columns:
        op.add_column('licenses', sa.Column('whatsapp_status', sa.String(length=32), nullable=True))
    
    if 'whatsapp_qr' not in columns:
        op.add_column('licenses', sa.Column('whatsapp_qr', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('licenses', 'whatsapp_qr')
    op.drop_column('licenses', 'whatsapp_status')
