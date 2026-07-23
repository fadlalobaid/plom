"""X-ray image request and response schemas."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import XrayViewType
from app.schemas.base import TimestampSchema, UUIDSchema


class XrayImageCreate(BaseModel):
    """Metadata submitted when uploading an X-ray (file handled separately via UploadFile)."""

    patient_id: UUID
    view_type: XrayViewType
    notes: str | None = None
    taken_at: datetime | None = None


class XrayImageUpdate(BaseModel):
    """Payload for partially updating X-ray image metadata."""

    view_type: XrayViewType | None = None
    notes: str | None = None
    taken_at: datetime | None = None

    @model_validator(mode="after")
    def reject_null_view_type(self) -> Self:
        """Reject an explicit null for the non-nullable view type."""
        if "view_type" in self.model_fields_set and self.view_type is None:
            raise ValueError("view_type cannot be null")
        return self


class XrayImageResponse(UUIDSchema, TimestampSchema):
    """X-ray image data returned by the API."""

    patient_id: UUID
    doctor_id: UUID
    image_path: str
    taken_at: datetime | None = None
    result: str | None = None
    view_type: XrayViewType
    notes: str | None
    uploaded_at: datetime
