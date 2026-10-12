"""Tests for session management, cookie flags, and session lifecycle"""
import pytest
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import jwt

from pqc_secure.db.models import Base, User, AuditLog, AuditEventType
from pqc_secure.core.config import settings
from pqc_secure.services.auth import AuthService


@pytest.fixture
def db_session():
    """Create an SQLite database session for testing"""
    engine = create_engine("sqlite:///test_session_pqc.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    
    import os
    try:
        if os.path.exists("test_session_pqc.db"):
            time.sleep(0.1)
            os.remove("test_session_pqc.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def reset_rate_limiter():
    """Reset rate limiter before each test"""
    from pqc_secure.middleware.rate_limit import rate_limiter
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()
    yield
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()


@pytest.fixture
def client(db_session, reset_rate_limiter):
    """Create a FastAPI test client with mocked database"""
    from pqc_secure.main import app
    from pqc_secure.db.session import get_db_session
    
    app.dependency_overrides[get_db_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestSessionCookieAndFlags:
    """Test session cookie setting, flags, and lifecycle"""

    def test_register_sets_secure_cookie(self, client):
        """Test registration sets session_token cookie with proper flags"""
        response = client.post(
            "/auth/register",
            json={
                "email": "cookies_reg@example.com",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 201
        assert "session_token" in response.cookies
        
        cookie_header = response.headers.get("set-cookie", "")
        assert "session_token=" in cookie_header
        assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()

    def test_login_sets_secure_cookie(self, client):
        """Test login sets session_token cookie with proper flags"""
        client.post(
            "/auth/register",
            json={
                "email": "cookies_login@example.com",
                "password": "SecurePass123"
            }
        )

        response = client.post(
            "/auth/login",
            json={
                "email": "cookies_login@example.com",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 200
        assert "session_token" in response.cookies

        cookie_header = response.headers.get("set-cookie", "")
        assert "session_token=" in cookie_header
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()


class TestSessionValidationAndProfile:
    """Test session validation via Bearer token and cookie, and /auth/me"""

    def test_me_endpoint_with_bearer_token(self, client):
        """Test /auth/me succeeds with Bearer token"""
        reg = client.post(
            "/auth/register",
            json={
                "email": "bearer_test@example.com",
                "password": "SecurePass123"
            }
        )
        token = reg.json()["session_token"]
        user_id = reg.json()["id"]

        # Call /auth/me with Authorization header
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == "bearer_test@example.com"
        assert data["account_status"] == "active"

    def test_me_endpoint_with_cookie(self, client):
        """Test /auth/me succeeds with session_token cookie"""
        reg = client.post(
            "/auth/register",
            json={
                "email": "cookie_auth@example.com",
                "password": "SecurePass123"
            }
        )
        token = reg.json()["session_token"]

        # Make request using cookie
        client.cookies.set("session_token", token)
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "cookie_auth@example.com"

    def test_me_endpoint_unauthenticated(self, client):
        """Test /auth/me fails when no token or cookie provided"""
        client.cookies.clear()
        response = client.get("/auth/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_me_endpoint_invalid_token(self, client):
        """Test /auth/me fails with invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.fake.token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_me_endpoint_expired_token(self, client, db_session):
        """Test /auth/me fails with expired token message"""
        auth_service = AuthService()
        reg_success, user, _ = auth_service.register_user(
            db_session,
            "expired_user@example.com",
            "SecurePass123"
        )
        assert reg_success is True

        # Generate expired token (-5 minutes)
        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": str(user.id),
            "exp": now - timedelta(minutes=5),
            "iat": now - timedelta(minutes=10)
        }
        expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"

    def test_me_endpoint_suspended_user(self, client, db_session):
        """Test /auth/me fails if account is suspended"""
        reg = client.post(
            "/auth/register",
            json={
                "email": "suspended_me@example.com",
                "password": "SecurePass123"
            }
        )
        token = reg.json()["session_token"]
        user_id = reg.json()["id"]

        user = db_session.query(User).filter_by(id=user_id).first()
        user.account_status = "suspended"
        db_session.commit()

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Account is not active"


class TestLogoutEndpoint:
    """Test /auth/logout endpoint and audit logging"""

    def test_logout_clears_cookie_and_audits(self, client, db_session):
        """Test logout clears session cookie and logs audit event"""
        reg = client.post(
            "/auth/register",
            json={
                "email": "logout_test@example.com",
                "password": "SecurePass123"
            }
        )
        token = reg.json()["session_token"]
        user_id = reg.json()["id"]

        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Check Set-Cookie deletes session_token
        set_cookie = response.headers.get("set-cookie", "")
        assert "session_token=" in set_cookie
        # Cookie expiration or max-age=0 indicates deletion
        assert "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()

        # Check audit log in database
        audit_entry = db_session.query(AuditLog).filter_by(
            user_id=user_id,
            event_type=AuditEventType.USER_LOGOUT
        ).first()
        assert audit_entry is not None
        assert audit_entry.status == "success"
