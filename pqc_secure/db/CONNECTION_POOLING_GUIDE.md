# Connection Pooling and Transaction Management Guide

## Overview

This guide explains the connection pooling and transaction management implementation in PQC-Secure.

## Connection Pooling

### What is Connection Pooling?

Connection pooling maintains a cache of database connections that can be reused by application threads instead of creating new connections for each database operation. This significantly improves performance and reduces resource usage.

### Current Configuration

The application uses SQLAlchemy's `QueuePool` implementation with the following settings:

```python
create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,              # Default: 10 connections in pool
    max_overflow=20,           # Allow up to 20 additional overflow connections
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Verify connections are alive before using
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pool_size` | 10 | Base number of connections to keep in the pool |
| `max_overflow` | 20 | Additional connections created when pool is exhausted |
| `pool_recycle` | 3600 | Seconds before connections are recycled (prevents stale connections) |
| `pool_pre_ping` | True | Test connections before using them (prevents "connection lost" errors) |
| `connect_timeout` | 10 | Seconds to wait when establishing a new connection |
| `keepalives` | 1 | Enable TCP keepalives for long-lived connections |
| `keepalives_idle` | 30 | Seconds before sending first keepalive probe |
| `keepalives_interval` | 10 | Seconds between keepalive probes |
| `keepalives_count` | 5 | Number of failed probes before giving up |

### Environment Variable Customization

You can override pool settings via environment variables:

```bash
# .env file
DATABASE_POOL_SIZE=20
DATABASE_POOL_RECYCLE=1800  # 30 minutes
```

### Monitoring Pool Status

Get current pool statistics:

```python
from pqc_secure.db.transaction import get_pool_status
from pqc_secure.db.session import engine

status = get_pool_status(engine)
print(f"Active connections: {status['checked_out']}")
print(f"Available connections: {status['available']}")
print(f"Total capacity: {status['total']}")
```

## Transaction Management

### Basic Usage

Use the `transaction` context manager for atomic database operations:

```python
from pqc_secure.db.session import SessionLocal
from pqc_secure.db.transaction import transaction

db = SessionLocal()

# Automatic commit on success, rollback on error
with transaction(db):
    user = User(email="user@example.com", password_hash="hashed")
    db.add(user)
    # Changes are committed automatically on successful exit
```

### Error Handling

Transactions automatically rollback on exceptions:

```python
from pqc_secure.db.transaction import transaction

db = SessionLocal()

try:
    with transaction(db):
        user = User(email="user@example.com", password_hash="hashed")
        db.add(user)
        # If any error occurs here, transaction is rolled back
        if some_validation_fails:
            raise ValueError("Validation failed")
except ValueError as e:
    # User was not added due to rollback
    print(f"Transaction failed: {e}")
```

### Nested Transactions with Savepoints

Use savepoints for nested transaction support:

```python
from pqc_secure.db.transaction import transaction, transaction_savepoint

db = SessionLocal()

with transaction(db):
    user1 = User(email="user1@example.com", password_hash="hash")
    db.add(user1)  # This will be committed
    
    try:
        with transaction_savepoint(db, "add_user2"):
            user2 = User(email="user2@example.com", password_hash="hash")
            db.add(user2)
            raise ValueError("Something went wrong")
    except ValueError:
        # user2 was rolled back, but user1 remains committed
        pass
```

### TransactionManager

For applications that need centralized transaction management:

```python
from pqc_secure.db.transaction import TransactionManager
from pqc_secure.db.session import SessionLocal

manager = TransactionManager(SessionLocal)

# Automatically gets/creates session per thread
with manager.transaction():
    session = manager.get_session()
    user = User(email="user@example.com", password_hash="hash")
    session.add(user)

# Cleanup when done
manager.close_session()
```

### Retry on Transient Failures

Retry operations that might fail transiently (e.g., connection timeouts):

```python
from pqc_secure.db.transaction import retry_transaction

def register_user(db):
    user = User(email="user@example.com", password_hash="hash")
    db.add(user)
    return user

# Automatically retries up to 3 times with exponential backoff
result = retry_transaction(
    db_session,
    register_user,
    max_retries=3,
    backoff_factor=0.1
)
```

## Usage in FastAPI Endpoints

### Basic Pattern

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pqc_secure.db.session import get_db_session
from pqc_secure.db.transaction import transaction

app = FastAPI()

@app.post("/users/")
def create_user(email: str, password: str, db: Session = Depends(get_db_session)):
    """Create a new user with automatic transaction management"""
    with transaction(db):
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
    return {"id": user.id, "email": user.email}
```

### With Error Handling

```python
from fastapi import HTTPException, status

@app.post("/users/")
def create_user(
    email: str,
    password: str,
    db: Session = Depends(get_db_session)
):
    """Create a new user with error handling"""
    try:
        with transaction(db):
            # Check if user exists
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                raise ValueError("User already exists")
            
            user = User(
                email=email,
                password_hash=hash_password(password),
                account_status="active"
            )
            db.add(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    return {"id": user.id, "email": user.email}
```

## Best Practices

### 1. Always Use Transaction Context Managers

✅ **Good:**
```python
with transaction(db):
    db.add(user)
    # Automatic commit/rollback
```

❌ **Bad:**
```python
db.add(user)
db.commit()  # Manual commit - error prone
```

### 2. Keep Transactions Small

✅ **Good:**
```python
with transaction(db):
    # Quick operation
    user = User(email=email, password_hash=hash)
    db.add(user)
```

❌ **Bad:**
```python
with transaction(db):
    # Long-running operations can lock resources
    for i in range(1000000):
        user = User(email=f"user{i}@example.com", ...)
        db.add(user)
```

### 3. Handle Specific Exceptions

✅ **Good:**
```python
from sqlalchemy.exc import IntegrityError

try:
    with transaction(db):
        db.add(user)
except IntegrityError:
    # Handle unique constraint violation
    raise ValueError("Email already exists")
```

❌ **Bad:**
```python
try:
    with transaction(db):
        db.add(user)
except Exception:
    # Too generic
    pass
```

### 4. Use Savepoints for Complex Operations

✅ **Good:**
```python
with transaction(db):
    db.add(user)  # Critical operation
    
    try:
        with transaction_savepoint(db):
            # Optional operation that might fail
            db.add(optional_data)
    except ValueError:
        # User still saved, optional data not added
        pass
```

### 5. Configure Pool Size Appropriately

For estimating pool size:
- Small app (< 10 concurrent users): `pool_size=5`
- Medium app (10-100 concurrent): `pool_size=20`
- Large app (100+ concurrent): `pool_size=50+`

Formula: `pool_size = peak_concurrent_requests * 1.2`

## Performance Tuning

### Connection Recycling

Connections are recycled after `pool_recycle` seconds (default 3600). This prevents:
- Stale connections from database restarts
- Connection timeouts from firewalls/proxies
- Memory leaks in long-running applications

If connections are timing out:
```python
# Reduce recycle time in .env
DATABASE_POOL_RECYCLE=600  # 10 minutes
```

### Pre-Ping

The `pool_pre_ping=True` setting verifies connections before using them:
- Adds small latency per request
- Prevents "connection lost" errors
- Usually worth the tradeoff

### TCP Keepalives

Keepalives prevent firewalls from dropping idle connections:
- Particularly important for cloud deployments
- Keep values are already optimized in configuration
- Adjust based on your network:

```python
connect_args={
    "keepalives_idle": 60,      # Start keepalives after 60s
    "keepalives_interval": 20,  # Probe every 20s
}
```

## Troubleshooting

### Too Many Connections Error

```
sqlalchemy.exc.OperationalError: too many connections
```

**Solution:**
1. Increase `pool_size` and/or `max_overflow` in environment variables
2. Reduce number of concurrent requests
3. Check for connection leaks - ensure sessions are properly closed

```python
# Monitor pool
from pqc_secure.db.transaction import get_pool_status
print(get_pool_status(engine))
```

### "Connection Lost" Errors

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) server closed the connection unexpectedly
```

**Solution:**
1. Enable `pool_pre_ping=True` (already enabled)
2. Reduce `pool_recycle` time in .env
3. Use `retry_transaction` for retry logic

### Stale Connections

**Problem:** Connections become stale after database restart or network issues

**Solution:**
- Already handled by `pool_pre_ping=True`
- Reduce `pool_recycle` if still having issues
- Dispose pool on demand:

```python
from pqc_secure.db.session import dispose_connection_pool
dispose_connection_pool()  # Forces all connections to be recreated
```

## Monitoring and Metrics

### Connection Pool Events

Pool events are automatically logged. Check logs for:
- Connection checkouts/check-ins
- Pool exhaustion (overflow being used)
- Connection errors

```python
# In logging.yml or config
loggers:
  sqlalchemy.pool:
    level: DEBUG  # To see pool events
```

### Application Startup/Shutdown

Ensure pool is properly disposed on shutdown:

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pqc_secure.db.session import dispose_connection_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up")
    yield
    # Shutdown
    print("Shutting down")
    dispose_connection_pool()

app = FastAPI(lifespan=lifespan)
```

## References

- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [PostgreSQL Connection Limits](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Database Best Practices](https://docs.sqlalchemy.org/en/20/faq/performance.html)
