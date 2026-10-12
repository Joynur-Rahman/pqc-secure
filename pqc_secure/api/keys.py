"""Key management API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from pqc_secure.api.deps import get_current_active_user, get_db
from pqc_secure.db.models import CryptographicKey, User
from pqc_secure.schemas.keys import (
    KeyListResponse,
    KeyRegisterRequest,
    KeyResponse,
    KeyRevokeRequest,
    KeyRevokeResponse,
    KeyRotateRequest,
)
from pqc_secure.services.crypto import CryptoService, InvalidKeyError
from pqc_secure.services.key import (
    KeyNotFoundError,
    KeyPermissionError,
    KeyService,
    KeyServiceError,
)

router = APIRouter(prefix="/keys", tags=["keys"])


def _format_key_response(key: CryptographicKey) -> KeyResponse:
    """Format ORM CryptographicKey into Pydantic KeyResponse."""
    return KeyResponse(
        id=key.id,
        key_id=key.key_id,
        user_id=key.user_id,
        algorithm=key.algorithm,
        key_type=key.key_type,
        version=key.version,
        public_key_material=CryptoService.encode_base64(key.public_key_material),
        status=key.status,
        created_at=key.created_at,
    )


@router.post("/register", response_model=KeyResponse, status_code=status.HTTP_201_CREATED)
async def register_key(
    request: Request,
    body: KeyRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Register public key for the authenticated user."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        key = KeyService.register_key(
            db=db,
            user_id=current_user.id,
            algorithm=body.algorithm,
            public_key_b64=body.public_key_material,
            key_type=body.key_type or "public",
            private_key_b64=body.private_key_material,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return _format_key_response(key)
    except InvalidKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except KeyServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/my-keys", response_model=KeyListResponse)
async def list_user_keys(
    include_inactive: bool = Query(True, description="Include revoked and superseded keys"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all cryptographic keys registered by the authenticated user."""
    keys = KeyService.list_user_keys(
        db=db,
        user_id=current_user.id,
        include_inactive=include_inactive,
    )
    return KeyListResponse(
        keys=[_format_key_response(k) for k in keys],
        total=len(keys),
    )


@router.get("/{key_id}", response_model=KeyResponse)
async def get_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve specific key by its canonical key identifier."""
    key = KeyService.get_key_by_id(db, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key {key_id} not found",
        )
    return _format_key_response(key)


@router.get("/user/{user_id}", response_model=KeyListResponse)
async def discover_user_keys(
    user_id: str,
    algorithm: Optional[str] = Query(None, description="Optional algorithm filter"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Discover active public keys for a specific recipient user."""
    keys = KeyService.get_user_public_keys(
        db=db,
        user_id=user_id,
        algorithm=algorithm,
    )
    return KeyListResponse(
        keys=[_format_key_response(k) for k in keys],
        total=len(keys),
    )


@router.post("/{key_id}/rotate", response_model=KeyResponse)
async def rotate_key(
    key_id: str,
    request: Request,
    body: Optional[KeyRotateRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Rotate an existing key to a new version, marking previous version as superseded."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    new_pub_b64 = body.public_key_material if body else None

    try:
        new_key = KeyService.rotate_key(
            db=db,
            user_id=current_user.id,
            key_id=key_id,
            new_public_key_b64=new_pub_b64,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return _format_key_response(new_key)
    except KeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except KeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidKeyError, KeyServiceError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{key_id}/revoke", response_model=KeyRevokeResponse)
async def revoke_key(
    key_id: str,
    request: Request,
    body: Optional[KeyRevokeRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke a key to prevent it from being used for future file shares."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    reason = body.reason if body else None

    try:
        key = KeyService.revoke_key(
            db=db,
            user_id=current_user.id,
            key_id=key_id,
            reason=reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return KeyRevokeResponse(
            key_id=key.key_id,
            status=key.status,
            message="Key revoked successfully",
        )
    except KeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except KeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except KeyServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
