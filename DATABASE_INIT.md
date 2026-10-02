# Database Initialization Guide for PQC-Secure

## Quick Start

### Using Docker Compose (Recommended)

```bash
# 1. Start all services (database initialization happens automatically)
make up

# 2. Verify database is initialized
make ps

# 3. Check database health
make health
```

### Manual Initialization (Local Development)

```bash
# 1. Install dependencies
pip install -e .

# 2. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 3. Initialize database
python -m pqc_secure.db.cli init

# 4. Verify initialization
python -m pqc_secure.db.cli status

# 5. (Optional) Seed demo data
python -m pqc_secure.db.cli seed
```

## What Gets Created

The database initialization creates 6 main tables:

1. **users** - User accounts with email and password
2. **cryptographic_keys** - Public/private keys for users (ML-KEM, ML-DSA, X25519, Ed25519)
3. **file_packages** - Encrypted file packages with metadata
4. **file_chunks** - Chunks for large file uploads
5. **access_grants** - Access control (who can access which files)
6. **audit_logs** - Security and compliance event logging

## Key Features

### Automatic Migrations with Alembic
- Migration version: `001_initial_schema`
- All tables created with proper indexes and foreign keys
- Migrations can be upgraded/downgraded independently

### Database CLI Tools
```bash
python -m pqc_secure.db.cli <command>

Commands:
  init          - Initialize database (create all tables)
  health        - Check database health
  status        - Show database status and table counts
  seed          - Seed demo data (alice@example.com, bob@example.com)
  clear-audit   - Clear audit logs
  drop          - Drop ALL tables (use with caution!)
  help          - Show help message
```

### Initialization Script
```bash
# Basic initialization
bash scripts/init_db.sh

# Initialize with demo data
DB_INIT_DEMO=true bash scripts/init_db.sh

# Without health verification
DB_VERIFY_HEALTH=false bash scripts/init_db.sh
```

## Docker Integration

### Automatic Initialization
The `docker-entrypoint.sh` automatically:
1. Waits for PostgreSQL to be ready
2. Runs Alembic migrations
3. Sets up MinIO bucket
4. Starts the application

### Manual Database Operations in Docker
```bash
# Run database CLI commands
docker-compose exec backend python -m pqc_secure.db.cli init

# Access PostgreSQL directly
docker-compose exec postgres psql -U pqc_user -d pqc_secure

# Run migrations
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current
```

## Configuration

### Environment Variables
Located in `.env` file:

```env
# Database Connection
DATABASE_URL=postgresql://pqc_user:pqc_password@localhost:5432/pqc_secure
DATABASE_POOL_SIZE=10
DATABASE_POOL_RECYCLE=3600
```

### Connection String Format
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

## Troubleshooting

### "psycopg2.OperationalError: could not connect to server"
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Verify port 5432 is accessible

### "table ... already exists"
- Database already initialized
- Safe to run init command again (idempotent)

### "alembic: Migration 001_initial_schema not found"
- Ensure `alembic/versions/001_initial_schema.py` exists
- Run: `python -m pqc_secure.db.cli init`

### Demo data has duplicate email error
- Clear existing demo data: `python -m pqc_secure.db.cli seed`
- Or drop and reinit: `python -m pqc_secure.db.cli drop && python -m pqc_secure.db.cli init`

## Database Models

### User Model
```python
id: UUID (primary key)
email: String (unique, indexed)
password_hash: String
account_status: Enum(active, suspended, deleted)
created_at: DateTime
updated_at: DateTime
```

### CryptographicKey Model
```python
id: UUID (primary key)
user_id: UUID (foreign key to User)
algorithm: String (ml-kem-768, ml-dsa-65, x25519, ed25519)
key_type: Enum(public, private)
version: Integer (for key rotation)
key_id: String (canonical identifier, unique)
public_key_material: Binary
private_key_material: Binary (optional, for server-managed keys)
status: Enum(active, revoked, superseded)
created_at: DateTime
```

### FilePackage Model
```python
id: UUID (primary key)
sender_id: UUID (foreign key to User)
recipient_key_id: String (foreign key to CryptographicKey)
package_version: String (versioned format)
crypto_mode: String (pqc or classical)
encapsulated_secret: Binary (ML-KEM ciphertext or ephemeral key)
payload_storage_key: String (file storage location)
manifest_json: Text (canonical manifest, no secrets)
signature: Binary (sender's signature)
original_filename: String
file_size: Integer
created_at: DateTime
```

### AccessGrant Model
```python
id: UUID (primary key)
package_id: UUID (foreign key to FilePackage)
recipient_id: UUID (foreign key to User)
status: Enum(active, revoked)
created_at: DateTime
revoked_at: DateTime (null until revoked)
```

### AuditLog Model
```python
id: UUID (primary key)
event_type: String (indexed)
user_id: UUID (optional, foreign key to User)
resource_id: String
resource_type: String
action: String
status: String (success or failure)
details: Text (JSON, no secrets)
ip_address: String
user_agent: String
created_at: DateTime (indexed)
```

## Next Steps

After initialization:

1. **Register users** - Use `/auth/register` endpoint (Phase 2)
2. **Register keys** - Use `/keys/register` endpoint (Phase 3)
3. **Upload files** - Use `/files/share` endpoint (Phase 4)
4. **Download files** - Use `/files/{package_id}/download` endpoint (Phase 5)

## Related Documentation

- [Full Database Setup Guide](./pqc_secure/db/DATABASE_SETUP.md)
- [Configuration Guide](./pqc_secure/core/settings_guide.md)
- [API Endpoints Documentation](./QUICKSTART.md)
- [Docker Setup Guide](./DOCKER_SETUP.md)
