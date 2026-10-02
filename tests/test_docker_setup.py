"""Tests for Docker Compose database setup"""
import pytest
import os
import subprocess
import time
from pathlib import Path


class TestDockerComposeConfiguration:
    """Test Docker Compose configuration files"""
    
    def test_docker_compose_yml_exists(self):
        """Test that docker-compose.yml file exists"""
        assert os.path.exists('docker-compose.yml'), "docker-compose.yml should exist"
        
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            assert 'services:' in content
            assert 'postgres:' in content
            assert 'minio:' in content
            assert 'backend:' in content
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists"""
        assert os.path.exists('Dockerfile'), "Dockerfile should exist"
        
        with open('Dockerfile', 'r') as f:
            content = f.read()
            assert 'FROM python:3.11' in content
            assert 'WORKDIR /app' in content
            assert 'pip install' in content
    
    def test_docker_compose_has_postgres_service(self):
        """Test that Docker Compose defines PostgreSQL service"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check postgres service configuration
            assert 'image: postgres:16-alpine' in content
            assert 'container_name: pqc-postgres' in content
            assert 'POSTGRES_USER: pqc_user' in content
            assert 'POSTGRES_PASSWORD: pqc_password' in content
            assert 'POSTGRES_DB: pqc_secure' in content
            assert 'ports:' in content and '5432:5432' in content
    
    def test_docker_compose_has_minio_service(self):
        """Test that Docker Compose defines MinIO service"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check minio service configuration
            assert 'image: minio/minio:latest' in content
            assert 'container_name: pqc-minio' in content
            assert 'MINIO_ROOT_USER: minioadmin' in content
            assert 'MINIO_ROOT_PASSWORD: minioadmin123' in content
            assert 'ports:' in content and '9000:9000' in content
    
    def test_docker_compose_has_backend_service(self):
        """Test that Docker Compose defines backend service"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check backend service configuration
            assert 'container_name: pqc-backend' in content
            assert 'depends_on:' in content
            assert 'DATABASE_URL: postgresql://pqc_user:pqc_password@postgres:5432/pqc_secure' in content
            assert 'ports:' in content and '8000:8000' in content
    
    def test_docker_compose_has_healthchecks(self):
        """Test that Docker Compose services have healthchecks"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check for healthcheck configurations
            assert 'healthcheck:' in content
            assert 'pg_isready' in content  # PostgreSQL healthcheck
    
    def test_docker_compose_has_volumes(self):
        """Test that Docker Compose defines volumes"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check for volume definitions
            assert 'volumes:' in content
            assert 'postgres_data:' in content
            assert 'minio_data:' in content
    
    def test_docker_compose_has_network(self):
        """Test that Docker Compose defines network"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check for network definitions
            assert 'networks:' in content
            assert 'pqc_network:' in content
            assert 'driver: bridge' in content


class TestDockerImageConfiguration:
    """Test Dockerfile configuration"""
    
    def test_dockerfile_has_python_base(self):
        """Test that Dockerfile uses Python 3.11"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            assert 'FROM python:3.11-slim' in content
    
    def test_dockerfile_installs_system_dependencies(self):
        """Test that Dockerfile installs system dependencies"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            
            # Check for apt-get installation
            assert 'apt-get update' in content
            assert 'apt-get install -y' in content
            assert 'liboqs' in content  # PQC library dependency
    
    def test_dockerfile_installs_python_dependencies(self):
        """Test that Dockerfile installs Python dependencies"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            
            # Check for pip installation
            assert 'pip install' in content
            assert 'pyproject.toml' in content
    
    def test_dockerfile_exposes_port(self):
        """Test that Dockerfile exposes port 8000"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            assert 'EXPOSE 8000' in content
    
    def test_dockerfile_has_entrypoint(self):
        """Test that Dockerfile has proper entrypoint"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            assert 'CMD' in content or 'ENTRYPOINT' in content


class TestDockerComposeDatabase:
    """Test Docker Compose database integration"""
    
    def test_postgres_environment_variables(self):
        """Test that PostgreSQL environment is properly configured"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Required environment variables
            assert 'POSTGRES_USER: pqc_user' in content
            assert 'POSTGRES_PASSWORD: pqc_password' in content
            assert 'POSTGRES_DB: pqc_secure' in content
    
    def test_backend_database_url_configured(self):
        """Test that backend has DATABASE_URL configured"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check DATABASE_URL format
            assert 'DATABASE_URL: postgresql://pqc_user:pqc_password@postgres:5432/pqc_secure' in content
    
    def test_backend_depends_on_postgres(self):
        """Test that backend depends on PostgreSQL"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            assert 'depends_on:' in content
            assert 'postgres:' in content
            assert 'condition: service_healthy' in content
    
    def test_database_volume_persistence(self):
        """Test that database volume is configured for persistence"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check for volume mapping
            assert 'postgres_data:/var/lib/postgresql/data' in content
    
    def test_storage_configuration(self):
        """Test that MinIO storage is configured"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check MinIO configuration in backend
            assert 'STORAGE_TYPE: s3' in content
            assert 'MINIO_ENDPOINT: minio:9000' in content


class TestDatabaseInitScripts:
    """Test database initialization scripts"""
    
    def test_init_db_script_exists(self):
        """Test that database initialization script exists"""
        assert os.path.exists('pqc_secure/db/init_db.py'), "init_db.py should exist"
    
    def test_alembic_env_exists(self):
        """Test that Alembic env.py exists"""
        assert os.path.exists('alembic/env.py'), "alembic/env.py should exist"
    
    def test_docker_entrypoint_exists(self):
        """Test that Docker entrypoint script exists (if used)"""
        entrypoint_path = 'docker-entrypoint.sh'
        if os.path.exists(entrypoint_path):
            with open(entrypoint_path, 'r') as f:
                content = f.read()
                # Verify it has commands to initialize database
                assert len(content) > 0


class TestDockerComposeEnvironment:
    """Test Docker Compose environment configuration"""
    
    def test_env_example_file_exists(self):
        """Test that .env.example file exists"""
        assert os.path.exists('.env.example'), ".env.example should exist"
        
        with open('.env.example', 'r') as f:
            content = f.read()
            # Should have some environment variables
            assert len(content) > 0
    
    def test_docker_compose_uses_environment_variables(self):
        """Test that docker-compose.yml references environment configuration"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check for environment section in services
            assert 'environment:' in content


class TestDockerImageBuildConfiguration:
    """Test Docker image build configuration"""
    
    def test_dockerfile_build_context(self):
        """Test that Dockerfile has proper build context"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check backend build configuration
            assert 'build:' in content
            assert 'context: .' in content
            assert 'dockerfile: Dockerfile' in content
    
    def test_dockerfile_copies_necessary_files(self):
        """Test that Dockerfile copies necessary project files"""
        with open('Dockerfile', 'r') as f:
            content = f.read()
            
            # Check COPY instructions
            assert 'COPY pyproject.toml' in content
            assert 'COPY pqc_secure' in content


class TestDockerNetworkConfiguration:
    """Test Docker network setup"""
    
    def test_services_on_same_network(self):
        """Test that all services are on the same network"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check that services reference the network
            assert 'networks:' in content
            assert 'pqc_network' in content
    
    def test_backend_can_reach_postgres(self):
        """Test that backend service hostname resolves PostgreSQL"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Backend uses 'postgres' hostname for database connection
            assert 'postgres:5432' in content


class TestDockerPortConfiguration:
    """Test Docker port configuration"""
    
    def test_postgres_port_exposed(self):
        """Test that PostgreSQL port is exposed"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check that postgres port mapping exists
            assert '5432:5432' in content
    
    def test_backend_port_exposed(self):
        """Test that backend API port is exposed"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check backend port mapping
            assert '8000:8000' in content
    
    def test_minio_ports_exposed(self):
        """Test that MinIO ports are exposed"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check MinIO port mappings
            assert '9000:9000' in content  # API port
            assert '9001:9001' in content  # Console port


class TestDockerServiceHealth:
    """Test Docker service health configuration"""
    
    def test_postgres_healthcheck_configured(self):
        """Test that PostgreSQL has healthcheck"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check healthcheck for postgres
            assert 'healthcheck:' in content
            assert 'pg_isready' in content
            assert 'pqc_user' in content
            assert 'pqc_secure' in content
    
    def test_postgres_healthcheck_has_intervals(self):
        """Test that PostgreSQL healthcheck has timing configuration"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check healthcheck timing in file
            assert 'interval: 10s' in content
            assert 'timeout: 5s' in content
            assert 'retries: 5' in content
    
    def test_backend_startup_depends_on_health(self):
        """Test that backend startup waits for service health"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check depends_on with condition
            assert 'depends_on:' in content
            assert 'condition: service_healthy' in content


class TestDockerVolumeConfiguration:
    """Test Docker volume setup"""
    
    def test_postgres_data_volume(self):
        """Test that PostgreSQL has data volume for persistence"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check volume mount
            assert 'postgres_data:/var/lib/postgresql/data' in content
    
    def test_minio_data_volume(self):
        """Test that MinIO has data volume for persistence"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check volume mount
            assert 'minio_data:/minio_data' in content
    
    def test_backend_code_volume_mount(self):
        """Test that backend mounts source code for development"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Check volume mount for code
            assert './pqc_secure:/app/pqc_secure' in content


class TestDockerComposeFileStructure:
    """Test overall docker-compose.yml file structure"""
    
    def test_docker_compose_has_version(self):
        """Test that docker-compose.yml has version"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            assert 'version:' in content
    
    def test_docker_compose_has_services_section(self):
        """Test that docker-compose.yml has services section"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            assert 'services:' in content
    
    def test_docker_compose_is_valid_yaml_structure(self):
        """Test that docker-compose.yml has valid YAML-like structure"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Basic YAML structure checks
            assert 'version:' in content
            assert 'services:' in content
            assert 'volumes:' in content
            assert 'networks:' in content


class TestDatabaseSetupIntegration:
    """Test integration of database setup with Docker"""
    
    def test_database_init_script_uses_alembic(self):
        """Test that init_db.py uses Alembic for migrations"""
        with open('pqc_secure/db/init_db.py', 'r') as f:
            content = f.read()
            
            assert 'alembic' in content
            assert 'upgrade head' in content
    
    def test_database_init_script_checks_connection(self):
        """Test that init_db.py checks database connection"""
        with open('pqc_secure/db/init_db.py', 'r') as f:
            content = f.read()
            
            assert 'connect' in content.lower()
            assert 'engine' in content
    
    def test_alembic_configured_for_migrations(self):
        """Test that Alembic is configured"""
        with open('alembic.ini', 'r') as f:
            content = f.read()
            
            assert '[alembic]' in content
            assert 'sqlalchemy.url' in content
    
    def test_models_match_database_setup(self):
        """Test that ORM models are defined"""
        with open('pqc_secure/db/models.py', 'r') as f:
            content = f.read()
            
            # Check for model definitions
            assert 'class User' in content
            assert 'class CryptographicKey' in content
            assert 'class FilePackage' in content
            assert 'class AccessGrant' in content
            assert 'class AuditLog' in content
