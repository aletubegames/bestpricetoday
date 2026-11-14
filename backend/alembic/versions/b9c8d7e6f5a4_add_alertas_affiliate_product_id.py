"""add alertas.affiliate_product_id (alerta Telegram por produto afiliado)

Revision ID: b9c8d7e6f5a4
Revises: a8b3c4d5e6f7
Create Date: 2026-11-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "b9c8d7e6f5a4"
down_revision = "a8b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alertas",
        sa.Column("affiliate_product_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_alertas_affiliate_product_id",
        "alertas",
        "affiliate_products",
        ["affiliate_product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_alertas_affiliate_product_id",
        "alertas",
        ["affiliate_product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_alertas_affiliate_product_id", table_name="alertas")
    op.drop_constraint("fk_alertas_affiliate_product_id", "alertas", type_="foreignkey")
    op.drop_column("alertas", "affiliate_product_id")
