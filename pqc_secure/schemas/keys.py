"""Key management request/response schemas"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class KeyRegisterRequest(BaseModel):
    """Key registration request"""
    algorithm: str = Field(..., description="Key algorithm (e.g. ml-kem-768, ml-dsa-65, x25519, ed25519)")
    public_key_material: str = Field(..., description="Base64-encoded public key bytes")
    key_type: Optional[str] = Field("public", description="Key type (public or private)")


class KeyRotateRequest(BaseModel):
    """Key rotation request"""
    public_key_material: Optional[str] = Field(
        None, description="Optional new Base64-encoded public key. If omitted, new key is generated."
    )


class KeyRevokeRequest(BaseModel):
    """Key revocation request"""
    reason: Optional[str] = Field(None, description="Reason for key revocation")


class KeyResponse(BaseModel):
    """Key representation schema"""
    id: str
    key_id: str
    user_id: str
    algorithm: str
    key_type: str
    version: int
    public_key_material: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeyListResponse(BaseModel):
    """List of keys response"""
    keys: List[KeyResponse]
    total: int


class KeyRevokeResponse(BaseModel):
    """Key revocation response"""
    key_id: str
    status: str
    message: str
