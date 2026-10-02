"""Transaction management and context managers for database operations"""
from contextlib import contextmanager
from typing import Generator, Optional, Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy import event
from sqlalchemy.pool import Pool
import logging

logger = logging.getLogger(__name__)


@contextmanager
def transaction(session: Session, rollback_on_error: bool = True) -> Generator[Session, None, None]:
    """
    Context manager for database transactions.
    
    Automatically commits on success or rolls back on error.
    
    Args:
        session: SQLAlchemy session
        rollback_on_error: Whether to rollback on exception (default: True)
    
    Yields:
        Session object for use in context
    
    Example:
        with transaction(session) as db:
            db.add(user)
            # commit happens automatically on exit
    """
    try:
        yield session
        session.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        if rollback_on_error:
            session.rollback()
            logger.warning(f"Transaction rolled back due to error: {e}")
        raise
    finally:
        pass  # Session cleanup handled by SessionLocal lifecycle


@contextmanager
def transaction_savepoint(session: Session, name: Optional[str] = None) -> Generator[Any, None, None]:
    """
    Context manager for database savepoints (nested transactions).
    
    Allows nested transactions with independent rollback capability.
    
    Args:
        session: SQLAlchemy session
        name: Optional savepoint name for debugging
    
    Yields:
        Savepoint object
    
    Example:
        with transaction(session) as db:
            db.add(user1)
            with transaction_savepoint(db) as sp:
                db.add(user2)  # Can rollback just this without rolling back user1
    """
    savepoint = session.begin_nested()
    try:
        yield savepoint
        savepoint.commit()
        logger.debug(f"Savepoint {'(' + name + ')' if name else ''} committed successfully")
    except Exception as e:
        savepoint.rollback()
        logger.warning(f"Savepoint {'(' + name + ')' if name else ''} rolled back due to error: {e}")
        raise


class TransactionManager:
    """Manager for database transactions with connection pooling integration"""
    
    def __init__(self, session_factory):
        """Initialize transaction manager with session factory"""
        self.session_factory = session_factory
        self._sessions: dict[int, Session] = {}
    
    def get_session(self) -> Session:
        """Get or create a database session"""
        import threading
        thread_id = threading.get_ident()
        
        if thread_id not in self._sessions or self._sessions[thread_id] is None:
            self._sessions[thread_id] = self.session_factory()
            logger.debug(f"Created new session for thread {thread_id}")
        
        return self._sessions[thread_id]
    
    def close_session(self) -> None:
        """Close the current thread's session"""
        import threading
        thread_id = threading.get_ident()
        
        if thread_id in self._sessions and self._sessions[thread_id] is not None:
            self._sessions[thread_id].close()
            del self._sessions[thread_id]
            logger.debug(f"Closed session for thread {thread_id}")
    
    @contextmanager
    def transaction(self, rollback_on_error: bool = True) -> Generator[Session, None, None]:
        """
        Context manager for transactions using this manager's session.
        
        Args:
            rollback_on_error: Whether to rollback on exception
        
        Yields:
            Session object
        """
        session = self.get_session()
        with transaction(session, rollback_on_error) as db:
            yield db


def setup_connection_pooling_listeners(engine) -> None:
    """
    Set up listeners for connection pool events for monitoring and optimization.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    
    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new connections"""
        logger.debug("New database connection established")
    
    @event.listens_for(Pool, "close")
    def receive_close(dbapi_conn, connection_record):
        """Log closed connections"""
        logger.debug("Database connection closed")
    
    @event.listens_for(Pool, "detach")
    def receive_detach(dbapi_conn, connection_record):
        """Log detached connections"""
        logger.debug("Database connection detached from pool")
    
    @event.listens_for(Pool, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout from pool"""
        logger.debug("Connection checked out from pool")
    
    @event.listens_for(Pool, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection check-in to pool"""
        logger.debug("Connection returned to pool")


def get_pool_status(engine) -> dict[str, Any]:
    """
    Get current connection pool status.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool
    # Handle different pool types - NullPool doesn't have these methods
    try:
        # Try QueuePool methods first
        return {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "available": pool.size() - pool.checkedout(),
        }
    except (AttributeError, TypeError):
        # For NullPool or other pool types, return default status
        return {
            "pool_size": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
            "available": 0,
        }


def retry_transaction(
    session: Session,
    func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 0.1
) -> Any:
    """
    Retry a database operation with exponential backoff.
    
    Useful for handling transient errors like connection timeouts or deadlocks.
    
    Args:
        session: SQLAlchemy session
        func: Callable that performs the database operation
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff factor for exponential backoff
    
    Returns:
        Result of the function call
    
    Raises:
        Exception: If all retries fail
    
    Example:
        def add_user(db):
            user = User(email="test@example.com", password_hash="hash")
            db.add(user)
            return user
        
        result = retry_transaction(session, add_user)
    """
    import time
    from sqlalchemy.exc import OperationalError
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with transaction(session) as db:
                result = func(db)
                logger.debug(f"Transaction succeeded on attempt {attempt + 1}")
                return result
        except OperationalError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"Transaction failed on attempt {attempt + 1}, retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Transaction failed after {max_retries} attempts")
    
    raise last_error
