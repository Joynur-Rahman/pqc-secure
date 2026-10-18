"""Standardized error handlers preventing sensitive information disclosure."""
from __future__ import annotations

import http
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("pqc_secure.errors")

SENSITIVE_FIELDS = {"password", "secret", "token", "private_key", "shared_secret", "plaintext", "key_material"}


def sanitize_validation_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize validation error messages to avoid reflecting passwords or secrets."""
    sanitized = []
    for err in errors:
        item = dict(err)
        loc = item.get("loc", ())
        # If any element in loc references a sensitive field, redact the input value
        if any(isinstance(part, str) and part.lower() in SENSITIVE_FIELDS for part in loc):
            if "input" in item:
                item["input"] = "[REDACTED]"
        sanitized.append(item)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle known HTTP exceptions with consistent response structure."""
        status_code = exc.status_code
        try:
            error_code = http.HTTPStatus(status_code).name
        except ValueError:
            error_code = "HTTP_ERROR"

        client_ip = request.client.host if request.client else "unknown"

        if status_code >= 500:
            logger.error(
                "HTTP %d error on %s %s from %s: %s",
                status_code,
                request.method,
                request.url.path,
                client_ip,
                exc.detail,
            )
        else:
            logger.info(
                "HTTP %d on %s %s from %s: %s",
                status_code,
                request.method,
                request.url.path,
                client_ip,
                exc.detail,
            )

        content = {
            "detail": exc.detail,
            "status_code": status_code,
            "error": error_code,
        }

        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle schema validation errors, redacting sensitive parameters."""
        sanitized_errors = sanitize_validation_errors(exc.errors())
        client_ip = request.client.host if request.client else "unknown"

        logger.warning(
            "Validation error on %s %s from %s: %d issues",
            request.method,
            request.url.path,
            client_ip,
            len(sanitized_errors),
        )

        # Build clean summary message
        detail_messages = []
        for err in sanitized_errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "invalid")
            detail_messages.append(f"{loc}: {msg}")
        summary_detail = "; ".join(detail_messages) if detail_messages else "Request validation failed"

        content = {
            "detail": summary_detail,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "error": "UNPROCESSABLE_ENTITY",
            "errors": sanitized_errors,
        }

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle unexpected internal exceptions:
        - Log full stack trace internally with exc_info.
        - Return safe generic message without exposing file paths, DB schemas, or tracebacks.
        """
        client_ip = request.client.host if request.client else "unknown"

        logger.error(
            "Unhandled exception on %s %s from %s: %s",
            request.method,
            request.url.path,
            client_ip,
            str(exc),
            exc_info=True,
        )

        content = {
            "detail": "An internal server error occurred.",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error": "INTERNAL_SERVER_ERROR",
        }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )
