"""Key management request/response schemas"""
from pydantic import BaseModel

class KeyRegisterRequest(BaseModel):
    """Key registration request"""
    algorithm: str
    public_key_material: str

class KeyResponse(BaseModel):
    """Key response"""
    key_id: str
    algorithm: str
    status: str
