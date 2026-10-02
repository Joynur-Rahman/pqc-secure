"""Tests for Alembic migration structure and configuration"""
import os
import pytest


class TestAlembicConfiguration:
    """Test Alembic migration configuration"""
    
    def test_alembic_ini_exists(self):
        """Test that alembic.ini configuration file exists"""
        assert os.path.exists('alembic.ini'), "alembic.ini should exist in project root"
        
        # Verify it has content
        with open('alembic.ini', 'r') as f:
            content = f.read()
            assert '[alembic]' in content, "alembic.ini should have [alembic] section"
            assert 'sqlalchemy.url' in content, "alembic.ini should configure sqlalchemy.url"
    
    def test_alembic_env_py_exists(self):
        """Test that alembic/env.py configuration exists"""
        assert os.path.exists('alembic/env.py'), "alembic/env.py should exist"
        
        # Verify it has proper configuration
        with open('alembic/env.py', 'r') as f:
            content = f.read()
            assert 'from pqc_secure.db.models import Base' in content, "env.py should import Base"
            assert 'target_metadata = Base.metadata' in content, "env.py should set target_metadata"
            assert 'run_migrations_offline()' in content, "env.py should have offline migration function"
            assert 'run_migrations_online()' in content, "env.py should have online migration function"
    
    def test_alembic_script_mako_template_exists(self):
        """Test that alembic migration template exists"""
        assert os.path.exists('alembic/script.py.mako'), "alembic/script.py.mako template should exist"
        
        with open('alembic/script.py.mako', 'r') as f:
            content = f.read()
            assert 'revision' in content, "Template should have revision"
            assert 'def upgrade()' in content, "Template should have upgrade function"
            assert 'def downgrade()' in content, "Template should have downgrade function"
    
    def test_versions_directory_exists(self):
        """Test that alembic/versions directory exists"""
        assert os.path.exists('alembic/versions'), "alembic/versions directory should exist"
        assert os.path.isdir('alembic/versions'), "versions should be a directory"
    
    def test_initial_migration_exists(self):
        """Test that the initial migration file exists"""
        migration_file = 'alembic/versions/001_initial_schema.py'
        assert os.path.exists(migration_file), f"Initial migration {migration_file} should exist"
    
    def test_initial_migration_structure(self):
        """Test that initial migration has proper structure"""
        migration_file = 'alembic/versions/001_initial_schema.py'
        
        with open(migration_file, 'r') as f:
            content = f.read()
            
            # Verify revision identifiers
            assert "revision = '001_initial_schema'" in content, "Should have correct revision ID"
            assert "down_revision = None" in content, "Initial migration should have no down_revision"
            assert "branch_labels = None" in content, "Should have branch_labels"
            assert "depends_on = None" in content, "Should have depends_on"
            
            # Verify functions
            assert "def upgrade() -> None:" in content, "Should have upgrade function"
            assert "def downgrade() -> None:" in content, "Should have downgrade function"
            
            # Verify imports
            assert "from alembic import op" in content, "Should import op from alembic"
            assert "import sqlalchemy as sa" in content, "Should import sqlalchemy"


class TestInitialMigrationContent:
    """Test that the initial migration creates all required tables"""
    
    def test_migration_creates_users_table(self):
        """Test that migration creates users table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "op.create_table(" in content
            assert "'users'" in content
            assert "sa.Column('id'" in content
            assert "sa.Column('email'" in content
            assert "sa.Column('password_hash'" in content
            assert "sa.Column('account_status'" in content
            assert "sa.Column('created_at'" in content
            assert "sa.Column('updated_at'" in content
    
    def test_migration_creates_cryptographic_keys_table(self):
        """Test that migration creates cryptographic_keys table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "'cryptographic_keys'" in content
            assert "sa.Column('algorithm'" in content
            assert "sa.Column('key_type'" in content
            assert "sa.Column('version'" in content
            assert "sa.Column('key_id'" in content
            assert "sa.Column('public_key_material'" in content
            assert "sa.Column('private_key_material'" in content
    
    def test_migration_creates_file_packages_table(self):
        """Test that migration creates file_packages table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "'file_packages'" in content
            assert "sa.Column('sender_id'" in content
            assert "sa.Column('recipient_key_id'" in content
            assert "sa.Column('crypto_mode'" in content
            assert "sa.Column('encapsulated_secret'" in content
            assert "sa.Column('manifest_json'" in content
            assert "sa.Column('signature'" in content
    
    def test_migration_creates_file_chunks_table(self):
        """Test that migration creates file_chunks table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "'file_chunks'" in content
            assert "sa.Column('package_id'" in content
            assert "sa.Column('chunk_number'" in content
            assert "sa.Column('chunk_size'" in content
            assert "sa.Column('storage_key'" in content
    
    def test_migration_creates_access_grants_table(self):
        """Test that migration creates access_grants table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "'access_grants'" in content
            assert "sa.Column('recipient_id'" in content
            assert "sa.Column('revoked_at'" in content
    
    def test_migration_creates_audit_logs_table(self):
        """Test that migration creates audit_logs table"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            assert "'audit_logs'" in content
            assert "sa.Column('event_type'" in content
            assert "sa.Column('resource_id'" in content
            assert "sa.Column('resource_type'" in content
            assert "sa.Column('action'" in content
            assert "sa.Column('details'" in content
            assert "sa.Column('ip_address'" in content
            assert "sa.Column('user_agent'" in content
    
    def test_migration_creates_foreign_keys(self):
        """Test that migration creates proper foreign keys"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            
            # Check for foreign key constraints
            assert "sa.ForeignKeyConstraint" in content
            assert "['user_id'], ['users.id']" in content
            assert "['sender_id'], ['users.id']" in content
            assert "['recipient_id'], ['users.id']" in content
            assert "['package_id'], ['file_packages.id']" in content
            assert "['recipient_key_id'], ['cryptographic_keys.key_id']" in content
    
    def test_migration_creates_indexes(self):
        """Test that migration creates appropriate indexes"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            
            # Check for index creation
            assert "op.create_index(" in content
            assert "ix_users_email" in content
            assert "ix_users_created_at" in content
            assert "ix_cryptographic_keys_user_id" in content
            assert "ix_cryptographic_keys_key_id" in content
            assert "ix_cryptographic_keys_created_at" in content
            assert "ix_file_packages_sender_id" in content
            assert "ix_file_packages_created_at" in content
            assert "ix_access_grants_package_id" in content
            assert "ix_access_grants_recipient_id" in content
            assert "ix_audit_logs_event_type" in content
            assert "ix_audit_logs_user_id" in content
            assert "ix_audit_logs_created_at" in content
    
    def test_migration_has_downgrade(self):
        """Test that migration has downgrade function that drops all tables"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            
            # Check downgrade function
            downgrade_section = content.split("def downgrade()")[1]
            
            assert "op.drop_table('audit_logs')" in downgrade_section
            assert "op.drop_table('access_grants')" in downgrade_section
            assert "op.drop_table('file_chunks')" in downgrade_section
            assert "op.drop_table('file_packages')" in downgrade_section
            assert "op.drop_table('cryptographic_keys')" in downgrade_section
            assert "op.drop_table('users')" in downgrade_section


class TestMigrationIntegration:
    """Test migration integration with the codebase"""
    
    def test_alembic_env_imports_settings(self):
        """Test that env.py imports settings for database URL"""
        with open('alembic/env.py', 'r') as f:
            content = f.read()
            assert 'from pqc_secure.core.config import settings' in content
            assert 'settings.database_url' in content
    
    def test_models_and_migration_versions_match(self):
        """Test that migration version matches expected initial version"""
        with open('alembic/versions/001_initial_schema.py', 'r') as f:
            content = f.read()
            # Should be at initial migration version
            assert "revision = '001_initial_schema'" in content
            assert "down_revision = None" in content
    
    def test_database_init_function_exists(self):
        """Test that database initialization function exists"""
        assert os.path.exists('pqc_secure/db/init_db.py'), "init_db.py should exist"
        
        with open('pqc_secure/db/init_db.py', 'r') as f:
            content = f.read()
            assert 'def init_db()' in content, "init_db function should exist"
            assert 'def run_alembic_migrations()' in content, "run_alembic_migrations should exist"
            assert 'subprocess.run' in content, "Should run alembic via subprocess"
            assert 'upgrade head' in content, "Should run alembic upgrade head"
