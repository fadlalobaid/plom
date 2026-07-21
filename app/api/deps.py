"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus
from app.services.auth_service import is_access_token_revoked
from app.services.doctor_service import get_doctor_by_id

security = HTTPBearer()


def get_current_doctor(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> Doctor:
    """Return the doctor associated with a valid JWT access token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None or is_access_token_revoked(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        doctor_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    doctor = get_doctor_by_id(db, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return doctor


def get_current_active_doctor(
    current_doctor: Annotated[Doctor, Depends(get_current_doctor)],
) -> Doctor:
    """Return the authenticated doctor only when the account is active."""
    if current_doctor.status != DoctorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return current_doctor


def require_admin(
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Doctor:
    """Return the authenticated doctor only when the account has admin role."""
    if current_doctor.role != DoctorRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_doctor
