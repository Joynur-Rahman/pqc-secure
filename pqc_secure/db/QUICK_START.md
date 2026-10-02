# Quick Start: Transaction Management

## Import Transaction Utilities

```python
from pqc_secure.db import (
    transaction,
    transaction_savepoint,
    TransactionManager,
    get_pool_status,
    retry_transaction,
    get_db_session,
)
from pqc_secure.db.session import SessionLocal
```

## Most Common Pattern: FastAPI Endpoint

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pqc_secure.db import transaction, get_db_session
from pqc_secure.db.models import User

app = FastAPI()

@app.post("/users/")
def create_user(email: str, password: str, db: Session = Depends(get_db_session)):
    """Transactions are automatic with this pattern"""
    with transaction(db):
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
    return {"id": user.id, "email": user.email}
```

## Quick Reference

### Transaction (Atomic Operation)
```python
from pqc_secure.db import transaction, SessionLocal

db = SessionLocal()
with transaction(db):
    # Changes auto-commit on exit
    db.add(user)
    db.add(file_package)
```

### Handle Errors
```python
try:
    with transaction(db):
        db.add(user)
except IntegrityError:
    print("User already exists")
```

### Nested Transactions (Savepoints)
```python
with transaction(db):
    db.add(required_data)
    
    try:
        with transaction_savepoint(db):
            db.add(optional_data)
    except ValueError:
        # Required data still committed, optional not added
        pass
```

### Retry on Failures
```python
from pqc_secure.db import retry_transaction

def register_user(db):
    user = User(email=email, password_hash=hash)
    db.add(user)
    return user

result = retry_transaction(db, register_user, max_retries=3)
```

### Check Pool Status
```python
from pqc_secure.db import get_pool_status
from pqc_secure.db.session import engine

status = get_pool_status(engine)
print(f"Available: {status['available']}")
print(f"In use: {status['checked_out']}")
```

### Multiple Operations in Transaction
```python
with transaction(db):
    # All succeed or all fail together
    user = User(email="test@example.com", password_hash="hash")
    db.add(user)
    
    key = CryptographicKey(user_id=user.id, algorithm="ml-kem-768", ...)
    db.add(key)
    
    grant = AccessGrant(user_id=user.id, ...)
    db.add(grant)
```

## Configuration

Edit `.env` file:
```bash
DATABASE_POOL_SIZE=10              # Default pool size
DATABASE_POOL_RECYCLE=3600         # Recycle after 1 hour
```

## Troubleshooting

### "Too many connections" error
- Increase `DATABASE_POOL_SIZE` in .env
- Make sure you're using `transaction` context manager
- Check for connection leaks

### "Connection lost" error
- Normal - connection will be re-established automatically
- If frequent, reduce `DATABASE_POOL_RECYCLE` time

### Transaction seems slow
- Check if you have long operations inside `transaction` blocks
- Keep transactions small and focused
- Profile with: `from pqc_secure.db import get_pool_status`

## Best Practices

✅ **DO:**
- Always use `transaction` context manager
- Keep transactions small
- Handle specific exceptions
- Use savepoints for optional operations

❌ **DON'T:**
- Use `db.commit()` and `db.rollback()` manually
- Do long-running tasks inside transactions
- Catch generic `Exception`
- Leave transactions open

## Testing

Run transaction management tests:
```bash
pytest tests/test_transaction_management.py -v
```

All tests should pass:
```
12 passed
```

---

For detailed information, see `CONNECTION_POOLING_GUIDE.md`
