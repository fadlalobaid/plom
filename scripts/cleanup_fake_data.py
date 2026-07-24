"""Remove fake seed data created by scripts/seed_fake_data.py.

WARNING
-------
This script is intended ONLY for Development / Test environments.
It deletes records matching the fake-data markers used by the seeder.
It does NOT delete the configured admin account.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, or_, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.enums import DoctorRole
from app.models.patient import Patient
from app.models.xray_image import XrayImage

WARNING_BANNER = """
============================================================
  WARNING: DEVELOPMENT / TEST FAKE DATA CLEANUP
  This will permanently delete seeded fake records.
============================================================
"""

FAKE_PATIENT_NATIONAL_ID_PREFIX = "FAKE-NID-"
FAKE_DOCTOR_NATIONAL_ID_PREFIX = "FAKE-DOC-"
FAKE_XRAY_PATH_PREFIX = "uploads/fake/seed_xray_"
FAKE_DOCTOR_EMAIL_PATTERNS = (
    "doctor%@pulmoscan.fake",
    "doctor%@sb3.com",
)


def _ensure_not_production() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit(
            "Refusing to delete fake data because ENVIRONMENT=production."
        )


def _fake_doctor_ids(db) -> list:
    settings = get_settings()
    doctors = db.scalars(
        select(Doctor).where(
            or_(
                Doctor.national_id.like(f"{FAKE_DOCTOR_NATIONAL_ID_PREFIX}%"),
                Doctor.email.like(FAKE_DOCTOR_EMAIL_PATTERNS[0]),
                Doctor.email.like(FAKE_DOCTOR_EMAIL_PATTERNS[1]),
            )
        )
    ).all()
    return [
        doctor.id
        for doctor in doctors
        if doctor.email != settings.first_admin_email
        and doctor.role != DoctorRole.ADMIN
    ]


def cleanup_fake_data() -> None:
    print(WARNING_BANNER)
    _ensure_not_production()

    settings = get_settings()
    print(f"Environment: {settings.environment}")
    print("Deleting seeded fake data only. Admin will be kept.")
    print()

    db = SessionLocal()
    try:
        fake_doctor_ids = _fake_doctor_ids(db)
        fake_patient_ids = list(
            db.scalars(
                select(Patient.id).where(
                    or_(
                        Patient.national_id.like(f"{FAKE_PATIENT_NATIONAL_ID_PREFIX}%"),
                        Patient.created_by_doctor_id.in_(fake_doctor_ids)
                        if fake_doctor_ids
                        else Patient.id.is_(None),
                    )
                )
            ).all()
        )
        fake_xray_ids = list(
            db.scalars(
                select(XrayImage.id).where(
                    or_(
                        XrayImage.image_path.like(f"{FAKE_XRAY_PATH_PREFIX}%"),
                        XrayImage.patient_id.in_(fake_patient_ids)
                        if fake_patient_ids
                        else XrayImage.id.is_(None),
                        XrayImage.doctor_id.in_(fake_doctor_ids)
                        if fake_doctor_ids
                        else XrayImage.id.is_(None),
                    )
                )
            ).all()
        )

        deleted_diagnoses = 0
        if fake_xray_ids or fake_patient_ids or fake_doctor_ids:
            conditions = []
            if fake_xray_ids:
                conditions.append(DiagnosisResult.xray_image_id.in_(fake_xray_ids))
            if fake_patient_ids:
                conditions.append(DiagnosisResult.patient_id.in_(fake_patient_ids))
            if fake_doctor_ids:
                conditions.append(DiagnosisResult.doctor_id.in_(fake_doctor_ids))
            result = db.execute(delete(DiagnosisResult).where(or_(*conditions)))
            deleted_diagnoses = result.rowcount or 0

        deleted_xrays = 0
        if fake_xray_ids:
            result = db.execute(delete(XrayImage).where(XrayImage.id.in_(fake_xray_ids)))
            deleted_xrays = result.rowcount or 0

        deleted_patients = 0
        if fake_patient_ids:
            result = db.execute(delete(Patient).where(Patient.id.in_(fake_patient_ids)))
            deleted_patients = result.rowcount or 0

        deleted_doctors = 0
        if fake_doctor_ids:
            result = db.execute(delete(Doctor).where(Doctor.id.in_(fake_doctor_ids)))
            deleted_doctors = result.rowcount or 0

        db.commit()

        print("Fake data deleted successfully")
        print(f"Doctors deleted: {deleted_doctors}")
        print(f"Patients deleted: {deleted_patients}")
        print(f"X-ray records deleted: {deleted_xrays}")
        print(f"Diagnosis results deleted: {deleted_diagnoses}")
        print(f"Admin kept: {settings.first_admin_email}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_fake_data()
