# Quick Start Guide - PQC-Secure Docker Setup

Get PQC-Secure running in 3 easy steps:

## Step 1: Prepare Environment

```bash
# Copy environment configuration
cp .env.example .env

# (Optional) Edit .env if you need to change defaults
# Default credentials are safe for local development only
```

## Step 2: Start Services

```bash
# Using Docker Compose directly
docker-compose up -d

# OR using Makefile (if available)
make up
```

The system will start three services:
- **PostgreSQL Database**: localhost:5432
- **MinIO Object Storage**: localhost:9000 (API) and localhost:9001 (Console)
- **Backend API**: localhost:8000

## Step 3: Verify Everything Works

```bash
# Check service status
docker-compose ps

# Test the API
curl http://localhost:8000/health

# View logs
docker-compose logs -f
```

## Common Commands

```bash
# Stop services
docker-compose down

# View logs for specific service
docker-compose logs backend
docker-compose logs postgres
docker-compose logs minio

# Open shell in backend container
docker-compose exec backend bash

# Run tests
docker-compose exec backend pytest

# Access PostgreSQL
docker-compose exec postgres psql -U pqc_user -d pqc_secure

# Access MinIO Console
# Open browser: http://localhost:9001
# Username: minioadmin
# Password: minioadmin123
```

## Useful Makefile Commands

If you have `make` installed:

```bash
make build       # Build Docker images
make up          # Start services
make down        # Stop services
make logs        # View logs
make ps          # Check status
make test        # Run tests
make clean       # Remove all containers and volumes
make health      # Check service health
```

## API Documentation

Once running, access:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Troubleshooting

### Services won't start
```bash
# View full logs
docker-compose logs

# Check Docker is running
docker ps
```

### Port already in use
```bash
# Find what's using a port (e.g., 8000)
lsof -i :8000

# Or modify docker-compose.yml ports
```

### Database connection errors
```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U pqc_user -d pqc_secure

# Check container is healthy
docker-compose ps
```

### Reset everything
```bash
# This removes all data!
docker-compose down -v
docker-compose up -d
```

## Next Steps

1. Read [DOCKER_SETUP.md](./DOCKER_SETUP.md) for detailed configuration
2. Check [README.md](./README.md) for project overview
3. Review [.kiro/specs/pqc-secure-file-sharing/requirements.md](./.kiro/specs/pqc-secure-file-sharing/requirements.md) for feature details
4. Start implementing tasks from [.kiro/specs/pqc-secure-file-sharing/tasks.md](./.kiro/specs/pqc-secure-file-sharing/tasks.md)

## Production Notes

This Docker setup is optimized for **local development**. For production:

- Change default passwords in `.env`
- Use strong `SECRET_KEY`
- Enable HTTPS/TLS
- Use managed database service
- Use cloud storage (AWS S3, Azure Blob, etc.)
- Set up proper monitoring and logging
- Configure backup and recovery procedures
- Run behind a reverse proxy (nginx, etc.)

See [DOCKER_SETUP.md](./DOCKER_SETUP.md#production-considerations) for production recommendations.
