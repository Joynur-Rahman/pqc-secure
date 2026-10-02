# PQC-Secure: Requirements

## Overview
PQC-Secure is a web-based file-sharing system using post-quantum cryptography (PQC). It enables authenticated users to encrypt, store, and share files securely with recipients, supporting both PQC algorithms (ML-KEM, ML-DSA) and classical comparison modes (X25519, Ed25519).

## Project Scope

### In Scope
- User registration, authentication, and login
- Public-key registration and management (ML-KEM, X25519)
- Digital signatures (ML-DSA, Ed25519)
- Encrypted file upload with recipient selection
- Secure package creation with signed metadata
- AES-256-GCM for file encryption
- HKDF for key derivation
- Access-controlled file sharing
- Recipient-side decryption and verification
- File integrity checks
- Audit event logging

### Out of Scope (Initial Release)
- Production-grade enterprise key management
- Hardware security module integration
- Multi-party access policies
- End-to-end encrypted group sharing
- Automated identity proofing
- Protection against compromised endpoints
- Formal cryptographic certification

### Important Note
This is an educational and prototype implementation. It is not independently audited or suitable for high-assurance production use.

---

## User Stories

### US-01: User Registration and Authentication
**As a** new user  
**I want to** register an account with email and password  
**So that** I can access the file-sharing system securely.

**Acceptance Criteria:**
- AC-01.1: User can register with email and password
- AC-01.2: Password is hashed using Argon2id or bcrypt
- AC-01.3: Email uniqueness is enforced (normalized)
- AC-01.4: Authentication endpoints are rate-limited
- AC-01.5: System does not reveal whether an email is registered
- AC-01.6: Existing users can login with email and password
- AC-01.7: Session expires on logout and is securely invalidated

### US-02: Cryptographic Key Registration
**As a** registered user  
**I want to** create and register my public key (PQC or classical mode)  
**So that** other users can send me encrypted files.

**Acceptance Criteria:**
- AC-02.1: User can generate or import a supported public key
- AC-02.2: Public key is validated for encoding, size, and correctness
- AC-02.3: Key metadata includes algorithm, version, creation time, and status
- AC-02.4: Private key custody follows a selected model (user-held, browser-held, or server-managed)
- AC-02.5: Multiple key versions are supported
- AC-02.6: Keys can be rotated without affecting existing packages
- AC-02.7: Keys can be revoked; revoked keys cannot be selected for new shares

### US-03: Encrypt and Share File
**As a** sender  
**I want to** upload a file and select recipients  
**So that** only authorized recipients can decrypt and view it.

**Acceptance Criteria:**
- AC-03.1: User can select a file for upload (with size validation)
- AC-03.2: User can select one or more registered recipients
- AC-03.3: User can select cryptographic mode (PQC or classical)
- AC-03.4: System validates recipient keys and file policy
- AC-03.5: File is encrypted using AES-256-GCM with a fresh nonce
- AC-03.6: Content-encryption key is derived via HKDF with context-bound information
- AC-03.7: Package metadata is signed using sender's private key
- AC-03.8: Encrypted payload and metadata are persisted atomically
- AC-03.9: Access grants are created for recipients
- AC-03.10: Nonces are never reused with the same key
- AC-03.11: Upload progress is displayed to user

### US-04: Receive and Decrypt File
**As a** recipient  
**I want to** retrieve and decrypt a file shared with me  
**So that** I can access its content securely.

**Acceptance Criteria:**
- AC-04.1: Recipient can view list of shared files
- AC-04.2: System checks authorization before allowing access
- AC-04.3: Package signature is verified against sender's public key
- AC-04.4: Verification failure prevents decryption
- AC-04.5: Recipient can decapsulate/derive the shared secret
- AC-04.6: Content-encryption key is derived using HKDF
- AC-04.7: File is decrypted using AES-256-GCM
- AC-04.8: Authentication failure prevents plaintext release
- AC-04.9: Decrypted file is returned with safe content-disposition headers

### US-05: Detect Tampering
**As a** tester  
**I want to** verify that tampering with encrypted content or metadata is detected  
**So that** I can confirm integrity protections work.

**Acceptance Criteria:**
- AC-05.1: Modifying ciphertext causes authentication tag validation to fail
- AC-05.2: Modifying package metadata causes signature verification to fail
- AC-05.3: No plaintext is released on verification/decryption failure
- AC-05.4: Clear error messages indicate signature or authentication failures

### US-06: Revoke Share
**As a** sender  
**I want to** revoke access to a shared file  
**So that** the recipient cannot download it via the server.

**Acceptance Criteria:**
- AC-06.1: Sender can revoke a grant
- AC-06.2: Future server-mediated access is denied
- AC-06.3: UI clarifies that downloaded copies cannot be recalled
- AC-06.4: Revocation does not affect existing key material held by recipient

### US-07: Key Management
**As a** user  
**I want to** review, rotate, and revoke my keys  
**So that** I can manage my cryptographic identity.

**Acceptance Criteria:**
- AC-07.1: User can view all registered keys with metadata
- AC-07.2: User can rotate to a new key version
- AC-07.3: User can revoke a key
- AC-07.4: Old package references remain intact after rotation
- AC-07.5: Revoked keys cannot be used for new shares

### US-08: Performance Measurement
**As a** evaluator  
**I want to** measure and compare performance between PQC and classical modes  
**So that** I can assess the overhead of post-quantum algorithms.

**Acceptance Criteria:**
- AC-08.1: System records timing for key generation, encapsulation, signing, encryption
- AC-08.2: System records sizes of public keys, ciphertexts, and signatures
- AC-08.3: Results include environment metadata (CPU, memory, OS, library versions)
- AC-08.4: Results show median and percentile values, not just single best run
- AC-08.5: Results clarify that measurements are environment-dependent

---

## Cryptographic Requirements

### Algorithm Suite (PQC Mode)
- **Key Establishment:** ML-KEM-768 (NIST FIPS 203)
- **Digital Signatures:** ML-DSA-65 (NIST FIPS 204)
- **File Encryption:** AES-256-GCM (NIST SP 800-38D)
- **Key Derivation:** HKDF-SHA-256 (RFC 5869)

### Algorithm Suite (Classical Comparison Mode)
- **Key Establishment:** X25519 (Elliptic Curve Diffie-Hellman)
- **Digital Signatures:** Ed25519 (Edwards-curve Digital Signature Algorithm)
- **File Encryption:** AES-256-GCM
- **Key Derivation:** HKDF-SHA-256

### Cryptographic Constraints
- All cryptographic algorithms must use standardized, maintained implementations
- Custom cryptographic primitives are prohibited
- ML-KEM must be used for key establishment, not as a direct file-encryption algorithm
- AES-GCM nonces must never be reused with the same encryption key
- Private keys, shared secrets, derived keys, and plaintext must not be logged

---

## Non-Functional Requirements

### Performance Targets
- User authentication (registration/login): < 500ms
- File encryption (per MB): < 100ms (target, environment-dependent)
- File decryption (per MB): < 100ms (target, environment-dependent)
- Signature verification: < 50ms
- Key generation: < 1 second

### Scalability
- Support 100+ concurrent users in demonstration environment
- Support file uploads up to 500MB (configurable)
- Support packages with up to 10 recipients (initial release)

### Availability
- System uptime target: 95% in hosted demonstration
- Database failover and backup procedures documented

### Security
- HTTPS for all client-server communication
- Rate-limiting on authentication endpoints
- Secure session management (Secure, HttpOnly, SameSite cookies)
- CORS restricted to configured origins
- Least-privilege database credentials

---

## Technology Stack

### Frontend
- Modern browser (desktop and mobile)
- React (or equivalent modern JavaScript framework)
- HTTPS for all communication

### Backend
- Python 3.11+
- FastAPI framework
- ASGI server (Uvicorn)
- PostgreSQL database

### Cryptography
- Supported library implementing standardized ML-KEM and ML-DSA (e.g., liboqs-python, ml-kem-python)
- Classical cryptography provider (e.g., cryptography.io)

### Storage
- Local filesystem (development)
- MinIO or S3-compatible object storage (production-like demo)

### Deployment
- Docker Compose for reproducible local deployment
- Reverse proxy with TLS for hosted demonstration

---

## Key Architectural Decisions

### Trust Boundaries
1. **Browser-to-Server:** HTTPS, secure session handling, CSRF protections, strict origin policy
2. **Application-to-Database:** Least-privilege credentials, parameterized queries
3. **Application-to-Storage:** Scoped credentials, encrypted payloads only
4. **Key Custody:** Private-key storage and recovery must be explicit
5. **Identity Binding:** Public keys bound to authenticated identities and versions

### Package Structure (Versioned)
- Algorithm suite identifier
- Package version
- Sender identity and verification key reference
- Recipient identity and recipient key version
- Encapsulated/shared secret (recipient-specific)
- Encrypted payload reference
- Signature over canonical manifest
- Nonce and authentication tag (or equivalent per algorithm suite)

### Sequence Flow (High-Level)
1. Recipient registers and creates key pair; public key stored
2. Sender authenticates, selects file and recipients
3. Backend validates file, size, recipients, and key versions
4. For each recipient: encapsulate/establish shared secret to recipient's public key
5. Derive content-encryption key using HKDF with context
6. Encrypt file using AES-256-GCM with fresh nonce
7. Sign canonical package manifest using sender's private key
8. Persist encrypted payload and metadata atomically
9. Create access grants for recipients
10. Recipient opens shared item; system checks authorization
11. System verifies signature before accepting package
12. Recipient decapsulates/derives shared secret, derives file key, decrypts payload

---

## MVP Scope (Time-Constrained Hackathon)

### Minimal Vertical Slice
1. Register two demo users with public keys (PQC mode)
2. Share one test file from sender to recipient using:
   - ML-KEM-768 for key establishment
   - HKDF-SHA-256 for key derivation
   - AES-256-GCM for file encryption
   - ML-DSA-65 for package signing
3. Verify signed manifest and decrypt file as recipient
4. Demonstrate ciphertext/metadata tampering detection
5. Run comparable classical workflow (X25519, Ed25519)
6. Display measured timings and key/ciphertext/signature sizes

### Deferred for Later
- Complex account recovery
- Multi-device synchronization
- Large-scale group sharing
- Production-grade key transparency
- Administrative key recovery workflows

---

## Assumptions and Dependencies

### Assumptions
- Users have supported browsers and network connectivity
- Server has sufficient storage and compute for demonstration workload
- Cryptographic provider correctly implements standardized algorithms
- Users protect account credentials and private keys (endpoint compromise out of scope)
- Key custody model (user-held, browser-held, or server-managed) will be agreed before implementation

### Dependencies
- Python runtime and package ecosystem
- FastAPI and ASGI server
- PostgreSQL database
- Supported cryptographic library (ML-KEM, ML-DSA implementations)
- Classical cryptography provider (X25519, Ed25519)
- Modern browser
- TLS certificates for hosted demo

---

## Security Model and Threat Considerations

### What the System Protects
- File confidentiality against server-side adversaries
- File integrity and authenticity through signatures
- Access control through recipient-bound encryption

### What the System Cannot Protect Against
- Compromised endpoints (user device or server)
- Key material compromise
- Quantum computer attacks (outside scope of standard algorithms)
- Social engineering or credential compromise

### Design Principles
- Principle of least privilege for database and service accounts
- Defense in depth through multiple verification layers
- Explicit algorithm versioning for future agility
- No implicit administrative access to plaintext or user keys
- Audit logging without logging secrets
