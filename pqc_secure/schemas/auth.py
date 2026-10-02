"""Authentication request/response schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    account_status: str = Field(..., description="User account status")
    
    class Config:
        from_attributes = True

class UserRegisterResponse(BaseModel):
    """User registration response"""
    id: str
    email: str
    account_status: str
    session_token: str = Field(..., description="JWT session token for authentication")
    
    class Config:
        from_attributes = True

class AuthErrorResponse(BaseModel):
    """Authentication error response"""
    detail: str = Field(..., description="Error message")
