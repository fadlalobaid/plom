"""Diagnosis analysis and result API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor, require_password_change_completed
from app.db.session import get_db
from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.schemas.diagnosis_result import DiagnosisAnalysisRequest, DiagnosisResultResponse
from app.services.ai_service import XrayImageFileNotFoundError
from app.services.diagnosis_service import (
    DiagnosisResultNotFoundError,
    InvalidDiagnosisRequestError,
    analyze_and_create_diagnosis_result,
    delete_diagnosis_result,
    get_diagnosis_result_by_id,
    list_diagnosis_results_by_patient,
    list_diagnosis_results_by_xray_image,
)
from app.services.patient_service import get_patient_by_id
from app.services.xray_service import get_xray_image_by_id

router = APIRouter(
    prefix="/diagnosis",
    tags=["diagnosis"],
    dependencies=[Depends(require_password_change_completed)],
)


@router.post("/analyze", response_model=DiagnosisResultResponse, status_code=status.HTTP_201_CREATED)
def analyze_xray_diagnosis(
    payload: DiagnosisAnalysisRequest,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> DiagnosisResult:
    """Analyze a chest X-ray image and store a mock diagnosis result."""
    try:
        return analyze_and_create_diagnosis_result(
            db,
            patient_id=payload.patient_id,
            xray_image_id=payload.xray_image_id,
            doctor_id=current_doctor.id,
        )
    except InvalidDiagnosisRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except XrayImageFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/patient/{patient_id}", response_model=list[DiagnosisResultResponse])
def get_patient_diagnosis_results(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> list[DiagnosisResult]:
    """List diagnosis results for a patient."""
    if get_patient_by_id(db, patient_id, current_doctor.id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return list_diagnosis_results_by_patient(db, patient_id, current_doctor.id)


@router.get("/xray-image/{xray_image_id}", response_model=list[DiagnosisResultResponse])
def get_xray_image_diagnosis_results(
    xray_image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> list[DiagnosisResult]:
    """List diagnosis results linked to an X-ray image."""
    if get_xray_image_by_id(db, xray_image_id, current_doctor.id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-ray image not found",
        )
    return list_diagnosis_results_by_xray_image(db, xray_image_id, current_doctor.id)


@router.get("/{diagnosis_id}", response_model=DiagnosisResultResponse)
def get_diagnosis_result_record(
    diagnosis_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> DiagnosisResult:
    """Retrieve a diagnosis result by ID."""
    diagnosis_result = get_diagnosis_result_by_id(db, diagnosis_id, current_doctor.id)
    if diagnosis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis result not found",
        )
    return diagnosis_result


@router.delete("/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnosis_result_record(
    diagnosis_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> None:
    """Delete a diagnosis result record."""
    try:
        delete_diagnosis_result(db, diagnosis_id, current_doctor.id)
    except DiagnosisResultNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis result not found",
        ) from exc
