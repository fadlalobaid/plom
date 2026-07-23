"""Patient request and response schemas."""

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Gender
from app.schemas.base import TimestampSchema, UUIDSchema
from app.schemas.diagnosis_result import DiagnosisResultResponse
from app.schemas.xray_image import XrayImageResponse


class PatientCreate(BaseModel):
    """Payload for registering a new patient."""

    first_name: str = Field(min_length=1, max_length=255)
    father_name: str = Field(min_length=1, max_length=255)
    mother_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    date_of_birth: date
    gender: Gender
    phone_number: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    national_id: str = Field(min_length=1, max_length=50)


class PatientUpdate(BaseModel):
    """Payload for partially updating a patient record."""

    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    father_name: str | None = Field(default=None, min_length=1, max_length=255)
    mother_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    national_id: str | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        """Reject explicit nulls for non-nullable patient columns."""
        required_fields = {
            "first_name",
            "father_name",
            "last_name",
            "date_of_birth",
            "gender",
            "national_id",
        }
        invalid_fields = [
            field
            for field in required_fields & self.model_fields_set
            if getattr(self, field) is None
        ]
        if invalid_fields:
            raise ValueError(
                f"Fields cannot be null: {', '.join(sorted(invalid_fields))}"
            )
        return self


class PatientResponse(UUIDSchema, TimestampSchema):
    """Patient data returned by the API."""

    full_name: str
    first_name: str | None = None
    father_name: str | None = None
    mother_name: str | None = None
    last_name: str | None = None
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
