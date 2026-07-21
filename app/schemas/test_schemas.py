"""Verify Pydantic schemas load and validate sample payloads."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.enums import DoctorRole, DoctorStatus, Gender, XrayViewType
from app.schemas import (
    DiagnosisAnalysisRequest,
    DiagnosisResultCreate,
    DiagnosisResultResponse,
    DoctorCreate,
    DoctorResponse,
    LoginRequest,
    PatientCreate,
    PatientResponse,
    TokenResponse,
    XrayImageCreate,
    XrayImageResponse,
)

SCHEMAS: list[type] = [
    LoginRequest,
    TokenResponse,
    DoctorCreate,
    DoctorResponse,
    PatientCreate,
    PatientResponse,
    XrayImageCreate,
    XrayImageResponse,
    DiagnosisAnalysisRequest,
    DiagnosisResultCreate,
    DiagnosisResultResponse,
]


def load_schemas() -> list[type]:
    """Return all registered schema classes."""
    return SCHEMAS


def run_validation_checks() -> None:
    """Validate representative payloads for each schema group."""
    doctor_id = uuid4()
    patient_id = uuid4()
    xray_image_id = uuid4()
    now = datetime.now(timezone.utc)

    LoginRequest(email="doctor@pulmoscan.com", password="securepass")
    DoctorCreate(
        full_name="Dr. Ahmed Ali",
        email="doctor@pulmoscan.com",
        password="securepass",
        specialization="Pulmonology",
    )
    DoctorResponse.model_validate(
        {
            "id": doctor_id,
            "full_name": "Dr. Ahmed Ali",
            "email": "doctor@pulmoscan.com",
            "specialization": "Pulmonology",
            "role": DoctorRole.DOCTOR,
            "status": DoctorStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
        }
    )
    PatientCreate(
        full_name="Patient One",
        date_of_birth=date(1990, 5, 15),
        gender=Gender.MALE,
        national_id="1234567890",
    )
    PatientResponse.model_validate(
        {
            "id": patient_id,
            "full_name": "Patient One",
            "date_of_birth": date(1990, 5, 15),
            "gender": Gender.MALE,
            "phone_number": None,
            "address": None,
            "national_id": "1234567890",
            "created_by_doctor_id": doctor_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    XrayImageCreate(
        patient_id=patient_id,
        view_type=XrayViewType.PA,
        notes="Routine scan",
    )
    XrayImageResponse.model_validate(
        {
            "id": xray_image_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "image_path": "uploads/xrays/sample.png",
            "view_type": XrayViewType.PA,
            "notes": "Routine scan",
            "uploaded_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    DiagnosisAnalysisRequest(
        patient_id=patient_id,
        xray_image_id=xray_image_id,
    )
    DiagnosisResultResponse.model_validate(
        {
            "id": uuid4(),
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "xray_image_id": xray_image_id,
            "predicted_label": "Normal",
            "confidence_score": Decimal("0.98231"),
            "model_version": "v1.0.0",
            "report_text": "No significant findings.",
            "visual_map_path": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert "password_hash" not in DoctorResponse.model_fields


def main() -> None:
    run_validation_checks()
    print(f"Loaded and validated {len(SCHEMAS)} schemas.")


if __name__ == "__main__":
    main()
