# PQC-Secure User Guide

Welcome to **PQC-Secure**, an enterprise-grade file sharing platform powered by quantum-resistant cryptography. This guide walks you through using the application to share files securely.

---

## 1. Getting Started

### 1.1 Account Registration & Login
1. Navigate to the web application at `http://localhost:3001` (or your deployment URL).
2. Click **Register** in the top navigation bar.
3. Enter your corporate email and a secure password (minimum 8 characters, with uppercase, lowercase, and numeric characters).
4. Upon registration, you are automatically logged in and issued a secure session.

---

## 2. Managing Cryptographic Keys

To receive encrypted files, you must have active public keys registered on the platform.

1. Navigate to the **Key Management** tab (`/keys`).
2. You will see your existing active keys or a notice that no keys are registered.
3. Click **Register New Key**:
   - Choose your algorithm:
     - **ML-KEM-768 (Recommended)**: NIST FIPS 203 Post-Quantum Key Encapsulation Mechanism.
     - **ML-DSA-65**: NIST FIPS 204 Post-Quantum Digital Signature Algorithm.
     - **X25519**: Classical Elliptic Curve Diffie-Hellman.
     - **Ed25519**: Classical Edwards-curve Digital Signature Algorithm.
   - Click **Generate Keypair & Register**. The platform generates a secure keypair and stores your public key material.
4. **Key Rotation**: You can rotate keys anytime by clicking **Rotate** next to an active key. The older version will be safely retired while active file grants remain verifiable.
5. **Key Revocation**: If a device is lost or compromised, click **Revoke** to immediately invalidate the key.

---

## 3. Uploading and Sharing Files

1. Navigate to the **Share File** tab (`/upload`).
2. **Select File**: Drag and drop your file or click to browse. The platform supports files up to 500 MB with chunked progress tracking.
3. **Select Recipients**: Choose one or more registered users from the multi-select recipient selector.
4. **Choose Encryption Mode**:
   - **Post-Quantum Mode (PQC - Recommended)**: Uses ML-KEM-768 to encapsulate Content Encryption Keys (CEK) and signs the manifest with ML-DSA-65. This protects against "Harvest Now, Decrypt Later" quantum adversaries.
   - **Classical Mode**: Uses X25519 ECDH key agreement and Ed25519 signatures.
5. Click **Encrypt & Share File**:
   - Your file is chunk-uploaded, encrypted with AES-256-GCM using a unique per-file CEK, signed by your private key, and stored securely.
   - A confirmation toast displays the package ID and recipient count.

---

## 4. Downloading and Decrypting Shared Files

1. Navigate to the **Shared Files** tab (`/files`).
2. The list displays all files sent by you or shared with you, including:
   - File Name & Size
   - Sender Email
   - Encryption Mode (`PQC` or `Classical`)
   - Share Date & Active Grant Status
3. Click **Download & Decrypt**:
   - The platform verifies the sender's digital signature over the canonical manifest.
   - Decapsulates the Content Encryption Key using your private key.
   - Decrypts the AES-256-GCM ciphertext payload and validates the authentication tag.
   - The verified plaintext is saved directly to your browser's downloads folder.

> **Security Note**: If the file ciphertext or metadata was tampered with in transit or on storage, the platform blocks the download, raises a **Security Alert**, and logs a `CRYPTO_VERIFICATION_FAILED` event to the audit trail.

---

## 5. Revoking Access Grants

If you shared a file and need to revoke access for a specific recipient:
1. Navigate to **Shared Files** (`/files`).
2. Locate the package you sent.
3. Click **Manage Grants**.
4. Click **Revoke Access** next to the recipient's name and confirm.
5. Access is revoked instantly. The recipient will receive a `403 Forbidden` error if they attempt to download the file.

---

## 6. Audit Trail & Compliance

1. Navigate to the **Audit Logs** tab (`/audit-logs`).
2. Review comprehensive compliance logs:
   - User logins and registrations
   - Key generation, rotation, and revocation events
   - File uploads, shares, and downloads
   - Cryptographic verification failures and access denials
3. Filter events by type, date range, or search keywords.

---

## 7. Performance Benchmarking

1. Navigate to the **Performance** tab (`/perf`).
2. Review real-time benchmarks comparing Post-Quantum algorithms (ML-KEM-768, ML-DSA-65) with Classical standards (X25519, Ed25519).
3. Click **Run Benchmark Suite** to trigger a benchmark on the current server hardware.
