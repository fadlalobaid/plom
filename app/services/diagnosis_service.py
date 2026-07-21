"""Diagnosis result business logic."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.diagnosis_result import DiagnosisResult
from app.models.xray_image import XrayImage
from app.services.ai_service import XrayImageFileNotFoundError, analyze_xray_image
from app.services.patient_service import get_patient_by_id
from app.services.xray_service import get_xray_image_by_id


class DiagnosisResultNotFoundError(Exception):
    """Raised when a diagnosis result record cannot be found."""


class InvalidDiagnosisRequestError(Exception):
    """Raised when a diagnosis analysis request fails validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def get_diagnosis_result_by_id(db: Session, diagnosis_id: UUID) -> DiagnosisResult | None:
    """Return a diagnosis result by primary key, or None if not found."""
    return db.get(DiagnosisResult, diagnosis_id)


def list_diagnosis_results_by_patient(db: Session, patient_id: UUID) -> list[DiagnosisResult]:
    """Return all diagnosis results linked to a patient ordered by creation time."""
    statement = (
        select(DiagnosisResult)
        .where(DiagnosisResult.patient_id == patient_id)
        .order_by(DiagnosisResult.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_diagnosis_results_by_xray_image(
    db: Session,
    xray_image_id: UUID,
) -> list[DiagnosisResult]:
    """Return diagnosis results linked to a specific X-ray image."""
    statement = (
        select(DiagnosisResult)
        .where(DiagnosisResult.xray_image_id == xray_image_id)
        .order_by(DiagnosisResult.created_at.desc())
    )
    return list(db.scalars(statement).all())


def validate_diagnosis_request(
    db: Session,
    patient_id: UUID,
    xray_image_id: UUID,
) -> XrayImage:
    """Validate analysis input and return the linked X-ray image record."""
    if get_patient_by_id(db, patient_id) is None:
        raise InvalidDiagnosisRequestError("Patient not found")

    xray_image = get_xray_image_by_id(db, xray_image_id)
    if xray_image is None:
        raise InvalidDiagnosisRequestError("X-ray image not found")

    if xray_image.patient_id != patient_id:
        raise InvalidDiagnosisRequestError(
            "X-ray image does not belong to the specified patient"
        )

    existing_result = db.scalar(
        select(DiagnosisResult).where(DiagnosisResult.xray_image_id == xray_image_id)
    )
    if existing_result is not None:
        raise InvalidDiagnosisRequestError(
            "A diagnosis result already exists for this X-ray image"
        )

    return xray_image


def analyze_and_create_diagnosis_result(
    db: Session,
    *,
    patient_id: UUID,
    xray_image_id: UUID,
    doctor_id: UUID,
) -> DiagnosisResult:
    """Validate input, run AI analysis, and persist the diagnosis result."""
    xray_image = validate_diagnosis_request(db, patient_id, xray_image_id)
    ai_result = analyze_xray_image(xray_image.image_path)

    confidence_score = ai_result["confidence_score"]
    if not isinstance(confidence_score, Decimal):
        confidence_score = Decimal(str(confidence_score))

    diagnosis_result = DiagnosisResult(
        patient_id=patient_id,
        doctor_id=doctor_id,
        xray_image_id=xray_image_id,
        predicted_label=str(ai_result["predicted_label"]),
        confidence_score=confidence_score,
        model_version=str(ai_result["model_version"]),
        report_text=str(ai_result["report_text"]) if ai_result["report_text"] is not None else None,
        visual_map_path=(
            str(ai_result["visual_map_path"]) if ai_result["visual_map_path"] is not None else None
        ),
    )
    db.add(diagnosis_result)
    db.commit()
    db.refresh(diagnosis_result)
    return diagnosis_result


def delete_diagnosis_result(db: Session, diagnosis_id: UUID) -> None:
    """Permanently delete a diagnosis result record."""
    diagnosis_result = get_diagnosis_result_by_id(db, diagnosis_id)
    if diagnosis_result is None:
        raise DiagnosisResultNotFoundError

    db.delete(diagnosis_result)
    db.commit()
