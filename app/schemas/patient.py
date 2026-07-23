"""Patient request and response schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Gender
from app.schemas.base import TimestampSchema, UUIDSchema
from app.schemas.diagnosis_result import DiagnosisResultResponse
from app.schemas.xray_image import XrayImageResponse


class PatientCreate(BaseModel):
    """Payload for registering a new patient."""

    full_name: str = Field(min_length=1, max_length=255)
    date_of_birth: date
    gender: Gender
    phone_number: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    national_id: str = Field(min_length=1, max_length=50)


class PatientUpdate(BaseModel):
    """Payload for partially updating a patient record."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    national_id: str | None = Field(default=None, min_length=1, max_length=50)


class PatientResponse(UUIDSchema, TimestampSchema):
    """Patient data returned by the API."""

    full_name: str
    date_of_birth: date
    gender: Gender
    phone_number: str | None
    address: str | None
    national_id: str
    created_by_doctor_id: UUID


class PatientXrayHistoryResponse(BaseModel):
    """An X-ray image and its associated analysis result."""

    xray_image: XrayImageResponse
    diagnosis_result: DiagnosisResultResponse | None


class PatientMedicalRecordResponse(BaseModel):
    """Patient details with chronological X-ray and diagnosis history."""

    patient: PatientResponse
    xray_history: list[PatientXrayHistoryResponse]
