# Database Setup and Initialization Guide

## Overview

This document describes how to set up and initialize the PQC-Secure PostgreSQL database. The project uses:
- **SQLAlchemy** as the ORM
- **Alembic** for database migrations
- **PostgreSQL** as the database engine

## Database Schema

### Entities

#### Users
Stores user account information with email and password authentication.

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    account_status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### CryptographicKeys
Stores public and optionally private cryptographic keys for users.

```sql
CREATE TABLE cryptographic_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    algorithm VARCHAR(50) NOT NULL,  -- ml-kem-768, ml-dsa-65, x25519, ed25519
    key_type VARCHAR(50) NOT NULL,   -- public, private
    version INTEGER NOT NULL DEFAULT 1,
    key_id VARCHAR(255) UNIQUE NOT NULL,
    public_key_material BYTEA NOT NULL,
    private_key_material BYTEA,      -- NULL if user-held or browser-held
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL
);
```

#### FilePackages
Represents encrypted files shared with recipients.

```sql
CREATE TABLE file_packages (
    id VARCHAR(36) PRIMARY KEY,
    sender_id VARCHAR(36) NOT NULL REFERENCES users(id),
    recipient_key_id VARCHAR(255) NOT NULL REFERENCES cryptographic_keys(key_id),
    package_version VARCHAR(50) NOT NULL,
    crypto_mode VARCHAR(50) NOT NULL,  -- pqc, classical
    encapsulated_secret BYTEA NOT NULL,
    payload_storage_key VARCHAR(255) NOT NULL,
    manifest_json TEXT NOT NULL,
    signature BYTEA NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

#### FileChunks
Supports large file uploads by storing chunks separately.

```sql
CREATE TABLE file_chunks (
    id VARCHAR(36) PRIMARY KEY,
    package_id VARCHAR(36) NOT NULL REFERENCES file_packages(id),
    chunk_number INTEGER NOT NULL,
    chunk_size INTEGER NOT NULL,
    storage_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

#### AccessGrants
Controls who can access which encrypted packages.

```sql
CREATE TABLE access_grants (
    id VARCHAR(36) PRIMARY KEY,
    package_id VARCHAR(36) NOT NULL REFERENCES file_packages(id),
    recipient_id VARCHAR(36) NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP
);
```

#### AuditLogs
Records security and compliance events.

```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    user_id VARCHAR(36) REFERENCES users(id),
    resource_id VARCHAR(255),
    resource_type VARCHAR(255),
    action VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP NOT NULL
);
```

## Initialization Methods

### Method 1: Using Docker Compose (Recommended)

The Docker Compose setup automatically initializes the database:

```bash
# Start all services
make up

# The database will be automatically initialized via the docker-entrypoint.sh script
```

The entrypoint script:
1. Waits for PostgreSQL to be ready
2. Runs Alembic migrations
3. Creates MinIO buckets if needed

### Method 2: Manual Initialization (Local Development)

#### Prerequisites
- PostgreSQL running on localhost:5432
- Python 3.11+ with dependencies installed

#### Steps

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Initialize the database:
```bash
# Option A: Using the CLI
python -m pqc_secure.db.cli init

# Option B: Using Alembic directly
alembic upgrade head

# Option C: Using Python
python -c "from pqc_secure.db import init_db; init_db()"
```

4. Verify the database:
```bash
python -m pqc_secure.db.cli status
```

5. (Optional) Seed demo data:
```bash
python -m pqc_secure.db.cli seed
```

### Method 3: Using Alembic Migrations

Alembic provides version control for database schema changes.

#### Alembic Directory Structure
```
alembic/
├── env.py              # Alembic runtime configuration
├── script.py.mako      # Migration template
└── versions/           # Migration scripts
    └── 001_initial_schema.py
```

#### Common Alembic Commands

```bash
# Run all pending migrations
alembic upgrade head

# Create a new migration (auto-detects schema changes)
alembic revision --autogenerate -m "Add new table"

# View current migration version
alembic current

# Show migration history
alembic history

# Downgrade to previous version
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 001_initial_schema
```

## Database CLI Commands

The `pqc_secure.db.cli` module provides utilities for database management:

```bash
# Initialize database
python -m pqc_secure.db.cli init

# Check database health
python -m pqc_secure.db.cli health

# Show database status and table counts
python -m pqc_secure.db.cli status

# Seed demo users
python -m pqc_secure.db.cli seed

# Clear audit logs
python -m pqc_secure.db.cli clear-audit

# Drop all tables (WARNING: destructive!)
python -m pqc_secure.db.cli drop
```

## Initialization Script

A shell script is provided for automated setup:

```bash
# Run database initialization script
bash scripts/init_db.sh

# Seed demo data during initialization
DB_INIT_DEMO=true bash scripts/init_db.sh
```

## Configuration

Database configuration is managed through environment variables in `.env`:

```env
# Database Connection
DATABASE_URL=postgresql://pqc_user:pqc_password@localhost:5432/pqc_secure
DATABASE_POOL_SIZE=10
DATABASE_POOL_RECYCLE=3600
```

See `pqc_secure/core/settings_guide.md` for all available configuration options.

## Troubleshooting

### Connection Issues

**Error: Cannot connect to database**

```bash
# Check if PostgreSQL is running
psql -U pqc_user -d pqc_secure -c "SELECT 1"

# Verify connection string
echo $DATABASE_URL

# Check database credentials
docker-compose exec postgres psql -U pqc_user -d pqc_secure
```

### Migration Issues

**Error: Table already exists**

```bash
# Check current migration version
alembic current

# View migration history
alembic history
```

**Error: Migration conflict**

```bash
# Downgrade and re-run
alembic downgrade -1
alembic upgrade head
```

### Seed Data Issues

**Duplicate email error when seeding**

```bash
# Clear existing data
python -m pqc_secure.db.cli clear-audit

# Or drop and reinitialize
python -m pqc_secure.db.cli drop
python -m pqc_secure.db.cli init
```

## Development Workflow

### Creating New Database Models

1. Define model in `pqc_secure/db/models.py`:
```python
class MyModel(Base):
    __tablename__ = "my_models"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
```

2. Create migration:
```bash
alembic revision --autogenerate -m "Add MyModel table"
```

3. Review generated migration in `alembic/versions/`

4. Apply migration:
```bash
alembic upgrade head
```

### Adding Indexes

Indexes are automatically created for foreign keys and frequently queried columns.

Add custom indexes in migration files:
```python
op.create_index('ix_my_column', 'my_table', ['column_name'])
```

## Performance Considerations

- Connection pooling is configured with 10 base connections
- Connection recycle time is set to 3600 seconds to prevent stale connections
- Indexes are created on all foreign keys and timestamp columns
- UUID strings are used as primary keys (consider switching to BIGINT for performance in production)

## Backup and Recovery

### Backup Database

```bash
# Using pg_dump
pg_dump -U pqc_user -d pqc_secure > backup.sql

# Using Docker
docker-compose exec postgres pg_dump -U pqc_user pqc_secure > backup.sql
```

### Restore Database

```bash
# Drop and recreate
psql -U pqc_user -d pqc_secure -f backup.sql

# Or using Docker
docker-compose exec postgres psql -U pqc_user pqc_secure < backup.sql
```

## Security Considerations

1. **Always use strong database passwords in production**
2. **Use SSL/TLS for database connections in production**
3. **Restrict database user permissions to minimum required**
4. **Never commit .env files with real credentials**
5. **Audit logs should not contain secrets or plaintext**
6. **Private key material should be encrypted before storage**

## Related Documentation

- [Configuration Guide](../../pqc_secure/core/settings_guide.md)
- [API Documentation](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
