"""add coupon_products table

Revision ID: a8b3c4d5e6f7
Revises: f7a2b3c4d5e6
Create Date: 2026-06-30 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "a8b3c4d5e6f7"
down_revision = "f7a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coupon_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("coupon_id", UUID(as_uuid=True), sa.ForeignKey("coupons.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("product_url", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("ml_code", sa.String(), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_coupon_products_coupon_id", "coupon_products", ["coupon_id"])


def downgrade() -> None:
    op.drop_index("ix_coupon_products_coupon_id", table_name="coupon_products")
    op.drop_table("coupon_products")
