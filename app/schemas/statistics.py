"""Statistics response schemas."""

from pydantic import BaseModel, Field


class StatisticsOverviewResponse(BaseModel):
    """Aggregated system statistics for the admin dashboard."""

    total_admins: int = Field(ge=0)
    total_doctors: int = Field(ge=0)
    active_doctors: int = Field(ge=0)
    inactive_doctors: int = Field(ge=0)
    total_patients: int = Field(ge=0)
    total_xray_images: int = Field(ge=0)
    total_diagnosis_results: int = Field(ge=0)
