"""Authentication API endpoints"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pqc_secure.core.config import settings
from pqc_secure.db.session import get_db_session
from pqc_secure.db.models import AuditEventType, User
from pqc_secure.services.auth import AuthService
from pqc_secure.api.deps import get_current_user, get_optional_current_user
from pqc_secure.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserResponse,
)
from pqc_secure.services.audit import (
    log_user_registered,
    log_registration_failure,
    log_authentication_event
)
from pqc_secure.middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Initialize services
auth_service = AuthService()


def set_session_cookie(response: Response, session_token: str) -> None:
    """Set secure session cookie on response"""
    is_secure = (settings.environment == "production") or (not settings.debug)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )



@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db_session)
):
    """
    User registration endpoint.
    
    Creates a new user account with email and password.
    
    **Requirements:**
    - Email must be valid and unique (case-insensitive)
    - Password must meet complexity requirements (min 8 chars, uppercase, lowercase, digit)
    - Returns user ID and session token on success
    - Rate-limited to 5 requests per minute per client
    
    **Access:** Public (no authentication required)
    
    **Rate limit:** 5 requests per minute (auth endpoints)
    """
    # Check rate limit
    if rate_limiter.check_auth_rate_limit(http_request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    try:
        # Register user
        success, user, error_msg = auth_service.register_user(db, request.email, request.password)
        
        if not success:
            # Log failed registration
            await log_registration_failure(
                email=request.email,
                reason=error_msg,
                db_session=db,
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Registration failed"
            )
        
        # Generate session token
        session_token = auth_service.generate_token(user.id)
        
        # Set session cookie
        set_session_cookie(response, session_token)
        
        # Log successful registration
        await log_user_registered(
            user_id=user.id,
            db_session=db,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        
        return UserRegisterResponse(
            id=user.id,
            email=user.email,
            account_status=user.account_status,
            session_token=session_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/login", response_model=UserRegisterResponse)
async def login(
    request: UserLoginRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db_session)
):
    """
    User login endpoint.
    
    Authenticates a user with email and password and returns a session token.
    Sets secure HttpOnly session cookie on response.
    
    **Rate limit:** 5 requests per minute (auth endpoints)
    """
    # Check rate limit
    if rate_limiter.check_auth_rate_limit(http_request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    try:
        success, user, error_msg = auth_service.authenticate_user(db, request.email, request.password)
        
        if not success:
            log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILED,
                status="failure",
                details={"email": request.email, "reason": error_msg},
                ip_address=client_ip,
                user_agent=user_agent,
                db_session=db
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg or "Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        session_token = auth_service.generate_token(user.id)
        
        # Set secure session cookie
        set_session_cookie(response, session_token)
        
        log_authentication_event(
            event_type=AuditEventType.USER_LOGIN,
            status="success",
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            db_session=db
        )
        
        return UserRegisterResponse(
            id=user.id,
            email=user.email,
            account_status=user.account_status,
            session_token=session_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    http_request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db_session)
):
    """
    User logout endpoint.
    
    Clears session cookie and records audit log.
    """
    response.delete_cookie(key="session_token", path="/")
    
    if current_user:
        client_ip = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")
        log_authentication_event(
            event_type=AuditEventType.USER_LOGOUT,
            status="success",
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            db_session=db
        )
        
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get profile information of currently authenticated user.
    Requires valid session token (via Bearer header or cookie).
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        account_status=current_user.account_status,
        created_at=current_user.created_at
    )

