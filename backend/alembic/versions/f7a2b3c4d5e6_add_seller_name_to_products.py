"""add seller_name to products

Revision ID: f7a2b3c4d5e6
Revises: e6f8a0b1c3d4
Create Date: 2026-06-30 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f7a2b3c4d5e6"
down_revision = "e6f8a0b1c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("seller_name", sa.String(), nullable=True))
    op.add_column("affiliate_products", sa.Column("seller_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "seller_name")
    op.drop_column("affiliate_products", "seller_name")
