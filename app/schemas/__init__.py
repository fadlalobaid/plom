"""Pydantic schemas for PulmoScan API validation and serialization."""

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    PasswordChangeResponse,
    TokenPayload,
    TokenResponse,
)
from app.schemas.diagnosis_result import (
    DiagnosisAnalysisRequest,
    DiagnosisResultCreate,
    DiagnosisResultResponse,
)
from app.schemas.doctor import (
    DoctorCreate,
    DoctorPasswordResetRequest,
    DoctorResponse,
    DoctorUpdate,
)
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.schemas.xray_image import XrayImageCreate, XrayImageResponse, XrayImageUpdate

__all__ = [
    "DiagnosisAnalysisRequest",
    "DiagnosisResultCreate",
    "DiagnosisResultResponse",
    "ChangePasswordRequest",
    "DoctorCreate",
    "DoctorPasswordResetRequest",
    "DoctorResponse",
    "DoctorUpdate",
    "LoginRequest",
    "LogoutResponse",
    "PasswordChangeResponse",
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    "TokenPayload",
    "TokenResponse",
    "XrayImageCreate",
    "XrayImageResponse",
    "XrayImageUpdate",
]
