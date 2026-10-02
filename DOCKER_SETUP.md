# Docker Compose Setup for PQC-Secure

This document describes the Docker Compose configuration for running PQC-Secure with all its dependencies.

## Architecture

The Docker Compose setup includes three main services:

1. **PostgreSQL Database** - Stores user data, keys, file metadata, and audit logs
2. **MinIO Object Storage** - Provides S3-compatible storage for encrypted files
3. **Backend API** - FastAPI application for file sharing and encryption

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- At least 2GB free RAM
- Ports 5432, 8000, 9000, 9001 available

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd pqc-secure

# Copy environment template
cp .env.example .env
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Verify Services

```bash
# Check service health
docker-compose ps

# Test backend API
curl http://localhost:8000/health

# Access MinIO Console
# Open browser to http://localhost:9001
# Username: minioadmin
# Password: minioadmin123
```

## Service Details

### PostgreSQL Database

- **Container**: pqc-postgres
- **Port**: 5432 (exposed)
- **Database**: pqc_secure
- **Username**: pqc_user
- **Password**: pqc_password
- **Data Directory**: postgres_data (Docker volume)
- **Health Check**: Verifies database is ready every 10s

**Connection String (from outside container)**:
```
postgresql://pqc_user:pqc_password@localhost:5432/pqc_secure
```

**Connection String (from backend container)**:
```
postgresql://pqc_user:pqc_password@postgres:5432/pqc_secure
```

### MinIO Object Storage

- **Container**: pqc-minio
- **API Port**: 9000 (exposed)
- **Console Port**: 9001 (exposed)
- **Access Key**: minioadmin
- **Secret Key**: minioadmin123
- **Data Directory**: minio_data (Docker volume)
- **Default Bucket**: pqc-files

**Access Methods**:
- S3-compatible API: http://localhost:9000
- Web Console: http://localhost:9001

### Backend API

- **Container**: pqc-backend
- **Port**: 8000 (exposed)
- **Framework**: FastAPI with Uvicorn
- **Code Directory**: ./pqc_secure (mounted for live reload)
- **Dependencies**: postgres, minio

**Endpoints**:
- Health Check: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

The `.env` file controls service configuration. Key variables:

```
# Database
DATABASE_URL=postgresql://pqc_user:pqc_password@postgres:5432/pqc_secure

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# API
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

## Data Persistence

All data is persisted in Docker volumes:

- **postgres_data**: PostgreSQL database files
- **minio_data**: MinIO object storage files

To reset all data:

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker volume rm pqc-postgres_data pqc-minio_data

# Start fresh
docker-compose up -d
```

## Development

### Live Code Reloading

The backend container mounts the local `./pqc_secure` directory, enabling live reload:

```bash
# Changes to .py files automatically reload the app
# Edit files locally, changes appear immediately
```

### Running Commands Inside Containers

```bash
# Execute Python command in backend
docker-compose exec backend python -m pytest

# Execute shell in postgres
docker-compose exec postgres psql -U pqc_user -d pqc_secure

# Execute MinIO admin commands
docker-compose exec minio mc ls local
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs postgres
docker-compose logs minio
docker-compose logs backend

# Follow logs (tail)
docker-compose logs -f backend
```

## Troubleshooting

### Services fail to start

Check logs for error messages:
```bash
docker-compose logs
```

Common issues:
- Port conflicts: Another service using 5432, 8000, 9000, or 9001
- Insufficient resources: Docker needs more RAM/disk
- Image pull failures: Check internet connection

### Database connection errors

Ensure PostgreSQL is healthy:
```bash
docker-compose ps
# postgres should show "healthy" in the STATUS column
```

### MinIO bucket issues

Create bucket manually:
```bash
docker-compose exec minio mc mb local/pqc-files
```

### Reset everything

```bash
# Stop and remove everything
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

## Production Considerations

This setup is optimized for development. For production deployment:

1. **Security**:
   - Change default credentials in `.env`
   - Use strong SECRET_KEY
   - Enable HTTPS/TLS
   - Restrict CORS origins
   - Run behind reverse proxy

2. **Database**:
   - Use managed PostgreSQL service
   - Enable backups and replication
   - Configure proper resource limits

3. **Storage**:
   - Use AWS S3 or equivalent
   - Enable encryption at rest
   - Configure versioning and lifecycle policies

4. **Monitoring**:
   - Set up logging aggregation
   - Configure health checks and alerting
   - Monitor resource usage

5. **Performance**:
   - Set appropriate resource limits
   - Configure connection pooling
   - Use CDN for static assets

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [MinIO Docker Documentation](https://min.io/docs/minio/linux/operations/installation.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
