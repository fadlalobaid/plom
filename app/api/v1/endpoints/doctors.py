"""Admin-only doctor management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.services.doctor_service import (
    DoctorNationalIdAlreadyRegisteredError,
    DoctorNotFoundError,
    EmailAlreadyRegisteredError,
    create_doctor,
    deactivate_doctor,
    get_doctor_by_id,
    list_doctors,
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
    db: Annotated[Session, Depends(get_db)],
) -> Doctor:
    """Create a new doctor account (admin only)."""
    try:
        return create_doctor(db, payload)
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


@router.patch("/{doctor_id}", response_model=DoctorResponse)
def update_doctor_account(
    doctor_id: UUID,
    payload: DoctorUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Doctor:
    """Update a doctor account (admin only)."""
    try:
        return update_doctor(db, doctor_id, payload)
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


@router.delete("/{doctor_id}", response_model=DoctorResponse)
def deactivate_doctor_account(
    doctor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Doctor:
    """Soft-delete a doctor account by setting status to inactive (admin only)."""
    try:
        return deactivate_doctor(db, doctor_id)
    except DoctorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        ) from exc
