# PQC-Secure Deployment Guide

This guide covers production and development deployment of the PQC-Secure stack using Docker Compose, reverse proxies, and automated database migrations.

---

## 1. System Architecture Overview

```
                      +-------------------+
                      |    Client (Web)   |
                      +---------+---------+
                                |  (HTTP / Port 3001)
                                v
               +---------------------------------+
               |        Nginx (Frontend)         |
               | Static SPA & Reverse Proxy /api |
               +----------------+----------------+
                                |  (Proxy Pass)
                                v
               +---------------------------------+
               |       FastAPI Backend:8000      |
               |  (ML-KEM / ML-DSA / AES-GCM)   |
               +--------+---------------+--------+
                        |               |
       (SQLAlchemy Pool)|               |(S3/Local FS)
                        v               v
           +------------------+   +-------------------+
           | PostgreSQL 16 DB |   | MinIO / Local S3  |
           +------------------+   +-------------------+
```

---

## 2. Docker Compose Deployment

### Prerequisites
- Docker Engine 24.0+ & Docker Compose v2.20+
- 4GB+ RAM recommended for liboqs compilation

### Quick Start

1. **Clone and Configure Environment**:
   ```bash
   git clone https://github.com/Joynur-Rahman/pqc-secure.git
   cd pqc-secure
   cp .env.example .env
   ```

2. **Launch Services**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify Health**:
   ```bash
   docker compose ps
   ```
   All 4 containers (`pqc-postgres`, `pqc-minio`, `pqc-backend`, `pqc-frontend`) should show healthy/running status.

4. **Access the Application**:
   - Web Application: `http://localhost:3001`
   - Backend API Docs (Swagger): `http://localhost:8000/docs`
   - MinIO Object Storage Console: `http://localhost:9001` (Credentials: `minioadmin` / `minioadmin123`)

---

## 3. Environment Variable Configuration

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Deployment mode (`development`, `staging`, `production`) |
| `DATABASE_URL` | `postgresql://pqc_user:pqc_password@postgres:5432/pqc_secure` | PostgreSQL connection string |
| `SECRET_KEY` | *(Set strong secret)* | 64+ char secret key used for session JWT token signing |
| `STORAGE_TYPE` | `s3` or `filesystem` | Storage backend for encrypted packages |
| `STORAGE_PATH` | `/app/uploads` | Local filesystem path if using filesystem storage |
| `MINIO_ENDPOINT` | `minio:9000` | S3-compatible MinIO endpoint |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated CORS allowed origins |
| `SESSION_COOKIE_SECURE` | `true` | Enforce HTTPS for session cookies in production |
| `RATE_LIMIT_AUTH` | `5` | Max authentication attempts per minute per IP |

---

## 4. Production Hardening Checklist

1. **Enable TLS/SSL**: Terminate SSL at Nginx or Cloudflare with modern TLS 1.3 cipher suites.
2. **Rotate Secrets**: Set high-entropy `SECRET_KEY` and PostgreSQL passwords via Docker secrets or HashiCorp Vault.
3. **Database Backups**: Schedule automated `pg_dump` jobs for PostgreSQL volumes.
4. **HSTS and CSP**: Maintain strict Content Security Policy (`script-src 'self'`) and HSTS headers (configured by `SecurityHeadersMiddleware`).
