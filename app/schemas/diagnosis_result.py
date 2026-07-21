"""Diagnosis request and response schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import TimestampSchema, UUIDSchema


class DiagnosisAnalysisRequest(BaseModel):
    """Payload to trigger AI analysis from a chest X-ray image only."""

    patient_id: UUID
    xray_image_id: UUID


class DiagnosisResultCreate(BaseModel):
    """Payload for persisting an AI diagnosis result (typically internal/service use)."""

    patient_id: UUID
    doctor_id: UUID
    xray_image_id: UUID
    predicted_label: str = Field(min_length=1, max_length=100)
    confidence_score: Decimal = Field(ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=50)
    report_text: str | None = None
    visual_map_path: str | None = Field(default=None, max_length=500)


class DiagnosisResultResponse(UUIDSchema, TimestampSchema):
    """Diagnosis result data returned by the API."""

    patient_id: UUID
    doctor_id: UUID
    xray_image_id: UUID
    predicted_label: str
    confidence_score: Decimal
    model_version: str
    report_text: str | None
    visual_map_path: str | None
