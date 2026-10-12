"""Session validation middleware"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Optional
import logging

from pqc_secure.services.auth import AuthService

logger = logging.getLogger(__name__)


class SessionValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that parses session tokens from Authorization headers or cookies
    and attaches user_id to request.state.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Default state
        request.state.user_id = None
        request.state.is_authenticated = False
        
        token: Optional[str] = None
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            
        # Fallback to session cookie
        if not token:
            token = request.cookies.get("session_token")
            
        if token:
            user_id = self.auth_service.verify_token(token)
            if user_id:
                request.state.user_id = user_id
                request.state.is_authenticated = True
                
        response = await call_next(request)
        return response
