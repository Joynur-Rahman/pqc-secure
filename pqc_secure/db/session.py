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

# Set up connect args depending on dialect
connect_args = {}
if settings.database_url.startswith("postgresql"):
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
elif settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine with advanced connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool if not settings.database_url.startswith("sqlite") else None,
    pool_size=settings.database_pool_size if not settings.database_url.startswith("sqlite") else 5,
    max_overflow=20 if not settings.database_url.startswith("sqlite") else 10,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    echo=settings.debug,
    connect_args=connect_args
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

