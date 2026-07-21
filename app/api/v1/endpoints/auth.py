from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor, security
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import DoctorStatus
from app.schemas.auth import LoginRequest, LogoutResponse, TokenResponse
from app.schemas.doctor import DoctorResponse
from app.services.auth_service import (
    authenticate_doctor,
    create_doctor_access_token,
    revoke_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    doctor = authenticate_doctor(db, payload.email, payload.password)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if doctor.status != DoctorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )

    access_token = create_doctor_access_token(doctor)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=DoctorResponse)
def get_me(
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Doctor:
    """Return the currently authenticated doctor profile."""
    return current_doctor


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    _current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> LogoutResponse:
    """Revoke the current access token and end the session."""
    revoke_access_token(credentials.credentials)
    return LogoutResponse()

