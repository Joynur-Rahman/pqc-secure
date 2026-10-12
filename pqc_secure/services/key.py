"""Key management service for key lifecycle, registration, rotation, and revocation."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from pqc_secure.db.models import AuditEventType, CryptographicKey, KeyStatus, User
from pqc_secure.services.audit import AuditService
from pqc_secure.services.crypto import CryptoService, InvalidKeyError

logger = logging.getLogger(__name__)


class KeyServiceError(Exception):
    """Base exception for KeyService errors"""
    pass


class KeyNotFoundError(KeyServiceError):
    """Raised when key is not found"""
    pass


class KeyPermissionError(KeyServiceError):
    """Raised when unauthorized operation on a key is attempted"""
    pass


class KeyService:
    """Enterprise Key Management Service handling lifecycle operations."""

    @classmethod
    def register_key(
        cls,
        db: Session,
        user_id: str,
        algorithm: str,
        public_key_b64: str,
        key_type: str = "public",
        private_key_b64: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CryptographicKey:
        """Register a user's public key with algorithm and version metadata."""
        # 1. Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise KeyServiceError(f"User {user_id} not found")

        # 2. Validate and normalize algorithm
        if not CryptoService.is_valid_algorithm(algorithm):
            raise InvalidKeyError(f"Unsupported algorithm: {algorithm}")
        norm_algorithm = CryptoService.normalize_algorithm(algorithm)

        # 3. Decode base64 public key material
        try:
            public_key_bytes = CryptoService.decode_base64(public_key_b64)
        except Exception as e:
            raise InvalidKeyError(f"Invalid public key base64 data: {e}") from e

        # 4. Validate public key format and length
        if not CryptoService.validate_public_key(norm_algorithm, public_key_bytes):
            raise InvalidKeyError(
                f"Public key bytes format or size invalid for algorithm {norm_algorithm}"
            )

        # 5. Compute canonical key ID
        canonical_key_id = CryptoService.generate_key_id(norm_algorithm, public_key_bytes)

        # 6. Check for duplicate key_id
        existing_key = (
            db.query(CryptographicKey)
            .filter(CryptographicKey.key_id == canonical_key_id)
            .first()
        )
        if existing_key:
            if existing_key.user_id == user_id:
                logger.info("Key %s already registered by user %s", canonical_key_id, user_id)
                return existing_key
            raise InvalidKeyError("Key is already registered to another user")

        # 7. Determine version for this user and algorithm
        max_version = (
            db.query(func.max(CryptographicKey.version))
            .filter(
                CryptographicKey.user_id == user_id,
                CryptographicKey.algorithm == norm_algorithm,
            )
            .scalar()
        )
        next_version = (max_version or 0) + 1

        private_key_bytes = None
        if private_key_b64:
            try:
                private_key_bytes = CryptoService.decode_base64(private_key_b64)
            except Exception:
                pass

        # 8. Create and persist key record
        new_key = CryptographicKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            algorithm=norm_algorithm,
            key_type=key_type,
            version=next_version,
            key_id=canonical_key_id,
            public_key_material=public_key_bytes,
            private_key_material=private_key_bytes,
            status=KeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        # 9. Audit event
        AuditService.log_event(
            event_type=AuditEventType.KEY_REGISTERED.value,
            action=f"Registered {norm_algorithm} key version {next_version}",
            status="success",
            user_id=user_id,
            resource_id=canonical_key_id,
            resource_type="key",
            details={
                "algorithm": norm_algorithm,
                "version": next_version,
                "key_id": canonical_key_id,
                "key_type": key_type,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        return new_key

    @classmethod
    def list_user_keys(
        cls,
        db: Session,
        user_id: str,
        include_inactive: bool = True,
    ) -> List[CryptographicKey]:
        """List keys owned by a specific user."""
        query = db.query(CryptographicKey).filter(CryptographicKey.user_id == user_id)
        if not include_inactive:
            query = query.filter(CryptographicKey.status == KeyStatus.ACTIVE.value)
        return query.order_by(desc(CryptographicKey.created_at)).all()

    @classmethod
    def get_key_by_id(cls, db: Session, key_id: str) -> Optional[CryptographicKey]:
        """Retrieve key metadata and material by canonical key ID."""
        return (
            db.query(CryptographicKey)
            .filter(CryptographicKey.key_id == key_id)
            .first()
        )

    @classmethod
    def get_user_public_keys(
        cls,
        db: Session,
        user_id: str,
        algorithm: Optional[str] = None,
    ) -> List[CryptographicKey]:
        """Discover active public keys for a specific user (e.g. for sharing files)."""
        query = db.query(CryptographicKey).filter(
            CryptographicKey.user_id == user_id,
            CryptographicKey.status == KeyStatus.ACTIVE.value,
        )
        if algorithm:
            norm_algorithm = CryptoService.normalize_algorithm(algorithm)
            query = query.filter(CryptographicKey.algorithm == norm_algorithm)
        return query.order_by(desc(CryptographicKey.version)).all()

    @classmethod
    def rotate_key(
        cls,
        db: Session,
        user_id: str,
        key_id: str,
        new_public_key_b64: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CryptographicKey:
        """Rotate a key to a new version, marking the previous version as superseded."""
        current_key = cls.get_key_by_id(db, key_id)
        if not current_key:
            raise KeyNotFoundError(f"Key {key_id} not found")

        if current_key.user_id != user_id:
            raise KeyPermissionError("Not authorized to rotate this key")

        if current_key.status == KeyStatus.REVOKED.value:
            raise KeyServiceError("Cannot rotate a revoked key")

        algorithm = current_key.algorithm

        # Determine new public key bytes
        if new_public_key_b64:
            new_pub_bytes = CryptoService.decode_base64(new_public_key_b64)
            if not CryptoService.validate_public_key(algorithm, new_pub_bytes):
                raise InvalidKeyError(
                    f"New public key invalid for algorithm {algorithm}"
                )
        else:
            # Generate new key pair on server
            if algorithm == CryptoService.ALG_ML_KEM_768:
                new_pub_bytes, _ = CryptoService.generate_keypair_kem()
            elif algorithm == CryptoService.ALG_ML_DSA_65:
                new_pub_bytes, _ = CryptoService.generate_keypair_sig()
            elif algorithm == CryptoService.ALG_X25519:
                new_pub_bytes, _ = CryptoService.generate_keypair_x25519()
            elif algorithm == CryptoService.ALG_ED25519:
                new_pub_bytes, _ = CryptoService.generate_keypair_ed25519()
            else:
                raise InvalidKeyError(f"Cannot auto-generate key for {algorithm}")

        new_key_id = CryptoService.generate_key_id(algorithm, new_pub_bytes)

        # Mark current key as superseded
        current_key.status = KeyStatus.SUPERSEDED.value

        # Create new version
        new_version = current_key.version + 1
        new_key = CryptographicKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            algorithm=algorithm,
            key_type=current_key.key_type,
            version=new_version,
            key_id=new_key_id,
            public_key_material=new_pub_bytes,
            status=KeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        # Audit event
        AuditService.log_event(
            event_type=AuditEventType.KEY_ROTATED.value,
            action=f"Rotated key {key_id} to {new_key_id} version {new_version}",
            status="success",
            user_id=user_id,
            resource_id=new_key_id,
            resource_type="key",
            details={
                "previous_key_id": key_id,
                "new_key_id": new_key_id,
                "algorithm": algorithm,
                "new_version": new_version,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        return new_key

    @classmethod
    def revoke_key(
        cls,
        db: Session,
        user_id: str,
        key_id: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CryptographicKey:
        """Mark a key as revoked, preventing its selection for future file shares."""
        key = cls.get_key_by_id(db, key_id)
        if not key:
            raise KeyNotFoundError(f"Key {key_id} not found")

        if key.user_id != user_id:
            raise KeyPermissionError("Not authorized to revoke this key")

        if key.status != KeyStatus.REVOKED.value:
            key.status = KeyStatus.REVOKED.value
            db.commit()
            db.refresh(key)

            AuditService.log_event(
                event_type=AuditEventType.KEY_REVOKED.value,
                action=f"Revoked key {key_id}",
                status="success",
                user_id=user_id,
                resource_id=key_id,
                resource_type="key",
                details={
                    "key_id": key_id,
                    "algorithm": key.algorithm,
                    "version": key.version,
                    "reason": reason or "User requested revocation",
                },
                ip_address=ip_address,
                user_agent=user_agent,
                db_session=db,
            )

        return key
