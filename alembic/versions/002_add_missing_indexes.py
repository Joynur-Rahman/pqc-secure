"""Add missing indexes for common queries

Revision ID: 002_add_missing_indexes
Revises: 001_initial_schema
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_missing_indexes'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing indexes for common queries"""
    
    # access_grants.created_at - for querying recent access grants
    op.create_index(
        op.f('ix_access_grants_created_at'),
        'access_grants',
        ['created_at']
    )
    
    # file_packages.recipient_key_id - for discovering packages for a specific recipient key
    op.create_index(
        op.f('ix_file_packages_recipient_key_id'),
        'file_packages',
        ['recipient_key_id']
    )
    
    # file_chunks.created_at - for ordering chunks by creation time
    op.create_index(
        op.f('ix_file_chunks_created_at'),
        'file_chunks',
        ['created_at']
    )
    
    # audit_logs.resource_id - for querying audit logs by resource
    op.create_index(
        op.f('ix_audit_logs_resource_id'),
        'audit_logs',
        ['resource_id']
    )


def downgrade() -> None:
    """Drop added indexes"""
    
    op.drop_index(op.f('ix_audit_logs_resource_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_file_chunks_created_at'), table_name='file_chunks')
    op.drop_index(op.f('ix_file_packages_recipient_key_id'), table_name='file_packages')
    op.drop_index(op.f('ix_access_grants_created_at'), table_name='access_grants')
