"""
Test suite for Phase 9: Security & Hardening.

Covers:
- 9.1 CORS, Security Headers, and CSRF Protection
- 9.2 Input Validation & Sanitization (emails, filenames, algorithms, dangerous extensions)
- 9.3 Standardized Error Handling & Information Disclosure Prevention
- 9.4 Secrets Management & Session Hardening
"""
import io
import logging
import pytest
from fastapi.testclient import TestClient

from pqc_secure.core.config import settings
from pqc_secure.core.logging import SecretFilteringFormatter
from pqc_secure.core.validation import (
    sanitize_filename,
    sanitize_text,
    validate_algorithm_selection,
    validate_crypto_mode,
    validate_email_format,
    validate_file_security,
)
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pqc_secure.db.models import Base
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db
from pqc_secure.main import app
from pqc_secure.middleware.rate_limit import rate_limiter
from pqc_secure.services.crypto import CryptoService


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Clear in-memory rate limiter history before and after each test."""
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()
    yield
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for security testing."""
    engine = create_engine("sqlite:///test_security.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    try:
        if os.path.exists("test_security.db"):
            time.sleep(0.05)
            os.remove("test_security.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def test_client(db_session):
    """Create test client for security testing with database dependency overrides."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_session(test_client):
    """Register and login a test user, returning auth token and user dict."""
    import uuid
    email = f"secuser_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    resp = test_client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201
    data = resp.json()
    token = data["session_token"]
    user_id = data["id"]
    return {"email": email, "token": token, "user_id": user_id}


class TestSecurityHeadersAndCORS:
    """9.1: Test CORS, defense-in-depth security headers, and CSRF protection."""

    def test_security_headers_present_on_all_responses(self, test_client):
        """Verify standard security headers are attached to API responses."""
        resp = test_client.get("/health")
        assert resp.status_code == 200

        # Check defensive security headers
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")
        assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")

    def test_cors_allowed_origin(self, test_client):
        """Verify preflight requests from configured origins are accepted."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        resp = test_client.options("/auth/login", headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_disallowed_origin(self, test_client):
        """Verify requests from unauthorized origins do not receive CORS allow header."""
        headers = {
            "Origin": "http://evil-attacker-site.com",
            "Access-Control-Request-Method": "POST",
        }
        resp = test_client.options("/auth/login", headers=headers)
        # Unauthorized origin must not be reflected in access-control-allow-origin
        assert resp.headers.get("access-control-allow-origin") != "http://evil-attacker-site.com"

    def test_csrf_protection_blocks_cookie_auth_from_foreign_origin(self, test_client, authenticated_session):
        """Verify cookie-authenticated state-changing POST from untrusted origin is rejected."""
        test_client.cookies.set("session_token", authenticated_session["token"])

        # Attempt POST with malicious Origin header and cookie auth
        headers = {
            "Origin": "http://malicious-website.com",
        }
        resp = test_client.post(
            "/keys/register",
            json={"algorithm": "ml-kem-768"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "CSRF validation failed" in resp.json()["detail"]

    def test_csrf_protection_allows_bearer_token(self, test_client, authenticated_session):
        """Verify Authorization: Bearer token requests are exempt from CSRF checks."""
        headers = {
            "Authorization": f"Bearer {authenticated_session['token']}",
            "Origin": "http://some-client-origin.com",
        }
        resp = test_client.post(
            "/keys/register",
            json={"algorithm": "ml-kem-768"},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_csrf_protection_allows_valid_origin_with_cookie(self, test_client, authenticated_session):
        """Verify cookie requests with valid allowed origin succeed."""
        test_client.cookies.set("session_token", authenticated_session["token"])
        headers = {
            "Origin": "http://localhost:3000",
        }
        resp = test_client.post(
            "/keys/register",
            json={"algorithm": "x25519"},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_csrf_protection_allows_custom_csrf_header(self, test_client, authenticated_session):
        """Verify cookie requests with X-CSRF-Token or X-Requested-With succeed."""
        test_client.cookies.set("session_token", authenticated_session["token"])
        headers = {
            "X-Requested-With": "XMLHttpRequest",
        }
        resp = test_client.post(
            "/keys/register",
            json={"algorithm": "ed25519"},
            headers=headers,
        )
        assert resp.status_code == 201


class TestInputValidationAndSanitization:
    """9.2: Test input sanitization, email validation, file constraints, and algorithm checking."""

    def test_sanitize_text_strips_html_and_scripts(self):
        """Verify HTML tags, script elements, and control characters are stripped."""
        dirty = "<script>alert('xss')</script>Hello <b>World</b>!\x00\x08"
        clean = sanitize_text(dirty)
        assert "<script>" not in clean
        assert "alert('xss')" in clean
        assert "<b>" not in clean
        assert clean.startswith("alert('xss')Hello World!")
        assert "\x00" not in clean

    def test_sanitize_filename_traversal_prevention(self):
        """Verify directory traversal patterns and unsafe characters are neutralized."""
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe") == "cmd.exe"
        assert sanitize_filename("my file (1) [test].pdf") == "my_file__1___test_.pdf"
        assert sanitize_filename("") == "uploaded_file.bin"
        assert sanitize_filename(None) == "uploaded_file.bin"

    def test_email_validation_strict(self):
        """Verify email format validation rejects invalid patterns and normalizes."""
        assert validate_email_format("  USER@Example.COM  ") == "user@example.com"
        assert validate_email_format("alice.smith+pqc@sub.domain.org") == "alice.smith+pqc@sub.domain.org"

        # Invalid emails
        with pytest.raises(ValueError):
            validate_email_format("not-an-email")
        with pytest.raises(ValueError):
            validate_email_format("user@")
        with pytest.raises(ValueError):
            validate_email_format("@domain.com")
        with pytest.raises(ValueError):
            validate_email_format("user..name@domain.com")
        with pytest.raises(ValueError):
            validate_email_format("")

    def test_file_security_blocks_executable_extensions(self):
        """Verify dangerous executables and scripts are blocked from upload."""
        dangerous_names = ["malware.exe", "script.bat", "trojan.dll", "hack.ps1", "payload.sh"]
        for name in dangerous_names:
            with pytest.raises(ValueError, match="not permitted"):
                validate_file_security(name, 1024)

        # Safe files pass
        validate_file_security("report.pdf", 1024)
        validate_file_security("dataset.csv", 2048)

    def test_file_security_enforces_size_limit(self):
        """Verify file size limit is strictly enforced."""
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        # Exceeds limit
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_file_security("big.iso", max_bytes + 1)

        # Within limit
        validate_file_security("good.bin", max_bytes)

    def test_algorithm_validation_strict(self):
        """Verify algorithm validation allows only recognized primitives."""
        assert validate_algorithm_selection("ML-KEM-768") == "ml-kem-768"
        assert validate_algorithm_selection("x25519") == "x25519"
        assert validate_algorithm_selection("ml-dsa-65", category="signature") == "ml-dsa-65"
        assert validate_algorithm_selection("ed25519", category="signature") == "ed25519"

        # Invalid algorithm strings
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            validate_algorithm_selection("rsa-512")
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            validate_algorithm_selection("md5")
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            validate_algorithm_selection("drop_table;--")

        # Wrong category
        with pytest.raises(ValueError, match="not a valid key establishment"):
            validate_algorithm_selection("ml-dsa-65", category="kem")

    def test_crypto_mode_validation(self):
        """Verify crypto mode validation accepts only pqc or classical."""
        assert validate_crypto_mode("pqc") == "pqc"
        assert validate_crypto_mode("CLASSICAL") == "classical"
        with pytest.raises(ValueError, match="Encryption mode must be"):
            validate_crypto_mode("quantum_magic")

    def test_api_upload_rejects_dangerous_executable(self, test_client, authenticated_session):
        """Verify the upload endpoint rejects executable files with 400 Bad Request."""
        headers = {"Authorization": f"Bearer {authenticated_session['token']}"}
        fake_exe = io.BytesIO(b"MZ\x90\x00executable content")
        files = {"file": ("malware.exe", fake_exe, "application/octet-stream")}

        resp = test_client.post("/files/upload", files=files, headers=headers)
        assert resp.status_code == 400
        assert "not permitted" in resp.json()["detail"].lower()

    def test_api_share_rejects_invalid_email(self, test_client, authenticated_session):
        """Verify the share endpoint rejects malformed recipient emails with 400."""
        headers = {"Authorization": f"Bearer {authenticated_session['token']}"}
        payload = {
            "upload_id": "test-upload-id",
            "recipient_emails": ["not-a-valid-email"],
            "encryption_mode": "pqc",
        }
        resp = test_client.post("/files/share", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "invalid email" in resp.json()["detail"].lower()

    def test_api_register_key_rejects_invalid_algorithm(self, test_client, authenticated_session):
        """Verify register key rejects unsupported algorithm selections with 400."""
        headers = {"Authorization": f"Bearer {authenticated_session['token']}"}
        resp = test_client.post(
            "/keys/register",
            json={"algorithm": "insecure-des"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "unsupported algorithm" in resp.json()["detail"].lower()


class TestErrorHandlingAndInformationDisclosure:
    """9.3: Test consistent error format and prevention of internal information leakage."""

    def test_consistent_error_response_format_404(self, test_client):
        """Verify 404 response follows standardized schema with status_code and error fields."""
        resp = test_client.get("/non-existent-endpoint-12345")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert data["status_code"] == 404
        assert data["error"] == "NOT_FOUND"

    def test_validation_error_format_422(self, test_client):
        """Verify 422 schema validation errors provide clean structure."""
        # Send empty payload to endpoint requiring fields
        resp = test_client.post("/auth/register", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data
        assert data["status_code"] == 422
        assert data["error"] == "UNPROCESSABLE_ENTITY"
        assert "errors" in data

    def test_validation_error_does_not_leak_password_in_input(self, test_client):
        """Verify validation errors redact sensitive field values."""
        resp = test_client.post("/auth/register", json={"email": "invalid-email", "password": "supersecretpassword123"})
        data = resp.json()
        # Ensure password value is not reflected in error inputs
        for err in data.get("errors", []):
            loc = err.get("loc", [])
            if "password" in loc:
                assert err.get("input") != "supersecretpassword123"

    def test_auth_login_uniform_error_message(self, test_client):
        """Verify authentication failure returns generic message preventing user enumeration."""
        resp = test_client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "Password123!"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"


class TestSecretsManagementAndSessionSecurity:
    """9.4: Test zero leakage of private keys, shared secrets, and passwords in logs/sessions."""

    def test_secret_filtering_formatter_redacts_credentials(self):
        """Verify SecretFilteringFormatter redacts passwords, tokens, and keys from logs."""
        formatter = SecretFilteringFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='User login with password="SuperSecretPassword!" and token=eyJhbGciOiJIUzI1NiJ9',
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "SuperSecretPassword!" not in formatted
        assert "eyJhbGciOiJIUzI1NiJ9" not in formatted
        assert "[REDACTED]" in formatted

    def test_key_response_never_contains_private_key_material(self, test_client, authenticated_session):
        """Verify key retrieval responses never expose private key bytes."""
        headers = {"Authorization": f"Bearer {authenticated_session['token']}"}
        resp = test_client.post("/keys/register", json={"algorithm": "ml-kem-768"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()

        # Public key is present, private key must NEVER be in response
        assert "public_key_material" in data
        assert "private_key_material" not in data
        assert "private_key" not in data

        # Check get key
        key_id = data["key_id"]
        get_resp = test_client.get(f"/keys/{key_id}", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert "private_key_material" not in get_data
        assert "private_key" not in get_data

    def test_session_cookie_attributes_are_secure(self, test_client):
        """Verify login sets HttpOnly and SameSite cookie attributes."""
        import uuid
        email = f"cookie_user_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "ComplexPassword123!"

        test_client.post("/auth/register", json={"email": email, "password": pwd})
        login_resp = test_client.post("/auth/login", json={"email": email, "password": pwd})
        assert login_resp.status_code == 200

        # Verify cookie headers
        set_cookie_header = login_resp.headers.get("set-cookie", "")
        assert "session_token" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "samesite=lax" in set_cookie_header.lower()
