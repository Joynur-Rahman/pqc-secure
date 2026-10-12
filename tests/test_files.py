"""Comprehensive integration and unit tests for File Upload & Encryption Pipeline (Phase 4).

Covers:
- POST /files/upload (single-shot, chunked uploads, size limits, 401)
- POST /files/share (PQC mode with ML-KEM-768 encapsulation, Classical mode with X25519)
- Recipient validation (active keys check, unknown recipients)
- GET /files (list accessible shared files)
- GET /files/{package_id} (metadata retrieval, 403 authorization check, 404)
"""
import io
import os
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.db.models import Base
from pqc_secure.services.auth import AuthService
from pqc_secure.services.crypto import CryptoService
from pqc_secure.services.key import KeyService
from pqc_secure.main import app
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for testing."""
    engine = create_engine("sqlite:///test_files_pqc.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    try:
        if os.path.exists("test_files_pqc.db"):
            time.sleep(0.05)
            os.remove("test_files_pqc.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def client(db_session):
    """Create FastAPI test client with mocked database dependencies."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()


@pytest.fixture
def alice(db_session):
    """Sender test user."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "alice@example.com", "Password123!")
    token = auth_service.generate_token(user.id)
    return user, token


@pytest.fixture
def bob(db_session):
    """Recipient test user with registered PQC and Classical keys."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "bob@example.com", "Password123!")
    token = auth_service.generate_token(user.id)

    # Register ML-KEM-768 key for Bob
    kem_pub, kem_priv = CryptoService.generate_keypair_kem()
    KeyService.register_key(
        db=db_session,
        user_id=user.id,
        algorithm="ml-kem-768",
        public_key_b64=CryptoService.encode_base64(kem_pub),
        private_key_b64=CryptoService.encode_base64(kem_priv),
    )

    # Register X25519 key for Bob
    x_pub, x_priv = CryptoService.generate_keypair_x25519()
    KeyService.register_key(
        db=db_session,
        user_id=user.id,
        algorithm="x25519",
        public_key_b64=CryptoService.encode_base64(x_pub),
        private_key_b64=CryptoService.encode_base64(x_priv),
    )

    return user, token


@pytest.fixture
def charlie(db_session):
    """Third party user without any shares."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "charlie@example.com", "Password123!")
    token = auth_service.generate_token(user.id)
    return user, token


class TestFileUpload:
    """Tests for POST /files/upload endpoint (Task 4.1)."""

    def test_single_shot_upload_success(self, client, alice):
        """Test uploading a single file completely."""
        _, token = alice
        file_content = b"Top secret post-quantum file content for secure exchange."

        response = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("secret.txt", io.BytesIO(file_content), "text/plain")},
            data={"chunk_number": 0, "total_chunks": 1},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "secret.txt"
        assert data["is_complete"] is True
        assert data["bytes_uploaded"] == len(file_content)
        assert len(data["upload_id"]) > 0

    def test_chunked_upload_assembly(self, client, alice):
        """Test uploading a file in two chunks."""
        _, token = alice
        part1 = b"Chunk 1: First part of large payload. "
        part2 = b"Chunk 2: Second part of large payload."

        # Upload chunk 0
        resp1 = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("large.dat", io.BytesIO(part1), "application/octet-stream")},
            data={"upload_id": "test-chunk-upload-123", "chunk_number": 0, "total_chunks": 2},
        )
        assert resp1.status_code == 201
        assert resp1.json()["is_complete"] is False

        # Upload chunk 1
        resp2 = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("large.dat", io.BytesIO(part2), "application/octet-stream")},
            data={"upload_id": "test-chunk-upload-123", "chunk_number": 1, "total_chunks": 2},
        )
        assert resp2.status_code == 201
        assert resp2.json()["is_complete"] is True
        assert resp2.json()["bytes_uploaded"] == len(part1) + len(part2)

    def test_upload_unauthenticated_rejected(self, client):
        """Test upload without authentication returns 401."""
        response = client.post(
            "/files/upload",
            files={"file": ("secret.txt", io.BytesIO(b"data"), "text/plain")},
        )
        assert response.status_code == 401


class TestFileEncryptionAndSharing:
    """Tests for POST /files/share encryption pipeline (Tasks 4.2, 4.3, 4.4)."""

    def test_share_file_pqc_mode_success(self, client, alice, bob):
        """Test encrypting and sharing file using ML-KEM-768 post-quantum mode."""
        _, alice_token = alice
        bob_user, _ = bob

        # 1. Upload file
        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("financial_report.pdf", io.BytesIO(b"Quarterly financial report data"), "application/pdf")},
        )
        upload_id = upload_resp.json()["upload_id"]

        # 2. Share with Bob using PQC mode
        share_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "pqc",
            },
        )

        assert share_resp.status_code == 201
        data = share_resp.json()
        assert data["crypto_mode"] == "pqc"
        assert data["original_filename"] == "financial_report.pdf"
        assert len(data["recipients"]) == 1
        assert data["recipients"][0]["recipient_id"] == bob_user.id
        assert data["recipients"][0]["recipient_email"] == "bob@example.com"
        assert "package_id" in data

    def test_share_file_classical_mode_success(self, client, alice, bob):
        """Test encrypting and sharing file using X25519 classical mode."""
        _, alice_token = alice

        # Upload file
        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("notes.txt", io.BytesIO(b"Confidential meeting notes"), "text/plain")},
        )
        upload_id = upload_resp.json()["upload_id"]

        # Share with Bob using Classical mode
        share_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "classical",
            },
        )

        assert share_resp.status_code == 201
        data = share_resp.json()
        assert data["crypto_mode"] == "classical"
        assert data["original_filename"] == "notes.txt"

    def test_share_recipient_missing_key_rejected(self, client, alice, charlie):
        """Test sharing with recipient who lacks required active key returns 400."""
        _, alice_token = alice

        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("file.txt", io.BytesIO(b"data"), "text/plain")},
        )
        upload_id = upload_resp.json()["upload_id"]

        # Charlie has no registered keys
        share_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_id,
                "recipient_emails": ["charlie@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert share_resp.status_code == 400
        assert "has no active ml-kem-768 key" in share_resp.json()["detail"]

    def test_share_unknown_recipient_rejected(self, client, alice):
        """Test sharing with non-existent email returns 400."""
        _, alice_token = alice

        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("doc.txt", io.BytesIO(b"data"), "text/plain")},
        )
        upload_id = upload_resp.json()["upload_id"]

        share_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_id,
                "recipient_emails": ["ghost@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert share_resp.status_code == 400


class TestFilePackageListingAndAccessControl:
    """Tests for GET /files and /files/{package_id}."""

    def test_list_and_get_file_access_control(self, client, alice, bob, charlie):
        """Test that sender and recipient can list and view package, while unauthorized user is denied."""
        _, alice_token = alice
        _, bob_token = bob
        _, charlie_token = charlie

        # Alice uploads and shares with Bob
        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("project_spec.pdf", io.BytesIO(b"Project specification details"), "application/pdf")},
        )
        package_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_resp.json()["upload_id"],
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "pqc",
            },
        )
        package_id = package_resp.json()["package_id"]

        # Alice lists files -> sees package
        alice_list = client.get("/files", headers={"Authorization": f"Bearer {alice_token}"})
        assert alice_list.status_code == 200
        assert alice_list.json()["total"] == 1

        # Bob lists files -> sees package
        bob_list = client.get("/files", headers={"Authorization": f"Bearer {bob_token}"})
        assert bob_list.status_code == 200
        assert bob_list.json()["total"] == 1

        # Charlie lists files -> sees 0 packages
        charlie_list = client.get("/files", headers={"Authorization": f"Bearer {charlie_token}"})
        assert charlie_list.status_code == 200
        assert charlie_list.json()["total"] == 0

        # Bob views specific metadata -> 200
        bob_meta = client.get(f"/files/{package_id}", headers={"Authorization": f"Bearer {bob_token}"})
        assert bob_meta.status_code == 200
        assert bob_meta.json()["package_id"] == package_id

        # Charlie views specific metadata -> 403 Forbidden
        charlie_meta = client.get(f"/files/{package_id}", headers={"Authorization": f"Bearer {charlie_token}"})
        assert charlie_meta.status_code == 403


class TestFileDownloadAndDecryption:
    """Comprehensive tests for Phase 5: File Download & Decryption Pipeline."""

    def test_download_pqc_file_success(self, client, alice, bob):
        """Test downloading and decrypting ML-KEM encrypted file as recipient."""
        _, alice_token = alice
        _, bob_token = bob
        original_data = b"Post-Quantum Encrypted Secret Payload 123456789"

        # 1. Alice uploads and shares with Bob in PQC mode
        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("secret_pqc.txt", io.BytesIO(original_data), "text/plain")},
        )
        package_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_resp.json()["upload_id"],
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "pqc",
            },
        )
        package_id = package_resp.json()["package_id"]

        # 2. Bob downloads the file
        download_resp = client.get(
            f"/files/{package_id}/download",
            headers={"Authorization": f"Bearer {bob_token}"},
        )

        assert download_resp.status_code == 200
        assert download_resp.content == original_data
        assert download_resp.headers.get("X-PQC-Decryption-Status") == "verified"
        assert 'filename="secret_pqc.txt"' in download_resp.headers.get("Content-Disposition", "")

    def test_download_classical_file_success(self, client, alice, bob):
        """Test downloading and decrypting X25519 encrypted file as recipient."""
        _, alice_token = alice
        _, bob_token = bob
        original_data = b"Classical X25519 Encrypted Payload with AES-GCM"

        # 1. Alice uploads and shares in Classical mode
        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("classical_spec.doc", io.BytesIO(original_data), "application/msword")},
        )
        package_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_resp.json()["upload_id"],
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "classical",
            },
        )
        package_id = package_resp.json()["package_id"]

        # 2. Bob downloads the file
        download_resp = client.get(
            f"/files/{package_id}/download",
            headers={"Authorization": f"Bearer {bob_token}"},
        )

        assert download_resp.status_code == 200
        assert download_resp.content == original_data
        assert download_resp.headers.get("X-PQC-Decryption-Status") == "verified"
        assert 'filename="classical_spec.doc"' in download_resp.headers.get("Content-Disposition", "")

    def test_download_unauthorized_access_denied(self, client, alice, bob, charlie):
        """Test that user without access grant receives 403 Forbidden."""
        _, alice_token = alice
        _, charlie_token = charlie

        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("secret.bin", io.BytesIO(b"Data"), "application/octet-stream")},
        )
        package_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_resp.json()["upload_id"],
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert package_resp.status_code == 201
        package_id = package_resp.json()["package_id"]

        # Charlie tries to download
        resp = client.get(
            f"/files/{package_id}/download",
            headers={"Authorization": f"Bearer {charlie_token}"},
        )
        assert resp.status_code == 403

    def test_download_nonexistent_package(self, client, bob):
        """Test downloading non-existent package returns 404."""
        _, bob_token = bob
        resp = client.get(
            "/files/non-existent-pkg-id/download",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 404

    def test_download_signature_tampering_rejected(self, client, alice, bob, db_session):
        """Test that tampered package manifest or signature fails verification."""
        from pqc_secure.db.models import FilePackage

        _, alice_token = alice
        _, bob_token = bob

        upload_resp = client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {alice_token}"},
            files={"file": ("tamper_test.txt", io.BytesIO(b"Sensory Data"), "text/plain")},
        )
        package_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "upload_id": upload_resp.json()["upload_id"],
                "recipient_emails": ["bob@example.com"],
                "encryption_mode": "pqc",
            },
        )
        package_id = package_resp.json()["package_id"]

        # Tamper the package signature in the database
        pkg = db_session.query(FilePackage).filter(FilePackage.id == package_id).first()
        pkg.signature = b"corrupted_invalid_signature" * 50
        db_session.commit()

        # Bob attempts download
        resp = client.get(
            f"/files/{package_id}/download",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 400
        assert "signature failed verification" in resp.json()["detail"].lower()

