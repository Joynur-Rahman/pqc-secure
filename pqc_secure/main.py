"""
PQC-Secure File Sharing Application
Main entry point for FastAPI application
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pqc_secure.core.config import settings
from pqc_secure.core.logging import logger
from pqc_secure.db.session import dispose_connection_pool, engine
from pqc_secure.db.transaction import get_pool_status
from pqc_secure.api import auth

# Initialize logging
logger.info(f"PQC-Secure starting up in {settings.environment} environment")
logger.info(f"Audit logging enabled: {settings.audit_logging_enabled}")
if settings.audit_logging_enabled:
    logger.info(f"Audit events configured: {settings.audit_log_events}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for FastAPI.
    Handles startup and shutdown events including database connection pool management.
    """
    # Startup
    logger.info("Application startup: Initializing database connection pool")
    pool_status = get_pool_status(engine)
    logger.info(f"Connection pool initialized - Pool size: {pool_status['pool_size']}, "
                f"Max overflow: {pool_status['total'] - pool_status['pool_size']}")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown: Disposing connection pool")
    dispose_connection_pool()
    logger.info("Connection pool disposed successfully")


app = FastAPI(
    title=settings.api_title,
    description="Post-quantum cryptography-based secure file sharing system",
    version=settings.api_version,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "testserver"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pqc-secure", "version": settings.api_version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port
    )
