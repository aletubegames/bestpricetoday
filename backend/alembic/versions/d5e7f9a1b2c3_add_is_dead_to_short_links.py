"""add is_dead to short_links

Revision ID: d5e7f9a1b2c3
Revises: c8a1f2d4e560
Create Date: 2026-06-30 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "d5e7f9a1b2c3"
down_revision = "c8a1f2d4e560"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("short_links", sa.Column("is_dead", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("short_links", sa.Column("dead_reported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("short_links", "dead_reported_at")
    op.drop_column("short_links", "is_dead")
