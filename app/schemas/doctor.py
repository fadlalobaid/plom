"""Doctor request and response schemas."""

from datetime import date
from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import DoctorRole, DoctorStatus
from app.schemas.base import TimestampSchema, UUIDSchema


class DoctorCreate(BaseModel):
    """Payload for admin-created doctor accounts."""

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    specialization: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    national_id: str | None = Field(default=None, min_length=1, max_length=50)
    certificate: str | None = Field(default=None, max_length=500)
    phone_number: str | None = Field(default=None, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class DoctorUpdate(BaseModel):
    """Payload for partially updating a doctor account."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    specialization: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    national_id: str | None = Field(default=None, min_length=1, max_length=50)
    certificate: str | None = Field(default=None, max_length=500)
    phone_number: str | None = Field(default=None, max_length=50)
    status: DoctorStatus | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

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
    email: EmailStr
    specialization: str | None
    date_of_birth: date | None = None
    national_id: str | None = None
    certificate: str | None = None
    phone_number: str | None = None
    role: DoctorRole
    status: DoctorStatus
