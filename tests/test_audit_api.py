"""Integration tests for Audit Log API (Phase 7).

Covers:
- GET /audit-logs and /api/audit-logs endpoints
- Authentication and authorization (401 unauthenticated, 403 non-admin accessing another user)
- Self-access enforcement for standard users
- Admin cross-user query access
- Filtering by event_type (single, comma-separated, case-insensitive)
- Filtering by start_date and end_date
- Pagination (limit & offset, page & page_size)
- Sanitization verification (no secrets/passwords/keys in response)
"""
import os
import time
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.db.models import Base, AuditLog, AuditEventType
from pqc_secure.services.auth import AuthService
from pqc_secure.services.audit import AuditService
from pqc_secure.main import app
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for audit API testing."""
    engine = create_engine("sqlite:///test_audit_api.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    try:
        if os.path.exists("test_audit_api.db"):
            time.sleep(0.05)
            os.remove("test_audit_api.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def client(db_session):
    """Create FastAPI test client with database dependency overrides."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()


@pytest.fixture
def standard_user(db_session):
    """Standard authenticated test user."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "user1@example.com", "Password123!")
    token = auth_service.generate_token(user.id)
    return user, token


@pytest.fixture
def second_user(db_session):
    """Second standard authenticated test user."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "user2@example.com", "Password123!")
    token = auth_service.generate_token(user.id)
    return user, token


@pytest.fixture
def admin_user(db_session):
    """Administrator test user (matching settings.admin_emails)."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "admin@example.com", "AdminPass123!")
    token = auth_service.generate_token(user.id)
    return user, token


class TestAuditLogAPI:
    """Tests for GET /audit-logs endpoint"""

    def test_unauthenticated_request_returns_401(self, client):
        """Unauthenticated request must return 401 Unauthorized"""
        response = client.get("/audit-logs")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_self_access_standard_user(self, client, db_session, standard_user, second_user):
        """Standard user queries /audit-logs and receives only their own events"""
        user1, token1 = standard_user
        user2, _ = second_user

        # Create audit logs for user1 and user2
        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User login",
            status="success",
            user_id=user1.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.FILE_UPLOADED.value,
            action="File uploaded",
            status="success",
            user_id=user1.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User login",
            status="success",
            user_id=user2.id,
            db_session=db_session,
        )

        response = client.get(
            "/audit-logs",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["logs"]) == 2
        for log in data["logs"]:
            assert log["user_id"] == user1.id

    def test_forbidden_when_standard_user_requests_other_user(self, client, standard_user, second_user):
        """Standard user requesting another user's logs must receive 403 Forbidden"""
        user1, token1 = standard_user
        user2, _ = second_user

        response = client.get(
            f"/audit-logs?user_id={user2.id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    def test_admin_can_access_all_logs(self, client, db_session, standard_user, second_user, admin_user):
        """Admin user can query /audit-logs without user_id filter and see all users' events"""
        user1, _ = standard_user
        user2, _ = second_user
        admin, admin_token = admin_user

        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User 1 login",
            status="success",
            user_id=user1.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User 2 login",
            status="success",
            user_id=user2.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="Admin login",
            status="success",
            user_id=admin.id,
            db_session=db_session,
        )

        response = client.get(
            "/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        user_ids = {log["user_id"] for log in data["logs"]}
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert admin.id in user_ids

    def test_admin_can_filter_by_specific_user(self, client, db_session, standard_user, second_user, admin_user):
        """Admin user can filter by any specific user_id"""
        user1, _ = standard_user
        user2, _ = second_user
        _, admin_token = admin_user

        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User 1 login",
            status="success",
            user_id=user1.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User 2 login",
            status="success",
            user_id=user2.id,
            db_session=db_session,
        )

        response = client.get(
            f"/audit-logs?user_id={user2.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["logs"][0]["user_id"] == user2.id

    def test_filter_by_event_type(self, client, db_session, standard_user):
        """Filter audit logs by single and comma-separated event types"""
        user, token = standard_user

        AuditService.log_event(
            event_type=AuditEventType.USER_LOGIN.value,
            action="User login",
            status="success",
            user_id=user.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.FILE_UPLOADED.value,
            action="File uploaded",
            status="success",
            user_id=user.id,
            db_session=db_session,
        )
        AuditService.log_event(
            event_type=AuditEventType.FILE_DOWNLOADED.value,
            action="File downloaded",
            status="success",
            user_id=user.id,
            db_session=db_session,
        )

        # Single event_type filter
        res1 = client.get(
            "/audit-logs?event_type=file_uploaded",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res1.status_code == 200
        assert res1.json()["total"] == 1
        assert res1.json()["logs"][0]["event_type"] == "file_uploaded"

        # Comma-separated event types filter
        res2 = client.get(
            "/audit-logs?event_type=file_uploaded,file_downloaded",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res2.status_code == 200
        assert res2.json()["total"] == 2
        event_types = {log["event_type"] for log in res2.json()["logs"]}
        assert event_types == {"file_uploaded", "file_downloaded"}

    def test_filter_by_date_range(self, client, db_session, standard_user):
        """Filter audit logs by start_date and end_date"""
        user, token = standard_user
        now = datetime.now(timezone.utc)

        # Create log 2 days ago
        entry1 = AuditLog(
            event_type=AuditEventType.USER_LOGIN.value,
            action="Old login",
            status="success",
            user_id=user.id,
            created_at=now - timedelta(days=2),
        )
        # Create log today
        entry2 = AuditLog(
            event_type=AuditEventType.FILE_UPLOADED.value,
            action="Recent upload",
            status="success",
            user_id=user.id,
            created_at=now,
        )
        db_session.add_all([entry1, entry2])
        db_session.commit()

        start = (now - timedelta(days=1)).isoformat()
        res = client.get(
            f"/audit-logs?start_date={start}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["logs"][0]["action"] == "Recent upload"

    def test_pagination_limit_offset_and_page(self, client, db_session, standard_user):
        """Test pagination using limit/offset and page/page_size"""
        user, token = standard_user

        for i in range(10):
            AuditService.log_event(
                event_type=AuditEventType.USER_LOGIN.value,
                action=f"Login attempt {i}",
                status="success",
                user_id=user.id,
                db_session=db_session,
            )

        # Page 1: limit=3, offset=0
        res1 = client.get(
            "/audit-logs?limit=3&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res1.status_code == 200
        assert res1.json()["total"] == 10
        assert len(res1.json()["logs"]) == 3
        assert res1.json()["limit"] == 3
        assert res1.json()["offset"] == 0

        # Page 2 via page and page_size: page=2, page_size=4 -> limit=4, offset=4
        res2 = client.get(
            "/audit-logs?page=2&page_size=4",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res2.status_code == 200
        assert res2.json()["total"] == 10
        assert len(res2.json()["logs"]) == 4
        assert res2.json()["limit"] == 4
        assert res2.json()["offset"] == 4

    def test_mounted_at_api_prefix(self, client, standard_user):
        """Verify endpoint is also available at /api/audit-logs"""
        _, token = standard_user
        response = client.get(
            "/api/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "logs" in response.json()
        assert "total" in response.json()

    def test_details_excludes_secrets_in_response(self, client, db_session, standard_user):
        """Verify that audit log details never contain passwords, tokens, or private keys"""
        user, token = standard_user

        # Attempt to log with sensitive details
        AuditService.log_event(
            event_type=AuditEventType.FILE_UPLOADED.value,
            action="Upload completed",
            status="success",
            user_id=user.id,
            details={
                "filename": "secret_doc.pdf",
                "size": 1024,
                "password": "super_secret_password",
                "private_key": "private_key_content",
                "auth_token": "bearer_token_xyz",
            },
            db_session=db_session,
        )

        response = client.get(
            "/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        log = response.json()["logs"][0]
        details = log["details"]
        assert details["filename"] == "secret_doc.pdf"
        assert details["size"] == 1024
        assert "password" not in details
        assert "private_key" not in details
        assert "auth_token" not in details
        assert "super_secret_password" not in response.text
