"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema"""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('account_status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'])
    
    # Create cryptographic_keys table
    op.create_table(
        'cryptographic_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False),
        sa.Column('key_type', sa.String(50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('key_id', sa.String(255), nullable=False),
        sa.Column('public_key_material', sa.LargeBinary(), nullable=False),
        sa.Column('private_key_material', sa.LargeBinary(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_id'),
    )
    op.create_index(op.f('ix_cryptographic_keys_user_id'), 'cryptographic_keys', ['user_id'])
    op.create_index(op.f('ix_cryptographic_keys_key_id'), 'cryptographic_keys', ['key_id'], unique=True)
    op.create_index(op.f('ix_cryptographic_keys_created_at'), 'cryptographic_keys', ['created_at'])
    
    # Create file_packages table
    op.create_table(
        'file_packages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('sender_id', sa.String(), nullable=False),
        sa.Column('recipient_key_id', sa.String(), nullable=False),
        sa.Column('package_version', sa.String(50), nullable=False),
        sa.Column('crypto_mode', sa.String(50), nullable=False),
        sa.Column('encapsulated_secret', sa.LargeBinary(), nullable=False),
        sa.Column('payload_storage_key', sa.String(255), nullable=False),
        sa.Column('manifest_json', sa.Text(), nullable=False),
        sa.Column('signature', sa.LargeBinary(), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recipient_key_id'], ['cryptographic_keys.key_id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_file_packages_sender_id'), 'file_packages', ['sender_id'])
    op.create_index(op.f('ix_file_packages_created_at'), 'file_packages', ['created_at'])
    
    # Create file_chunks table
    op.create_table(
        'file_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('package_id', sa.String(), nullable=False),
        sa.Column('chunk_number', sa.Integer(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['file_packages.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_file_chunks_package_id'), 'file_chunks', ['package_id'])
    
    # Create access_grants table
    op.create_table(
        'access_grants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('package_id', sa.String(), nullable=False),
        sa.Column('recipient_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['package_id'], ['file_packages.id'], ),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_access_grants_package_id'), 'access_grants', ['package_id'])
    op.create_index(op.f('ix_access_grants_recipient_id'), 'access_grants', ['recipient_id'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'])
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'])
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'])


def downgrade() -> None:
    """Drop all tables"""
    
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_access_grants_recipient_id'), table_name='access_grants')
    op.drop_index(op.f('ix_access_grants_package_id'), table_name='access_grants')
    op.drop_table('access_grants')
    
    op.drop_index(op.f('ix_file_chunks_package_id'), table_name='file_chunks')
    op.drop_table('file_chunks')
    
    op.drop_index(op.f('ix_file_packages_created_at'), table_name='file_packages')
    op.drop_index(op.f('ix_file_packages_sender_id'), table_name='file_packages')
    op.drop_table('file_packages')
    
    op.drop_index(op.f('ix_cryptographic_keys_created_at'), table_name='cryptographic_keys')
    op.drop_index(op.f('ix_cryptographic_keys_key_id'), table_name='cryptographic_keys')
    op.drop_index(op.f('ix_cryptographic_keys_user_id'), table_name='cryptographic_keys')
    op.drop_table('cryptographic_keys')
    
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
