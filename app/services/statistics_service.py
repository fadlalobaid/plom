"""System statistics business logic."""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus
from app.models.patient import Patient
from app.models.xray_image import XrayImage
from app.schemas.statistics import StatisticsOverviewResponse


def _count(db: Session, statement: Select[Any]) -> int:
    """Return a scalar count from a SQLAlchemy select statement."""
    return db.scalar(statement) or 0


def get_statistics_overview(db: Session) -> StatisticsOverviewResponse:
    """Return aggregated counts for the admin statistics dashboard."""
    total_admins = _count(
        db,
        select(func.count())
        .select_from(Doctor)
        .where(Doctor.role == DoctorRole.ADMIN),
    )
    total_doctors = _count(
        db,
        select(func.count())
        .select_from(Doctor)
        .where(Doctor.role == DoctorRole.DOCTOR),
    )
    active_doctors = _count(
        db,
        select(func.count())
        .select_from(Doctor)
        .where(
            Doctor.role == DoctorRole.DOCTOR,
            Doctor.status == DoctorStatus.ACTIVE,
        ),
    )
    inactive_doctors = _count(
        db,
        select(func.count())
        .select_from(Doctor)
        .where(
            Doctor.role == DoctorRole.DOCTOR,
            Doctor.status == DoctorStatus.INACTIVE,
        ),
    )
    total_patients = _count(
        db,
        select(func.count()).select_from(Patient),
    )
    total_xray_images = _count(
        db,
        select(func.count()).select_from(XrayImage),
    )
    total_diagnosis_results = _count(
        db,
        select(func.count()).select_from(DiagnosisResult),
    )

    return StatisticsOverviewResponse(
        total_admins=total_admins,
        total_doctors=total_doctors,
        active_doctors=active_doctors,
        inactive_doctors=inactive_doctors,
        total_patients=total_patients,
        total_xray_images=total_xray_images,
        total_diagnosis_results=total_diagnosis_results,
    )
