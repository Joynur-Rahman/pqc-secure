# PQC-Secure: Post-Quantum Cryptography File Sharing System

A web-based file-sharing system using post-quantum cryptography (PQC) algorithms. This system enables authenticated users to encrypt, store, and share files securely with recipients using both PQC algorithms (ML-KEM, ML-DSA) and classical algorithms (X25519, Ed25519).

## Current Status

### Phase 2: Authentication & User Management (In Progress)

- ✅ **2.1: User Registration API** - COMPLETE
  - `/auth/register` POST endpoint implemented
  - Email validation and normalization
  - Password hashing (Argon2id/bcrypt)
  - Rate limiting (5 requests/minute)
  - **Integration tests: 10 new tests added, all passing (48 total tests)**

- ⏳ **2.2: User Login API** - Not Started
- ⏳ **2.3: Session Management** - Not Started
- ⏳ **2.4: Authentication UI** - Not Started

### Previous Phases (Complete)

- ✅ Phase 1: Project Setup & Core Infrastructure
- ✅ Phase 1.1-1.3: Database, ORM, Frontend project setup

## Project Structure

```
pqc_secure/
├── api/                    # FastAPI route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── keys.py            # Key management endpoints
│   └── files.py           # File sharing endpoints
├── services/              # Business logic services
│   ├── auth.py            # Authentication service
│   ├── crypto.py          # Cryptographic operations
│   ├── file.py            # File operations
│   ├── key.py             # Key management
│   ├── access_control.py  # Authorization
│   └── audit.py           # Audit logging
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy ORM models
│   └── session.py         # Database session management
├── core/                  # Core configuration
│   ├── config.py          # Application settings
│   └── logging.py         # Logging configuration
├── schemas/               # Pydantic request/response models
│   ├── auth.py
│   ├── keys.py
│   └── files.py
├── middleware/            # Middleware components
│   └── rate_limit.py      # Rate limiting for auth endpoints
└── main.py                # FastAPI application entry point

frontend/                  # React/TypeScript frontend
├── src/
│   ├── pages/            # Page components
│   ├── components/       # UI components
│   ├── services/         # API service layer
│   └── types/            # TypeScript types
└── vite.config.ts        # Vite configuration

tests/                     # Test suite
├── test_auth_endpoints.py # Authentication tests (48 tests)
└── ...                    # Other test modules
```

## Requirements

- Python 3.11+
- PostgreSQL 12+
- Node.js 18+ (for frontend)
- Docker Compose (optional, for containerized deployment)

## Setup

### Backend

1. Clone the repository and navigate to the project directory

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Copy environment configuration:
```bash
cp .env.example .env
```

4. Install dependencies:
```bash
pip install -e ".[dev]"
```

For PQC support, install the optional PQC dependencies:
```bash
pip install -e ".[pqc]"
```

### Frontend

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

### Start Backend Server

```bash
python -m uvicorn pqc_secure.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Start Frontend Development Server

In a new terminal:
```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the URL shown in the terminal)

## Testing

### Run All Tests

```bash
pytest -v
```

### Run Authentication Tests Only

```bash
pytest tests/test_auth_endpoints.py -v
```

### Run Tests with Coverage

```bash
pytest --cov=pqc_secure tests/
```

### Test Results

**Current Test Suite Status:**
- Total Tests: 48
- Passing: 48 ✅
- Failing: 0
- Coverage: Comprehensive coverage of:
  - User registration endpoint
  - Password hashing and verification
  - Email validation and normalization
  - Rate limiting
  - Database persistence
  - Session token generation

### Key Integration Tests Added (Task 2.1)

1. `test_registration_workflow_success` - Complete registration flow with DB verification
2. `test_registration_with_invalid_input` - Input validation
3. `test_registration_prevents_duplicate_emails` - Email uniqueness enforcement
4. `test_registration_validates_email_format` - Email format validation
5. `test_registration_validates_password_requirements` - Password complexity validation
6. `test_registration_normalizes_email` - Email normalization (lowercase/trim)
7. `test_registration_hashes_password` - Password hashing verification
8. `test_registration_returns_valid_session_token` - JWT token validation
9. Plus all existing unit tests for services and middleware

## API Documentation

### Authentication Endpoints

**POST /auth/register**
- Register a new user with email and password
- Request:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePass123"
  }
  ```
- Response (201 Created):
  ```json
  {
    "id": "uuid-string",
    "email": "user@example.com",
    "account_status": "active",
    "session_token": "jwt-token"
  }
  ```
- Rate limited: 5 requests per minute per client

**Interactive API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Code Quality

```bash
# Format code
black pqc_secure/ frontend/
isort pqc_secure/ frontend/

# Lint code
flake8 pqc_secure/

# Type checking
mypy pqc_secure/
```

### Database

Initialize the database:
```bash
python -m pqc_secure.db.cli init
```

Run migrations:
```bash
alembic upgrade head
```

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

## Security Features

- ✅ Passwords hashed with Argon2id (configurable to bcrypt)
- ✅ Email validation and normalization (lowercase, trimmed)
- ✅ Email uniqueness enforcement (case-insensitive)
- ✅ JWT-based session tokens
- ✅ Rate limiting on authentication endpoints (5 req/min)
- ✅ CORS configured for trusted origins
- ✅ HTTPS-only secure cookies
- ✅ Audit logging of authentication events
- ✅ No secrets logged (passwords, tokens, keys)

## Requirements Compliance

### Acceptance Criteria Met (US-01: User Registration)

- ✅ AC-01.1: User can register with email and password
- ✅ AC-01.2: Password is hashed using Argon2id or bcrypt
- ✅ AC-01.3: Email uniqueness is enforced (normalized)
- ✅ AC-01.4: Authentication endpoints are rate-limited
- ✅ AC-01.5: System does not reveal whether an email is registered

## Deployment

### Docker Compose

```bash
docker-compose up
```

This will start:
- PostgreSQL database
- FastAPI backend
- Frontend development server

See `DOCKER_SETUP.md` for more details.

## Documentation

- [Database Setup](pqc_secure/db/DATABASE_SETUP.md)
- [Connection Pooling](pqc_secure/db/CONNECTION_POOLING_GUIDE.md)
- [Configuration Guide](pqc_secure/core/settings_guide.md)
- [HTTPS Local Development](frontend/HTTPS_SETUP.md)
- [Build Tooling](frontend/BUILD_TOOLING.md)

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Submit a pull request

## License

MIT
