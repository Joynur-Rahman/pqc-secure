# PQC-Secure: Design Document

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Browser)                │
│  Landing │ Register │ Login │ Dashboard │ Upload │ Files   │
└──────────────────────────────────────────────────────────────┘
                          ↓ HTTPS
┌──────────────────────────────────────────────────────────────┐
│           Backend (Python FastAPI + ASGI Server)            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Auth API  │  Key API  │  File API  │  Share API       │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Auth Service │ Crypto Service │ File Service          │  │
│  │  Key Service  │ Access Control  │ Audit Logging        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
          ↓              ↓                    ↓
    ┌──────────┐   ┌────────────┐   ┌──────────────────┐
    │PostgreSQL│   │  Storage   │   │ Crypto Libraries │
    │ Database │   │(FS/MinIO)  │   │(liboqs, etc)     │
    └──────────┘   └────────────┘   └──────────────────┘
```

### Service Components

#### 1. Authentication Service
- User registration with email and password
- Secure password hashing (Argon2id/bcrypt)
- Session management with JWT or secure cookies
- Rate-limiting on login/registration endpoints
- Multi-factor authentication (future)

#### 2. Cryptographic Service
- Key generation (ML-KEM, ML-DSA, X25519, Ed25519)
- Encapsulation/decapsulation (ML-KEM)
- Key agreement (X25519)
- Signature generation/verification (ML-DSA, Ed25519)
- HKDF-based key derivation
- AES-256-GCM encryption/decryption

#### 3. Key Management Service
- Key registration and versioning
- Key rotation
- Key revocation
- Private-key custody model selection
- Key lifecycle tracking

#### 4. File Service
- File upload with size validation
- File encryption pipeline
- Encrypted storage management
- File download with authorization
- Decryption orchestration

#### 5. Access Control Service
- Recipient authorization checks
- Grant creation and revocation
- Object-level permission enforcement
- Audit trail maintenance

#### 6. Audit Logging Service
- Record authentication events
- Record permission denials
- Record cryptographic verification failures
- Record upload/download outcomes
- Exclude secrets and plaintext from logs

---

## Data Model

### Core Entities

#### User
```
id: UUID (primary key)
email: String (unique, normalized)
password_hash: String (Argon2id/bcrypt)
created_at: Timestamp
updated_at: Timestamp
account_status: Enum (active, suspended, deleted)
```

#### CryptographicKey
```
id: UUID (primary key)
user_id: UUID (foreign key to User)
algorithm: String (ml-kem-768, ml-dsa-65, x25519, ed25519)
key_type: Enum (public, private)
version: Integer (versioning for rotation)
public_key_material: Bytes (encoded public key)
private_key_material: Bytes (encrypted private key, if server-managed)
key_id: String (canonical identifier for reference)
created_at: Timestamp
status: Enum (active, revoked)
```

#### FilePackage
```
id: UUID (primary key)
sender_id: UUID (forei