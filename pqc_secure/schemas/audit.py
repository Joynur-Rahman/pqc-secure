"""Audit logging response schemas"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, model_validator, field_validator


class AuditLogResponse(BaseModel):
    """Schema representing an individual audit log entry"""
    id: str
    event_type: str
    action: str
    status: str
    user_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    timestamp: Optional[datetime] = None
    eventType: Optional[str] = None
    userId: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v: Any) -> Optional[Dict[str, Any]]:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                return {"raw": v}
        if isinstance(v, dict):
            return v
        return None

    @model_validator(mode="after")
    def populate_compatibility_fields(self) -> AuditLogResponse:
        if self.timestamp is None:
            self.timestamp = self.created_at
        if self.eventType is None:
            self.eventType = self.event_type
        if self.userId is None:
            self.userId = self.user_id
        return self


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries"""
    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)
