"""End-to-End Integration and Security Testing Suite (Phase 10: 10.2 & 10.3).

Covers:
- Complete end-to-end lifecycle (Registration -> Login -> Key Generation & Registration ->
  Chunked File Upload -> PQC & Classical Sharing -> Metadata Retrieval -> Download & Decryption).
- Error scenarios (unregistered recipient, missing key, unauthenticated requests).
- Access control verification (cross-user access blocks, share revocation enforcement).
- Cryptographic tampering detection (ciphertext payload tampering, manifest metadata tampering,
  digital signature bit tampering, GCM nonce/tag tampering).
- Rate limiting and session security validation.
"""
from __future__ import annotations

import io
import json
import os
import time
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.main import app
from pqc_secure.db.models import (
    AuditEventType,
    AuditLog,
    Base,
    FilePackage,
    GrantStatus,
    User,
)
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db
from pqc_secure.middleware.rate_limit import rate_limiter
from pqc_secure.services.crypto import CryptoService
from pqc_secure.services.storage import storage_service


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for e2e tests."""
    db_file = f"test_e2e_{uuid.uuid4().hex[:8]}.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    try:
        if os.path.exists(db_file):
            time.sleep(0.05)
            os.remove(db_file)
    except (PermissionError, OSError):
        pass


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset rate limiter buckets before and after each test."""
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()
    yield
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()


@pytest.fixture
def client(db_session):
    """Create FastAPI test client with isolated database session overrides."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestE2EFullLifecycle:
    """10.2 Integration Tests: Full end-to-end user and cryptographic lifecycles."""

    def test_e2e_pqc_lifecycle_flow(self, client):
        """Complete PQC lifecycle:

        1. Register Alice & Bob.
        2. Authenticate Alice & Bob.
        3. Bob registers ML-KEM-768 public key.
        4. Alice registers ML-DSA-65 public key.
        5. Alice chunk-uploads a sensitive document.
        6. Alice shares document using PQC encryption mode.
        7. Bob discovers shared package in file listing.
        8. Bob inspects package metadata.
        9. Bob downloads and decrypts document.
        10. Assert plaintext matches original byte-for-byte.
        """
        # 1. Register Alice and Bob
        resp_alice_reg = client.post(
            "/auth/register",
            json={"email": "alice_pqc@example.com", "password": "SecurePassword123!"},
        )
        assert resp_alice_reg.status_code == 201
        alice_data = resp_alice_reg.json()
        assert alice_data["email"] == "alice_pqc@example.com"

        resp_bob_reg = client.post(
            "/auth/register",
            json={"email": "bob_pqc@example.com", "password": "SecurePassword123!"},
        )
        assert resp_bob_reg.status_code == 201
        bob_data = resp_bob_reg.json()
        assert bob_data["email"] == "bob_pqc@example.com"

        # 2. Login Alice and Bob
        rate_limiter.auth_limiter.request_history.clear()
        resp_alice_login = client.post(
            "/auth/login",
            json={"email": "alice_pqc@example.com", "password": "SecurePassword123!"},
        )
        assert resp_alice_login.status_code == 200
        alice_token = resp_alice_login.json()["session_token"]
        alice_auth = {"Authorization": f"Bearer {alice_token}"}

        resp_bob_login = client.post(
            "/auth/login",
            json={"email": "bob_pqc@example.com", "password": "SecurePassword123!"},
        )
        assert resp_bob_login.status_code == 200
        bob_token = resp_bob_login.json()["session_token"]
        bob_auth = {"Authorization": f"Bearer {bob_token}"}

        # 3. Bob registers ML-KEM-768 keypair
        bob_kem_pub, bob_kem_priv = CryptoService.generate_keypair_kem()
        resp_bob_key = client.post(
            "/keys/register",
            headers=bob_auth,
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(bob_kem_pub),
                "private_key_material": CryptoService.encode_base64(bob_kem_priv),
            },
        )
        assert resp_bob_key.status_code == 201
        assert resp_bob_key.json()["algorithm"] == "ml-kem-768"

        # 4. Alice registers ML-DSA-65 keypair
        alice_dsa_pub, alice_dsa_priv = CryptoService.generate_keypair_sig()
        resp_alice_key = client.post(
            "/keys/register",
            headers=alice_auth,
            json={
                "algorithm": "ml-dsa-65",
                "public_key_material": CryptoService.encode_base64(alice_dsa_pub),
                "private_key_material": CryptoService.encode_base64(alice_dsa_priv),
            },
        )
        assert resp_alice_key.status_code == 201
        assert resp_alice_key.json()["algorithm"] == "ml-dsa-65"

        # 5. Alice chunk-uploads a sensitive document
        upload_id = str(uuid.uuid4())
        chunk1 = b"TOP SECRET PQC REPORT PART 1: Post-quantum cryptography deployment is essential. "
        chunk2 = b"PART 2: Kyber/ML-KEM and Dilithium/ML-DSA protect against Shor's algorithm."
        original_content = chunk1 + chunk2

        # Upload Chunk 0
        resp_c0 = client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 2},
            files={"file": ("quantum_report.txt", io.BytesIO(chunk1), "text/plain")},
        )
        assert resp_c0.status_code == 201
        assert resp_c0.json()["is_complete"] is False

        # Upload Chunk 1
        resp_c1 = client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 1, "total_chunks": 2},
            files={"file": ("quantum_report.txt", io.BytesIO(chunk2), "text/plain")},
        )
        assert resp_c1.status_code == 201
        assert resp_c1.json()["is_complete"] is True

        # 6. Alice shares document using PQC encryption mode with Bob
        resp_share = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob_pqc@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert resp_share.status_code == 201
        package_info = resp_share.json()
        package_id = package_info["package_id"]
        assert package_info["crypto_mode"] == "pqc"
        assert package_info["original_filename"] == "quantum_report.txt"

        # 7. Bob discovers package in file listing
        resp_list = client.get("/files", headers=bob_auth)
        assert resp_list.status_code == 200
        packages = resp_list.json()["packages"]
        assert any(p["package_id"] == package_id for p in packages)

        # 8. Bob inspects package metadata
        resp_meta = client.get(f"/files/{package_id}", headers=bob_auth)
        assert resp_meta.status_code == 200
        meta = resp_meta.json()
        assert meta["sender_email"] == "alice_pqc@example.com"
        assert meta["crypto_mode"] == "pqc"

        # 9. Bob downloads and decrypts document
        resp_download = client.get(f"/files/{package_id}/download", headers=bob_auth)
        assert resp_download.status_code == 200
        assert "attachment" in resp_download.headers.get("content-disposition", "")
        assert "quantum_report.txt" in resp_download.headers.get("content-disposition", "")

        # 10. Plaintext matches exactly
        assert resp_download.content == original_content

    def test_e2e_classical_lifecycle_flow(self, client):
        """Complete Classical lifecycle:

        1. Register Alice & Bob.
        2. Authenticate users.
        3. Bob registers X25519 keypair.
        4. Alice registers Ed25519 keypair.
        5. Alice uploads file.
        6. Alice shares file via classical encryption mode.
        7. Bob downloads and decrypts file.
        8. Assert decrypted content matches original plaintext.
        """
        # Register & Login
        r_a = client.post("/auth/register", json={"email": "alice_classic@example.com", "password": "Password123!"})
        r_b = client.post("/auth/register", json={"email": "bob_classic@example.com", "password": "Password123!"})
        alice_token = r_a.json()["session_token"]
        bob_token = r_b.json()["session_token"]

        alice_auth = {"Authorization": f"Bearer {alice_token}"}
        bob_auth = {"Authorization": f"Bearer {bob_token}"}

        # Bob registers X25519 key
        x_pub, x_priv = CryptoService.generate_keypair_x25519()
        client.post(
            "/keys/register",
            headers=bob_auth,
            json={
                "algorithm": "x25519",
                "public_key_material": CryptoService.encode_base64(x_pub),
                "private_key_material": CryptoService.encode_base64(x_priv),
            },
        )

        # Alice registers Ed25519 key
        ed_pub, ed_priv = CryptoService.generate_keypair_ed25519()
        client.post(
            "/keys/register",
            headers=alice_auth,
            json={
                "algorithm": "ed25519",
                "public_key_material": CryptoService.encode_base64(ed_pub),
                "private_key_material": CryptoService.encode_base64(ed_priv),
            },
        )

        # Upload file
        upload_id = str(uuid.uuid4())
        plaintext = b"Classical cryptography benchmark payload using X25519 and Ed25519."
        upload_resp = client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("classical.txt", io.BytesIO(plaintext), "text/plain")},
        )
        assert upload_resp.status_code == 201

        # Share file
        share_resp = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob_classic@example.com"],
                "encryption_mode": "classical",
            },
        )
        assert share_resp.status_code == 201
        package_id = share_resp.json()["package_id"]
        assert share_resp.json()["crypto_mode"] == "classical"

        # Download & verify
        download_resp = client.get(f"/files/{package_id}/download", headers=bob_auth)
        assert download_resp.status_code == 200
        assert download_resp.content == plaintext


class TestE2EErrorScenariosAndAccessControl:
    """10.2 Integration Tests: Error scenarios and access control boundaries."""

    def test_missing_recipient_keys_error(self, client):
        """Alice sharing with a user who lacks active keys for chosen mode fails gracefully."""
        r_a = client.post("/auth/register", json={"email": "alice_nokey@example.com", "password": "Password123!"})
        client.post("/auth/register", json={"email": "bob_nokey@example.com", "password": "Password123!"})
        alice_token = r_a.json()["session_token"]
        alice_auth = {"Authorization": f"Bearer {alice_token}"}

        upload_id = str(uuid.uuid4())
        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        )

        resp = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob_nokey@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert resp.status_code == 400
        assert "no active" in resp.json()["detail"].lower()

    def test_unregistered_recipient_error(self, client):
        """Sharing with nonexistent email is rejected."""
        r_a = client.post("/auth/register", json={"email": "alice_unreg@example.com", "password": "Password123!"})
        alice_token = r_a.json()["session_token"]
        alice_auth = {"Authorization": f"Bearer {alice_token}"}

        upload_id = str(uuid.uuid4())
        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        )

        resp = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["ghost_user@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert resp.status_code == 400
        assert "recipient" in resp.json()["detail"].lower()

    def test_unauthorized_third_party_access_blocked(self, client):
        """Charlie cannot read metadata or download package shared between Alice and Bob."""
        # Register Alice, Bob, Charlie using session_token directly from registration response
        a_token = client.post("/auth/register", json={"email": "alice_sec@example.com", "password": "Password123!"}).json()["session_token"]
        b_token = client.post("/auth/register", json={"email": "bob_sec@example.com", "password": "Password123!"}).json()["session_token"]
        c_token = client.post("/auth/register", json={"email": "charlie_sec@example.com", "password": "Password123!"}).json()["session_token"]

        # Bob registers PQC key
        k_pub, k_priv = CryptoService.generate_keypair_kem()
        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {b_token}"},
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(k_pub),
                "private_key_material": CryptoService.encode_base64(k_priv),
            },
        )

        # Alice uploads and shares
        upload_id = str(uuid.uuid4())
        client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {a_token}"},
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("secret.txt", io.BytesIO(b"Confidential"), "text/plain")},
        )
        pkg_id = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {a_token}"},
            json={"upload_id": upload_id, "recipient_emails": ["bob_sec@example.com"], "encryption_mode": "pqc"},
        ).json()["package_id"]

        # Charlie attempts metadata read -> 403 Forbidden
        resp_meta = client.get(f"/files/{pkg_id}", headers={"Authorization": f"Bearer {c_token}"})
        assert resp_meta.status_code == 403

        # Charlie attempts download -> 403 Forbidden
        resp_down = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {c_token}"})
        assert resp_down.status_code == 403

    def test_revocation_lifecycle_enforcement(self, client, db_session):
        """Alice revokes Bob's grant; Bob's subsequent download attempts are rejected."""
        # Setup users & keys
        a_token = client.post("/auth/register", json={"email": "alice_rev@example.com", "password": "Password123!"}).json()["session_token"]
        b_token = client.post("/auth/register", json={"email": "bob_rev@example.com", "password": "Password123!"}).json()["session_token"]

        k_pub, k_priv = CryptoService.generate_keypair_kem()
        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {b_token}"},
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(k_pub),
                "private_key_material": CryptoService.encode_base64(k_priv),
            },
        )

        # Upload and share
        upload_id = str(uuid.uuid4())
        client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {a_token}"},
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("audit_rev.txt", io.BytesIO(b"To be revoked"), "text/plain")},
        )
        pkg_id = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {a_token}"},
            json={"upload_id": upload_id, "recipient_emails": ["bob_rev@example.com"], "encryption_mode": "pqc"},
        ).json()["package_id"]

        # Get grant ID
        grants = client.get(f"/files/{pkg_id}/grants", headers={"Authorization": f"Bearer {a_token}"}).json()
        grant_id = grants[0]["grant_id"]

        # Bob can download prior to revocation
        resp_pre = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {b_token}"})
        assert resp_pre.status_code == 200

        # Alice revokes Bob's grant
        resp_revoke = client.post(
            f"/files/{pkg_id}/grants/{grant_id}/revoke",
            headers={"Authorization": f"Bearer {a_token}"},
            json={"reason": "Project access decommissioned"},
        )
        assert resp_revoke.status_code == 200
        assert resp_revoke.json()["status"] == GrantStatus.REVOKED.value

        # Bob attempts download after revocation -> 403 Forbidden
        resp_post = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {b_token}"})
        assert resp_post.status_code == 403
        assert "revoked" in resp_post.json()["detail"].lower()


class TestSecurityTamperingDetection:
    """10.3 Security Tests: Tampering detection across all cryptographic layers."""

    def _setup_pqc_package(self, client):
        """Helper to create a valid shared PQC package between sender and recipient."""
        sender_email = f"sender_{uuid.uuid4().hex[:6]}@example.com"
        recip_email = f"recip_{uuid.uuid4().hex[:6]}@example.com"

        s_token = client.post("/auth/register", json={"email": sender_email, "password": "Password123!"}).json()["session_token"]
        r_token = client.post("/auth/register", json={"email": recip_email, "password": "Password123!"}).json()["session_token"]

        k_pub, k_priv = CryptoService.generate_keypair_kem()
        client.post(
            "/keys/register",
            headers={"Authorization": f"Bearer {r_token}"},
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(k_pub),
                "private_key_material": CryptoService.encode_base64(k_priv),
            },
        )

        upload_id = str(uuid.uuid4())
        plaintext = b"CRITICAL INTEL: Authenticity and integrity protected by ML-DSA and AES-GCM."
        client.post(
            "/files/upload",
            headers={"Authorization": f"Bearer {s_token}"},
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 1},
            files={"file": ("intel.bin", io.BytesIO(plaintext), "application/octet-stream")},
        )

        share_resp = client.post(
            "/files/share",
            headers={"Authorization": f"Bearer {s_token}"},
            json={"upload_id": upload_id, "recipient_emails": [recip_email], "encryption_mode": "pqc"},
        )
        package_id = share_resp.json()["package_id"]
        return package_id, s_token, r_token

    def test_tampered_ciphertext_payload_rejection(self, client, db_session):
        """Tampering with encrypted ciphertext bytes in storage triggers AES-GCM authentication failure."""
        pkg_id, _, r_token = self._setup_pqc_package(client)
        pkg = db_session.query(FilePackage).filter(FilePackage.id == pkg_id).first()

        # Read original payload
        original_payload = storage_service.read_payload(pkg.payload_storage_key)

        # Corrupt 1 byte in ciphertext
        tampered_payload = bytearray(original_payload)
        tampered_payload[15] ^= 0xFF
        storage_service.save_payload(pkg.payload_storage_key, bytes(tampered_payload))

        # Recipient attempts download -> Must be rejected with 400
        resp = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {r_token}"})
        assert resp.status_code == 400
        assert "decryption failed" in resp.json()["detail"].lower()

        # Verify audit event for crypto verification failure
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.event_type == AuditEventType.CRYPTO_VERIFICATION_FAILED.value,
                AuditLog.resource_id == pkg_id,
            )
            .first()
        )
        assert audit is not None
        assert audit.status == "failure"

    def test_tampered_manifest_metadata_rejection(self, client, db_session):
        """Tampering with manifest JSON (e.g. filename or timestamp) invalidates sender's signature."""
        pkg_id, _, r_token = self._setup_pqc_package(client)
        pkg = db_session.query(FilePackage).filter(FilePackage.id == pkg_id).first()

        # Tamper manifest metadata in database
        manifest = json.loads(pkg.manifest_json)
        manifest["original_filename"] = "tampered_evil_script.sh"
        pkg.manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        db_session.commit()

        # Recipient attempts download -> Rejected with 400 signature verification failure
        resp = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {r_token}"})
        assert resp.status_code == 400
        detail_msg = resp.json()["detail"].lower()
        assert "signature failed verification" in detail_msg or "tampered" in detail_msg

        # Verify audit log
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.event_type == AuditEventType.CRYPTO_VERIFICATION_FAILED.value,
                AuditLog.resource_id == pkg_id,
            )
            .first()
        )
        assert audit is not None

    def test_tampered_digital_signature_rejection(self, client, db_session):
        """Tampering with the ML-DSA / Ed25519 digital signature bytes causes rejection."""
        pkg_id, _, r_token = self._setup_pqc_package(client)
        pkg = db_session.query(FilePackage).filter(FilePackage.id == pkg_id).first()

        # Flip bytes of digital signature
        sig_bytes = bytearray(pkg.signature)
        sig_bytes[5] ^= 0x55
        sig_bytes[6] ^= 0xAA
        pkg.signature = bytes(sig_bytes)
        db_session.commit()

        # Recipient attempts download -> Rejected with 400
        resp = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {r_token}"})
        assert resp.status_code == 400
        detail_msg = resp.json()["detail"].lower()
        assert "signature failed verification" in detail_msg or "tampered" in detail_msg

    def test_tampered_gcm_tag_or_nonce_rejection(self, client, db_session):
        """Tampering with GCM nonce or payload tag invalidates decryption."""
        pkg_id, _, r_token = self._setup_pqc_package(client)
        pkg = db_session.query(FilePackage).filter(FilePackage.id == pkg_id).first()

        # Read encrypted payload (nonce + ciphertext + tag)
        original_payload = storage_service.read_payload(pkg.payload_storage_key)

        # Corrupt the 12-byte GCM nonce at the front
        tampered_payload = bytearray(original_payload)
        tampered_payload[:12] = b"\x00" * 12
        storage_service.save_payload(pkg.payload_storage_key, bytes(tampered_payload))

        resp = client.get(f"/files/{pkg_id}/download", headers={"Authorization": f"Bearer {r_token}"})
        assert resp.status_code == 400
        assert "decryption failed" in resp.json()["detail"].lower()


class TestRateLimitingAndSessionSecurity:
    """10.3 Security Tests: Rate-limiting and session security mechanisms."""

    def test_auth_rate_limiting_enforcement(self, client):
        """Sending more than 5 authentication requests within 1 minute triggers HTTP 429."""
        email = f"ratelimit_{uuid.uuid4().hex[:6]}@example.com"
        client.post("/auth/register", json={"email": email, "password": "Password123!"})

        # Clear rate limiter history so we test pure login burst
        rate_limiter.auth_limiter.request_history.clear()

        # Rapidly attempt 5 logins (which will return 401)
        for _ in range(5):
            res = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
            assert res.status_code in (400, 401)

        # 6th attempt must be blocked by rate limiter with 429
        res_blocked = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert res_blocked.status_code == 429
        assert "too many" in res_blocked.json()["detail"].lower()

    def test_session_security_and_cookie_attributes(self, client):
        """Session cookies must include security flags (HttpOnly, SameSite)."""
        email = f"cookie_{uuid.uuid4().hex[:6]}@example.com"
        resp = client.post("/auth/register", json={"email": email, "password": "Password123!"})
        assert resp.status_code == 201

        # Check Set-Cookie header attributes
        set_cookie = resp.headers.get("set-cookie", "").lower()
        assert "session_token=" in set_cookie
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie

    def test_invalid_or_tampered_jwt_token_rejection(self, client):
        """Requests with malformed or tampered JWT bearer tokens return 401 Unauthorized."""
        # Malformed token
        resp1 = client.get("/files", headers={"Authorization": "Bearer not-a-valid-token"})
        assert resp1.status_code == 401

        # Expired or signature-tampered JWT structure
        tampered_jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNjAwMDAwMDAwfQ."
            "InvalidSignatureBytes1234567890"
        )
        resp2 = client.get("/files", headers={"Authorization": f"Bearer {tampered_jwt}"})
        assert resp2.status_code == 401
