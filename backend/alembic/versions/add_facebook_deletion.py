"""add facebook_id to users and data_deletion_requests table

Revision ID: f8a9b0c1d2e3
Revises: c7d8e9f0a1b2
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f8a9b0c1d2e3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None

def upgrade():
    # Adicionar coluna facebook_id à tabela users
    op.add_column('users', sa.Column('facebook_id', sa.String(), nullable=True, unique=True))
    op.create_index('ix_users_facebook_id', 'users', ['facebook_id'])
    
    # Adicionar coluna deleted_at à tabela users (para soft delete)
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Criar tabela data_deletion_requests
    op.create_table(
        'data_deletion_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('facebook_id', sa.String(), nullable=True),
        sa.Column('confirmation_code', sa.String(), nullable=False, unique=True),
        sa.Column('source', sa.String(), nullable=False, server_default='facebook'),
        sa.Column('status', sa.String(), nullable=False, server_default='processing'),
        sa.Column('deleted_fields', sa.JSON(), nullable=True),
        sa.Column('deletion_error', sa.String(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Criar índices para data_deletion_requests
    op.create_index('ix_data_deletion_requests_user_id', 'data_deletion_requests', ['user_id'])
    op.create_index('ix_data_deletion_requests_facebook_id', 'data_deletion_requests', ['facebook_id'])
    op.create_index('ix_data_deletion_requests_confirmation_code', 'data_deletion_requests', ['confirmation_code'])
    op.create_index('ix_data_deletion_requests_requested_at', 'data_deletion_requests', ['requested_at'])

def downgrade():
    # Remover índices
    op.drop_index('ix_data_deletion_requests_requested_at')
    op.drop_index('ix_data_deletion_requests_confirmation_code')
    op.drop_index('ix_data_deletion_requests_facebook_id')
    op.drop_index('ix_data_deletion_requests_user_id')
    
    # Remover tabela
    op.drop_table('data_deletion_requests')
    
    # Remover colunas da tabela users
    op.drop_index('ix_users_facebook_id')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'facebook_id')
