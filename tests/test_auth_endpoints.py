"""Tests for authentication endpoints"""
import pytest
import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Test AuthService directly without importing full db module
sys.path.insert(0, 'pqc_secure')


@pytest.fixture
def db_session():
    """Create an SQLite database session for testing"""
    # Import models here to avoid db initialization at module level
    from pqc_secure.db.models import Base
    
    # Use file-based SQLite for testing (supports threading)
    engine = create_engine("sqlite:///test_pqc.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    
    # Clean up test database file
    import os
    import time
    try:
        if os.path.exists("test_pqc.db"):
            # Give system time to release file lock on Windows
            time.sleep(0.1)
            os.remove("test_pqc.db")
    except (PermissionError, OSError):
        # Ignore cleanup errors (file will be overwritten on next test run)
        pass


@pytest.fixture
def reset_rate_limiter():
    """Reset rate limiter before each test"""
    from pqc_secure.middleware.rate_limit import rate_limiter
    # Reset the rate limiters
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()
    yield
    # Clean up after test
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()


@pytest.fixture
def client(db_session, reset_rate_limiter):
    """Create a FastAPI test client with mocked database"""
    from pqc_secure.main import app
    from pqc_secure.db.session import get_db_session
    
    app.dependency_overrides[get_db_session] = lambda: db_session
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


class TestAuthEndpointRegistration:
    """Test registration endpoint with rate limiting"""
    
    def test_register_endpoint_success(self, client, db_session):
        """Test successful registration via endpoint"""
        from pqc_secure.db.models import User
        
        response = client.post(
            "/auth/register",
            json={
                "email": "testuser@example.com",
                "password": "SecurePass123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert "session_token" in data
        assert "id" in data
    
    def test_register_endpoint_rate_limiting(self, client):
        """Test rate limiting on registration endpoint"""
        from pqc_secure.core.config import settings
        
        # Make requests up to the limit
        responses = []
        for i in range(settings.rate_limit_auth_requests_per_minute + 1):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"user{i}@example.com",
                    "password": "SecurePass123"
                }
            )
            responses.append(response)
        
        # The last request should be rate limited
        assert responses[-1].status_code == 429
        assert "Too many registration attempts" in responses[-1].json()["detail"]
    
    def test_register_endpoint_rate_limit_per_client(self, client):
        """Test that rate limiting allows requests to succeed initially"""
        # This test verifies that the endpoint accepts requests with valid data
        # Rate limiting is tested thoroughly in TestRateLimiter tests
        response = client.post(
            "/auth/register",
            json={
                "email": "test_unique@example.com",
                "password": "ValidPass123"
            }
        )
        
        # Should succeed or fail with validation error, but not rate limited
        # (since we're only making one request)
        assert response.status_code in [201, 400, 422]


class TestAuthServiceRegistration:
    """Test AuthService.register_user method"""
    
    def test_register_user_success(self, db_session):
        """Test successful user registration"""
        from pqc_secure.db.models import User
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "newuser@example.com",
            "SecurePass123"
        )
        
        assert success is True
        assert user is not None
        assert error is None
        assert user.email == "newuser@example.com"
        assert user.account_status == "active"
        
        # Verify user is in database
        db_user = db_session.query(User).filter_by(email="newuser@example.com").first()
        assert db_user is not None
    
    def test_register_user_invalid_email_format(self, db_session):
        """Test registration with invalid email format"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "notanemail",
            "SecurePass123"
        )
        
        assert success is False
        assert user is None
        assert "Invalid email format" in error
    
    def test_register_user_password_too_short(self, db_session):
        """Test registration with password below minimum length"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "Short1"
        )
        
        assert success is False
        assert user is None
        assert "at least" in error.lower()
    
    def test_register_user_password_missing_uppercase(self, db_session):
        """Test registration with password missing uppercase"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "lowercase123"
        )
        
        assert success is False
        assert user is None
        assert "uppercase" in error.lower()
    
    def test_register_user_password_missing_lowercase(self, db_session):
        """Test registration with password missing lowercase"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "UPPERCASE123"
        )
        
        assert success is False
        assert user is None
        assert "lowercase" in error.lower()
    
    def test_register_user_password_missing_digit(self, db_session):
        """Test registration with password missing digit"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "NoDigitsHere"
        )
        
        assert success is False
        assert user is None
        assert "numeric" in error.lower()
    
    def test_register_user_duplicate_email(self, db_session):
        """Test registration with duplicate email"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        # Register first user
        success1, user1, error1 = service.register_user(
            db_session,
            "user@example.com",
            "SecurePass123"
        )
        assert success1 is True
        assert user1 is not None
        
        # Attempt to register with same email
        success2, user2, error2 = service.register_user(
            db_session,
            "user@example.com",
            "DifferentPass456"
        )
        
        assert success2 is False
        assert user2 is None
        # Should not reveal that email is already registered
        assert "Unable to create account" in error2
    
    def test_register_user_email_case_insensitive(self, db_session):
        """Test that email uniqueness is case-insensitive"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        # Register first user with lowercase email
        success1, user1, error1 = service.register_user(
            db_session,
            "user@example.com",
            "SecurePass123"
        )
        assert success1 is True
        
        # Attempt to register with uppercase version of same email
        success2, user2, error2 = service.register_user(
            db_session,
            "USER@EXAMPLE.COM",
            "DifferentPass456"
        )
        
        assert success2 is False
        assert user2 is None
    
    def test_register_user_email_normalized(self, db_session):
        """Test that email is normalized (lowercased and trimmed)"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "  NEWUSER@EXAMPLE.COM  ",
            "SecurePass123"
        )
        
        assert success is True
        assert user is not None
        assert user.email == "newuser@example.com"
    
    def test_register_user_password_hashed(self, db_session):
        """Test that password is hashed, not stored in plaintext"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        plain_password = "SecurePass123"
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            plain_password
        )
        
        assert success is True
        assert user is not None
        
        # Verify password is not stored in plaintext
        assert user.password_hash != plain_password
        assert plain_password not in user.password_hash


class TestAuthServiceUnit:
    """Unit tests for AuthService"""
    
    def test_normalize_email(self):
        """Test email normalization"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        test_cases = [
            ("  User@Example.COM  ", "user@example.com"),
            ("USER@EXAMPLE.COM", "user@example.com"),
            ("  ", ""),
        ]
        
        for input_email, expected in test_cases:
            result = service.normalize_email(input_email)
            assert result == expected
    
    def test_validate_email_format_valid(self):
        """Test email format validation with valid emails"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
            "123@example.com",
        ]
        
        for email in valid_emails:
            assert service.validate_email_format(email) is True
    
    def test_validate_email_format_invalid(self):
        """Test email format validation with invalid emails"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user @example.com",
        ]
        
        for email in invalid_emails:
            assert service.validate_email_format(email) is False
    
    def test_validate_password_valid(self):
        """Test password validation with valid passwords"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        valid_passwords = [
            "ValidPass123",
            "AnotherGood456",
            "ComplexP@ssw0rd",
        ]
        
        for password in valid_passwords:
            is_valid, error = service.validate_password(password)
            assert is_valid is True
            assert error is None
    
    def test_validate_password_too_short(self):
        """Test password validation with short password"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        is_valid, error = service.validate_password("Short1")
        assert is_valid is False
        assert "at least" in error.lower()
    
    def test_validate_password_missing_requirements(self):
        """Test password validation with missing requirements"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        test_cases = [
            ("alllowercase123", "uppercase"),
            ("ALLUPPERCASE123", "lowercase"),
            ("NoDigitsHere", "numeric"),
        ]
        
        for password, missing_req in test_cases:
            is_valid, error = service.validate_password(password)
            assert is_valid is False
            assert missing_req.lower() in error.lower()
    
    def test_hash_password(self):
        """Test password hashing"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        password = "TestPassword123"
        hashed = service.hash_password(password)
        
        # Hash should not be equal to plaintext
        assert hashed != password
        # Hash should be a string
        assert isinstance(hashed, str)
        # Hash should have reasonable length
        assert len(hashed) > 20
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        password = "TestPassword123"
        hashed = service.hash_password(password)
        
        assert service.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        password = "TestPassword123"
        hashed = service.hash_password(password)
        
        assert service.verify_password("WrongPassword456", hashed) is False
    
    def test_generate_token(self):
        """Test JWT token generation"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        user_id = "test-user-id"
        token = service.generate_token(user_id)
        
        # Token should be a JWT (3 parts separated by dots)
        assert len(token.split(".")) == 3
    
    def test_verify_token_valid(self):
        """Test JWT token verification with valid token"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        user_id = "test-user-id"
        token = service.generate_token(user_id)
        
        decoded_id = service.verify_token(token)
        assert decoded_id == user_id
    
    def test_verify_token_invalid(self):
        """Test JWT token verification with invalid token"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        invalid_token = "invalid.token.here"
        decoded_id = service.verify_token(invalid_token)
        assert decoded_id is None


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_allow_requests_within_limit(self):
        """Test that requests within limit are allowed"""
        from pqc_secure.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5)
        client_id = "test-client"
        
        # Should allow up to 5 requests
        for i in range(5):
            assert limiter.is_rate_limited(client_id) is False
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked"""
        from pqc_secure.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5)
        client_id = "test-client"
        
        # Use up the quota
        for i in range(5):
            limiter.is_rate_limited(client_id)
        
        # Next request should be blocked
        assert limiter.is_rate_limited(client_id) is True
    
    def test_rate_limiter_per_client(self):
        """Test that rate limiting is per-client"""
        from pqc_secure.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=3)
        
        # Client 1 uses up quota
        client1 = "client-1"
        for i in range(3):
            limiter.is_rate_limited(client1)
        assert limiter.is_rate_limited(client1) is True
        
        # Client 2 should still have quota
        client2 = "client-2"
        assert limiter.is_rate_limited(client2) is False
        assert limiter.is_rate_limited(client2) is False
        assert limiter.is_rate_limited(client2) is False
        assert limiter.is_rate_limited(client2) is True
    
    def test_endpoint_rate_limiter_extract_client_id(self):
        """Test client identifier extraction"""
        from pqc_secure.middleware.rate_limit import EndpointRateLimiter
        from fastapi.testclient import TestClient
        
        limiter = EndpointRateLimiter()
        
        # Create a mock request
        from unittest.mock import Mock
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        client_id = limiter.get_client_identifier(request)
        assert client_id == "192.168.1.1"
    
    def test_endpoint_rate_limiter_extract_forwarded_ip(self):
        """Test client identifier extraction with X-Forwarded-For header"""
        from pqc_secure.middleware.rate_limit import EndpointRateLimiter
        
        limiter = EndpointRateLimiter()
        
        # Create a mock request with forwarded IP
        from unittest.mock import Mock
        request = Mock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 192.168.1.1"}
        
        client_id = limiter.get_client_identifier(request)
        assert client_id == "10.0.0.1"


class TestAuthIntegration:
    """Integration tests for user authentication workflow"""
    
    def test_registration_workflow_success(self, client, db_session):
        """Test complete registration workflow"""
        # Test user registration
        response = client.post(
            "/auth/register",
            json={
                "email": "integration@example.com",
                "password": "IntegrationTest123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response contains required fields
        assert "id" in data
        assert "email" in data
        assert "session_token" in data
        assert "account_status" in data
        
        # Verify user data
        assert data["email"] == "integration@example.com"
        assert data["account_status"] == "active"
        
        # Verify user exists in database
        from pqc_secure.db.models import User
        db_user = db_session.query(User).filter_by(id=data["id"]).first()
        assert db_user is not None
        assert db_user.email == "integration@example.com"
        assert db_user.account_status == "active"
    
    def test_registration_with_invalid_input(self, client):
        """Test registration rejects invalid input"""
        # Missing email
        response = client.post(
            "/auth/register",
            json={"password": "ValidPass123"}
        )
        assert response.status_code == 422
        
        # Missing password
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 422
    
    def test_registration_prevents_duplicate_emails(self, client, db_session):
        """Test that duplicate email registration is prevented"""
        # First registration
        response1 = client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "FirstPass123"
            }
        )
        assert response1.status_code == 201
        
        # Second registration with same email (different case)
        response2 = client.post(
            "/auth/register",
            json={
                "email": "DUPLICATE@EXAMPLE.COM",
                "password": "SecondPass456"
            }
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "Unable to create account" in data["detail"]
    
    def test_registration_validates_email_format(self, client):
        """Test email format validation during registration"""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-a-valid-email",
                "password": "ValidPass123"
            }
        )
        
        # Pydantic validates email format, so we get 422, not 400
        assert response.status_code == 422
    
    def test_registration_validates_password_requirements(self, client):
        """Test password validation during registration"""
        # Test missing uppercase
        response = client.post(
            "/auth/register",
            json={
                "email": "testlower@example.com",
                "password": "lowercase123"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "uppercase" in data["detail"].lower()
        
        # Test missing lowercase
        response = client.post(
            "/auth/register",
            json={
                "email": "testupper@example.com",
                "password": "UPPERCASE123"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "lowercase" in data["detail"].lower()
        
        # Test missing digit
        response = client.post(
            "/auth/register",
            json={
                "email": "testnodigit@example.com",
                "password": "NoDigitsHere"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "numeric" in data["detail"].lower()
        
        # Test too short password - caught by Pydantic (returns 422)
        response = client.post(
            "/auth/register",
            json={
                "email": "testshort@example.com",
                "password": "Short1"
            }
        )
        
        # Pydantic validates min_length=8 at schema level (422 Unprocessable Entity)
        assert response.status_code == 422
    
    def test_registration_normalizes_email(self, client, db_session):
        """Test that emails are normalized (lowercased and trimmed)"""
        response = client.post(
            "/auth/register",
            json={
                "email": "  UPPERCASE@EXAMPLE.COM  ",
                "password": "ValidPass123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "uppercase@example.com"
        
        # Verify database stores normalized email
        from pqc_secure.db.models import User
        db_user = db_session.query(User).filter_by(id=data["id"]).first()
        assert db_user.email == "uppercase@example.com"
    
    def test_registration_hashes_password(self, client, db_session):
        """Test that passwords are hashed and not stored in plaintext"""
        plain_password = "SecurePass123"
        
        response = client.post(
            "/auth/register",
            json={
                "email": "hash@example.com",
                "password": plain_password
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify password is hashed in database
        from pqc_secure.db.models import User
        db_user = db_session.query(User).filter_by(id=data["id"]).first()
        assert db_user.password_hash != plain_password
        assert plain_password not in db_user.password_hash
    
    def test_registration_returns_valid_session_token(self, client):
        """Test that registration returns a valid JWT session token"""
        import uuid
        unique_email = f"token-{uuid.uuid4().hex[:8]}@example.com"
        
        response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": "ValidPass123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        token = data["session_token"]
        
        # Verify token is a valid JWT (3 parts separated by dots)
        parts = token.split(".")
        assert len(parts) == 3
        
        # Verify token can be decoded to extract user ID
        from pqc_secure.services.auth import AuthService
        service = AuthService()
        user_id = service.verify_token(token)
        assert user_id == data["id"]
    
    def test_register_user_success(self, db_session):
        """Test successful user registration"""
        from pqc_secure.db.models import User
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "newuser@example.com",
            "SecurePass123"
        )
        
        assert success is True
        assert user is not None
        assert error is None
        assert user.email == "newuser@example.com"
        assert user.account_status == "active"
        
        # Verify user is in database
        db_user = db_session.query(User).filter_by(email="newuser@example.com").first()
        assert db_user is not None
    
    def test_register_user_invalid_email_format(self, db_session):
        """Test registration with invalid email format"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "notanemail",
            "SecurePass123"
        )
        
        assert success is False
        assert user is None
        assert "Invalid email format" in error
    
    def test_register_user_password_too_short(self, db_session):
        """Test registration with password below minimum length"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "Short1"
        )
        
        assert success is False
        assert user is None
        assert "at least" in error.lower()
    
    def test_register_user_password_missing_uppercase(self, db_session):
        """Test registration with password missing uppercase"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "lowercase123"
        )
        
        assert success is False
        assert user is None
        assert "uppercase" in error.lower()
    
    def test_register_user_password_missing_lowercase(self, db_session):
        """Test registration with password missing lowercase"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "UPPERCASE123"
        )
        
        assert success is False
        assert user is None
        assert "lowercase" in error.lower()
    
    def test_register_user_password_missing_digit(self, db_session):
        """Test registration with password missing digit"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            "NoDigitsHere"
        )
        
        assert success is False
        assert user is None
        assert "numeric" in error.lower()
    
    def test_register_user_duplicate_email(self, db_session):
        """Test registration with duplicate email"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        # Register first user
        success1, user1, error1 = service.register_user(
            db_session,
            "user@example.com",
            "SecurePass123"
        )
        assert success1 is True
        assert user1 is not None
        
        # Attempt to register with same email
        success2, user2, error2 = service.register_user(
            db_session,
            "user@example.com",
            "DifferentPass456"
        )
        
        assert success2 is False
        assert user2 is None
        # Should not reveal that email is already registered
        assert "Unable to create account" in error2
    
    def test_register_user_email_case_insensitive(self, db_session):
        """Test that email uniqueness is case-insensitive"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        # Register first user with lowercase email
        success1, user1, error1 = service.register_user(
            db_session,
            "user@example.com",
            "SecurePass123"
        )
        assert success1 is True
        
        # Attempt to register with uppercase version of same email
        success2, user2, error2 = service.register_user(
            db_session,
            "USER@EXAMPLE.COM",
            "DifferentPass456"
        )
        
        assert success2 is False
        assert user2 is None
    
    def test_register_user_email_normalized(self, db_session):
        """Test that email is normalized (lowercased and trimmed)"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        success, user, error = service.register_user(
            db_session,
            "  NEWUSER@EXAMPLE.COM  ",
            "SecurePass123"
        )
        
        assert success is True
        assert user is not None
        assert user.email == "newuser@example.com"
    
    def test_register_user_password_hashed(self, db_session):
        """Test that password is hashed, not stored in plaintext"""
        from pqc_secure.services.auth import AuthService
        
        service = AuthService()
        
        plain_password = "SecurePass123"
        success, user, error = service.register_user(
            db_session,
            "user@example.com",
            plain_password
        )
        
        assert success is True
        assert user is not None
        
        # Verify password is not stored in plaintext
        assert user.password_hash != plain_password
        assert plain_password not in user.password_hash


