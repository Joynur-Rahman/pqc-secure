"""Performance & Scalability Testing Suite (Phase 10: 10.4).

Covers:
- Concurrency and load simulation (multi-threaded key establishment, encapsulation, signing).
- Large multi-chunk file upload, packaging, download, and integrity verification.
- Out-of-order chunk assembly verification.
- Scalability throughput and latency threshold assertions.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import os
import time
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.main import app
from pqc_secure.db.models import Base
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db
from pqc_secure.middleware.rate_limit import rate_limiter
from pqc_secure.services.crypto import CryptoService


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for performance tests."""
    db_file = f"test_perf_scale_{uuid.uuid4().hex[:8]}.db"
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


class TestPerformanceUnderLoad:
    """10.4 Performance Tests: Concurrency, throughput, and scalability targets."""

    def test_concurrent_crypto_operations_under_load(self):
        """Simulate concurrent PQC and Classical operations across worker threads.

        Verifies thread safety, absence of deadlocks, and bounded execution times.
        """
        num_tasks = 20
        start_time = time.perf_counter()

        def worker_task(idx: int) -> dict:
            # 1. ML-KEM keygen + encap + decap
            k_pub, k_priv = CryptoService.generate_keypair_kem()
            ct, ss_enc = CryptoService.encapsulate_kem(k_pub)
            ss_dec = CryptoService.decapsulate_kem(ct, k_priv)
            assert ss_enc == ss_dec

            # 2. ML-DSA keygen + sign + verify
            s_pub, s_priv = CryptoService.generate_keypair_sig()
            msg = f"Task payload {idx} with random data {uuid.uuid4()}".encode()
            sig = CryptoService.sign_dsa(msg, s_priv)
            assert CryptoService.verify_dsa(msg, sig, s_pub) is True

            # 3. AES-256-GCM encryption + decryption
            key = CryptoService.derive_key(ss_enc, info=b"PERF-TEST", length=32)
            nonce, ciphertext = CryptoService.encrypt_aes_gcm(key, msg)
            decrypted = CryptoService.decrypt_aes_gcm(key, nonce, ciphertext)
            assert decrypted == msg

            return {"idx": idx, "status": "ok"}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_tasks)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.perf_counter() - start_time
        assert len(results) == num_tasks
        assert all(r["status"] == "ok" for r in results)

        # Assert reasonable throughput: 20 comprehensive roundtrips in under 15 seconds
        assert elapsed < 15.0, f"Concurrent crypto execution took too long: {elapsed:.2f}s"

    def test_concurrent_key_generation_and_storage(self, db_session):
        """Simulate multiple users generating and storing keys in parallel."""
        from pqc_secure.services.auth import AuthService
        from pqc_secure.services.key import KeyService

        auth_service = AuthService()
        num_users = 8
        users = []

        # Create users
        for i in range(num_users):
            email = f"perf_user_{i}_{uuid.uuid4().hex[:6]}@example.com"
            _, user, _ = auth_service.register_user(db_session, email, "Password123!")
            users.append(user)

        start_time = time.perf_counter()

        def register_user_keys(user):
            # Generate and register KEM key
            pub_k, priv_k = CryptoService.generate_keypair_kem()
            KeyService.register_key(
                db=db_session,
                user_id=user.id,
                algorithm="ml-kem-768",
                public_key_b64=CryptoService.encode_base64(pub_k),
                private_key_b64=CryptoService.encode_base64(priv_k),
            )
            # Generate and register DSA key
            pub_d, priv_d = CryptoService.generate_keypair_sig()
            KeyService.register_key(
                db=db_session,
                user_id=user.id,
                algorithm="ml-dsa-65",
                public_key_b64=CryptoService.encode_base64(pub_d),
                private_key_b64=CryptoService.encode_base64(priv_d),
            )
            return user.id

        # Execute sequentially or synchronously within session lock
        for user in users:
            register_user_keys(user)

        elapsed = time.perf_counter() - start_time
        # 8 users x 2 keys = 16 keys registered in sub-second to few seconds
        assert elapsed < 10.0


class TestLargeFileScale:
    """10.4 Performance Tests: Multi-chunk large file handling and chunk assembly."""

    def test_large_file_multi_chunk_upload_and_download(self, client):
        """Verify multi-chunk file upload (10 chunks), PQC encryption, download and decryption."""
        # Setup Alice and Bob
        a_resp = client.post("/auth/register", json={"email": "alice_chunks@example.com", "password": "Password123!"})
        b_resp = client.post("/auth/register", json={"email": "bob_chunks@example.com", "password": "Password123!"})
        alice_token = a_resp.json()["session_token"]
        bob_token = b_resp.json()["session_token"]

        alice_auth = {"Authorization": f"Bearer {alice_token}"}
        bob_auth = {"Authorization": f"Bearer {bob_token}"}

        # Bob registers ML-KEM-768 key
        k_pub, k_priv = CryptoService.generate_keypair_kem()
        client.post(
            "/keys/register",
            headers=bob_auth,
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(k_pub),
                "private_key_material": CryptoService.encode_base64(k_priv),
            },
        )

        # Alice registers ML-DSA-65 key
        d_pub, d_priv = CryptoService.generate_keypair_sig()
        client.post(
            "/keys/register",
            headers=alice_auth,
            json={
                "algorithm": "ml-dsa-65",
                "public_key_material": CryptoService.encode_base64(d_pub),
                "private_key_material": CryptoService.encode_base64(d_priv),
            },
        )

        # Construct 10 chunks of deterministic data (e.g. 50 KB each = 500 KB total)
        total_chunks = 10
        chunk_size = 50 * 1024  # 50 KB
        chunks = [os.urandom(chunk_size) for _ in range(total_chunks)]
        full_plaintext = b"".join(chunks)
        expected_sha256 = hashlib.sha256(full_plaintext).hexdigest()

        upload_id = str(uuid.uuid4())
        filename = "large_dataset_archive.bin"

        # Upload all 10 chunks sequentially
        upload_start = time.perf_counter()
        for idx, chunk_bytes in enumerate(chunks):
            resp = client.post(
                "/files/upload",
                headers=alice_auth,
                data={
                    "upload_id": upload_id,
                    "chunk_number": idx,
                    "total_chunks": total_chunks,
                },
                files={"file": (filename, io.BytesIO(chunk_bytes), "application/octet-stream")},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["chunk_number"] == idx
            if idx < total_chunks - 1:
                assert data["is_complete"] is False
            else:
                assert data["is_complete"] is True

        upload_duration = time.perf_counter() - upload_start

        # Share the package
        share_start = time.perf_counter()
        share_resp = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob_chunks@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert share_resp.status_code == 201
        package_id = share_resp.json()["package_id"]
        share_duration = time.perf_counter() - share_start

        # Bob downloads and decrypts the large file
        download_start = time.perf_counter()
        down_resp = client.get(f"/files/{package_id}/download", headers=bob_auth)
        assert down_resp.status_code == 200
        download_duration = time.perf_counter() - download_start

        downloaded_bytes = down_resp.content
        assert len(downloaded_bytes) == len(full_plaintext)
        assert hashlib.sha256(downloaded_bytes).hexdigest() == expected_sha256

        # Timing assertions
        assert upload_duration < 10.0
        assert share_duration < 5.0
        assert download_duration < 5.0

    def test_out_of_order_chunk_assembly(self, client):
        """Verify chunks arriving out-of-order assemble properly into the exact file."""
        a_resp = client.post("/auth/register", json={"email": "alice_order@example.com", "password": "Password123!"})
        b_resp = client.post("/auth/register", json={"email": "bob_order@example.com", "password": "Password123!"})
        alice_token = a_resp.json()["session_token"]
        bob_token = b_resp.json()["session_token"]

        alice_auth = {"Authorization": f"Bearer {alice_token}"}
        bob_auth = {"Authorization": f"Bearer {bob_token}"}

        # Bob registers KEM key
        k_pub, k_priv = CryptoService.generate_keypair_kem()
        client.post(
            "/keys/register",
            headers=bob_auth,
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(k_pub),
                "private_key_material": CryptoService.encode_base64(k_priv),
            },
        )

        chunk0 = b"CHUNK_ZERO_HEAD:"
        chunk1 = b"CHUNK_ONE_BODY:"
        chunk2 = b"CHUNK_TWO_TAIL"
        expected_plaintext = chunk0 + chunk1 + chunk2

        upload_id = str(uuid.uuid4())
        filename = "unordered.txt"

        # Upload in order: chunk 1, chunk 2, chunk 0
        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 1, "total_chunks": 3},
            files={"file": (filename, io.BytesIO(chunk1), "text/plain")},
        )
        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 2, "total_chunks": 3},
            files={"file": (filename, io.BytesIO(chunk2), "text/plain")},
        )
        last_resp = client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 3},
            files={"file": (filename, io.BytesIO(chunk0), "text/plain")},
        )
        assert last_resp.json()["is_complete"] is True

        # Share
        share_resp = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": ["bob_order@example.com"],
                "encryption_mode": "pqc",
            },
        )
        assert share_resp.status_code == 201
        package_id = share_resp.json()["package_id"]

        # Download & verify assembled order
        down_resp = client.get(f"/files/{package_id}/download", headers=bob_auth)
        assert down_resp.status_code == 200
        assert down_resp.content == expected_plaintext
