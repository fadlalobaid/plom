"""Patient request and response schemas."""

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.core.validators import (
    Area,
    DateOfBirth,
    FatherName,
    FirstName,
    LastName,
    MotherName,
    NationalId,
    OptionalArea,
    OptionalDateOfBirth,
    OptionalFatherName,
    OptionalFirstName,
    OptionalLastName,
    OptionalMotherName,
    OptionalNationalId,
    OptionalPhoneNumber,
)
from app.models.enums import Gender, SyrianGovernorate
from app.schemas.base import TimestampSchema, UUIDSchema
from app.schemas.diagnosis_result import DiagnosisResultResponse
from app.schemas.xray_image import XrayImageResponse


class PatientCreate(BaseModel):
    """Payload for registering a new patient."""

    first_name: FirstName
    father_name: FatherName
    mother_name: MotherName
    last_name: LastName
    date_of_birth: DateOfBirth
    gender: Gender
    phone_number: OptionalPhoneNumber = None
    governorate: SyrianGovernorate
    area: Area
    national_id: NationalId


class PatientUpdate(BaseModel):
    """Payload for partially updating a patient record."""

    first_name: OptionalFirstName = None
    father_name: OptionalFatherName = None
    mother_name: OptionalMotherName = None
    last_name: OptionalLastName = None
    date_of_birth: OptionalDateOfBirth = None
    gender: Gender | None = None
    phone_number: OptionalPhoneNumber = None
    governorate: SyrianGovernorate | None = None
    area: OptionalArea = None
    national_id: OptionalNationalId = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        """Reject explicit nulls for non-nullable patient columns."""
        required_fields = {
            "first_name",
            "father_name",
            "mother_name",
            "last_name",
            "date_of_birth",
            "gender",
            "governorate",
            "area",
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

    first_name: str
    father_name: str
    mother_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    phone_number: str | None
    governorate: SyrianGovernorate
    area: str
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
