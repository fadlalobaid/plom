"""X-ray image request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import XrayViewType
from app.schemas.base import TimestampSchema, UUIDSchema


class XrayImageCreate(BaseModel):
    """Metadata submitted when uploading an X-ray (file handled separately via UploadFile)."""

    patient_id: UUID
    view_type: XrayViewType
    notes: str | None = None


class XrayImageUpdate(BaseModel):
    """Payload for partially updating X-ray image metadata."""

    view_type: XrayViewType | None = None
    notes: str | None = None


class XrayImageResponse(UUIDSchema, TimestampSchema):
    """X-ray image data returned by the API."""

    patient_id: UUID
    doctor_id: UUID
    image_path: str
    view_type: XrayViewType
    notes: str | None
    uploaded_at: datetime
