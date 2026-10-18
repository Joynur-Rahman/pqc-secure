"""Security and CSRF protection middleware."""
from __future__ import annotations

import logging
from typing import Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pqc_secure.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects defense-in-depth HTTP security headers on all responses.
    
    Includes:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (clickjacking protection)
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricted hardware API access
    - Content-Security-Policy: restricting script/frame execution sources
    - Strict-Transport-Security: HSTS header when running under HTTPS or production
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # MIME sniffing protection
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Frame hijacking / clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"

        # Cross-site scripting filter protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy to prevent information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict dangerous browser features and sensors
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )

        # Baseline Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )

        # HSTS (Strict-Transport-Security) for production or HTTPS
        if (
            settings.is_production()
            or settings.session_cookie_secure
            or request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto") == "https"
        ):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for cookie-authenticated state-changing requests.
    
    Exemptions:
    - Safe read-only HTTP methods (GET, HEAD, OPTIONS).
    - Public authentication endpoints (login, register, health, docs).
    - Authorization: Bearer token authenticated requests (browser does not auto-send).
    
    Enforcement for Cookie Authentication:
    - Validates Origin or Referer against configured allowed origins.
    - Alternatively checks for explicit custom header (X-CSRF-Token or X-Requested-With).
    """

    SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS: Set[str] = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/login",
        "/api/auth/login",
        "/auth/register",
        "/api/auth/register",
        "/login",
        "/api/login",
        "/register",
        "/api/register",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Path exemption check
        clean_path = request.url.path.rstrip("/")
        if any(clean_path == exempt.rstrip("/") for exempt in self.EXEMPT_PATHS):
            return await call_next(request)

        # If authenticated via explicit Bearer token in Authorization header,
        # request is not vulnerable to standard cross-site request forgery.
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await call_next(request)

        # Check if request relies on session cookie authentication
        session_cookie = request.cookies.get("session_token")
        if session_cookie:
            # 1. Custom CSRF header check
            csrf_token = request.headers.get("X-CSRF-Token") or request.headers.get("X-Requested-With")
            if csrf_token:
                return await call_next(request)

            # 2. Origin / Referer validation against allowed origins
            origin = request.headers.get("Origin") or request.headers.get("Referer")
            if origin:
                allowed_origins = [o.rstrip("/") for o in settings.get_allowed_origins_list()]
                # Include test environment origin
                allowed_origins.extend(["http://testserver", "https://testserver"])

                clean_origin = origin.rstrip("/")
                is_allowed = any(
                    clean_origin == allowed or clean_origin.startswith(f"{allowed}/")
                    for allowed in allowed_origins
                )
                if not is_allowed:
                    logger.warning(
                        "CSRF origin validation failed for origin '%s' on path %s",
                        origin,
                        request.url.path,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed: Origin not permitted."},
                    )
            else:
                # Cookie authenticated state-changing request without Origin or CSRF header
                logger.warning(
                    "CSRF validation failed: Missing origin and CSRF headers on path %s",
                    request.url.path,
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: Missing origin or CSRF token."},
                )

        return await call_next(request)
