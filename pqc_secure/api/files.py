"""File sharing and upload API endpoints."""
from __future__ import annotations

import json
import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from pqc_secure.api.deps import get_current_active_user, get_db
from pqc_secure.db.models import AccessGrant, FilePackage, GrantStatus, User
from pqc_secure.schemas.files import (
    AccessGrantResponse,
    AccessGrantRevokeResponse,
    FilePackageListResponse,
    FilePackageResponse,
    FileShareRequest,
    FileUploadResponse,
    RecipientInfo,
)
from pqc_secure.services.access_control import (
    AccessControlService,
    GrantNotFoundError,
    PackageNotFoundError as ACPackageNotFoundError,
    UnauthorizedRevocationError,
)
from pqc_secure.services.file import (
    AccessDeniedError,
    DecryptionFailedError,
    FileService,
    FileServiceError,
    FileUploadError,
    PackageNotFoundError,
    RecipientValidationError,
    SignatureVerificationError,
)

router = APIRouter(prefix="/files", tags=["files"])


def _format_package_response(package: FilePackage, db: Session) -> FilePackageResponse:
    """Format ORM FilePackage into Pydantic FilePackageResponse."""
    sender = db.query(User).filter(User.id == package.sender_id).first()
    sender_email = sender.email if sender else None

    # Load access grants for this package to provide accurate status & grant_id
    grants = db.query(AccessGrant).filter(AccessGrant.package_id == package.id).all()
    grant_by_recipient = {g.recipient_id: g for g in grants}

    # Parse recipients from canonical manifest
    recipients_info = []
    try:
        manifest = json.loads(package.manifest_json)
        for r in manifest.get("recipients", []):
            rec_id = r.get("recipient_id")
            grant = grant_by_recipient.get(rec_id)
            recipients_info.append(
                RecipientInfo(
                    recipient_id=rec_id,
                    recipient_email=r.get("recipient_email"),
                    recipient_key_id=r.get("key_id", ""),
                    grant_id=grant.id if grant else None,
                    status=grant.status if grant else "active",
                    revoked_at=grant.revoked_at if grant else None,
                )
            )
    except Exception:
        pass

    return FilePackageResponse(
        id=package.id,
        package_id=package.id,
        original_filename=package.original_filename,
        file_size=package.file_size,
        crypto_mode=package.crypto_mode,
        package_version=package.package_version,
        sender_id=package.sender_id,
        sender_email=sender_email,
        recipients=recipients_info,
        created_at=package.created_at,
        status="active",
    )


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    upload_id: Optional[str] = Form(None),
    chunk_number: int = Form(0),
    total_chunks: int = Form(1),
    current_user: User = Depends(get_current_active_user),
):
    """Upload complete file or chunk for subsequent encryption and sharing."""
    effective_upload_id = upload_id or str(uuid.uuid4())
    filename = file.filename or "uploaded_file"

    try:
        chunk_data = await file.read()
        is_complete, total_bytes = FileService.save_upload_chunk(
            upload_id=effective_upload_id,
            filename=filename,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            chunk_data=chunk_data,
        )

        return FileUploadResponse(
            upload_id=effective_upload_id,
            filename=filename,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            bytes_uploaded=total_bytes,
            is_complete=is_complete,
            message="Chunk uploaded successfully" if not is_complete else "File upload complete and staged",
        )
    except FileUploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload error: {str(e)}",
        )


@router.post("/share", response_model=FilePackageResponse, status_code=status.HTTP_201_CREATED)
async def share_file(
    request: Request,
    body: FileShareRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Encrypt and share an uploaded file with validated recipients."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        package = FileService.share_file_package(
            db=db,
            sender_id=current_user.id,
            upload_id=body.upload_id,
            recipient_emails=body.recipient_emails,
            recipient_ids=body.recipient_ids,
            encryption_mode=body.encryption_mode,
            sender_signing_key_id=body.sender_signing_key_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return _format_package_response(package, db)
    except (FileUploadError, RecipientValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File sharing pipeline error: {str(e)}",
        )


@router.get("/", response_model=FilePackageListResponse)
@router.get("", response_model=FilePackageListResponse)
async def list_files(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List files shared by or accessible to the current user."""
    packages = FileService.list_user_packages(db, current_user.id)
    return FilePackageListResponse(
        packages=[_format_package_response(p, db) for p in packages],
        total=len(packages),
    )


@router.get("/{package_id}", response_model=FilePackageResponse)
async def get_file_metadata(
    package_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata for a specific shared file package with access verification."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    is_authorized, reason, grant, package = AccessControlService.check_package_access(
        db=db,
        user_id=current_user.id,
        package_id=package_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package {package_id} not found",
        )
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason,
        )

    return _format_package_response(package, db)


@router.get("/{package_id}/download")
async def download_file(
    package_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Decrypt and download shared file package with access control and signature verification."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        filename, plaintext_bytes = FileService.decrypt_file_package(
            db=db,
            package_id=package_id,
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        safe_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
        headers = {
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(plaintext_bytes)),
            "X-PQC-Decryption-Status": "verified",
        }

        return Response(content=plaintext_bytes, headers=headers, media_type="application/octet-stream")

    except PackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security alert: Package signature failed verification. File may be tampered.",
        )
    except DecryptionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decryption failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download service error: {str(e)}",
        )


@router.post("/{package_id}/grants/{grant_id}/revoke", response_model=AccessGrantRevokeResponse)
async def revoke_access_grant(
    package_id: str,
    grant_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke an access grant for a package recipient.
    
    Only the sender who created the package can revoke access grants.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        grant = FileService.revoke_access_grant(
            db=db,
            sender_id=current_user.id,
            package_id=package_id,
            grant_id=grant_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return AccessGrantRevokeResponse(
            package_id=package_id,
            grant_id=grant.id,
            status=grant.status,
            message="Access grant successfully revoked",
        )
    except ACPackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except GrantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedRevocationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revocation error: {str(e)}",
        )


@router.get("/{package_id}/grants", response_model=List[AccessGrantResponse])
async def list_package_grants(
    package_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all access grants for a package (only accessible by sender)."""
    try:
        grants = AccessControlService.list_package_grants(
            db=db,
            user_id=current_user.id,
            package_id=package_id,
        )
        res = []
        for g in grants:
            recipient = db.query(User).filter(User.id == g.recipient_id).first()
            res.append(
                AccessGrantResponse(
                    id=g.id,
                    grant_id=g.id,
                    package_id=g.package_id,
                    recipient_id=g.recipient_id,
                    recipient_email=recipient.email if recipient else None,
                    status=g.status,
                    created_at=g.created_at,
                    revoked_at=g.revoked_at,
                )
            )
        return res
    except ACPackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedRevocationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


