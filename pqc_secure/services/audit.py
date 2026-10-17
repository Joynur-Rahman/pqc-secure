"""Audit logging service for compliance and security monitoring"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
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
            lower_enabled = [e.lower() for e in enabled_events]
            auth_events = {"user_login", "user_logout", "login_failed", "registration_failed", "user_registered"}
            is_auth_event = (event_type.lower() in auth_events) and ("auth" in lower_enabled)
            
            # Check if this event's category is enabled
            category_enabled = is_auth_event or any(
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
    def _sanitize_details(details: Any) -> Any:
        """
        Recursively remove sensitive fields from audit details.
        
        Excluded fields: password, private_key, secret, token, plaintext, ciphertext,
        shared_secret, key_material, nonce, authentication_tag, signature, etc.
        """
        if not isinstance(details, dict):
            if isinstance(details, list):
                return [AuditService._sanitize_details(item) for item in details]
            return details

        sensitive_exact = {
            'password', 'private_key', 'secret', 'token', 'plaintext', 
            'ciphertext', 'shared_secret', 'key_material', 'nonce',
            'authentication_tag', 'signature', 'public_key_material',
            'private_key_material', 'session_token', 'access_token',
            'refresh_token', 'auth_token', 'api_key', 'api_secret',
            'symmetric_key', 'wrapping_key', 'cek', 'credentials'
        }
        
        sensitive_substrings = (
            'password', 'secret', 'private_key', 'token', 'plaintext', 'ciphertext'
        )

        sanitized = {}
        for key, value in details.items():
            key_str = str(key)
            key_lower = key_str.lower()
            
            # Check exact match or sensitive substring
            if key_lower in sensitive_exact or any(sub in key_lower for sub in sensitive_substrings):
                continue
                
            # If value is a nested dictionary or list, sanitize recursively
            if isinstance(value, dict):
                sanitized[key] = AuditService._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    AuditService._sanitize_details(item) if isinstance(item, (dict, list)) else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Redact PEM private key or obvious raw key material
                if "BEGIN PRIVATE KEY" in value or "BEGIN RSA PRIVATE KEY" in value or "BEGIN EC PRIVATE KEY" in value:
                    sanitized[key] = "[REDACTED_PRIVATE_KEY]"
                else:
                    sanitized[key] = value
            else:
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
            event_type: Filter by event type (single or comma-separated)
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
            types = [t.strip().lower() for t in event_type.split(",") if t.strip()]
            if len(types) == 1:
                query = query.filter(func.lower(AuditLog.event_type) == types[0])
            elif len(types) > 1:
                query = query.filter(func.lower(AuditLog.event_type).in_(types))
        
        if start_date:
            clean_start = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
            query = query.filter(AuditLog.created_at >= clean_start)
        
        if end_date:
            clean_end = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            query = query.filter(AuditLog.created_at <= clean_end)
        
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
    db_session: Optional[Session] = None,
    user_agent: Optional[str] = None,
):
    """Log authentication-related events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"Authentication event: {event_type}",
        status=status,
        user_id=user_id,
        resource_type="user",
        ip_address=ip_address,
        user_agent=user_agent,
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
    db_session: Optional[Session] = None,
    user_agent: Optional[str] = None,
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
        user_agent=user_agent,
        details=details,
        db_session=db_session
    )


def log_crypto_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Log cryptographic operation events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"Cryptographic operation: {event_type}",
        status=status,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="cryptographic_operation",
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        db_session=db_session
    )


def log_file_event(
    event_type: str,
    status: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Log file operation events"""
    return AuditService.log_event(
        event_type=event_type,
        action=f"File operation: {event_type}",
        status=status,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="file",
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        db_session=db_session
    )


async def log_user_registered(
    user_id: str,
    db_session: Optional[Session] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Log user registration event"""
    return AuditService.log_event(
        event_type=AuditEventType.USER_REGISTERED,
        action="User account registered",
        status="success",
        user_id=user_id,
        resource_id=user_id,
        resource_type="user",
        ip_address=ip_address,
        user_agent=user_agent,
        db_session=db_session
    )


async def log_registration_failure(
    email: str,
    reason: Optional[str] = None,
    db_session: Optional[Session] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Log failed registration attempt"""
    return AuditService.log_event(
        event_type=AuditEventType.REGISTRATION_FAILED,
        action=f"User registration failed: {reason or 'unknown reason'}",
        status="failure",
        resource_id=email,
        resource_type="user",
        details={"email": email, "reason": reason},
        ip_address=ip_address,
        user_agent=user_agent,
        db_session=db_session
    )
