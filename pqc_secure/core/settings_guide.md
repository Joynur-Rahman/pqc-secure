# Environment Variables & Settings Configuration Guide

This guide explains all configuration options available for the PQC-Secure application.

## Overview

The application uses Pydantic Settings to load configuration from environment variables (`.env` file or system environment). All settings have sensible defaults suitable for development.

## Configuration Categories

### 1. Environment & Debug Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Execution environment: `development`, `staging`, `production` |
| `DEBUG` | `true` | Enable debug mode (disable in production) |

### 2. Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8000` | Server port number |

### 3. Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://pqc_user:pqc_password@localhost:5432/pqc_secure` | PostgreSQL connection URL |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `DATABASE_POOL_RECYCLE` | `3600` | Connection recycle time in seconds |

### 4. Security & Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT signing key (MUST be changed in production) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |

### 5. Password Hashing

| Variable | Default | Description |
|----------|---------|-------------|
| `PASSWORD_HASHING_ALGORITHM` | `argon2id` | Password hashing: `argon2id` or `bcrypt` |
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length requirement |

### 6. Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting on endpoints |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | General endpoint rate limit |
| `RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` | `5` | Login/register endpoint rate limit |

### 7. File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_TYPE` | `filesystem` | Storage backend: `filesystem` or `s3` |
| `STORAGE_PATH` | `./data/uploads` | Local filesystem storage path |
| `STORAGE_BUCKET` | `pqc-files` | Storage bucket name |
| `MAX_FILE_SIZE_MB` | `500` | Maximum file upload size in MB |
| `MAX_RECIPIENTS_PER_SHARE` | `10` | Maximum recipients per file share |

### 8. MinIO / S3 Storage (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | (empty) | MinIO endpoint URL (e.g., `localhost:9000`) |
| `MINIO_ACCESS_KEY` | (empty) | MinIO access key |
| `MINIO_SECRET_KEY` | (empty) | MinIO secret key |
| `MINIO_USE_SSL` | `false` | Use SSL/TLS for MinIO connection |

### 9. CORS Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated CORS origins |

### 10. Cryptographic Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_CRYPTO_MODE` | `pqc` | Default mode: `pqc` (post-quantum) or `classical` |
| `ENABLE_PQC_MODE` | `true` | Enable post-quantum algorithms (ML-KEM, ML-DSA) |
| `ENABLE_CLASSICAL_MODE` | `true` | Enable classical algorithms (X25519, Ed25519) |

### 11. Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FILE` | (empty) | Log file path (empty = console only) |
| `LOG_FORMAT` | Standard format | Log message format string |

### 12. Audit Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_LOGGING_ENABLED` | `true` | Enable audit event logging |
| `AUDIT_LOG_EVENTS` | `auth,permission,crypto,upload,download` | Comma-separated audit event types |

### 13. Session & Cookies

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_COOKIE_SECURE` | `false` | Use secure cookies (HTTPS only) - set to `true` in production |
| `SESSION_COOKIE_HTTPONLY` | `true` | Make cookies HTTP-only (JavaScript inaccessible) |
| `SESSION_COOKIE_SAMESITE` | `lax` | SameSite attribute: `strict`, `lax`, or `none` |

## Usage Examples

### Development Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env for local development
# Most defaults are suitable for local development
```

### Production Environment

```bash
# Set critical production values
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-random-key>
DATABASE_URL=<production-db-url>
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=strict
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Performance Tuning

```bash
# For high-concurrency scenarios
DATABASE_POOL_SIZE=20
RATE_LIMIT_REQUESTS_PER_MINUTE=100
MAX_FILE_SIZE_MB=1000
```

### S3 Storage Setup

```bash
STORAGE_TYPE=s3
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=<your-access-key>
MINIO_SECRET_KEY=<your-secret-key>
MINIO_USE_SSL=true
```

## Configuration Methods

Settings are loaded in priority order:

1. **Environment variables** (highest priority)
2. **`.env` file** in project root
3. **Default values** defined in Settings class

Example:

```bash
# Method 1: Environment variable
export SECRET_KEY="my-secret-key"

# Method 2: .env file
echo 'SECRET_KEY=my-secret-key' >> .env

# Method 3: Programmatic (in code)
settings.secret_key  # Uses value from Method 1 or 2, or default
```

## Security Best Practices

1. **Never commit `.env` files** with production secrets to version control
2. **Always change `SECRET_KEY`** in production
3. **Enable `SESSION_COOKIE_SECURE`** when using HTTPS
4. **Restrict `ALLOWED_ORIGINS`** to your frontend domain
5. **Use environment-specific `.env` files**: `.env.production`, `.env.staging`
6. **Rotate credentials** regularly
7. **Monitor `LOG_LEVEL`** in production (use WARNING or ERROR)
8. **Keep database passwords** out of version control

## Accessing Settings in Code

```python
from pqc_secure.core.config import settings

# Access individual settings
print(settings.server_port)
print(settings.database_url)

# Use helper methods
if settings.is_production():
    # Production-specific logic
    pass

allowed_origins = settings.get_allowed_origins_list()
audit_events = settings.get_audit_log_events()
log_level = settings.get_log_level()
```

## Validation & Defaults

All settings are validated by Pydantic:
- Type checking
- Range validation
- Format validation
- Default value fallbacks

Invalid values will raise configuration errors on startup.

