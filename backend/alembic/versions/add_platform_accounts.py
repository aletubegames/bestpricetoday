"""add youtube instagram facebook accounts and platform_metadata

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = None  # ajuste para o último revision existente
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'youtube_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), unique=True, nullable=False),
        sa.Column('channel_title', sa.String(), nullable=True),
        sa.Column('channel_url', sa.String(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.String(), nullable=True),
        sa.Column('publishes_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'instagram_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('instagram_id', sa.String(), unique=True, nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('profile_url', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('publishes_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'facebook_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('page_id', sa.String(), unique=True, nullable=False),
        sa.Column('page_name', sa.String(), nullable=True),
        sa.Column('page_url', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('publishes_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    # Adicionar colunas em admin_videos
    op.add_column('admin_videos', sa.Column('instagram_media_id', sa.String(), nullable=True))
    op.add_column('admin_videos', sa.Column('instagram_short_link', sa.String(), nullable=True))
    op.add_column('admin_videos', sa.Column('facebook_post_id', sa.String(), nullable=True))
    op.add_column('admin_videos', sa.Column('facebook_short_link', sa.String(), nullable=True))
    op.add_column('admin_videos', sa.Column('platform_metadata', postgresql.JSON(), nullable=True))


def downgrade():
    op.drop_table('youtube_accounts')
    op.drop_table('instagram_accounts')
    op.drop_table('facebook_accounts')
    op.drop_column('admin_videos', 'instagram_media_id')
    op.drop_column('admin_videos', 'instagram_short_link')
    op.drop_column('admin_videos', 'facebook_post_id')
    op.drop_column('admin_videos', 'facebook_short_link')
    op.drop_column('admin_videos', 'platform_metadata')
