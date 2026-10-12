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


class PackageNotFoundError(FileServiceError):
    """Raised when package is not found"""
    pass


class AccessDeniedError(FileServiceError):
    """Raised when user has no active permission to access or download the file"""
    pass


class SignatureVerificationError(FileServiceError):
    """Raised when sender signature on manifest fails verification"""
    pass


class DecryptionFailedError(FileServiceError):
    """Raised when decryption or integrity verification fails"""
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
        # Context binding in AAD: package_id
        aad = f"PQC-PACKAGE:{package_id}".encode("utf-8")
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

        # 8. Sign Canonical Manifest
        sender_signing_key = None
        if sender_signing_key_id:
            sender_signing_key = (
                db.query(CryptographicKey)
                .filter(
                    CryptographicKey.key_id == sender_signing_key_id,
                    CryptographicKey.user_id == sender_id,
                    CryptographicKey.status == KeyStatus.ACTIVE.value,
                )
                .first()
            )
        if not sender_signing_key:
            target_sig_algo = (
                CryptoService.ALG_ML_DSA_65 if norm_mode == "pqc" else CryptoService.ALG_ED25519
            )
            sender_signing_key = (
                db.query(CryptographicKey)
                .filter(
                    CryptographicKey.user_id == sender_id,
                    CryptographicKey.algorithm == target_sig_algo,
                    CryptographicKey.status == KeyStatus.ACTIVE.value,
                )
                .order_by(CryptographicKey.version.desc())
                .first()
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
            "sender_signing_key_id": sender_signing_key.key_id if sender_signing_key else None,
        }
        canonical_manifest_json = json.dumps(
            manifest_data, sort_keys=True, separators=(",", ":")
        )
        manifest_bytes = canonical_manifest_json.encode("utf-8")

        # Sign manifest
        if sender_signing_key and sender_signing_key.private_key_material:
            if norm_mode == "pqc":
                signature = CryptoService.sign_dsa(manifest_bytes, sender_signing_key.private_key_material)
            else:
                signature = CryptoService.sign_ed25519(manifest_bytes, sender_signing_key.private_key_material)
        else:
            if norm_mode == "pqc":
                test_pub, test_priv = CryptoService.generate_keypair_sig()
                signature = CryptoService.sign_dsa(manifest_bytes, test_priv)
                # Store test signing key for verification if sender doesn't have one registered
                if not sender_signing_key:
                    test_key_id = CryptoService.generate_key_id(CryptoService.ALG_ML_DSA_65, test_pub)
                    sender_signing_key = CryptographicKey(
                        id=str(uuid.uuid4()),
                        user_id=sender_id,
                        algorithm=CryptoService.ALG_ML_DSA_65,
                        key_type="public",
                        version=1,
                        key_id=test_key_id,
                        public_key_material=test_pub,
                        private_key_material=test_priv,
                        status=KeyStatus.ACTIVE.value,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(sender_signing_key)
                    db.flush()
                    manifest_data["sender_signing_key_id"] = test_key_id
                    canonical_manifest_json = json.dumps(
                        manifest_data, sort_keys=True, separators=(",", ":")
                    )
                    manifest_bytes = canonical_manifest_json.encode("utf-8")
                    signature = CryptoService.sign_dsa(manifest_bytes, test_priv)
            else:
                test_pub, test_priv = CryptoService.generate_keypair_ed25519()
                signature = CryptoService.sign_ed25519(manifest_bytes, test_priv)
                if not sender_signing_key:
                    test_key_id = CryptoService.generate_key_id(CryptoService.ALG_ED25519, test_pub)
                    sender_signing_key = CryptographicKey(
                        id=str(uuid.uuid4()),
                        user_id=sender_id,
                        algorithm=CryptoService.ALG_ED25519,
                        key_type="public",
                        version=1,
                        key_id=test_key_id,
                        public_key_material=test_pub,
                        private_key_material=test_priv,
                        status=KeyStatus.ACTIVE.value,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(sender_signing_key)
                    db.flush()
                    manifest_data["sender_signing_key_id"] = test_key_id
                    canonical_manifest_json = json.dumps(
                        manifest_data, sort_keys=True, separators=(",", ":")
                    )
                    manifest_bytes = canonical_manifest_json.encode("utf-8")
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

    @classmethod
    def verify_manifest_signature(
        cls,
        db: Session,
        package: FilePackage,
    ) -> bool:
        """Verify sender's digital signature over the package canonical manifest.

        Supports ML-DSA-65 (PQC) and Ed25519 (classical).
        """
        manifest_bytes = package.manifest_json.encode("utf-8")
        signature = package.signature

        try:
            manifest_data = json.loads(package.manifest_json)
        except Exception:
            return False

        sender_signing_key_id = manifest_data.get("sender_signing_key_id")
        signing_key = None

        if sender_signing_key_id:
            signing_key = (
                db.query(CryptographicKey)
                .filter(
                    CryptographicKey.key_id == sender_signing_key_id,
                    CryptographicKey.user_id == package.sender_id,
                )
                .first()
            )

        if not signing_key:
            # Fallback to sender's active key for this crypto mode
            target_algo = (
                CryptoService.ALG_ML_DSA_65
                if package.crypto_mode.lower() == "pqc"
                else CryptoService.ALG_ED25519
            )
            signing_key = (
                db.query(CryptographicKey)
                .filter(
                    CryptographicKey.user_id == package.sender_id,
                    CryptographicKey.algorithm == target_algo,
                )
                .order_by(CryptographicKey.version.desc())
                .first()
            )

        if not signing_key:
            logger.warning(
                "Could not find sender signing key for package %s sender %s",
                package.id,
                package.sender_id,
            )
            return False

        sender_pub_bytes = signing_key.public_key_material

        if package.crypto_mode.lower() == "pqc":
            return CryptoService.verify_dsa(manifest_bytes, signature, sender_pub_bytes)
        else:
            return CryptoService.verify_ed25519(manifest_bytes, signature, sender_pub_bytes)

    @classmethod
    def decrypt_file_package(
        cls,
        db: Session,
        package_id: str,
        user_id: str,
        private_key_bytes: Optional[bytes] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, bytes]:
        """Decrypt file package for an authorized sender or recipient.

        Performs:
        1. Package existence and access grant verification.
        2. Manifest signature verification (ML-DSA / Ed25519).
        3. Recipient encapsulation lookup.
        4. Key decapsulation (ML-KEM-768) or key agreement (X25519).
        5. CEK unwrapping via HKDF-derived wrap key + AES-256-GCM.
        6. Payload retrieval and AES-256-GCM file decryption with AAD check.
        7. Audit event logging.

        Returns (original_filename, plaintext_bytes).
        """
        # 1. Fetch package
        package = cls.get_package_by_id(db, package_id)
        if not package:
            raise PackageNotFoundError(f"Package {package_id} not found")

        # 2. Authorization check
        is_sender = (package.sender_id == user_id)
        active_grant = None

        if not is_sender:
            active_grant = (
                db.query(AccessGrant)
                .filter(
                    AccessGrant.package_id == package_id,
                    AccessGrant.recipient_id == user_id,
                    AccessGrant.status == GrantStatus.ACTIVE.value,
                )
                .first()
            )
            if not active_grant:
                raise AccessDeniedError(
                    f"Access denied: No active grant for user {user_id} on package {package_id}"
                )

        # 3. Signature verification
        sig_valid = cls.verify_manifest_signature(db, package)
        if not sig_valid:
            AuditService.log_event(
                event_type=AuditEventType.FILE_DOWNLOADED.value,
                action=f"Download rejected: invalid signature on package {package_id}",
                status="failure",
                user_id=user_id,
                resource_id=package_id,
                resource_type="package",
                ip_address=ip_address,
                user_agent=user_agent,
                db_session=db,
            )
            raise SignatureVerificationError("Package manifest signature verification failed")

        # 4. Parse manifest and locate recipient record
        try:
            manifest_data = json.loads(package.manifest_json)
        except Exception as e:
            raise DecryptionFailedError(f"Corrupted package manifest JSON: {e}") from e

        recipients_list = manifest_data.get("recipients", [])
        if not recipients_list:
            raise DecryptionFailedError("Package manifest contains no recipient encapsulation records")

        # Find matching recipient record
        target_record = None
        target_user_id = user_id

        if is_sender:
            # If sender is downloading, decrypt using the first recipient record
            target_record = recipients_list[0]
            target_user_id = target_record["recipient_id"]
        else:
            for r in recipients_list:
                if r.get("recipient_id") == user_id:
                    target_record = r
                    break

        if not target_record:
            raise AccessDeniedError(f"No encapsulation record found for user {user_id} in package manifest")

        # 5. Acquire private key
        key_id = target_record["key_id"]
        recipient_priv = private_key_bytes

        if not recipient_priv:
            key_record = (
                db.query(CryptographicKey)
                .filter(CryptographicKey.key_id == key_id)
                .first()
            )
            if key_record and key_record.private_key_material:
                recipient_priv = key_record.private_key_material

        if not recipient_priv:
            raise DecryptionFailedError(
                f"Recipient private key material for key_id {key_id} is missing or requires client-held key"
            )

        # 6. Decapsulate shared secret & derive wrap key
        encapsulation_bytes = CryptoService.decode_base64(target_record["encapsulation"])
        wrapped_cek_payload = CryptoService.decode_base64(target_record["wrapped_cek"])

        crypto_mode = package.crypto_mode.lower()
        if crypto_mode == "pqc":
            kem_ss = CryptoService.decapsulate_kem(encapsulation_bytes, recipient_priv)
            kdf_info = f"PQC-CEK-WRAP:{package.sender_id}:{target_user_id}:{cls.PACKAGE_VERSION}".encode()
            wrap_key = CryptoService.derive_key(kem_ss, info=kdf_info, length=32)
        else:
            shared_secret = CryptoService.agree_x25519(recipient_priv, encapsulation_bytes)
            kdf_info = f"CLASSICAL-CEK-WRAP:{package.sender_id}:{target_user_id}:{cls.PACKAGE_VERSION}".encode()
            wrap_key = CryptoService.derive_key(shared_secret, info=kdf_info, length=32)

        # 7. Decrypt CEK
        if len(wrapped_cek_payload) < CryptoService.AES_GCM_NONCE_SIZE + CryptoService.AES_GCM_TAG_SIZE:
            raise DecryptionFailedError("Wrapped CEK payload is truncated or malformed")

        wrap_nonce = wrapped_cek_payload[:CryptoService.AES_GCM_NONCE_SIZE]
        wrapped_cek_ct = wrapped_cek_payload[CryptoService.AES_GCM_NONCE_SIZE:]

        try:
            cek = CryptoService.decrypt_aes_gcm(wrap_key, wrap_nonce, wrapped_cek_ct)
        except Exception as e:
            raise DecryptionFailedError(f"Failed to unwrap content encryption key: {e}") from e

        # 8. Load encrypted payload from storage
        try:
            encrypted_payload = storage_service.read_payload(package.payload_storage_key)
        except Exception as e:
            raise DecryptionFailedError(f"Payload storage key {package.payload_storage_key} not found: {e}") from e

        # 9. Decrypt payload using AES-256-GCM with context AAD
        if len(encrypted_payload) < CryptoService.AES_GCM_NONCE_SIZE + CryptoService.AES_GCM_TAG_SIZE:
            raise DecryptionFailedError("Encrypted payload is truncated or invalid")

        file_nonce = encrypted_payload[:CryptoService.AES_GCM_NONCE_SIZE]
        file_ct = encrypted_payload[CryptoService.AES_GCM_NONCE_SIZE:]

        aad = f"PQC-PACKAGE:{package.id}".encode("utf-8")
        try:
            plaintext = CryptoService.decrypt_aes_gcm(cek, file_nonce, file_ct, associated_data=aad)
        except Exception as e:
            raise DecryptionFailedError(f"File payload authentication or decryption failed: {e}") from e

        # 10. Audit event logging
        AuditService.log_event(
            event_type=AuditEventType.FILE_DOWNLOADED.value,
            action=f"Downloaded and decrypted package {package_id} ({len(plaintext)} bytes)",
            status="success",
            user_id=user_id,
            resource_id=package_id,
            resource_type="package",
            details={
                "package_id": package_id,
                "crypto_mode": package.crypto_mode,
                "filename": package.original_filename,
                "size": len(plaintext),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        filename = package.original_filename or f"download_{package_id}"
        return filename, plaintext

