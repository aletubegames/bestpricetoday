"""add coupons table

Revision ID: e6f8a0b1c3d4
Revises: d5e7f9a1b2c3
Create Date: 2026-06-30 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "e6f8a0b1c3d4"
down_revision = "d5e7f9a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "coupons",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("store_name", sa.String(), nullable=True),
        sa.Column("coupon_code", sa.String(), nullable=False),
        sa.Column("discount_text", sa.String(), nullable=True),
        sa.Column("discount_percent", sa.Float(), nullable=True),
        sa.Column("discount_value", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budget_remaining", sa.String(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("product_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_coupons_provider", "coupons", ["provider"])
    op.create_index("ix_coupons_store_name", "coupons", ["store_name"])
    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])


def downgrade():
    op.drop_index("ix_coupons_is_active", table_name="coupons")
    op.drop_index("ix_coupons_store_name", table_name="coupons")
    op.drop_index("ix_coupons_provider", table_name="coupons")
    op.drop_table("coupons")
