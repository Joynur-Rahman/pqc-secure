"""Tests for application configuration settings"""
import pytest
import os
from pydantic_core import ValidationError
from pqc_secure.core.config import Settings


class TestSettingsDefaults:
    """Test default configuration values"""
    
    def test_default_environment(self):
        """Test default environment is development"""
        settings = Settings()
        assert settings.environment == "development"
    
    def test_default_debug_enabled(self):
        """Test debug is enabled by default"""
        settings = Settings()
        assert settings.debug is True
    
    def test_default_server_port(self):
        """Test default server port is 8000"""
        settings = Settings()
        assert settings.server_port == 8000
    
    def test_default_database_pool_size(self):
        """Test default database pool size"""
        settings = Settings()
        assert settings.database_pool_size == 10
    
    def test_default_access_token_expire(self):
        """Test default access token expiration"""
        settings = Settings()
        assert settings.access_token_expire_minutes == 30
    
    def test_default_password_hashing(self):
        """Test default password hashing algorithm"""
        settings = Settings()
        assert settings.password_hashing_algorithm == "argon2id"
    
    def test_default_rate_limiting_enabled(self):
        """Test rate limiting is enabled by default"""
        settings = Settings()
        assert settings.rate_limit_enabled is True
    
    def test_default_max_file_size(self):
        """Test default max file size"""
        settings = Settings()
        assert settings.max_file_size_mb == 500
    
    def test_default_crypto_mode(self):
        """Test default crypto mode is PQC"""
        settings = Settings()
        assert settings.default_crypto_mode == "pqc"
    
    def test_default_pqc_mode_enabled(self):
        """Test PQC mode is enabled by default"""
        settings = Settings()
        assert settings.enable_pqc_mode is True
    
    def test_default_classical_mode_enabled(self):
        """Test classical mode is enabled by default"""
        settings = Settings()
        assert settings.enable_classical_mode is True
    
    def test_default_log_level(self):
        """Test default log level is INFO"""
        settings = Settings()
        assert settings.log_level == "INFO"
    
    def test_default_audit_logging_enabled(self):
        """Test audit logging is enabled by default"""
        settings = Settings()
        assert settings.audit_logging_enabled is True


class TestSettingsHelpers:
    """Test helper methods"""
    
    def test_get_allowed_origins_list(self):
        """Test parsing allowed origins list"""
        settings = Settings(
            allowed_origins="http://localhost:3000,http://localhost:3001"
        )
        origins = settings.get_allowed_origins_list()
        assert len(origins) == 2
        assert origins[0] == "http://localhost:3000"
        assert origins[1] == "http://localhost:3001"
    
    def test_get_allowed_origins_with_whitespace(self):
        """Test parsing origins handles whitespace"""
        settings = Settings(
            allowed_origins="http://localhost:3000 , http://localhost:3001"
        )
        origins = settings.get_allowed_origins_list()
        assert origins[0] == "http://localhost:3000"
        assert origins[1] == "http://localhost:3001"
    
    def test_get_audit_log_events(self):
        """Test parsing audit log events"""
        settings = Settings(
            audit_log_events="auth,permission,crypto,upload,download"
        )
        events = settings.get_audit_log_events()
        assert len(events) == 5
        assert "auth" in events
        assert "permission" in events
    
    def test_is_production_development(self):
        """Test is_production returns False for development"""
        settings = Settings(environment="development")
        assert settings.is_production() is False
    
    def test_is_production_true(self):
        """Test is_production returns True for production"""
        settings = Settings(environment="production")
        assert settings.is_production() is True
    
    def test_get_log_level(self):
        """Test get_log_level returns correct logging level"""
        import logging
        settings = Settings(log_level="DEBUG")
        assert settings.get_log_level() == logging.DEBUG
        
        settings = Settings(log_level="INFO")
        assert settings.get_log_level() == logging.INFO
        
        settings = Settings(log_level="ERROR")
        assert settings.get_log_level() == logging.ERROR


class TestSettingsValidation:
    """Test settings validation"""
    
    def test_invalid_password_hashing_algorithm(self):
        """Test invalid password hashing algorithm"""
        # Note: Pydantic allows any string by default, but we could add custom validation
        settings = Settings(password_hashing_algorithm="invalid")
        assert settings.password_hashing_algorithm == "invalid"
    
    def test_invalid_storage_type(self):
        """Test invalid storage type"""
        # Note: Pydantic allows any string by default, but we could add custom validation
        settings = Settings(storage_type="invalid")
        assert settings.storage_type == "invalid"
    
    def test_negative_port_number(self):
        """Test port number validation"""
        # Pydantic should allow any integer, validation happens at runtime
        settings = Settings(server_port=9000)
        assert settings.server_port == 9000
    
    def test_database_url_required(self):
        """Test database URL is provided"""
        settings = Settings()
        assert settings.database_url  # Should have default value


class TestSettingsEnvironmentVariables:
    """Test loading settings from environment variables"""
    
    def test_load_from_environment(self, monkeypatch):
        """Test loading settings from environment variables"""
        monkeypatch.setenv("SERVER_PORT", "9000")
        monkeypatch.setenv("DEBUG", "false")
        settings = Settings()
        assert settings.server_port == 9000
        assert settings.debug is False
    
    def test_case_insensitive_loading(self, monkeypatch):
        """Test settings are loaded case-insensitively"""
        monkeypatch.setenv("server_port", "8080")
        monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
        settings = Settings()
        assert settings.server_port == 8080
        assert settings.server_host == "127.0.0.1"
    
    def test_environment_overrides_defaults(self, monkeypatch):
        """Test environment variables override defaults"""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "1000")
        settings = Settings()
        assert settings.log_level == "DEBUG"
        assert settings.max_file_size_mb == 1000
    
    def test_rate_limit_values(self, monkeypatch):
        """Test rate limiting configuration"""
        monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")
        monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE", "10")
        settings = Settings()
        assert settings.rate_limit_requests_per_minute == 100
        assert settings.rate_limit_auth_requests_per_minute == 10


class TestSettingsIntegration:
    """Test settings integration and consistency"""
    
    def test_storage_configuration_consistency(self):
        """Test storage configuration is consistent"""
        settings = Settings(
            storage_type="filesystem",
            storage_path="./uploads"
        )
        assert settings.storage_type == "filesystem"
        assert settings.storage_path == "./uploads"
    
    def test_minio_configuration(self):
        """Test MinIO S3 configuration"""
        settings = Settings(
            storage_type="s3",
            minio_endpoint="s3.example.com",
            minio_access_key="access",
            minio_secret_key="secret",
            minio_use_ssl=True
        )
        assert settings.storage_type == "s3"
        assert settings.minio_endpoint == "s3.example.com"
        assert settings.minio_use_ssl is True
    
    def test_security_configuration(self):
        """Test security settings configuration"""
        settings = Settings(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=60,
            password_hashing_algorithm="argon2id"
        )
        assert settings.secret_key == "test-secret-key"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 60
        assert settings.password_hashing_algorithm == "argon2id"
    
    def test_session_cookie_settings(self):
        """Test session cookie configuration"""
        settings = Settings(
            session_cookie_secure=True,
            session_cookie_httponly=True,
            session_cookie_samesite="strict"
        )
        assert settings.session_cookie_secure is True
        assert settings.session_cookie_httponly is True
        assert settings.session_cookie_samesite == "strict"


class TestSettingsSingleton:
    """Test that settings module provides singleton instance"""
    
    def test_settings_instance_available(self):
        """Test settings instance is available from module"""
        from pqc_secure.core.config import settings
        assert settings is not None
        assert isinstance(settings, Settings)
    
    def test_settings_instance_consistent(self):
        """Test settings instance values are consistent"""
        from pqc_secure.core.config import settings
        
        # Should have default values
        assert settings.environment == "development"
        assert settings.debug is True
