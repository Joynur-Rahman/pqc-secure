"""Tests for SQLAlchemy ORM models"""
import pytest
import sys
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models directly to avoid session initialization
sys.path.insert(0, 'pqc_secure/db')
from models import (
    Base,
    User,
    CryptographicKey,
    FilePackage,
    FileChunk,
    AccessGrant,
    AuditLog,
    AccountStatus,
    KeyStatus,
    KeyType,
    GrantStatus,
    AuditEventType,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestUserModel:
    """Test User model"""
    
    def test_user_creation(self, db_session):
        """Test basic user creation"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            account_status="active"
        )
        db_session.add(user)
        db_session.commit()
        
        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.password_hash == "hashed_password"
        assert retrieved.account_status == "active"
    
    def test_user_has_id(self, db_session):
        """Test user has auto-generated UUID"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert isinstance(user.id, str)
    
    def test_user_email_unique(self, db_session):
        """Test email uniqueness constraint"""
        user1 = User(email="test@example.com", password_hash="hash1")
        user2 = User(email="test@example.com", password_hash="hash2")
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()
    
    def test_user_timestamps(self, db_session):
        """Test user creation and update timestamps"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_account_status_default(self, db_session):
        """Test default account status is active"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.account_status == "active"
    
    def test_user_account_status_values(self, db_session):
        """Test account status enum values"""
        statuses = [AccountStatus.ACTIVE, AccountStatus.SUSPENDED, AccountStatus.DELETED]
        
        for status in statuses:
            user = User(
                email=f"user_{status.value}@example.com",
                password_hash="hash",
                account_status=status
            )
            db_session.add(user)
        
        db_session.commit()
        assert db_session.query(User).count() == 3


class TestCryptographicKeyModel:
    """Test CryptographicKey model"""
    
    def test_key_creation(self, db_session):
        """Test basic key creation"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"public_key_bytes",
            status="active"
        )
        db_session.add(key)
        db_session.commit()
        
        retrieved = db_session.query(CryptographicKey).filter_by(
            key_id=key.key_id
        ).first()
        assert retrieved is not None
        assert retrieved.algorithm == "ml-kem-768"
        assert retrieved.key_type == "public"
    
    def test_key_version_default(self, db_session):
        """Test key version defaults to 1"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="x25519",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        assert key.version == 1
    
    def test_key_id_unique(self, db_session):
        """Test key_id uniqueness constraint"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key_id = f"key_{uuid4()}"
        key1 = CryptographicKey(
            user_id=user.id,
            algorithm="ed25519",
            key_type="public",
            key_id=key_id,
            public_key_material=b"key1_bytes"
        )
        db_session.add(key1)
        db_session.commit()
        
        key2 = CryptographicKey(
            user_id=user.id,
            algorithm="ed25519",
            key_type="public",
            key_id=key_id,
            public_key_material=b"key2_bytes"
        )
        db_session.add(key2)
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_key_status_values(self, db_session):
        """Test key status enum values"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        statuses = [KeyStatus.ACTIVE, KeyStatus.REVOKED, KeyStatus.SUPERSEDED]
        
        for i, status in enumerate(statuses):
            key = CryptographicKey(
                user_id=user.id,
                algorithm="ml-kem-768",
                key_type="public",
                key_id=f"key_{uuid4()}",
                public_key_material=b"key_bytes",
                status=status
            )
            db_session.add(key)
        
        db_session.commit()
        assert db_session.query(CryptographicKey).count() == 3
    
    def test_key_multiple_versions(self, db_session):
        """Test multiple key versions for a user"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key1 = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_v1_{uuid4()}",
            public_key_material=b"key_v1_bytes",
            version=1,
            status="active"
        )
        key2 = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_v2_{uuid4()}",
            public_key_material=b"key_v2_bytes",
            version=2,
            status="active"
        )
        db_session.add(key1)
        db_session.add(key2)
        db_session.commit()
        
        keys = db_session.query(CryptographicKey).filter_by(user_id=user.id).all()
        assert len(keys) == 2
        assert keys[0].version == 1
        assert keys[1].version == 2
    
    def test_key_private_key_material_optional(self, db_session):
        """Test private_key_material is optional (user-held or browser-held)"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        # Public key only (user-held private key)
        key = CryptographicKey(
            user_id=user.id,
            algorithm="x25519",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"public_bytes",
            private_key_material=None
        )
        db_session.add(key)
        db_session.commit()
        
        retrieved = db_session.query(CryptographicKey).filter_by(
            key_id=key.key_id
        ).first()
        assert retrieved.private_key_material is None


class TestFilePackageModel:
    """Test FilePackage model"""
    
    def test_package_creation(self, db_session):
        """Test basic file package creation"""
        user = User(email="sender@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=user.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"encapsulated_bytes",
            payload_storage_key="s3://bucket/file.enc",
            manifest_json='{"sender": "test", "recipients": []}',
            signature=b"signature_bytes",
            file_size=1024
        )
        db_session.add(package)
        db_session.commit()
        
        retrieved = db_session.query(FilePackage).filter_by(id=package.id).first()
        assert retrieved is not None
        assert retrieved.crypto_mode == "pqc"
        assert retrieved.file_size == 1024
    
    def test_package_crypto_modes(self, db_session):
        """Test both crypto modes: pqc and classical"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        for mode in ["pqc", "classical"]:
            package = FilePackage(
                sender_id=user.id,
                recipient_key_id=key.key_id,
                package_version="1.0",
                crypto_mode=mode,
                encapsulated_secret=b"secret",
                payload_storage_key=f"storage_{mode}",
                manifest_json='{}',
                signature=b"sig",
                file_size=100
            )
            db_session.add(package)
        
        db_session.commit()
        packages = db_session.query(FilePackage).all()
        assert len(packages) == 2
    
    def test_package_original_filename_optional(self, db_session):
        """Test original_filename is optional"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="x25519",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=user.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="classical",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=100,
            original_filename=None
        )
        db_session.add(package)
        db_session.commit()
        
        retrieved = db_session.query(FilePackage).filter_by(id=package.id).first()
        assert retrieved.original_filename is None


class TestFileChunkModel:
    """Test FileChunk model"""
    
    def test_chunk_creation(self, db_session):
        """Test basic file chunk creation"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=user.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=10000
        )
        db_session.add(package)
        db_session.commit()
        
        chunk = FileChunk(
            package_id=package.id,
            chunk_number=1,
            chunk_size=1024,
            storage_key="s3://bucket/chunk_1"
        )
        db_session.add(chunk)
        db_session.commit()
        
        retrieved = db_session.query(FileChunk).filter_by(
            package_id=package.id
        ).first()
        assert retrieved is not None
        assert retrieved.chunk_number == 1
        assert retrieved.chunk_size == 1024
    
    def test_multiple_chunks_per_package(self, db_session):
        """Test multiple chunks for a single package"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=user.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=50000
        )
        db_session.add(package)
        db_session.commit()
        
        for i in range(5):
            chunk = FileChunk(
                package_id=package.id,
                chunk_number=i + 1,
                chunk_size=10240,
                storage_key=f"s3://bucket/chunk_{i+1}"
            )
            db_session.add(chunk)
        
        db_session.commit()
        chunks = db_session.query(FileChunk).filter_by(package_id=package.id).all()
        assert len(chunks) == 5


class TestAccessGrantModel:
    """Test AccessGrant model"""
    
    def test_grant_creation(self, db_session):
        """Test basic access grant creation"""
        sender = User(email="sender@example.com", password_hash="hash")
        recipient = User(email="recipient@example.com", password_hash="hash")
        db_session.add(sender)
        db_session.add(recipient)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=sender.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=sender.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=1024
        )
        db_session.add(package)
        db_session.commit()
        
        grant = AccessGrant(
            package_id=package.id,
            recipient_id=recipient.id,
            status="active"
        )
        db_session.add(grant)
        db_session.commit()
        
        retrieved = db_session.query(AccessGrant).filter_by(id=grant.id).first()
        assert retrieved is not None
        assert retrieved.status == "active"
        assert retrieved.recipient_id == recipient.id
    
    def test_grant_status_values(self, db_session):
        """Test grant status enum values"""
        sender = User(email="sender@example.com", password_hash="hash")
        recipient = User(email="recipient@example.com", password_hash="hash")
        db_session.add(sender)
        db_session.add(recipient)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=sender.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=sender.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=1024
        )
        db_session.add(package)
        db_session.commit()
        
        for status in [GrantStatus.ACTIVE, GrantStatus.REVOKED]:
            grant = AccessGrant(
                package_id=package.id,
                recipient_id=recipient.id,
                status=status
            )
            db_session.add(grant)
        
        db_session.commit()
        grants = db_session.query(AccessGrant).all()
        assert len(grants) == 2
    
    def test_grant_revoked_at_timestamp(self, db_session):
        """Test revoked_at timestamp tracking"""
        sender = User(email="sender@example.com", password_hash="hash")
        recipient = User(email="recipient@example.com", password_hash="hash")
        db_session.add(sender)
        db_session.add(recipient)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=sender.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=sender.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=1024
        )
        db_session.add(package)
        db_session.commit()
        
        grant = AccessGrant(
            package_id=package.id,
            recipient_id=recipient.id,
            status="active",
            revoked_at=None
        )
        db_session.add(grant)
        db_session.commit()
        
        retrieved = db_session.query(AccessGrant).filter_by(id=grant.id).first()
        assert retrieved.revoked_at is None


class TestAuditLogModel:
    """Test AuditLog model"""
    
    def test_audit_log_creation(self, db_session):
        """Test basic audit log creation"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        log = AuditLog(
            event_type="user_login",
            user_id=user.id,
            action="authentication",
            status="success",
            details='{"ip": "192.168.1.1"}'
        )
        db_session.add(log)
        db_session.commit()
        
        retrieved = db_session.query(AuditLog).filter_by(
            event_type="user_login"
        ).first()
        assert retrieved is not None
        assert retrieved.action == "authentication"
        assert retrieved.status == "success"
    
    def test_audit_log_event_types(self, db_session):
        """Test all audit event types"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        event_types = [
            AuditEventType.USER_REGISTERED,
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGOUT,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.FILE_UPLOADED,
            AuditEventType.FILE_DOWNLOADED,
        ]
        
        for event_type in event_types:
            log = AuditLog(
                event_type=event_type,
                user_id=user.id,
                action="test",
                status="success"
            )
            db_session.add(log)
        
        db_session.commit()
        logs = db_session.query(AuditLog).all()
        assert len(logs) == len(event_types)
    
    def test_audit_log_resource_tracking(self, db_session):
        """Test resource tracking in audit logs"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        log = AuditLog(
            event_type="file_uploaded",
            user_id=user.id,
            resource_id="file_123",
            resource_type="FilePackage",
            action="upload",
            status="success",
            details='{"size": 1024}'
        )
        db_session.add(log)
        db_session.commit()
        
        retrieved = db_session.query(AuditLog).filter_by(
            resource_id="file_123"
        ).first()
        assert retrieved is not None
        assert retrieved.resource_type == "FilePackage"
    
    def test_audit_log_optional_fields(self, db_session):
        """Test optional fields in audit log"""
        log = AuditLog(
            event_type="access_denied",
            user_id=None,  # Optional
            resource_id=None,  # Optional
            resource_type=None,  # Optional
            action="access",
            status="failure",
            details=None,  # Optional
            ip_address=None,  # Optional
            user_agent=None  # Optional
        )
        db_session.add(log)
        db_session.commit()
        
        retrieved = db_session.query(AuditLog).filter_by(
            event_type="access_denied"
        ).first()
        assert retrieved.user_id is None
        assert retrieved.resource_id is None


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_user_to_keys_relationship(self, db_session):
        """Test User has multiple CryptographicKeys"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        for i in range(3):
            key = CryptographicKey(
                user_id=user.id,
                algorithm="ml-kem-768",
                key_type="public",
                key_id=f"key_{uuid4()}",
                public_key_material=b"key_bytes",
                version=i + 1
            )
            db_session.add(key)
        
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter_by(id=user.id).first()
        assert len(retrieved_user.keys) == 3
    
    def test_sender_to_packages_relationship(self, db_session):
        """Test User (as sender) has multiple FilePackages"""
        sender = User(email="sender@example.com", password_hash="hash")
        db_session.add(sender)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=sender.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        for i in range(2):
            package = FilePackage(
                sender_id=sender.id,
                recipient_key_id=key.key_id,
                package_version="1.0",
                crypto_mode="pqc",
                encapsulated_secret=b"secret",
                payload_storage_key=f"storage_{i}",
                manifest_json='{}',
                signature=b"sig",
                file_size=1024
            )
            db_session.add(package)
        
        db_session.commit()
        
        retrieved_sender = db_session.query(User).filter_by(id=sender.id).first()
        assert len(retrieved_sender.sent_packages) == 2
    
    def test_package_to_chunks_relationship(self, db_session):
        """Test FilePackage has multiple FileChunks"""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=user.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=user.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=10000
        )
        db_session.add(package)
        db_session.commit()
        
        for i in range(4):
            chunk = FileChunk(
                package_id=package.id,
                chunk_number=i + 1,
                chunk_size=2500,
                storage_key=f"s3://bucket/chunk_{i+1}"
            )
            db_session.add(chunk)
        
        db_session.commit()
        
        retrieved_package = db_session.query(FilePackage).filter_by(
            id=package.id
        ).first()
        assert len(retrieved_package.chunks) == 4
    
    def test_package_to_access_grants_relationship(self, db_session):
        """Test FilePackage has multiple AccessGrants"""
        sender = User(email="sender@example.com", password_hash="hash")
        recipients = [
            User(email="recipient1@example.com", password_hash="hash"),
            User(email="recipient2@example.com", password_hash="hash"),
        ]
        
        db_session.add(sender)
        for recipient in recipients:
            db_session.add(recipient)
        db_session.commit()
        
        key = CryptographicKey(
            user_id=sender.id,
            algorithm="ml-kem-768",
            key_type="public",
            key_id=f"key_{uuid4()}",
            public_key_material=b"key_bytes"
        )
        db_session.add(key)
        db_session.commit()
        
        package = FilePackage(
            sender_id=sender.id,
            recipient_key_id=key.key_id,
            package_version="1.0",
            crypto_mode="pqc",
            encapsulated_secret=b"secret",
            payload_storage_key="storage",
            manifest_json='{}',
            signature=b"sig",
            file_size=1024
        )
        db_session.add(package)
        db_session.commit()
        
        for recipient in recipients:
            grant = AccessGrant(
                package_id=package.id,
                recipient_id=recipient.id,
                status="active"
            )
            db_session.add(grant)
        
        db_session.commit()
        
        retrieved_package = db_session.query(FilePackage).filter_by(
            id=package.id
        ).first()
        assert len(retrieved_package.access_grants) == 2


class TestModelEnums:
    """Test enum values match requirements"""
    
    def test_account_status_enum(self):
        """Test AccountStatus enum has required values"""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.DELETED.value == "deleted"
    
    def test_key_status_enum(self):
        """Test KeyStatus enum has required values"""
        assert KeyStatus.ACTIVE.value == "active"
        assert KeyStatus.REVOKED.value == "revoked"
        assert KeyStatus.SUPERSEDED.value == "superseded"
    
    def test_key_type_enum(self):
        """Test KeyType enum has required values"""
        assert KeyType.PUBLIC.value == "public"
        assert KeyType.PRIVATE.value == "private"
    
    def test_grant_status_enum(self):
        """Test GrantStatus enum has required values"""
        assert GrantStatus.ACTIVE.value == "active"
        assert GrantStatus.REVOKED.value == "revoked"
    
    def test_audit_event_type_enum(self):
        """Test AuditEventType enum has required values"""
        required_events = [
            "user_registered", "user_login", "user_logout",
            "login_failed", "registration_failed", "permission_denied",
            "crypto_verification_failed", "file_uploaded", "file_downloaded",
            "file_shared", "share_revoked", "key_registered",
            "key_rotated", "key_revoked", "access_denied"
        ]
        
        for event in required_events:
            enum_attr = event.upper()
            assert hasattr(AuditEventType, enum_attr)
