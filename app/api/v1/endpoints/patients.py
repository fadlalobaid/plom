"""Patient CRUD API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor, require_password_change_completed
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.diagnosis_result import DiagnosisResultResponse
from app.schemas.patient import (
    PatientCreate,
    PatientMedicalRecordResponse,
    PatientResponse,
    PatientUpdate,
    PatientXrayHistoryResponse,
)
from app.schemas.xray_image import XrayImageResponse
from app.services.patient_service import (
    InvalidPatientNameError,
    NationalIdAlreadyRegisteredError,
    PatientNotFoundError,
    create_patient,
    delete_patient,
    get_patient_by_id,
    list_patients,
    update_patient,
)
from app.services.xray_service import list_xray_images_by_patient

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(require_password_change_completed)],
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
    except InvalidPatientNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=list[PatientResponse])
def get_patients(
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
    full_name: Annotated[str | None, Query(description="Search by patient full name")] = None,
    phone_number: Annotated[str | None, Query(description="Search by phone number")] = None,
    national_id: Annotated[str | None, Query(description="Search by national ID")] = None,
) -> list[Patient]:
    """List patients with optional search filters."""
    return list_patients(
        db,
        doctor_id=current_doctor.id,
        full_name=full_name,
        phone_number=phone_number,
        national_id=national_id,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_record(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Patient:
    """Retrieve a patient record by ID."""
    patient = get_patient_by_id(db, patient_id, current_doctor.id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return patient


@router.get("/{patient_id}/medical-record", response_model=PatientMedicalRecordResponse)
def get_patient_medical_record(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> PatientMedicalRecordResponse:
    """Return patient details and prior X-rays with their analysis results."""
    patient = get_patient_by_id(db, patient_id, current_doctor.id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    xray_images = list_xray_images_by_patient(db, patient_id, current_doctor.id)
    return PatientMedicalRecordResponse(
        patient=PatientResponse.model_validate(patient),
        xray_history=[
            PatientXrayHistoryResponse(
                xray_image=XrayImageResponse.model_validate(xray_image),
                diagnosis_result=(
                    DiagnosisResultResponse.model_validate(xray_image.diagnosis_result)
                    if xray_image.diagnosis_result is not None
                    else None
                ),
            )
            for xray_image in xray_images
        ],
    )


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient_record(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> Patient:
    """Update a patient record."""
    try:
        return update_patient(db, patient_id, payload, current_doctor.id)
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
    except InvalidPatientNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_record(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> None:
    """Delete a patient record."""
    try:
        delete_patient(db, patient_id, current_doctor.id)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        ) from exc
