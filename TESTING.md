# Testing Guide - PQC-Secure

## Overview

PQC-Secure uses a comprehensive testing strategy combining unit tests, integration tests, and property-based tests to ensure correctness and reliability.

## Test Organization

```
tests/
├── test_auth_endpoints.py      # Authentication tests (48 tests)
├── test_audit.py               # Audit logging tests
├── test_config.py              # Configuration tests
├── test_docker_setup.py        # Docker setup validation
├── test_logging.py             # Logging tests
├── test_migration_structure.py # Database migration tests
├── test_models.py              # ORM model tests
└── test_transaction_management.py  # Transaction handling tests
```

## Running Tests

### Run All Tests
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest tests/test_auth_endpoints.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_auth_endpoints.py::TestAuthEndpointRegistration -v
```

### Run Specific Test
```bash
pytest tests/test_auth_endpoints.py::TestAuthIntegration::test_registration_workflow_success -v
```

### Run with Coverage Report
```bash
pytest --cov=pqc_secure tests/ --cov-report=html
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

**Example:** `TestAuthServiceUnit`
- `test_normalize_email` - Email normalization logic
- `test_validate_email_format_valid` - Valid email formats
- `test_validate_password_valid` - Password requirements
- `test_hash_password` - Password hashing
- `test_verify_password_*` - Password verification

### 2. Integration Tests (New - Task 2.1)

Test complete workflows across multiple components.

**TestAuthIntegration (10 tests)**
- `test_registration_workflow_success` - Full registration with DB persistence
- `test_registration_with_invalid_input` - Input validation
- `test_registration_prevents_duplicate_emails` - Email uniqueness
- `test_registration_validates_email_format` - Format validation
- `test_registration_validates_password_requirements` - Complexity requirements
- `test_registration_normalizes_email` - Email normalization
- `test_registration_hashes_password` - Password security
- `test_registration_returns_valid_session_token` - JWT validation
- Plus additional inherited tests

### 3. Endpoint Tests

Test API endpoints and their behavior.

**TestAuthEndpointRegistration**
- `test_register_endpoint_success` - Successful registration
- `test_register_endpoint_rate_limiting` - Rate limit enforcement
- `test_register_endpoint_rate_limit_per_client` - Per-client limiting

### 4. Rate Limiting Tests

Test rate limiting middleware.

**TestRateLimiter**
- `test_rate_limiter_allow_requests_within_limit`
- `test_rate_limiter_blocks_requests_over_limit`
- `test_rate_limiter_per_client`
- `test_endpoint_rate_limiter_extract_client_id`
- `test_endpoint_rate_limiter_extract_forwarded_ip`

## Test Fixtures

### `db_session` Fixture
Creates an isolated SQLite test database that's cleaned up after each test.

```python
@pytest.fixture
def db_session():
    # Creates test database
    # Yields session
    # Cleans up afterward
```

### `reset_rate_limiter` Fixture
Resets rate limiter state between tests to prevent cross-test pollution.

```python
@pytest.fixture
def reset_rate_limiter():
    # Clears rate limiter state before test
    yield
    # Clears after test
```

### `client` Fixture
Creates a FastAPI test client with mocked database and reset rate limiter.

```python
@pytest.fixture
def client(db_session, reset_rate_limiter):
    # Creates test client
    yield
    # Cleans up
```

## Test Data

Tests use realistic data that conforms to validation rules:

- **Valid Email:** `user@example.com`, `test.user@example.co.uk`
- **Valid Password:** `SecurePass123` (8+ chars, uppercase, lowercase, digit)
- **Invalid Email:** `notanemail`, `user@`, `@example.com`
- **Invalid Password:** `short1` (too short), `lowercase123` (no uppercase)

## Test Coverage

### Current Coverage

**Authentication (Task 2.1): 48 tests**
- User registration: 15 tests
- Email validation: 5 tests
- Password validation: 8 tests
- Rate limiting: 5 tests
- Token management: 4 tests
- Inherited/service tests: 6 tests

### Requirements Validation

All acceptance criteria for US-01 are tested:

| Criterion | Test | Status |
|-----------|------|--------|
| AC-01.1 - User registration | `test_registration_workflow_success` | ✅ |
| AC-01.2 - Password hashing | `test_registration_hashes_password` | ✅ |
| AC-01.3 - Email uniqueness | `test_registration_prevents_duplicate_emails` | ✅ |
| AC-01.4 - Rate limiting | `test_register_endpoint_rate_limiting` | ✅ |
| AC-01.5 - No email enumeration | `test_registration_with_invalid_input` | ✅ |

## Common Test Patterns

### Testing Successful Workflow
```python
def test_registration_workflow_success(self, client, db_session):
    response = client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "SecurePass123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    
    # Verify database persistence
    user = db_session.query(User).filter_by(id=data["id"]).first()
    assert user is not None
```

### Testing Validation
```python
def test_registration_validates_email_format(self, client):
    response = client.post("/auth/register", json={
        "email": "invalid-email",
        "password": "ValidPass123"
    })
    
    assert response.status_code == 422  # Pydantic validation
```

### Testing Error Cases
```python
def test_registration_prevents_duplicate_emails(self, client):
    # First registration
    response1 = client.post("/auth/register", json={...})
    assert response1.status_code == 201
    
    # Duplicate registration
    response2 = client.post("/auth/register", json={...})
    assert response2.status_code == 400
    assert "Unable to create account" in response2.json()["detail"]
```

## Debugging Tests

### Run with Detailed Output
```bash
pytest -vv tests/test_auth_endpoints.py
```

### Run with Print Statements
```bash
pytest -s tests/test_auth_endpoints.py
```

### Run with Debugger
```bash
pytest --pdb tests/test_auth_endpoints.py
```

### View Captured Logs
```bash
pytest --log-cli-level=DEBUG tests/test_auth_endpoints.py
```

## Continuous Integration

Tests are run automatically on:
- Git commits (with pre-commit hooks)
- Pull requests
- Scheduled builds

### Example CI Configuration

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=pqc_secure tests/

# Generate coverage report
coverage report --fail-under=80
```

## Future Testing

### Upcoming Tests (Tasks 2.2-2.4)
- Login endpoint tests
- Session validation tests
- Logout endpoint tests
- Protected route tests

### Property-Based Testing
Tests will be enhanced with property-based testing (Hypothesis/QuickCheck) for:
- Password validation properties
- Email normalization invariants
- Rate limiting consistency

## Contributing Tests

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests cover:
   - Happy path (success case)
   - Validation errors
   - Edge cases
   - Database persistence
3. Run full test suite: `pytest -v`
4. Check coverage: `pytest --cov`
5. Commit with tests

## Troubleshooting

### Tests Failing Unexpectedly

**Rate Limiter State Pollution**
- Ensure `reset_rate_limiter` fixture is used
- Check test order dependencies

**Database Issues**
- Verify SQLite temp database cleanup
- Check `db_session` fixture is used
- Run `pytest --lf` (last failed) to debug

**Flaky Tests**
- Check for timing dependencies
- Verify mock setup/teardown
- Look for shared state between tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
