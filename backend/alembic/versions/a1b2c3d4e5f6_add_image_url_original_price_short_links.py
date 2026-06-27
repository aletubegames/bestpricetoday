"""add image_url and original_price to short_links

Revision ID: a1b2c3d4e5f6
Revises: b3f094352350
Create Date: 2026-06-27 03:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'b3f094352350'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('short_links', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('short_links', sa.Column('original_price', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('short_links', 'original_price')
    op.drop_column('short_links', 'image_url')
