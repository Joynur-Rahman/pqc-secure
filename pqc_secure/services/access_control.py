"""Access control and share revocation service for PQC-Secure."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from pqc_secure.db.models import (
    AccessGrant,
    AuditEventType,
    FilePackage,
    GrantStatus,
    User,
)
from pqc_secure.services.audit import AuditService

logger = logging.getLogger(__name__)


class AccessControlError(Exception):
    """Base exception for access control errors."""
    pass


class PackageNotFoundError(AccessControlError):
    """Raised when the specified file package does not exist."""
    pass


class GrantNotFoundError(AccessControlError):
    """Raised when the access grant does not exist."""
    pass


class UnauthorizedRevocationError(AccessControlError):
    """Raised when a non-sender user attempts to revoke an access grant."""
    pass


class AccessDeniedError(AccessControlError):
    """Raised when a user lacks permission to access a file package."""
    pass


class AccessControlService:
    """Enterprise Access Control Service enforcing fine-grained package authorization and revocation."""

    @classmethod
    def check_package_access(
        cls,
        db: Session,
        user_id: str,
        package_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[AccessGrant], Optional[FilePackage]]:
        """
        Verify whether user has authorized access to a file package.
        Returns (is_authorized, reason, access_grant, package).
        """
        package = db.query(FilePackage).filter(FilePackage.id == package_id).first()
        if not package:
            return False, f"Package {package_id} not found", None, None

        # Sender always has access
        if package.sender_id == user_id:
            return True, "Authorized as sender", None, package

        # Recipient access check
        grant = (
            db.query(AccessGrant)
            .filter(
                AccessGrant.package_id == package_id,
                AccessGrant.recipient_id == user_id,
            )
            .first()
        )

        if not grant:
            AuditService.log_event(
                event_type=AuditEventType.ACCESS_DENIED.value,
                action=f"Access denied: No grant found for user {user_id} on package {package_id}",
                status="failure",
                user_id=user_id,
                resource_id=package_id,
                resource_type="package",
                details={"package_id": package_id, "user_id": user_id, "reason": "no_grant"},
                ip_address=ip_address,
                user_agent=user_agent,
                db_session=db,
            )
            return False, "Not authorized to access this file package", None, package

        if grant.status == GrantStatus.REVOKED.value:
            AuditService.log_event(
                event_type=AuditEventType.ACCESS_DENIED.value,
                action=f"Access denied: Grant {grant.id} for user {user_id} on package {package_id} is revoked",
                status="failure",
                user_id=user_id,
                resource_id=package_id,
                resource_type="package",
                details={"package_id": package_id, "grant_id": grant.id, "reason": "grant_revoked"},
                ip_address=ip_address,
                user_agent=user_agent,
                db_session=db,
            )
            return False, "Access to this file package has been revoked", grant, package

        return True, "Authorized as recipient", grant, package

    @classmethod
    def revoke_grant(
        cls,
        db: Session,
        sender_id: str,
        package_id: str,
        grant_id: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AccessGrant:
        """
        Revoke an access grant for a specific package recipient.
        Only the sender who created the package can revoke grants.
        """
        package = db.query(FilePackage).filter(FilePackage.id == package_id).first()
        if not package:
            raise PackageNotFoundError(f"Package {package_id} not found")

        # Validate sender authorization
        if package.sender_id != sender_id:
            AuditService.log_event(
                event_type=AuditEventType.PERMISSION_DENIED.value,
                action=f"Unauthorized revocation attempt by {sender_id} on package {package_id}",
                status="failure",
                user_id=sender_id,
                resource_id=package_id,
                resource_type="package",
                details={"package_id": package_id, "grant_id": grant_id},
                ip_address=ip_address,
                user_agent=user_agent,
                db_session=db,
            )
            raise UnauthorizedRevocationError("Only the package sender can revoke access grants")

        grant = (
            db.query(AccessGrant)
            .filter(
                AccessGrant.id == grant_id,
                AccessGrant.package_id == package_id,
            )
            .first()
        )
        if not grant:
            raise GrantNotFoundError(f"Access grant {grant_id} not found for package {package_id}")

        # Idempotent revocation
        if grant.status == GrantStatus.REVOKED.value:
            logger.info("Access grant %s on package %s is already revoked", grant_id, package_id)
            return grant

        # Mark grant as revoked
        grant.status = GrantStatus.REVOKED.value
        grant.revoked_at = datetime.now(timezone.utc)

        # Audit trail
        AuditService.log_event(
            event_type=AuditEventType.SHARE_REVOKED.value,
            action=f"Revoked access grant {grant_id} for recipient {grant.recipient_id} on package {package_id}",
            status="success",
            user_id=sender_id,
            resource_id=package_id,
            resource_type="package",
            details={
                "package_id": package_id,
                "grant_id": grant_id,
                "recipient_id": grant.recipient_id,
                "reason": reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=db,
        )

        db.commit()
        db.refresh(grant)
        logger.info("Access grant %s on package %s successfully revoked by sender %s", grant_id, package_id, sender_id)
        return grant

    @classmethod
    def list_package_grants(
        cls,
        db: Session,
        user_id: str,
        package_id: str,
    ) -> List[AccessGrant]:
        """List all access grants for a package (only accessible by sender)."""
        package = db.query(FilePackage).filter(FilePackage.id == package_id).first()
        if not package:
            raise PackageNotFoundError(f"Package {package_id} not found")

        if package.sender_id != user_id:
            raise UnauthorizedRevocationError("Only the package sender can view access grants")

        return (
            db.query(AccessGrant)
            .filter(AccessGrant.package_id == package_id)
            .order_by(AccessGrant.created_at.asc())
            .all()
        )
