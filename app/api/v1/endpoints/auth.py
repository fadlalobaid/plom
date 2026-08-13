from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor, security
from app.core import messages
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import AuditAction, AuditEntityType, DoctorStatus
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    PasswordChangeResponse,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.doctor import DoctorResponse
from app.services.audit_service import audit_operation
from app.services.auth_service import (
    IncorrectCurrentPasswordError,
    InvalidRefreshTokenError,
    PasswordReuseError,
    authenticate_doctor,
    change_doctor_password,
    extract_session_id,
    issue_login_tokens,
    refresh_auth_session,
    revoke_access_token,
    revoke_auth_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    doctor = authenticate_doctor(db, payload.email, payload.password)
    if doctor is None:
        audit_operation(
            db,
            action=AuditAction.LOGIN_FAILED,
            success=False,
            entity_type=AuditEntityType.DOCTOR,
            reason="invalid_credentials",
            email=payload.email,
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if doctor.status != DoctorStatus.ACTIVE:
        audit_operation(
            db,
            action=AuditAction.LOGIN_FAILED,
            success=False,
            user_id=doctor.id,
            entity_type=AuditEntityType.DOCTOR,
            entity_id=doctor.id,
            reason="inactive_account",
            email=doctor.email,
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=messages.INACTIVE_ACCOUNT,
        )

    access_token, refresh_token = issue_login_tokens(
        db,
        doctor,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    audit_operation(
        db,
        action=AuditAction.LOGIN,
        success=True,
        user_id=doctor.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=doctor.id,
        email=doctor.email,
        request=request,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=doctor.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Rotate a refresh session and issue a new short-lived access token."""
    try:
        doctor, access_token, refresh_token = refresh_auth_session(
            db,
            payload.refresh_token,
            ip_address=_client_ip(request),
        )
    except InvalidRefreshTokenError as exc:
        audit_operation(
            db,
            action=AuditAction.REFRESH_FAILED,
            success=False,
            entity_type=AuditEntityType.DOCTOR,
            reason="invalid_refresh_token",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages.INVALID_SESSION,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=doctor.must_change_password,
    )


@router.get("/me", response_model=DoctorResponse)
def get_me(
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Doctor:
    """Return the currently authenticated doctor profile."""
    return current_doctor


@router.post("/change-password", response_model=PasswordChangeResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> PasswordChangeResponse:
    """Replace the authenticated doctor's password."""
    try:
        change_doctor_password(
            db,
            current_doctor,
            payload.current_password,
            payload.new_password,
        )
    except IncorrectCurrentPasswordError as exc:
        audit_operation(
            db,
            action=AuditAction.CHANGE_PASSWORD,
            success=False,
            user_id=current_doctor.id,
            entity_type=AuditEntityType.DOCTOR,
            entity_id=current_doctor.id,
            reason="incorrect_current_password",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=messages.CURRENT_PASSWORD_INCORRECT,
        ) from exc
    except PasswordReuseError as exc:
        audit_operation(
            db,
            action=AuditAction.CHANGE_PASSWORD,
            success=False,
            user_id=current_doctor.id,
            entity_type=AuditEntityType.DOCTOR,
            entity_id=current_doctor.id,
            reason="password_reuse",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=messages.PASSWORD_REUSE_NOT_ALLOWED,
        ) from exc
    revoke_access_token(credentials.credentials)
    audit_operation(
        db,
        action=AuditAction.CHANGE_PASSWORD,
        success=True,
        user_id=current_doctor.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=current_doctor.id,
        request=request,
    )
    return PasswordChangeResponse()


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> LogoutResponse:
    """Revoke the current access token and its persistent refresh session."""
    session_id = extract_session_id(credentials.credentials)
    if session_id is not None:
        revoke_auth_session(db, session_id)
    revoke_access_token(credentials.credentials)
    audit_operation(
        db,
        action=AuditAction.LOGOUT,
        success=True,
        user_id=current_doctor.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=current_doctor.id,
        request=request,
    )
    return LogoutResponse()
