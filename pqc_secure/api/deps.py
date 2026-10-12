"""API Dependencies for session validation and authentication"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from pqc_secure.db.session import get_db_session
from pqc_secure.db.models import User
from pqc_secure.services.auth import AuthService

auth_service = AuthService()
bearer_scheme = HTTPBearer(auto_error=False)


def extract_token(
    http_request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[str]:
    """
    Extract token from either Authorization header (Bearer) or session cookie.
    
    Checks in priority:
    1. Authorization: Bearer <token> header
    2. Cookie: session_token=<token>
    """
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    
    cookie_token = http_request.cookies.get("session_token")
    if cookie_token:
        return cookie_token
        
    return None


async def get_current_user(
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Dependency that validates the session token and returns the authenticated User.
    
    Raises HTTPException(401) if:
    - Token is missing
    - Token is expired
    - Token is invalid
    - User does not exist
    - User account is not active
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    is_valid, payload, error_msg = auth_service.decode_token(token)
    if not is_valid or not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg or "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency verifying user is active"""
    if current_user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active"
        )
    return current_user


async def get_optional_current_user(
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db_session)
) -> Optional[User]:
    """Dependency returning authenticated User if valid token is provided, or None"""
    if not token:
        return None
    
    is_valid, payload, _ = auth_service.decode_token(token)
    if not is_valid or not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.account_status != "active":
        return None
    
    return user
