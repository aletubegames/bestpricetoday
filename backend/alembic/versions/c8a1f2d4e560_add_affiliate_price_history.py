"""add_affiliate_price_history

Revision ID: c8a1f2d4e560
Revises: b3f094352350
Create Date: 2026-06-30 03:00:00.000000

Cria tabela affiliate_price_history para histórico de preços
de produtos afiliados (ML + Amazon). Cada scrape salva um snapshot.
Retenção: 2 anos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8a1f2d4e560'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'affiliate_price_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('affiliate_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index('ix_affiliate_price_history_product_id', 'affiliate_price_history', ['product_id'])
    op.create_index('ix_affiliate_price_history_provider', 'affiliate_price_history', ['provider'])
    op.create_index('ix_affiliate_price_history_recorded_at', 'affiliate_price_history', ['recorded_at'])


def downgrade() -> None:
    op.drop_index('ix_affiliate_price_history_recorded_at', table_name='affiliate_price_history')
    op.drop_index('ix_affiliate_price_history_provider', table_name='affiliate_price_history')
    op.drop_index('ix_affiliate_price_history_product_id', table_name='affiliate_price_history')
    op.drop_table('affiliate_price_history')
