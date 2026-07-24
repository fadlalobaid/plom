"""Admin-only doctor management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import AuditAction, AuditEntityType
from app.schemas.auth import PasswordChangeResponse
from app.schemas.doctor import (
    DoctorCreate,
    DoctorPasswordResetRequest,
    DoctorResponse,
    DoctorUpdate,
)
from app.services.audit_service import create_audit_log
from app.services.doctor_service import (
    DoctorNationalIdAlreadyRegisteredError,
    DoctorNotFoundError,
    EmailAlreadyRegisteredError,
    InvalidDoctorPasswordResetError,
    create_doctor,
    deactivate_doctor,
    get_doctor_by_id,
    list_doctors,
    reset_doctor_password,
    update_doctor,
)

router = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    dependencies=[Depends(require_admin)],
)


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_account(
    payload: DoctorCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[Doctor, Depends(require_admin)],
) -> Doctor:
    """Create a new doctor account (admin only)."""
    try:
        doctor = create_doctor(db, payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        ) from exc
    except DoctorNationalIdAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="National ID is already registered",
        ) from exc

    create_audit_log(
        db,
        action=AuditAction.CREATE_DOCTOR,
        user_id=current_admin.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=doctor.id,
        details={
            "result": "success",
            "email": doctor.email,
            "role": doctor.role.value,
            "status": doctor.status.value,
        },
        request=request,
    )
    return doctor


@router.get("/", response_model=list[DoctorResponse])
def get_doctors(
    db: Annotated[Session, Depends(get_db)],
) -> list[Doctor]:
    """List all doctor accounts (admin only)."""
    return list_doctors(db)


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_account(
    doctor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Doctor:
    """Retrieve a doctor account by ID (admin only)."""
    doctor = get_doctor_by_id(db, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    return doctor


@router.post("/{doctor_id}/reset-password", response_model=PasswordChangeResponse)
def reset_doctor_account_password(
    doctor_id: UUID,
    payload: DoctorPasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[Doctor, Depends(require_admin)],
) -> PasswordChangeResponse:
    """Assign a temporary password to a doctor account (admin only)."""
    try:
        doctor = reset_doctor_password(db, doctor_id, payload)
    except DoctorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        ) from exc
    except InvalidDoctorPasswordResetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is only available for doctor accounts",
        ) from exc

    create_audit_log(
        db,
        action=AuditAction.UPDATE_DOCTOR,
        user_id=current_admin.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=doctor.id,
        details={
            "result": "success",
            "updated_fields": ["password", "must_change_password"],
            "must_change_password": True,
        },
        request=request,
    )
    return PasswordChangeResponse(message="Password reset successfully")


@router.patch("/{doctor_id}", response_model=DoctorResponse)
def update_doctor_account(
    doctor_id: UUID,
    payload: DoctorUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[Doctor, Depends(require_admin)],
) -> Doctor:
    """Update a doctor account (admin only)."""
    previous_status = None
    existing_doctor = get_doctor_by_id(db, doctor_id)
    if existing_doctor is not None:
        previous_status = existing_doctor.status

    try:
        doctor = update_doctor(db, doctor_id, payload)
    except DoctorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        ) from exc
    except DoctorNationalIdAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="National ID is already registered",
        ) from exc
    except InvalidDoctorPasswordResetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is only available for doctor accounts",
        ) from exc

    updated_fields = sorted(
        field for field in payload.model_fields_set if field != "password"
    )
    if "password" in payload.model_fields_set:
        updated_fields.append("password")

    details: dict[str, object] = {
        "result": "success",
        "updated_fields": updated_fields,
    }
    if previous_status is not None and previous_status != doctor.status:
        details["previous_status"] = previous_status.value
        details["new_status"] = doctor.status.value

    create_audit_log(
        db,
        action=AuditAction.UPDATE_DOCTOR,
        user_id=current_admin.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=doctor.id,
        details=details,
        request=request,
    )
    return doctor


@router.delete("/{doctor_id}", response_model=DoctorResponse)
def deactivate_doctor_account(
    doctor_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[Doctor, Depends(require_admin)],
) -> Doctor:
    """Soft-delete a doctor account by setting status to inactive (admin only)."""
    try:
        doctor = deactivate_doctor(db, doctor_id)
    except DoctorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        ) from exc

    create_audit_log(
        db,
        action=AuditAction.DELETE_DOCTOR,
        user_id=current_admin.id,
        entity_type=AuditEntityType.DOCTOR,
        entity_id=doctor.id,
        details={
            "result": "success",
            "soft_delete": True,
            "status": doctor.status.value,
        },
        request=request,
    )
    return doctor
