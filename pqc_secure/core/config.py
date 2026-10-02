"""Application configuration"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
import logging

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Environment
    environment: str = Field(default="development", description="Environment mode: development, staging, production")
    debug: bool = Field(default=True, description="Enable debug mode")
    
    # API Configuration
    api_title: str = "PQC-Secure File Sharing"
    api_version: str = "0.1.0"
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", description="Server host address")
    server_port: int = Field(default=8000, description="Server port number")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://pqc_user:pqc_password@localhost:5432/pqc_secure",
        description="PostgreSQL database connection URL"
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_pool_recycle: int = Field(default=3600, description="Database connection recycle time in seconds")
    
    # Security Configuration
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing - MUST be changed in production"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration time in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration time in days")
    
    # Password Hashing Configuration
    password_hashing_algorithm: str = Field(
        default="argon2id",
        description="Password hashing algorithm: argon2id or bcrypt"
    )
    password_min_length: int = Field(default=8, description="Minimum password length")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Rate limit requests per minute for general endpoints")
    rate_limit_auth_requests_per_minute: int = Field(default=5, description="Rate limit for authentication endpoints (login/register)")
    
    # Storage Configuration
    storage_type: str = Field(default="filesystem", description="Storage type: filesystem or s3")
    storage_path: str = Field(default="./data/uploads", description="Local filesystem storage path")
    storage_bucket: str = Field(default="pqc-files", description="Storage bucket name")
    max_file_size_mb: int = Field(default=500, description="Maximum file upload size in MB")
    max_recipients_per_share: int = Field(default=10, description="Maximum number of recipients per file share")
    
    # MinIO Configuration (S3-compatible)
    minio_endpoint: Optional[str] = Field(default=None, description="MinIO endpoint URL")
    minio_access_key: Optional[str] = Field(default=None, description="MinIO access key")
    minio_secret_key: Optional[str] = Field(default=None, description="MinIO secret key")
    minio_use_ssl: bool = Field(default=False, description="Use SSL for MinIO connection")
    
    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Cryptographic Configuration
    default_crypto_mode: str = Field(
        default="pqc",
        description="Default cryptographic mode: pqc (post-quantum) or classical"
    )
    enable_pqc_mode: bool = Field(default=True, description="Enable post-quantum cryptography algorithms (ML-KEM, ML-DSA)")
    enable_classical_mode: bool = Field(default=True, description="Enable classical algorithms (X25519, Ed25519)")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_file: Optional[str] = Field(default=None, description="Log file path (None for console only)")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    # Audit Logging Configuration
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")
    audit_log_events: str = Field(
        default="auth,permission,crypto,upload,download",
        description="Comma-separated list of audit event types to log"
    )
    
    # Session Configuration
    session_cookie_secure: bool = Field(default=False, description="Use secure cookies (HTTPS only)")
    session_cookie_httponly: bool = Field(default=True, description="Make cookies HTTP only")
    session_cookie_samesite: str = Field(default="lax", description="SameSite cookie attribute: strict, lax, or none")
    
    def get_allowed_origins_list(self) -> list:
        """Parse allowed origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    def get_audit_log_events(self) -> list:
        """Parse audit log events from comma-separated string"""
        return [event.strip() for event in self.audit_log_events.split(",")]
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    def get_log_level(self) -> int:
        """Get numeric log level for logging module"""
        return getattr(logging, self.log_level.upper(), logging.INFO)
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )

settings = Settings()
