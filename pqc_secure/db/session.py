"""Database session management with connection pooling and transaction support"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool, QueuePool
from pqc_secure.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Import transaction setup function - handle circular imports
try:
    from pqc_secure.db.transaction import setup_connection_pooling_listeners
except ImportError:
    # For testing, we can skip this if transaction module isn't available yet
    def setup_connection_pooling_listeners(engine):
        pass

# Create engine with advanced connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=20,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.debug,  # Log SQL in debug mode
    connect_args={
        "connect_timeout": 10,  # Connection timeout
        "keepalives": 1,  # Enable TCP keepalives
        "keepalives_idle": 30,  # Start keepalives after 30s
        "keepalives_interval": 10,  # Send keepalives every 10s
        "keepalives_count": 5,  # Give up after 5 failed keepalives
    }
)

# Set up connection pool event listeners for monitoring
setup_connection_pooling_listeners(engine)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=True,  # Refresh objects after commit
)


def get_db_session() -> Session:
    """
    Dependency for FastAPI that provides database sessions.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db_session)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy Session object
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error in database session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def dispose_connection_pool() -> None:
    """
    Dispose of all connections in the pool.
    
    Use this during application shutdown to ensure clean connection cleanup.
    Should be called in FastAPI lifespan context manager.
    """
    engine.dispose()
    logger.info("Connection pool disposed")

