# PQC-Secure REST API Documentation

The PQC-Secure platform exposes a high-performance REST API built with FastAPI, adhering strictly to OpenAPI 3.1 standards with interactive Swagger UI (`/docs`) and ReDoc (`/redoc`).

---

## 1. Authentication & Session Management

All authenticated endpoints require an `Authorization: Bearer <session_token>` header or an authenticated `session_token` HttpOnly cookie.

### `POST /api/auth/register`
Creates a new user account with secure password hashing.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!"
  }
  ```
- **Responses**:
  - `201 Created`: User registered successfully. Returns `{"id": "...", "email": "...", "account_status": "active", "session_token": "..."}` and sets `Set-Cookie: session_token=...; HttpOnly; SameSite=Lax`.
  - `400 Bad Request`: Email already registered or invalid complexity.
  - `429 Too Many Requests`: Rate limit exceeded (5 requests/minute).

### `POST /api/auth/login`
Authenticates a user and issues a session token.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!"
  }
  ```
- **Responses**:
  - `200 OK`: Returns user profile and session token. Sets secure cookie.
  - `401 Unauthorized`: Invalid credentials.
  - `429 Too Many Requests`: Rate limit exceeded.

### `GET /api/auth/me`
Retrieves currently authenticated user profile.
- **Headers**: `Authorization: Bearer <token>`
- **Responses**:
  - `200 OK`: `{"id": "...", "email": "...", "account_status": "active"}`
  - `401 Unauthorized`: Missing or invalid session token.

---

## 2. Cryptographic Key Management

Handles registration, rotation, and revocation of Post-Quantum and Classical public keys.

### `POST /api/keys/register`
Registers a public key for the authenticated user.
- **Request Body**:
  ```json
  {
    "algorithm": "ml-kem-768",
    "public_key_material": "<base64_encoded_bytes>",
    "private_key_material": "<optional_base64_for_client_storage>",
    "key_type": "public"
  }
  ```
  *Algorithms supported*: `ml-kem-768`, `ml-dsa-65`, `x25519`, `ed25519`.
- **Responses**:
  - `201 Created`: Key registered with canonical fingerprint `key_id`.

### `GET /api/keys`
Lists registered keys for the authenticated user.
- **Responses**:
  - `200 OK`: `{"keys": [...], "total": 2}`

### `POST /api/keys/{key_id}/revoke`
Revokes an existing cryptographic key.
- **Request Body**: `{"reason": "Compromised or decommissioned"}`
- **Responses**: `200 OK`: Returns revocation confirmation.

---

## 3. File Upload & Sharing Pipeline

### `POST /api/files/upload`
Uploads full files or chunked components.
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: Raw binary chunk.
  - `upload_id`: Optional UUID. Generated on initial chunk and reused.
  - `chunk_number`: Integer index (0-indexed).
  - `total_chunks`: Total expected chunks.
- **Responses**:
  - `201 Created`: Returns upload progress and `is_complete: bool`.

### `POST /api/files/share`
Packages and encrypts uploaded payload using envelope encryption and digital signing.
- **Request Body**:
  ```json
  {
    "upload_id": "8b770270-45f1-4915-9129-9c7579a47c26",
    "recipient_emails": ["bob@example.com"],
    "encryption_mode": "pqc"
  }
  ```
- **Responses**:
  - `201 Created`:
    ```json
    {
      "package_id": "3e470d53-6807-4fe9-a6d7-adc68d43c66d",
      "original_filename": "dataset.csv",
      "file_size": 1048576,
      "crypto_mode": "pqc",
      "recipients": [{"recipient_id": "...", "status": "active"}]
    }
    ```

---

## 4. File Download & Decryption

### `GET /api/files`
Lists packages shared by or with the current user.
- **Responses**: `200 OK`: Returns package summaries.

### `GET /api/files/{package_id}`
Retrieves metadata of a shared file package.
- **Responses**:
  - `200 OK`: Package metadata with recipient grant statuses.
  - `403 Forbidden`: User has no active grant.
  - `404 Not Found`: Package does not exist.

### `GET /api/files/{package_id}/download`
Verifies sender's digital signature, decapsulates CEK, and streams decrypted plaintext.
- **Responses**:
  - `200 OK`: Binary stream with `Content-Disposition: attachment; filename="..."`.
  - `400 Bad Request`: Cryptographic verification failed (tampered ciphertext or invalid signature).
  - `403 Forbidden`: Access denied or grant revoked.

### `POST /api/files/{package_id}/grants/{grant_id}/revoke`
Revokes recipient access to a package.
- **Responses**: `200 OK`: Grant marked as `revoked`.

---

## 5. Audit Logging & Performance

### `GET /api/audit-logs`
Queries tamper-evident compliance audit trail. Supports pagination and filtering (`event_type`, `user_id`, `start_date`, `end_date`).

### `POST /api/perf/benchmark`
Executes real-time cryptographic benchmark suite (PQC vs Classical) and returns latency, size overheads, and system context.
