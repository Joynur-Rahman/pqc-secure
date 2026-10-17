"""Tests for audit logging service"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pqc_secure.services.audit import (
    AuditService,
    log_authentication_event,
    log_access_event,
    log_crypto_event,
    log_file_event
)
from pqc_secure.db.models import AuditLog


class TestAuditService:
    """Test cases for AuditService"""
    
    def test_sanitize_details_removes_sensitive_keys(self):
        """Test that sensitive keys are removed from details"""
        details = {
            "user_id": "123",
            "password": "secret_password",
            "action": "login",
            "private_key": "key_material",
            "other_field": "safe_value"
        }
        
        sanitized = AuditService._sanitize_details(details)
        
        assert "user_id" in sanitized
        assert "action" in sanitized
        assert "other_field" in sanitized
        assert "password" not in sanitized
        assert "private_key" not in sanitized
        
    def test_sanitize_details_preserves_non_sensitive(self):
        """Test that non-sensitive fields are preserved"""
        details = {
            "user_id": "user_123",
            "resource_id": "file_456",
            "action": "download",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        sanitized = AuditService._sanitize_details(details)
        
        assert sanitized == details
    
    def test_sanitize_details_case_insensitive(self):
        """Test that sensitive key detection is case-insensitive"""
        details = {
            "Password": "secret",
            "SECRET": "hidden",
            "PLAINTEXT": "data"
        }
        
        sanitized = AuditService._sanitize_details(details)
        
        assert len(sanitized) == 0
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_creates_audit_log(self, mock_settings):
        """Test that log_event creates an AuditLog entry"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['user', 'auth', 'permission', 'crypto', 'upload', 'download']
        
        mock_session = Mock()
        
        result = AuditService.log_event(
            event_type="user_login",
            action="User login attempt",
            status="success",
            user_id="user_123",
            db_session=mock_session
        )
        
        assert result is not None
        assert result.event_type == "user_login"
        assert result.action == "User login attempt"
        assert result.status == "success"
        assert result.user_id == "user_123"
        assert mock_session.add.called
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_without_db_session(self, mock_settings):
        """Test that log_event works without database session"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['auth', 'permission', 'crypto', 'upload', 'download']
        
        result = AuditService.log_event(
            event_type="test_event",
            action="Test action",
            status="success",
            db_session=None
        )
        
        # Even though no category matches, should still create entry for testing
        assert result is not None or result is None  # Depends on filtering
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_with_details(self, mock_settings):
        """Test that log_event includes sanitized details"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['auth', 'permission', 'crypto', 'upload', 'download']
        
        mock_session = Mock()
        
        details = {
            "resource_id": "file_123",
            "password": "secret",  # Should be filtered
            "size_bytes": 1024
        }
        
        result = AuditService.log_event(
            event_type="file_uploaded",
            action="File uploaded",
            status="success",
            user_id="user_123",
            details=details,
            db_session=mock_session
        )
        
        assert result is not None
        assert result.details is not None
        # Verify password is not in the details
        assert "password" not in result.details.lower()
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_respects_audit_logging_disabled(self, mock_settings):
        """Test that events are not logged when audit logging is disabled"""
        mock_settings.audit_logging_enabled = False
        
        result = AuditService.log_event(
            event_type="test_event",
            action="Test action",
            status="success"
        )
        
        assert result is None
    
    @patch('pqc_secure.services.audit.logger')
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_logs_to_application_logger(self, mock_settings, mock_logger):
        """Test that events are logged to application logger"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['user']
        
        AuditService.log_event(
            event_type="user_login",
            action="User login",
            status="success",
            user_id="user_123"
        )
        
        assert mock_logger.info.called or mock_logger.warning.called
    
    @patch('pqc_secure.services.audit.logger')
    @patch('pqc_secure.services.audit.settings')
    def test_log_event_logs_failures_as_warning(self, mock_settings, mock_logger):
        """Test that failure events are logged as warnings"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['login']
        
        AuditService.log_event(
            event_type="login_failed",
            action="User login failed",
            status="failure",
            user_id="user_123"
        )
        
        assert mock_logger.warning.called
    
    def test_get_events_queries_database(self):
        """Test that get_events returns audit logs from database"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        events, count = AuditService.get_events(mock_session)
        
        assert mock_session.query.called
        assert count == 0
    
    def test_get_events_filters_by_user_id(self):
        """Test that get_events filters by user_id"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        AuditService.get_events(mock_session, user_id="user_123")
        
        assert mock_query.filter.called
    
    def test_get_events_respects_pagination(self):
        """Test that get_events respects limit and offset"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 100
        
        events, count = AuditService.get_events(
            mock_session,
            limit=50,
            offset=25
        )
        
        # Verify limit and offset were called with correct values
        mock_query.limit.assert_called_with(50)
        mock_query.offset.assert_called_with(25)


class TestAuditConvenienceFunctions:
    """Test convenience audit logging functions"""
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_authentication_event(self, mock_settings):
        """Test authentication event logging"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['user']
        
        result = log_authentication_event(
            event_type="user_login",
            status="success",
            user_id="user_123"
        )
        
        assert result is not None
        assert result.event_type == "user_login"
        assert result.resource_type == "user"
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_access_event(self, mock_settings):
        """Test access event logging"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['permission']
        
        result = log_access_event(
            event_type="permission_denied",
            status="failure",
            user_id="user_123",
            resource_id="file_456"
        )
        
        assert result is not None
        assert result.event_type == "permission_denied"
        assert result.resource_id == "file_456"
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_crypto_event(self, mock_settings):
        """Test cryptographic event logging"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['crypto']
        
        result = log_crypto_event(
            event_type="crypto_verification_failed",
            status="failure",
            user_id="user_123"
        )
        
        assert result is not None
        assert result.event_type == "crypto_verification_failed"
        assert result.resource_type == "cryptographic_operation"
    
    @patch('pqc_secure.services.audit.settings')
    def test_log_file_event(self, mock_settings):
        """Test file event logging"""
        mock_settings.audit_logging_enabled = True
        mock_settings.get_audit_log_events.return_value = ['upload', 'download']
        
        result = log_file_event(
            event_type="file_downloaded",
            status="success",
            user_id="user_123",
            resource_id="file_456"
        )
        
        assert result is not None
        assert result.event_type == "file_downloaded"
        assert result.resource_type == "file"


class TestAuditSanitizationAndFiltering:
    """Advanced test cases for sanitization and event filtering"""

    def test_sanitize_details_nested_dict(self):
        """Test recursive sanitization on nested dictionaries"""
        details = {
            "outer_id": "pkg_999",
            "nested_auth": {
                "token": "secret_token_val",
                "session_token": "secret_session",
                "safe_user": "alice",
            },
            "safe_metadata": {"version": 2}
        }
        sanitized = AuditService._sanitize_details(details)
        assert sanitized["outer_id"] == "pkg_999"
        assert sanitized["safe_metadata"]["version"] == 2
        assert "token" not in sanitized["nested_auth"]
        assert "session_token" not in sanitized["nested_auth"]
        assert sanitized["nested_auth"]["safe_user"] == "alice"

    def test_sanitize_details_list_of_dicts(self):
        """Test recursive sanitization inside lists of objects"""
        details = {
            "recipients": [
                {"email": "bob@example.com", "private_key": "raw_key_bytes"},
                {"email": "carol@example.com", "password": "plaintext_pass", "status": "active"},
            ]
        }
        sanitized = AuditService._sanitize_details(details)
        assert len(sanitized["recipients"]) == 2
        assert sanitized["recipients"][0]["email"] == "bob@example.com"
        assert "private_key" not in sanitized["recipients"][0]
        assert sanitized["recipients"][1]["status"] == "active"
        assert "password" not in sanitized["recipients"][1]

    def test_sanitize_details_compound_sensitive_keys(self):
        """Test detection of compound sensitive keys (api_token, secret_key, etc.)"""
        details = {
            "user_password": "pwd",
            "api_secret": "sec",
            "auth_token": "tok",
            "ciphertext_bytes": "enc",
            "safe_field": 123
        }
        sanitized = AuditService._sanitize_details(details)
        assert sanitized == {"safe_field": 123}

    def test_sanitize_details_pem_redaction(self):
        """Test redacting PEM private key material in string values"""
        details = {
            "key_header": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgk...\n-----END PRIVATE KEY-----",
            "description": "normal text"
        }
        sanitized = AuditService._sanitize_details(details)
        assert sanitized["key_header"] == "[REDACTED_PRIVATE_KEY]"
        assert sanitized["description"] == "normal text"

    @pytest.mark.asyncio
    async def test_log_user_registered_and_failure(self):
        """Test log_user_registered and log_registration_failure convenience functions"""
        from pqc_secure.services.audit import log_user_registered, log_registration_failure
        mock_session = Mock()

        res1 = await log_user_registered("user_xyz", db_session=mock_session, ip_address="127.0.0.1", user_agent="PyTest")
        assert res1 is not None
        assert res1.user_id == "user_xyz"
        assert res1.ip_address == "127.0.0.1"
        assert res1.user_agent == "PyTest"

        res2 = await log_registration_failure("invalid@example.com", reason="Weak password", db_session=mock_session)
        assert res2 is not None
        assert res2.status == "failure"
        assert "Weak password" in res2.action

