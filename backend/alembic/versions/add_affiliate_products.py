"""add affiliate_products table

Revision ID: c7d8e9f0a1b2
Revises: 5da6e6d999e9
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7d8e9f0a1b2'
down_revision = '5da6e6d999e9'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'affiliate_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ml_code', sa.String(), nullable=True),
        sa.Column('affiliate_url', sa.String(), unique=True, nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('commission_pct', sa.Float(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

def downgrade():
    op.drop_table('affiliate_products')
