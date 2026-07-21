"""SQLAlchemy ORM models for PulmoScan."""

from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.xray_image import XrayImage

__all__ = [
    "DiagnosisResult",
    "Doctor",
    "Patient",
    "XrayImage",
]
