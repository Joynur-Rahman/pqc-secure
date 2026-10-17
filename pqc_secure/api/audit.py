"""Audit logging API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from pqc_secure.api.deps import get_current_active_user, get_db, is_admin_user
from pqc_secure.db.models import User
from pqc_secure.schemas.audit import AuditLogListResponse, AuditLogResponse
from pqc_secure.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def _parse_date_param(val: Optional[str]) -> Optional[datetime]:
    """Parse date/datetime string handling URL space decoding and ISO formats."""
    if not val:
        return None
    cleaned = val.strip().replace(" ", "+")
    try:
        return datetime.fromisoformat(cleaned)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(cleaned, fmt)
        except Exception:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid date format: {val}. Expected ISO 8601 format (e.g. YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
    )


@router.get("", response_model=AuditLogListResponse)
@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type (single or comma-separated)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Filter events after timestamp (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter events before timestamp (ISO 8601)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    page: Optional[int] = Query(None, ge=1, description="Optional page number (1-based)"),
    page_size: Optional[int] = Query(None, ge=1, le=1000, description="Optional page size"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve audit logs with filtering, pagination, and role-based access control.
    
    Access Control:
    - Administrators (configured via settings.admin_emails) can query across all users or filter by any user_id.
    - Standard authenticated users can only view their own audit logs (self-access). Attempting to query another
      user's logs returns a 403 Forbidden.
    """
    parsed_start = _parse_date_param(start_date)
    parsed_end = _parse_date_param(end_date)

    effective_limit = page_size if page_size is not None else limit
    effective_offset = ((page - 1) * effective_limit) if page is not None else offset

    is_admin = is_admin_user(current_user)

    if is_admin:
        target_user_id = user_id
    else:
        if user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only access your own audit logs",
            )
        target_user_id = current_user.id

    events, total_count = AuditService.get_events(
        db_session=db,
        user_id=target_user_id,
        event_type=event_type,
        start_date=parsed_start,
        end_date=parsed_end,
        limit=effective_limit,
        offset=effective_offset,
    )

    log_items = [AuditLogResponse.model_validate(e) for e in events]

    return AuditLogListResponse(
        logs=log_items,
        total=total_count,
        limit=effective_limit,
        offset=effective_offset,
    )
