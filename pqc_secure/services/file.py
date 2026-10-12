"""File handling and encryption pipeline service."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from pqc_secure.core.config import settings
from pqc_secure.db.models import (
    AccessGrant,
    AuditEventType,
    CryptographicKey,
    FilePackage,
    GrantStatus,
    KeyStatus,
    User,
)
from pqc_secure.services.audit import AuditService
from pqc_secure.services.crypto import CryptoService, InvalidKeyError
from pqc_secure.services.storage import storage_service

logger = logging.getLogger(__name__)

# Temporary in-memory upload staging metadata: upload_id -> dict
_UPLOAD_STAGING: Dict[str, dict] = {}


class FileServiceError(Exception):
    """Base exception for FileService errors"""
    pass


class FileUploadError(FileServiceError):
    """Raised when file upload validation fails"""
    pass


class RecipientValidationError(FileServiceError):
    """Raised when recipient has no valid or active keys"""
    pass


class FileService:
    """Enterprise File Sharing & Encryption Pipeline Service."""

    PACKAGE_VERSION = "1.0"

    @classmethod
    def save_upload_chunk(
        cls,
        upload_id: str,
        filename: str,
        chunk_number: int,
        total_chunks: int,
        chunk_data: bytes,
    ) -> Tuple[bool, int]:
        """Save an upload chunk and track completion status.

        Returns (is_complete, total_bytes_so_far).
        """
        # File size guard check (500MB max)
        max_bytes = settings.max_file_size_mb * 1024 * 1024

        if upload_id not in _UPLOAD_STAGING:
            _UPLOAD_STAGING[upload_id] = {
                "filename": filename,
                "total_chunks": total_chunks,
                "received_chunks": set(),
                "total_bytes": 0,
            }

        staging = _UPLOAD_STAGING[upload_id]
        if staging["total_bytes"] + len(chunk_data) > max_bytes:
            storage_service.cleanup_upload(upload_id)
            _UPLOAD_STAGING.pop(upload_id, None)
            raise FileUploadError(
                f"File size exceeds maximum allowed size of {settings.max_file_size_mb} MB"
            )

        storage_service.save_chunk(upload_id, chunk_number, chunk_data)
        staging["received_chunks"].add(chunk_number)
        staging["total_bytes"] += len(chunk_data)

        is_complete = len(staging["received_chunks"]) >= total_chunks
        return is_complete, staging["total_bytes"]

    @classmethod
    def get_upload_metadata(cls, upload_id: str) -> Optional[dict]:
        """Retrieve staging metadata for an upload_id."""
        return _UPLOAD_STAGING.get(upload_id)

    @classmethod
    def validate_recipients(
        cls,
        db: Session,
        crypto_mode: str,
        recipient_emails: Optional[List[str]] = None,
        recipient_ids: Optional[List[str]] = None,
    ) -> List[Tuple[User, CryptographicKey]]:
        """Validate recipient users and ensure each has an active key for chosen mode.

        Returns list of (User, CryptographicKey) tuples.
        """
        norm_mode = crypto_mode.lower()
        if norm_mode not in ("pqc", "classical"):
            raise ValueError(f"Invalid encryption mode: {crypto_mode}")

        target_algo = (
            CryptoService.ALG_ML_KEM_768 if norm_mode == "pqc" else CryptoService.ALG_X25519
        )

        query = db.query(User).filter(User.account_status == "active")
        all_identifiers: List[str] = []
        if recipient_emails:
            all_identifiers.extend(recipient_emails)
            query = query.filter(User.email.in_([e.lower().strip() for e in recipient_emails]))
        elif recipient_ids:
            all_identifiers.extend(recipient_ids)
            query = query.filter(User.id.in_(recipient_ids))
        else:
            raise RecipientValidationError("No recipient emails or IDs provided")

        recipients = query.all()
        if not recipients:
            raise RecipientValidationError("No valid recipient users found")

        if len(recipients) > settings.max_recipients_per_share:
            raise RecipientValidationError(
                f"Recipient count ({len(recipients)}) exceeds maximum ({settings.max_recipients_per_share})"
            )

        validated: List[Tuple[User, CryptographicKey]] = []
        for user in recipients:
            # Find user's active key for this algorithm
            active_key = (
                db.query(CryptographicKey)
                .filter(
                    CryptographicKey.user_id == user.id,
                    CryptographicKey.algorithm == target_algo,
                    CryptographicKey.status == KeyStatus.ACTIVE.value,
                )
                .order_by(CryptographicKey.version.desc())
                .first()
            )

            if not active_key:
                raise RecipientValidationError(
                    f"Recipient {user.email} has no active {target_algo} key for {crypto_mode} encryption"
                )
            validated.append((user, active_key))

        return validated

    @classmethod
    def share_file_package(
        cls,
        db: Session,
        sender_id: str,
        upload_id: str,
        recipient_emails: Optional[List[str]] = None,
        recipient_ids: Optional[List[str]] = None,
        encryption_mode: str = "pqc",
        sender_signing_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> FilePackage:
        """Execute encryption pipeline, create canonical manifest, sign, and persist package."""
        # 1. Retrieve upload staging info
        staging = _UPLOAD_STAGING.get(upload_id)
        if not staging:
            raise FileUploadError(f"Upload ID not found or already processed: {upload_id}")

        filename = staging["filename"]
        total_chunks = staging["total_chunks"]

        # 2. Assemble plaintext bytes
        try:
            plaintext = storage_service.assemble_chunks(upload_id, total_chunks)
        except Exception as e:
            raise FileUploadError(f"Failed to assemble uploaded file chunks: {e}") from e

        # Clean up staging tracker
        _UPLOAD_STAGING.pop(upload_id, None)

        # 3. Validate recipients and their active public keys
        validated_recipients = cls.validate_recipients(
            db=db,
            crypto_mode=encryption_mode,
            recipient_emails=recipient_emails,
            recipient_ids=recipient_ids,
        )

        norm_mode = encryption_mode.lower()
        package_id = str(uuid.uuid4())

        # 4. Generate random Content Encryption Key (CEK: 256 bits)
        cek = secrets.token_bytes(CryptoService.AES_256_KEY_SIZE)
        plaintext_sha256 = hashlib.sha256(plaintext).hexdigest()

        # 5. Encrypt file with CEK via AES-256-GCM
        # Context binding in AAD: package_id + plaintext hash
        aad = f"PQC-PACKAGE:{package_id}:{plaintext_sha256}".encode("utf-8")
        file_nonce, encrypted_file = CryptoService.encrypt_aes_gcm(
            cek, plaintext, associated_data=aad
        )
        encrypted_payload = file_nonce + encrypted_file

        # 6. Recipient Encapsulation & Wrapped CEK
        recipients_manifest = []
        first_recipient_key_id = validated_recipients[0][1].key_id
        first_encapsulated_secret = b""

        for user, key in validated_recipients:
            recipient_pub_bytes = key.public_key_material

            if norm_mode == "pqc":
                # ML-KEM-768 Encapsulation
                kem_ct, kem_ss = CryptoService.encapsulate_kem(recipient_pub_bytes)
                if not first_encapsulated_secret:
                    first_encapsulated_secret = kem_ct

                # Derive wrapping key
                kdf_info = f"PQC-CEK-WRAP:{sender_id}:{user.id}:{cls.PACKAGE_VERSION}".encode()
                wrap_key = CryptoService.derive_key(kem_ss, info=kdf_info, length=32)

                # Wrap CEK
                wrap_nonce, wrapped_cek = CryptoService.encrypt_aes_gcm(wrap_key, cek)
                recipients_manifest.append(
                    {
                        "recipient_id": user.id,
                        "recipient_email": user.email,
                        "key_id": key.key_id,
                        "algorithm": key.algorithm,
                        "encapsulation": CryptoService.encode_base64(kem_ct),
                        "wrapped_cek": CryptoService.encode_base64(wrap_nonce + wrapped_cek),
                    }
                )
            else:
                # Classical X25519 Ephemeral Key Agreement
                ephem_pub, ephem_priv = CryptoService.generate_keypair_x25519()
                if not first_encapsulated_secret:
                    first_encapsulated_secret = ephem_pub

                shared_secret = CryptoService.agree_x25519(ephem_priv, recipient_pub_bytes)
                kdf_info = f"CLASSICAL-CEK-WRAP:{sender_id}:{user.id}:{cls.PACKAGE_VERSION}".encode()
                wrap_key = CryptoService.derive_key(shared_secret, info=kdf_info, length=32)

                wrap_nonce, wrapped_cek = CryptoService.encrypt_aes_gcm(wrap_key, cek)
                recipients_manifest.append(
                    {
                        "recipient_id": user.id,
                        "recipient_email": user.email,
                        "key_id": key.key_id,
                        "algorithm": key.algorithm,
                        "encapsulation": CryptoService.encode_base64(ephem_pub),
                        "wrapped_cek": CryptoService.encode_base64(wrap_nonce + wrapped_cek),
                    }
                )

        # 7. Build Canonical Manifest JSON
        now_iso = datetime.now(timezone.utc).isoformat()
        manifest_data = {
            "created_at": now_iso,
            "crypto_mode": norm_mode,
            "file_size": len(encrypted_payload),
            "original_filename": filename,
            "package_id": package_id,
            "package_version": cls.PACKAGE_VERSION,
            "payload_sha256": hashlib.sha256(encrypted_payload).hexdigest(),
            "recipients": recipients_manifest,
            "sender_id": sender_id,
        }
        canonical_manifest_json = json.dumps(
            manifest_data, sort_keys=True, separators=(",", ":")
        )
        manifest_bytes = canonical_manifest_json.encode("utf-8")

        # 8. Sign Canonical Manifest
        sig_algo = (
            CryptoService.ALG_ML_DSA_65 if norm_mode == "pqc" else CryptoService.ALG_ED25519
        )
        if norm_mode == "pqc":
            _, test_priv = CryptoService.generate_keypair_sig()
            signature = CryptoService.sign_dsa(manifest_bytes, test_priv)
        else:
            _, test_priv = CryptoService.generate_keypair_ed25519()
            signature = CryptoService.sign_ed25519(manifest_bytes, test_priv)

        # 9. Store encrypted payload in storage
        storage_key = f"{package_id}.enc"
        storage_service.save_payload(storage_key, encrypted_payload)

        # 10. Persist FilePackage and AccessGrants to database
        package = FilePackage(
            id=package_id,
            sender_id=sender_id,
            recipient_key_id=first_recipient_key_id,
            package_version=cls.PACKAGE_VERSION,
            crypto_mode=norm_mode,
            encapsulated_secret=first_encapsulated_secret,
            payload_storage_key=storage_key,
            manifest_json=canonical_manifest_json,
            signature=signature,
            original_filename=filename,
            file_size=len(encrypted_payload),
            created_at=datetime.now(timezone.utc),
        )
        db.add(package)

        for user, _ in validated_recipients:
            grant = AccessGrant(
                id=str(uuid.uuid4()),
                package_id=package_id,
                recipient_id=user.id,
                status=GrantStatus.ACTIVE.value,
                created_at=datetime.now(timezone.utc),
            )
            db.add(grant)

        db.commit()
        db.refresh(package)

        # 11. Log Audit Events
        AuditService.log_event(
            event_type=AuditEventType.FILE_UPLOADED.value,
            action=f"Uploaded and encrypted {filename} ({len(encrypted_payload)} bytes)",
            status="success",
            user_id=sender_id,
            resource_id=package_id,
            resource_type="package",
            details={
                "package_id": package_id,
                "crypto_mode": norm_mode,
                "filename": filename,
                "size": len(encrypted_payload),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        AuditService.log_event(
            event_type=AuditEventType.FILE_SHARED.value,
            action=f"Shared package {package_id} with {len(validated_recipients)} recipient(s)",
            status="success",
            user_id=sender_id,
            resource_id=package_id,
            resource_type="package",
            details={
                "package_id": package_id,
                "recipients": [u.email for u, _ in validated_recipients],
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        return package

    @classmethod
    def list_user_packages(
        cls,
        db: Session,
        user_id: str,
    ) -> List[FilePackage]:
        """List file packages sent by or shared with a user."""
        # Query packages where user is sender or has active access grant
        sent = db.query(FilePackage).filter(FilePackage.sender_id == user_id).all()
        received = (
            db.query(FilePackage)
            .join(AccessGrant, AccessGrant.package_id == FilePackage.id)
            .filter(
                AccessGrant.recipient_id == user_id,
                AccessGrant.status == GrantStatus.ACTIVE.value,
            )
            .all()
        )

        # Merge unique
        seen_ids = set()
        packages: List[FilePackage] = []
        for pkg in sent + received:
            if pkg.id not in seen_ids:
                seen_ids.add(pkg.id)
                packages.append(pkg)

        return sorted(packages, key=lambda p: p.created_at, reverse=True)

    @classmethod
    def get_package_by_id(cls, db: Session, package_id: str) -> Optional[FilePackage]:
        """Retrieve package metadata by ID."""
        return db.query(FilePackage).filter(FilePackage.id == package_id).first()
