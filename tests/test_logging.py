"""Tests for logging configuration"""
import pytest
import logging
from pqc_secure.core.logging import SecretFilteringFormatter


class TestSecretFilteringFormatter:
    """Test cases for SecretFilteringFormatter"""
    
    def test_formatter_redacts_password(self):
        """Test that formatter redacts password fields"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User login attempt with password=secret123",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "secret123" not in formatted
        assert "[REDACTED]" in formatted
    
    def test_formatter_redacts_token(self):
        """Test that formatter redacts token fields"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='API token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in formatted
        assert "[REDACTED]" in formatted
    
    def test_formatter_redacts_private_key(self):
        """Test that formatter redacts private key fields"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Cryptographic key: private_key=MIIEvQIBADANBgkq",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "MIIEvQIBADANBgkq" not in formatted
        assert "[REDACTED]" in formatted
    
    def test_formatter_preserves_non_sensitive_data(self):
        """Test that formatter preserves non-sensitive data"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User user_123 performed action on resource_456",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "user_123" in formatted
        assert "resource_456" in formatted
        assert "[REDACTED]" not in formatted
    
    def test_formatter_case_insensitive_redaction(self):
        """Test that formatter is case-insensitive when redacting"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='Database secret="very_secret_value"',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "very_secret_value" not in formatted
        assert "[REDACTED]" in formatted
    
    def test_formatter_handles_json_like_syntax(self):
        """Test formatter handles JSON-like syntax"""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"password": "my_password", "user": "admin"}',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "my_password" not in formatted
        assert "admin" in formatted  # Non-sensitive field preserved
        assert "[REDACTED]" in formatted
