"""Doctor request and response schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DoctorRole, DoctorStatus
from app.schemas.base import TimestampSchema, UUIDSchema


class DoctorCreate(BaseModel):
    """Payload for admin-created doctor accounts."""

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    specialization: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class DoctorUpdate(BaseModel):
    """Payload for partially updating a doctor account."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    specialization: str | None = Field(default=None, max_length=255)
    status: DoctorStatus | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class DoctorResponse(UUIDSchema, TimestampSchema):
    """Doctor data returned by the API (excludes password_hash)."""

    full_name: str
    email: EmailStr
    specialization: str | None
    role: DoctorRole
    status: DoctorStatus
