"""Database initialization and seeding utilities"""
import logging
import subprocess
import sys
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from pqc_secure.db.models import Base, User, AuditLog, AuditEventType
from pqc_secure.db.session import engine, SessionLocal
from pqc_secure.core.config import settings

logger = logging.getLogger(__name__)


def run_alembic_migrations() -> None:
    """Run Alembic migrations to initialize database schema"""
    logger.info("Running Alembic migrations...")
    try:
        # Run alembic upgrade head to apply all migrations
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd="/",  # Use root to find alembic.ini
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Alembic migration failed: {result.stderr}")
            # Fallback to metadata.create_all if migration fails
            logger.warning("Falling back to SQLAlchemy metadata.create_all()")
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Alembic migrations applied successfully")
            logger.debug(f"Migration output: {result.stdout}")
    except Exception as e:
        logger.warning(f"Failed to run Alembic migrations, falling back to metadata.create_all(): {e}")
        Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """Initialize the database by running Alembic migrations"""
    logger.info("Initializing database...")
    
    # Check if database is accessible
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    # Run migrations
    try:
        run_alembic_migrations()
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def drop_all_tables() -> None:
    """Drop all tables from the database (use with caution!)"""
    logger.warning("Dropping all database tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def get_migration_status() -> dict:
    """Get current migration status"""
    logger.debug("Checking migration status...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd="/",
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "current_revision": result.stdout.strip(),
            }
        else:
            return {
                "status": "error",
                "message": result.stderr.strip(),
            }
    except Exception as e:
        logger.warning(f"Failed to get migration status: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def is_database_initialized() -> bool:
    """Check if database is initialized by checking if any tables exist"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return len(tables) > 0
    except Exception as e:
        logger.error(f"Failed to check database initialization: {e}")
        return False


def get_table_count() -> dict:
    """Get count of records in each table"""
    db = SessionLocal()
    try:
        tables = {
            'users': db.query(User).count(),
            'audit_logs': db.query(AuditLog).count(),
        }
        return tables
    except Exception as e:
        logger.error(f"Failed to get table counts: {e}")
        return {}
    finally:
        db.close()


def seed_demo_data() -> None:
    """Seed database with demo/test data"""
    db = SessionLocal()
    try:
        # Check if demo data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            logger.info("Demo data already exists, skipping seeding")
            return
        
        logger.info("Seeding demo data...")
        
        # Create demo users (passwords are hashed - these are just placeholders)
        # In production, passwords should be properly hashed
        demo_user_1 = User(
            email="alice@example.com",
            password_hash="$argon2id$v=19$m=65540,t=3,p=4$seed1234567890ab$" + "x" * 43,
            account_status="active"
        )
        demo_user_2 = User(
            email="bob@example.com",
            password_hash="$argon2id$v=19$m=65540,t=3,p=4$seed1234567890ab$" + "y" * 43,
            account_status="active"
        )
        
        db.add(demo_user_1)
        db.add(demo_user_2)
        db.commit()
        
        logger.info("Demo data seeded successfully")
        
        # Log seeding event
        audit_entry = AuditLog(
            event_type="database_seeded",
            user_id=None,
            resource_id=None,
            resource_type="database",
            action="seed_demo_data",
            status="success",
            details="Demo users created for testing"
        )
        db.add(audit_entry)
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed demo data: {e}")
        raise
    finally:
        db.close()


def verify_database_health() -> bool:
    """Verify database health and connectivity"""
    try:
        db = SessionLocal()
        # Simple query to verify connection
        result = db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database health check passed")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def clear_audit_logs() -> int:
    """Clear all audit logs (use with caution!)"""
    db = SessionLocal()
    try:
        count = db.query(AuditLog).delete()
        db.commit()
        logger.info(f"Cleared {count} audit log entries")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear audit logs: {e}")
        raise
    finally:
        db.close()
