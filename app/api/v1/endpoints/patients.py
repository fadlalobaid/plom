"""Patient CRUD API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services.patient_service import (
    NationalIdAlreadyRegisteredError,
    PatientNotFoundError,
    create_patient,
    delete_patient,
    get_patient_by_id,
    list_patients,
    update_patient,
)

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(get_current_active_doctor)],
)


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient_record(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Patient:
    """Register a new patient linked to the authenticated doctor."""
    try:
        return create_patient(db, payload, created_by_doctor_id=current_doctor.id)
    except NationalIdAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="National ID is already registered",
        ) from exc


@router.get("/", response_model=list[PatientResponse])
def get_patients(
    db: Annotated[Session, Depends(get_db)],
    full_name: Annotated[str | None, Query(description="Search by patient full name")] = None,
    phone_number: Annotated[str | None, Query(description="Search by phone number")] = None,
    national_id: Annotated[str | None, Query(description="Search by national ID")] = None,
) -> list[Patient]:
    """List patients with optional search filters."""
    return list_patients(
        db,
        full_name=full_name,
        phone_number=phone_number,
        national_id=national_id,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_record(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Patient:
    """Retrieve a patient record by ID."""
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient_record(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Patient:
    """Update a patient record."""
    try:
        return update_patient(db, patient_id, payload)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        ) from exc
    except NationalIdAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="National ID is already registered",
        ) from exc


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_record(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a patient record."""
    try:
        delete_patient(db, patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        ) from exc
