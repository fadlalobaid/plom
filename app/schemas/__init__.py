"""Pydantic schemas for PulmoScan API validation and serialization."""

from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    PasswordChangeResponse,
    RefreshRequest,
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
    "AuditLogListResponse",
    "AuditLogResponse",
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
    "RefreshRequest",
    "TokenPayload",
    "TokenResponse",
    "XrayImageCreate",
    "XrayImageResponse",
    "XrayImageUpdate",
]
