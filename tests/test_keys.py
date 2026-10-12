"""Comprehensive integration and unit tests for Key Management API (Tasks 3.2, 3.3, 3.4, 3.5).

Covers:
- POST /keys/register (ML-KEM-768, ML-DSA-65, X25519, Ed25519, validations, 401/400)
- GET /keys/my-keys (list user's keys, version ordering)
- GET /keys/{key_id} (retrieve key by ID, 404 handling)
- GET /keys/user/{user_id} (recipient key discovery and algorithm filtering)
- POST /keys/{key_id}/rotate (version increment, superseded status, 403 on other user's key)
- POST /keys/{key_id}/revoke (revoked status, excluded from discovery, 403 unauthorized)
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.db.models import Base, User
from pqc_secure.services.auth import AuthService
from pqc_secure.services.crypto import CryptoService
from pqc_secure.main import app
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for testing."""
    engine = create_engine("sqlite:///test_keys_pqc.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    import os
    import time
    try:
        if os.path.exists("test_keys_pqc.db"):
            time.sleep(0.05)
            os.remove("test_keys_pqc.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def client(db_session):
    """Create FastAPI test client with mocked database dependencies."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user(db_session):
    """Create and return authenticated test user and JWT session token."""
    auth_service = AuthService()
    success, user, _ = auth_service.register_user(
        db=db_session,
        email="alice@example.com",
        password="SecurePassword123!",
    )
    token = auth_service.generate_token(user.id)
    return user, token


@pytest.fixture
def other_user(db_session):
    """Create and return a second test user and JWT token."""
    auth_service = AuthService()
    success, user, _ = auth_service.register_user(
        db=db_session,
        email="bob@example.com",
        password="SecurePassword123!",
    )
    token = auth_service.generate_token(user.id)
    return user, token


class TestKeyRegistration:
    """Tests for POST /keys/register endpoint (Task 3.2)."""

    def test_register_ml_kem_768_key_success(self, client, auth_user):
        """Test successful registration of ML-KEM-768 public key."""
        user, token = auth_user
        pub, _ = CryptoService.generate_keypair_kem()
        pub_b64 = CryptoService.encode_base64(pub)

        response = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": pub_b64,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["algorithm"] == "ml-kem-768"
        assert data["user_id"] == user.id
        assert data["version"] == 1
        assert data["status"] == "active"
        assert data["key_id"].startswith("ml-kem-768:")
        assert data["public_key_material"] == pub_b64

    def test_register_ml_dsa_65_key_success(self, client, auth_user):
        """Test successful registration of ML-DSA-65 signature public key."""
        user, token = auth_user
        pub, _ = CryptoService.generate_keypair_sig()
        pub_b64 = CryptoService.encode_base64(pub)

        response = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "ml-dsa-65",
                "public_key_material": pub_b64,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["algorithm"] == "ml-dsa-65"
        assert data["version"] == 1
        assert data["status"] == "active"

    def test_register_classical_keys_success(self, client, auth_user):
        """Test registering X25519 and Ed25519 keys."""
        _, token = auth_user

        # X25519
        x_pub, _ = CryptoService.generate_keypair_x25519()
        resp_x = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "x25519",
                "public_key_material": CryptoService.encode_base64(x_pub),
            },
        )
        assert resp_x.status_code == 201
        assert resp_x.json()["algorithm"] == "x25519"

        # Ed25519
        ed_pub, _ = CryptoService.generate_keypair_ed25519()
        resp_ed = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "ed25519",
                "public_key_material": CryptoService.encode_base64(ed_pub),
            },
        )
        assert resp_ed.status_code == 201
        assert resp_ed.json()["algorithm"] == "ed25519"

    def test_register_invalid_algorithm_rejected(self, client, auth_user):
        """Test registration with unsupported algorithm returns 400."""
        _, token = auth_user
        response = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "rsa-2048",
                "public_key_material": "AAAA",
            },
        )
        assert response.status_code == 400
        assert "Unsupported algorithm" in response.json()["detail"]

    def test_register_invalid_public_key_size_rejected(self, client, auth_user):
        """Test registration with corrupted/wrong-size public key returns 400."""
        _, token = auth_user
        bad_b64 = CryptoService.encode_base64(b"too_short")
        response = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": bad_b64,
            },
        )
        assert response.status_code == 400

    def test_register_unauthenticated_rejected(self, client):
        """Test registration without auth token returns 401."""
        response = client.post(
            "/keys/register",
            json={
                "algorithm": "x25519",
                "public_key_material": "AAAA",
            },
        )
        assert response.status_code == 401


class TestKeyRetrievalAndDiscovery:
    """Tests for GET /keys/my-keys, /keys/{key_id}, and /keys/user/{user_id} (Task 3.3)."""

    def test_list_my_keys(self, client, auth_user):
        """Test listing authenticated user's registered keys."""
        _, token = auth_user

        # Register two keys
        pub1, _ = CryptoService.generate_keypair_kem()
        pub2, _ = CryptoService.generate_keypair_x25519()

        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"algorithm": "ml-kem-768", "public_key_material": CryptoService.encode_base64(pub1)},
        )
        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"algorithm": "x25519", "public_key_material": CryptoService.encode_base64(pub2)},
        )

        response = client.get(
            "/keys/my-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        algorithms = [k["algorithm"] for k in data["keys"]]
        assert "ml-kem-768" in algorithms
        assert "x25519" in algorithms

    def test_get_key_by_id_success_and_not_found(self, client, auth_user):
        """Test retrieving specific key by ID and 404 for unknown ID."""
        _, token = auth_user
        pub, _ = CryptoService.generate_keypair_sig()
        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"algorithm": "ml-dsa-65", "public_key_material": CryptoService.encode_base64(pub)},
        )
        key_id = reg_resp.json()["key_id"]

        # Fetch existing key
        get_resp = client.get(
            f"/keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["key_id"] == key_id

        # Fetch non-existent key
        not_found_resp = client.get(
            "/keys/ml-dsa-65:nonexistent123456",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert not_found_resp.status_code == 404

    def test_discover_user_keys(self, client, auth_user, other_user):
        """Test recipient public key discovery with algorithm filtering."""
        alice, alice_token = auth_user
        bob, bob_token = other_user

        # Alice registers a KEM and an Ed25519 key
        kem_pub, _ = CryptoService.generate_keypair_kem()
        ed_pub, _ = CryptoService.generate_keypair_ed25519()

        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"algorithm": "ml-kem-768", "public_key_material": CryptoService.encode_base64(kem_pub)},
        )
        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"algorithm": "ed25519", "public_key_material": CryptoService.encode_base64(ed_pub)},
        )

        # Bob discovers Alice's keys
        disc_resp = client.get(
            f"/keys/user/{alice.id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert disc_resp.status_code == 200
        assert disc_resp.json()["total"] == 2

        # Bob filters for only ML-KEM-768 keys
        filter_resp = client.get(
            f"/keys/user/{alice.id}?algorithm=ml-kem-768",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert filter_resp.status_code == 200
        assert filter_resp.json()["total"] == 1
        assert filter_resp.json()["keys"][0]["algorithm"] == "ml-kem-768"


class TestKeyRotationAndRevocation:
    """Tests for POST /keys/{key_id}/rotate and /revoke (Tasks 3.4, 3.5)."""

    def test_rotate_key_success(self, client, auth_user):
        """Test rotating a key creates new version and supersedes previous version."""
        _, token = auth_user
        pub1, _ = CryptoService.generate_keypair_kem()

        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"algorithm": "ml-kem-768", "public_key_material": CryptoService.encode_base64(pub1)},
        )
        old_key_id = reg_resp.json()["key_id"]
        assert reg_resp.json()["version"] == 1

        # Rotate key
        rot_resp = client.post(
            f"/keys/{old_key_id}/rotate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rot_resp.status_code == 200
        new_key_data = rot_resp.json()
        assert new_key_data["version"] == 2
        assert new_key_data["status"] == "active"
        assert new_key_data["key_id"] != old_key_id

        # Check old key is marked superseded
        old_key_check = client.get(
            f"/keys/{old_key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert old_key_check.json()["status"] == "superseded"

    def test_rotate_other_user_key_forbidden(self, client, auth_user, other_user):
        """Test rotating another user's key returns 403 Forbidden."""
        _, alice_token = auth_user
        _, bob_token = other_user

        pub, _ = CryptoService.generate_keypair_x25519()
        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"algorithm": "x25519", "public_key_material": CryptoService.encode_base64(pub)},
        )
        alice_key_id = reg_resp.json()["key_id"]

        # Bob attempts to rotate Alice's key
        hack_resp = client.post(
            f"/keys/{alice_key_id}/rotate",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert hack_resp.status_code == 403

    def test_revoke_key_and_exclusion_from_discovery(self, client, auth_user, other_user):
        """Test revoking key marks it revoked and excludes it from discovery."""
        alice, alice_token = auth_user
        _, bob_token = other_user

        pub, _ = CryptoService.generate_keypair_sig()
        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"algorithm": "ml-dsa-65", "public_key_material": CryptoService.encode_base64(pub)},
        )
        key_id = reg_resp.json()["key_id"]

        # Revoke key
        rev_resp = client.post(
            f"/keys/{key_id}/revoke",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"reason": "Suspected device compromise"},
        )
        assert rev_resp.status_code == 200
        assert rev_resp.json()["status"] == "revoked"

        # Check key status
        key_resp = client.get(f"/keys/{key_id}", headers={"Authorization": f"Bearer {alice_token}"})
        assert key_resp.json()["status"] == "revoked"

        # Bob discovers Alice's active keys - should be empty!
        disc_resp = client.get(f"/keys/user/{alice.id}", headers={"Authorization": f"Bearer {bob_token}"})
        assert disc_resp.json()["total"] == 0

    def test_revoke_other_user_key_forbidden(self, client, auth_user, other_user):
        """Test revoking another user's key returns 403 Forbidden."""
        _, alice_token = auth_user
        _, bob_token = other_user

        pub, _ = CryptoService.generate_keypair_ed25519()
        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"algorithm": "ed25519", "public_key_material": CryptoService.encode_base64(pub)},
        )
        alice_key_id = reg_resp.json()["key_id"]

        # Bob attempts to revoke Alice's key
        hack_resp = client.post(
            f"/keys/{alice_key_id}/revoke",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert hack_resp.status_code == 403

    def test_cannot_rotate_revoked_key(self, client, auth_user):
        """Test that rotating an already revoked key returns 400 Bad Request."""
        _, token = auth_user
        pub, _ = CryptoService.generate_keypair_kem()
        reg_resp = client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"algorithm": "ml-kem-768", "public_key_material": CryptoService.encode_base64(pub)},
        )
        key_id = reg_resp.json()["key_id"]

        client.post(f"/keys/{key_id}/revoke", headers={"Authorization": f"Bearer {token}"})

        # Try rotating
        rot_resp = client.post(f"/keys/{key_id}/rotate", headers={"Authorization": f"Bearer {token}"})
        assert rot_resp.status_code == 400
