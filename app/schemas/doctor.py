"""Doctor request and response schemas."""

from datetime import date
from typing import Self

from pydantic import BaseModel, model_validator

from app.core.validators import (
    FullName,
    NormalizedEmail,
    OptionalCertificate,
    OptionalDateOfBirth,
    OptionalFullName,
    OptionalNationalId,
    OptionalNormalizedEmail,
    OptionalPhoneNumber,
    OptionalSpecialization,
)
from app.models.enums import DoctorRole, DoctorStatus
from app.schemas.auth import StrongPassword
from app.schemas.base import TimestampSchema, UUIDSchema


class DoctorCreate(BaseModel):
    """Payload for admin-created doctor accounts."""

    full_name: FullName
    email: NormalizedEmail
    specialization: OptionalSpecialization = None
    date_of_birth: OptionalDateOfBirth = None
    national_id: OptionalNationalId = None
    certificate: OptionalCertificate = None
    phone_number: OptionalPhoneNumber = None
    password: StrongPassword


class DoctorUpdate(BaseModel):
    """Payload for partially updating a doctor account."""

    full_name: OptionalFullName = None
    email: OptionalNormalizedEmail = None
    specialization: OptionalSpecialization = None
    date_of_birth: OptionalDateOfBirth = None
    national_id: OptionalNationalId = None
    certificate: OptionalCertificate = None
    phone_number: OptionalPhoneNumber = None
    status: DoctorStatus | None = None
    password: StrongPassword | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        """Reject explicit nulls that cannot be persisted safely."""
        required_fields = {"full_name", "email", "status", "password"}
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


class DoctorResponse(UUIDSchema, TimestampSchema):
    """Doctor data returned by the API (excludes password_hash)."""

    full_name: str
    email: NormalizedEmail
    specialization: str | None
    date_of_birth: date | None = None
    national_id: str | None = None
    certificate: str | None = None
    phone_number: str | None = None
    role: DoctorRole
    status: DoctorStatus
    must_change_password: bool


class DoctorPasswordResetRequest(BaseModel):
    """Temporary password assigned to a doctor by an administrator."""

    new_password: StrongPassword
