"""File sharing and upload request/response schemas"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FileUploadResponse(BaseModel):
    """File upload progress and completion response"""
    upload_id: str
    filename: str
    chunk_number: int
    total_chunks: int
    bytes_uploaded: int
    is_complete: bool
    message: str


class FileShareRequest(BaseModel):
    """Request to encrypt and share an uploaded file with recipients"""
    upload_id: str = Field(..., description="ID of previously uploaded file/chunks")
    recipient_emails: Optional[List[str]] = Field(
        default=None, description="List of recipient user emails"
    )
    recipient_ids: Optional[List[str]] = Field(
        default=None, description="List of recipient user IDs"
    )
    encryption_mode: str = Field(
        default="pqc", description="Encryption mode: 'pqc' (ML-KEM/ML-DSA) or 'classical' (X25519/Ed25519)"
    )
    sender_signing_key_id: Optional[str] = Field(
        default=None, description="Optional key ID to sign the manifest with"
    )


class RecipientInfo(BaseModel):
    """Recipient information in shared package"""
    recipient_id: str
    recipient_email: Optional[str] = None
    recipient_key_id: str
    grant_id: Optional[str] = None
    status: str = "active"
    revoked_at: Optional[datetime] = None


class AccessGrantResponse(BaseModel):
    """Access grant response schema"""
    id: str
    grant_id: str
    package_id: str
    recipient_id: str
    recipient_email: Optional[str] = None
    status: str
    created_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FilePackageResponse(BaseModel):
    """File package summary and metadata"""
    id: str
    package_id: str
    original_filename: Optional[str] = None
    file_size: int
    crypto_mode: str
    package_version: str
    sender_id: str
    sender_email: Optional[str] = None
    recipients: List[RecipientInfo] = []
    created_at: datetime
    status: str = "active"

    model_config = ConfigDict(from_attributes=True)


class FilePackageListResponse(BaseModel):
    """List of file packages"""
    packages: List[FilePackageResponse]
    total: int


class AccessGrantRevokeResponse(BaseModel):
    """Access grant revocation response"""
    package_id: str
    grant_id: str
    status: str
    message: str
