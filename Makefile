.PHONY: help build up down logs restart clean ps test

help:
	@echo "PQC-Secure Docker Commands"
	@echo "============================"
	@echo "make build         - Build Docker images"
	@echo "make up            - Start all services"
	@echo "make down          - Stop all services"
	@echo "make restart       - Restart all services"
	@echo "make logs          - View service logs"
	@echo "make ps            - Show service status"
	@echo "make clean         - Remove containers and volumes"
	@echo "make test          - Run tests in backend container"
	@echo "make shell         - Open shell in backend container"
	@echo "make db-shell      - Open PostgreSQL shell"
	@echo "make db-migrate    - Run database migrations"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started. Check status with 'make ps'"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

ps:
	docker-compose ps

clean:
	docker-compose down -v
	@echo "All containers and volumes removed"

test:
	docker-compose exec backend pytest

shell:
	docker-compose exec backend bash

db-shell:
	docker-compose exec postgres psql -U pqc_user -d pqc_secure

db-migrate:
	docker-compose exec backend alembic upgrade head

health:
	@echo "Checking service health..."
	@docker-compose exec backend curl -s http://localhost:8000/health | python -m json.tool || echo "Backend: Not ready"
	@docker-compose exec postgres pg_isready -U pqc_user -d pqc_secure && echo "Database: Ready" || echo "Database: Not ready"
	@docker-compose exec minio curl -s http://localhost:9000/minio/health/live && echo "MinIO: Ready" || echo "MinIO: Not ready"
