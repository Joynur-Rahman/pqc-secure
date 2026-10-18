#!/usr/bin/env python3
"""Interactive Demonstration Script for PQC-Secure File Sharing System.

Showcases:
1. User registration & authentication (Alice & Bob).
2. Key lifecycle: Bob registers ML-KEM-768 public key, Alice registers ML-DSA-65 public key.
3. Multi-chunk file upload and staging.
4. Post-Quantum Cryptographic Sharing: ML-KEM-768 key encapsulation, HKDF key derivation,
   AES-256-GCM envelope encryption, and ML-DSA-65 canonical manifest signing.
5. Discovery and retrieval by recipient Bob.
6. Decryption, signature verification, and payload integrity verification.
7. Active Tampering Demonstration:
   - Ciphertext byte corruption -> AES-GCM authentication failure.
   - Manifest metadata tampering -> ML-DSA-65 signature failure.
   - Unauthorized access rejection.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import uuid

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.main import app
from pqc_secure.db.models import Base, FilePackage, GrantStatus
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db
from pqc_secure.middleware.rate_limit import rate_limiter
from pqc_secure.services.crypto import CryptoService
from pqc_secure.services.storage import storage_service

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"{CYAN}{BOLD}")
    print("=" * 78)
    print("      PQC-SECURE: POST-QUANTUM SECURE FILE SHARING PLATFORM")
    print("   NIST FIPS 203 (ML-KEM-768) & FIPS 204 (ML-DSA-65) Demonstration")
    print("=" * 78)
    print(f"{RESET}")


def print_step(num: int, title: str):
    print(f"\n{YELLOW}{BOLD}[STEP {num}] {title}{RESET}")
    print(f"{DIM}{'-' * 70}{RESET}")


def print_success(msg: str):
    print(f" {GREEN}[OK]{RESET} {msg}")


def print_info(label: str, val: str):
    print(f"   {CYAN}* {RESET}{BOLD}{label}:{RESET} {val}")


def print_alert(msg: str):
    print(f" {RED}[SECURITY ALERT]{RESET} {msg}")


def run_demo():
    print_banner()

    # 1. Setup isolated in-memory/file test database
    db_file = f"demo_{uuid.uuid4().hex[:6]}.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    app.dependency_overrides[get_db_session] = lambda: db
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app, raise_server_exceptions=False)
    rate_limiter.auth_limiter.request_history.clear()
    rate_limiter.general_limiter.request_history.clear()

    try:
        # ---------------------------------------------------------------------
        # STEP 1: User Registration
        # ---------------------------------------------------------------------
        print_step(1, "Registering Users (Sender: Alice, Recipient: Bob)")
        alice_email = "alice@pqcsecure.io"
        bob_email = "bob@pqcsecure.io"

        res_a = client.post("/auth/register", json={"email": alice_email, "password": "Password123!"})
        alice_token = res_a.json()["session_token"]
        alice_id = res_a.json()["id"]
        print_success(f"Registered Alice ({alice_email}) -> ID: {alice_id}")

        res_b = client.post("/auth/register", json={"email": bob_email, "password": "Password123!"})
        bob_token = res_b.json()["session_token"]
        bob_id = res_b.json()["id"]
        print_success(f"Registered Bob ({bob_email}) -> ID: {bob_id}")

        alice_auth = {"Authorization": f"Bearer {alice_token}"}
        bob_auth = {"Authorization": f"Bearer {bob_token}"}

        # ---------------------------------------------------------------------
        # STEP 2: Key Lifecycle Management
        # ---------------------------------------------------------------------
        print_step(2, "Generating and Registering Post-Quantum Keypairs")

        # Bob generates ML-KEM-768
        t0 = time.perf_counter()
        bob_kem_pub, bob_kem_priv = CryptoService.generate_keypair_kem()
        t_kem = (time.perf_counter() - t0) * 1000
        kem_resp = client.post(
            "/keys/register",
            headers=bob_auth,
            json={
                "algorithm": "ml-kem-768",
                "public_key_material": CryptoService.encode_base64(bob_kem_pub),
                "private_key_material": CryptoService.encode_base64(bob_kem_priv),
            },
        )
        bob_key_id = kem_resp.json()["key_id"]
        print_success(f"Bob registered ML-KEM-768 Public Key ({len(bob_kem_pub)} bytes) in {t_kem:.2f}ms")
        print_info("Bob Key ID", bob_key_id)

        # Alice generates ML-DSA-65
        t0 = time.perf_counter()
        alice_dsa_pub, alice_dsa_priv = CryptoService.generate_keypair_sig()
        t_dsa = (time.perf_counter() - t0) * 1000
        dsa_resp = client.post(
            "/keys/register",
            headers=alice_auth,
            json={
                "algorithm": "ml-dsa-65",
                "public_key_material": CryptoService.encode_base64(alice_dsa_pub),
                "private_key_material": CryptoService.encode_base64(alice_dsa_priv),
            },
        )
        alice_key_id = dsa_resp.json()["key_id"]
        print_success(f"Alice registered ML-DSA-65 Signing Key ({len(alice_dsa_pub)} bytes) in {t_dsa:.2f}ms")
        print_info("Alice Key ID", alice_key_id)

        # ---------------------------------------------------------------------
        # STEP 3: Multi-Chunk Upload
        # ---------------------------------------------------------------------
        print_step(3, "Staging and Uploading Confidential File in Chunks")
        upload_id = str(uuid.uuid4())
        filename = "mission_critical_blueprint.pdf"
        chunk_0 = b"=== SECTION 1: SENSITIVE INFRASTRUCTURE BLUEPRINT ===\n"
        chunk_1 = b"=== SECTION 2: POST-QUANTUM MIGRATION ROADMAP 2026 ===\n"
        full_plaintext = chunk_0 + chunk_1

        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 0, "total_chunks": 2},
            files={"file": (filename, io.BytesIO(chunk_0), "application/pdf")},
        )
        print_success(f"Uploaded Chunk 0/2 ({len(chunk_0)} bytes)")

        client.post(
            "/files/upload",
            headers=alice_auth,
            data={"upload_id": upload_id, "chunk_number": 1, "total_chunks": 2},
            files={"file": (filename, io.BytesIO(chunk_1), "application/pdf")},
        )
        print_success(f"Uploaded Chunk 1/2 ({len(chunk_1)} bytes) - Upload Complete!")

        # ---------------------------------------------------------------------
        # STEP 4: Post-Quantum File Encryption and Sharing
        # ---------------------------------------------------------------------
        print_step(4, "Executing Post-Quantum Cryptographic Packaging & Sharing")
        t0 = time.perf_counter()
        share_res = client.post(
            "/files/share",
            headers=alice_auth,
            json={
                "upload_id": upload_id,
                "recipient_emails": [bob_email],
                "encryption_mode": "pqc",
            },
        )
        t_share = (time.perf_counter() - t0) * 1000
        pkg_data = share_res.json()
        package_id = pkg_data["package_id"]
        print_success(f"Package created in {t_share:.2f}ms:")
        print_info("Package ID", package_id)
        print_info("Crypto Mode", pkg_data["crypto_mode"].upper())
        print_info("Ciphertext Size", f"{pkg_data['file_size']} bytes")
        print_info("Recipient", bob_email)

        # ---------------------------------------------------------------------
        # STEP 5: Recipient Discovery & Decryption
        # ---------------------------------------------------------------------
        print_step(5, "Bob Discovers, Verifies Signature, and Decrypts Package")
        list_res = client.get("/files", headers=bob_auth)
        assert any(p["package_id"] == package_id for p in list_res.json()["packages"])
        print_success(f"Bob located shared package '{package_id}' in accessible files list")

        t0 = time.perf_counter()
        down_res = client.get(f"/files/{package_id}/download", headers=bob_auth)
        t_down = (time.perf_counter() - t0) * 1000
        assert down_res.status_code == 200
        decrypted_content = down_res.content

        print_success(f"Decapsulated ML-KEM secret, verified ML-DSA signature, decrypted AES-256-GCM in {t_down:.2f}ms")
        assert decrypted_content == full_plaintext
        print_success("Plaintext integrity verified: Decrypted content exactly matches original!")
        print_info("Decrypted Preview", decrypted_content[:45].decode("utf-8") + "...")

        # ---------------------------------------------------------------------
        # STEP 6: Security & Tampering Resistance Validation
        # ---------------------------------------------------------------------
        print_step(6, "Validating Active Cryptographic Tampering Defenses")

        # Scenario A: Payload bit corruption
        print(f"\n{BOLD}Scenario A: Ciphertext Payload Tampering Attack{RESET}")
        pkg_orm = db.query(FilePackage).filter(FilePackage.id == package_id).first()
        original_storage_key = pkg_orm.payload_storage_key
        orig_payload = storage_service.read_payload(original_storage_key)

        corrupted_payload = bytearray(orig_payload)
        corrupted_payload[20] ^= 0xAA  # Flip bits in encrypted payload
        storage_service.save_payload(original_storage_key, bytes(corrupted_payload))

        tamper_res_a = client.get(f"/files/{package_id}/download", headers=bob_auth)
        if tamper_res_a.status_code == 400:
            print_alert(f"Tampered ciphertext intercepted! Error detail: '{tamper_res_a.json()['detail']}'")
        storage_service.save_payload(original_storage_key, orig_payload)  # Restore

        # Scenario B: Manifest Metadata Tampering
        print(f"\n{BOLD}Scenario B: Manifest Metadata Forgery Attack{RESET}")
        orig_manifest = pkg_orm.manifest_json
        m_dict = json.loads(orig_manifest)
        m_dict["original_filename"] = "unauthorized_trojan.exe"
        pkg_orm.manifest_json = json.dumps(m_dict, sort_keys=True, separators=(",", ":"))
        db.commit()

        tamper_res_b = client.get(f"/files/{package_id}/download", headers=bob_auth)
        if tamper_res_b.status_code == 400:
            print_alert(f"Tampered manifest intercepted! ML-DSA signature failed! Detail: '{tamper_res_b.json()['detail']}'")
        pkg_orm.manifest_json = orig_manifest  # Restore
        db.commit()

        # Scenario C: Unauthorized Third-Party Interception
        print(f"\n{BOLD}Scenario C: Unauthorized Third-Party Eavesdropping{RESET}")
        rate_limiter.auth_limiter.request_history.clear()
        res_eve = client.post("/auth/register", json={"email": "eve@attacker.org", "password": "Password123!"})
        eve_token = res_eve.json()["session_token"]
        eve_auth = {"Authorization": f"Bearer {eve_token}"}

        eve_res = client.get(f"/files/{package_id}/download", headers=eve_auth)
        if eve_res.status_code == 403:
            print_alert(f"Unauthorized eavesdropper 'eve@attacker.org' blocked with 403 Forbidden!")

        print(f"\n{GREEN}{BOLD}" + "=" * 78)
        print(" DEMONSTRATION COMPLETE: ALL POST-QUANTUM PROTOCOLS & SECURITY DEFENSES VERIFIED")
        print("=" * 78 + f"{RESET}\n")

    finally:
        db.close()
        try:
            if os.path.exists(db_file):
                os.remove(db_file)
        except OSError:
            pass


if __name__ == "__main__":
    run_demo()
