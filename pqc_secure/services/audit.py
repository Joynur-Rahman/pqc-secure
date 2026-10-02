"""Audit logging service for compliance and security monitoring"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from pqc_secure.db.models import AuditLog, AuditEventType
from pqc_secure.core.config import settings

logger = logging.getLogger(__name__)


class AuditService:
    """Handle audit event logging and compliance tracking"""
    
    @staticmethod
    def log_event(
        event_type: str,
        action: str,
        status: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> Optional[AuditLog]:
        """
        Log an audit event to the database and application logs.
        
        Args:
            event_type: Type of event (see AuditEventType enum)
            action: Description of the action taken
            status: success or failure
            user_id: ID of the user performing the action
            resource_id: ID of the resource being acted upon
            resource_type: Type of resource (user, file, key, etc.)
            details: Additional details (must not contain secrets/plaintext)
            ip_address: Client IP address
            user_agent: Client user agent
            db_session: Database session for persistence
            
        Returns:
            AuditLog instance if database persistence succeeded, None otherwise
        """
        if not settings.audit_logging_enabled:
            return None
            
        # Check if this event type should be logged based on enabled event categories
        enabled_events = settings.get_audit_log_events()
        # Extract category from event type (e.g., "user" from "user_login")
        event_category = event_type.split("_")[0].lower()
        
        # Check if category is in enabled events
        if enabled_events and enabled_events != ['']:
            # Check if this event's category is enabled
            category_enabled = any(
                event_category == enabled_event.lower() or 
                enabled_event.lower() in event_type.lower()
                for enabled_event in enabled_events
            )
            if not category_enabled:
                return None
        
        try:
            # Sanitize details to ensure no secrets are logged
            safe_details = AuditService._sanitize_details(details or {})
            details_json = json.dumps(safe_details) if safe_details else None
            
            # Create audit log entry
            audit_entry = AuditLog(
                event_type=event_type,
                action=action,
                status=status,
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                details=details_json,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Persist to database if session provided
            if db_session:
                db_session.add(audit_entry)
                try:
                    db_session.commit()
                except Exception as e:
                    logger.error(f"Failed to persist audit log to database: {str(e)}")
                    db_session.rollback()
                    return None
            
            # Also log to application logger at appropriate level
            log_level = "warning" if status == "failure" else "info"
            log_message = f"[AUDIT] {event_type}: {action} (user={user_id}, resource={resource_id}, status={status})"
            
            if log_level == "warning":
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            return audit_entry
            
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            return None
    
    @staticmethod
    def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from audit details.
        
        Excluded fields: password, private_key, secret, token, plaintext, ciphertext
        """
        sensitive_keys = {
            'password', 'private_key', 'secret', 'token', 'plaintext', 
            'ciphertext', 'shared_secret', 'key_material', 'nonce',
            'authentication_tag', 'signature', 'public_key_material'
        }
        
        sanitized = {}
        for key, value in details.items():
            if key.lower() not in sensitive_keys:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def get_events(
        db_session: Session,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[AuditLog], int]:
        """
        Query audit events from the database.
        
        Args:
            db_session: Database session
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (events list, total count)
        """
        query = db_session.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        events = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()
        
        return events, total_count


# Convenience functions for common audit events
def log_authentication_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None
):
    """Log authentication-related events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"Authentication event: {event_type}",
        status=status,
        user_id=user_id,
        resource_type="user",
        ip_address=ip_address,
        details=details,
        db_session=db_session
    )


def log_access_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None
):
    """Log access/permission-related events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"Access event: {event_type}",
        status=status,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        ip_address=ip_address,
        details=details,
        db_session=db_session
    )


def log_crypto_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None
):
    """Log cryptographic operation events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"Cryptographic operation: {event_type}",
        status=status,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="cryptographic_operation",
        details=details,
        db_session=db_session
    )


def log_file_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None
):
    """Log file operation events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"File operation: {event_type}",
        status=status,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="file",
        details=details,
        db_session=db_session
    )


async def log_user_registered(user_id: str, db_session: Optional[Session] = None):
    """Log user registration event"""
    return AuditService.log_event(
        event_type=AuditEventType.USER_REGISTERED,
        action="User account registered",
        status="success",
        user_id=user_id,
        resource_id=user_id,
        resource_type="user",
        db_session=db_session
    )


async def log_registration_failure(email: str, reason: Optional[str] = None, db_session: Optional[Session] = None):
    """Log failed registration attempt"""
    return AuditService.log_event(
        event_type=AuditEventType.REGISTRATION_FAILED,
        action=f"User registration failed: {reason or 'unknown reason'}",
        status="failure",
        resource_id=email,
        resource_type="user",
        details={"email": email, "reason": reason},
        db_session=db_session
    )
