"""add affiliate_metrics_snapshots table

Revision ID: a1b2c3d4e5f6
Revises: f8a9b0c1d2e3
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'affiliate_metrics_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('period_until', sa.String(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('orders', sa.Integer(), nullable=True),
        sa.Column('estimated_earnings', sa.Float(), nullable=True),
        sa.Column('confirmed_earnings', sa.Float(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_affiliate_metrics_snapshots_provider', 'affiliate_metrics_snapshots', ['provider'])
    op.create_index('ix_affiliate_metrics_snapshots_collected_at', 'affiliate_metrics_snapshots', ['collected_at'])

def downgrade():
    op.drop_index('ix_affiliate_metrics_snapshots_collected_at', table_name='affiliate_metrics_snapshots')
    op.drop_index('ix_affiliate_metrics_snapshots_provider', table_name='affiliate_metrics_snapshots')
    op.drop_table('affiliate_metrics_snapshots')
