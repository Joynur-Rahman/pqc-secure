# PQC-Secure Developer Setup & Contributing Guide

Welcome to the PQC-Secure codebase. This document outlines local environment setup, testing standards, architecture patterns, and contribution workflows.

---

## 1. Local Development Setup

### Backend (Python 3.11+)

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # Linux/macOS
   source venv/bin/activate
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```bash
   pip install -e ".[dev,pqc]"
   ```

3. **Start local development server**:
   ```bash
   uvicorn pqc_secure.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend (Node.js 20+)

1. **Install NPM packages**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Vite development server**:
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:3000` or `http://localhost:3001`.

---

## 2. Test Execution & Quality Assurance

### Running Backend Tests
Execute the full pytest suite with 370+ tests covering unit, integration, security, and performance scenarios:
```bash
# Set PYTHONPATH and execute pytest
pytest -v
```

Run specific test modules:
```bash
# End-to-end integration & tampering tests
pytest tests/test_e2e_integration.py -v

# Concurrency & load benchmarks
pytest tests/test_performance_scale.py -v

# Core cryptographic operations
pytest tests/test_crypto.py -v
```

### Running Frontend Tests & Typecheck
```bash
cd frontend

# Run Vitest component unit tests
npm test

# Build production bundle and check TypeScript types
npm run build
```

---

## 3. Cryptographic Service Layer

- **`CryptoService` (`pqc_secure/services/crypto.py`)**:
  - Implements NIST FIPS 203 (`ml-kem-768`) and NIST FIPS 204 (`ml-dsa-65`) through `liboqs` with high-performance emulation fallbacks.
  - Implements Classical algorithms (`x25519`, `ed25519`) via `cryptography.hazmat`.
  - Implements AES-256-GCM envelope encryption with per-file random Content Encryption Keys (CEK) and context-bound Additional Authenticated Data (`PQC-PACKAGE:{package_id}`).
- **`FileService` (`pqc_secure/services/file.py`)**:
  - Manages chunk staging, assembly, recipient validation, canonical manifest signing, and envelope decapsulation.
- **`AccessControlService` (`pqc_secure/services/access_control.py`)**:
  - Enforces active grant authorization, sender permissions, and real-time grant revocations.
- **`AuditService` (`pqc_secure/services/audit.py`)**:
  - Records tamper-evident audit logs with automatic secret redaction.

---

## 4. Code Standards & Architecture Guidelines

1. **Secret Redaction**: Never write private keys, shared secrets, or plaintext payload data to logs or persistent error messages.
2. **Deterministic Canonical JSON**: All manifests MUST be formatted using `json.dumps(obj, sort_keys=True, separators=(",", ":"))` before signing to guarantee bit-for-bit signature verification.
3. **Database Test Isolation**: Tests MUST use isolated SQLite test databases with `app.dependency_overrides` for `get_db_session` and `get_db`.
