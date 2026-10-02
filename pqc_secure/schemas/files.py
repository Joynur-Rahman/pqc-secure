"""File sharing request/response schemas"""
from pydantic import BaseModel

class FileShareRequest(BaseModel):
    """File share request"""
    package_id: str
    recipient_ids: list[str]
    encryption_mode: str

class FileMetadataResponse(BaseModel):
    """File metadata response"""
    package_id: str
    sender_id: str
    recipients: list[str]
    created_at: str
