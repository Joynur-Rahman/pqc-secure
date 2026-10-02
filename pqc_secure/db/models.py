"""SQLAlchemy ORM models"""
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Enum, ForeignKey, LargeBinary, DECIMAL
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class AccountStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class KeyStatus(str, enum.Enum):
    """Cryptographic key status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class KeyType(str, enum.Enum):
    """Key type (public or private)"""
    PUBLIC = "public"
    PRIVATE = "private"


class GrantStatus(str, enum.Enum):
    """File access grant status"""
    ACTIVE = "active"
    REVOKED = "revoked"


class AuditEventType(str, enum.Enum):
    """Audit event types"""
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    LOGIN_FAILED = "login_failed"
    REGISTRATION_FAILED = "registration_failed"
    PERMISSION_DENIED = "permission_denied"
    CRYPTO_VERIFICATION_FAILED = "crypto_verification_failed"
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_SHARED = "file_shared"
    SHARE_REVOKED = "share_revoked"
    KEY_REGISTERED = "key_registered"
    KEY_ROTATED = "key_rotated"
    KEY_REVOKED = "key_revoked"
    ACCESS_DENIED = "access_denied"


class User(Base):
    """User accounts"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    account_status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    keys = relationship("CryptographicKey", back_populates="user", cascade="all, delete-orphan")
    sent_packages = relationship("FilePackage", foreign_keys="FilePackage.sender_id", back_populates="sender")
    access_grants = relationship("AccessGrant", back_populates="recipient")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, status={self.account_status})>"


class CryptographicKey(Base):
    """User's cryptographic keys for encryption and signing"""
    __tablename__ = "cryptographic_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)  # ml-kem-768, ml-dsa-65, x25519, ed25519
    key_type = Column(String(50), nullable=False)  # public, private
    version = Column(Integer, nullable=False, default=1)
    key_id = Column(String(255), nullable=False, unique=True, index=True)
    public_key_material = Column(LargeBinary, nullable=False)
    private_key_material = Column(LargeBinary, nullable=True)  # NULL if user-held or browser-held
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="keys")
    packages = relationship("FilePackage", back_populates="recipient_key")
    
    def __repr__(self):
        return f"<CryptographicKey(key_id={self.key_id}, algorithm={self.algorithm}, status={self.status})>"


class FilePackage(Base):
    """Encrypted file packages with metadata and recipient encapsulations"""
    __tablename__ = "file_packages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    recipient_key_id = Column(String, ForeignKey("cryptographic_keys.key_id"), nullable=False)
    package_version = Column(String(50), nullable=False)  # versioned package format
    crypto_mode = Column(String(50), nullable=False)  # pqc or classical
    
    # Encapsulation/shared secret per recipient
    encapsulated_secret = Column(LargeBinary, nullable=False)  # ML-KEM ciphertext or ephemeral public key
    
    # Encrypted payload reference
    payload_storage_key = Column(String(255), nullable=False)  # filesystem path or S3 key
    
    # Canonical manifest and signature
    manifest_json = Column(Text, nullable=False)  # canonical manifest (no secrets)
    signature = Column(LargeBinary, nullable=False)  # sender's signature over manifest
    
    # File metadata
    original_filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=False)  # encrypted file size
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_packages")
    recipient_key = relationship("CryptographicKey", back_populates="packages")
    access_grants = relationship("AccessGrant", back_populates="package")
    chunks = relationship("FileChunk", back_populates="package", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<FilePackage(id={self.id}, sender_id={self.sender_id}, crypto_mode={self.crypto_mode})>"


class FileChunk(Base):
    """File chunks for large file handling"""
    __tablename__ = "file_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    package_id = Column(String, ForeignKey("file_packages.id"), nullable=False, index=True)
    chunk_number = Column(Integer, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    storage_key = Column(String(255), nullable=False)  # filesystem path or S3 key
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    package = relationship("FilePackage", back_populates="chunks")
    
    def __repr__(self):
        return f"<FileChunk(package_id={self.package_id}, chunk_number={self.chunk_number})>"


class AccessGrant(Base):
    """Access grants: who can access which package"""
    __tablename__ = "access_grants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    package_id = Column(String, ForeignKey("file_packages.id"), nullable=False, index=True)
    recipient_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    package = relationship("FilePackage", back_populates="access_grants")
    recipient = relationship("User", back_populates="access_grants")
    
    def __repr__(self):
        return f"<AccessGrant(package_id={self.package_id}, recipient_id={self.recipient_id}, status={self.status})>"


class AuditLog(Base):
    """Audit log entries for compliance and security monitoring"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    resource_id = Column(String, nullable=True, index=True)
    resource_type = Column(String, nullable=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, failure
    details = Column(Text, nullable=True)  # JSON serialized details, no secrets
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(event_type={self.event_type}, user_id={self.user_id}, status={self.status}, created_at={self.created_at})>"
