"""Pydantic schemas for PulmoScan API validation and serialization."""

from app.schemas.auth import LoginRequest, LogoutResponse, TokenPayload, TokenResponse
from app.schemas.diagnosis_result import (
    DiagnosisAnalysisRequest,
    DiagnosisResultCreate,
    DiagnosisResultResponse,
)
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.schemas.xray_image import XrayImageCreate, XrayImageResponse, XrayImageUpdate

__all__ = [
    "DiagnosisAnalysisRequest",
    "DiagnosisResultCreate",
    "DiagnosisResultResponse",
    "DoctorCreate",
    "DoctorResponse",
    "DoctorUpdate",
    "LoginRequest",
    "LogoutResponse",
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    "TokenPayload",
    "TokenResponse",
    "XrayImageCreate",
    "XrayImageResponse",
    "XrayImageUpdate",
]
