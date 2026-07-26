"""Seed realistic fake data for PulmoScan development and testing.

WARNING
-------
This script is intended ONLY for Development / Test environments.
Do NOT run it against a Production database that contains real patient data.
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure the backend package root is on sys.path when running as a script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash, validate_admin_seed_password
from app.db.session import SessionLocal
from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.enums import (
    DoctorRole,
    DoctorStatus,
    Gender,
    SyrianGovernorate,
    XrayViewType,
)
from app.models.patient import Patient
from app.models.xray_image import XrayImage

# ---------------------------------------------------------------------------
# Safety / seed configuration
# ---------------------------------------------------------------------------

WARNING_BANNER = """
============================================================
  WARNING: DEVELOPMENT / TEST DATA SEEDER
  Do NOT run this script in Production on real data.
============================================================
"""

TARGET_DOCTORS = 25
TARGET_PATIENTS = 200
TARGET_XRAYS = 20
TARGET_DIAGNOSES = 120

DOCTOR_PASSWORD = "sb30021"
FAKE_DOCTOR_EMAIL_DOMAIN = "sb3.com"
FAKE_DOCTOR_NATIONAL_ID_BASE = 8_000_000_000
FAKE_PATIENT_NATIONAL_ID_BASE = 9_000_000_000
FAKE_XRAY_PATH_PREFIX = "uploads/fake/seed_xray_"

SPECIALIZATIONS = (
    "Pulmonology",
    "Radiology",
    "Internal Medicine",
    "Respiratory Medicine",
    "Family Medicine",
)

DIAGNOSIS_LABELS = (
    "normal",
    "pneumonia",
    "tuberculosis",
    "covid-19",
    "lung_opacity",
)

MODEL_VERSION = "mock-ai-v1"

fake = Faker()
Faker.seed(42)
random.seed(42)


def _print_warning() -> None:
    print(WARNING_BANNER)


def _ensure_not_production() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit(
            "Refusing to seed fake data because ENVIRONMENT=production."
        )


def _ensure_admin(db: Session) -> None:
    """Create the configured admin only when it does not already exist."""
    settings = get_settings()
    existing_admin = db.scalar(
        select(Doctor).where(Doctor.email == settings.first_admin_email)
    )
    if existing_admin is not None:
        print(f"Admin already exists: {settings.first_admin_email}")
        return

    admin_password = validate_admin_seed_password(settings.first_admin_password)
    admin = Doctor(
        full_name=settings.first_admin_full_name,
        email=settings.first_admin_email,
        password_hash=get_password_hash(admin_password),
        specialization="Administration",
        date_of_birth=datetime(1980, 1, 1).date(),
        phone_number="0900000001",
        governorate=SyrianGovernorate.DAMASCUS,
        area="مركز المدينة",
        role=DoctorRole.ADMIN,
        status=DoctorStatus.ACTIVE,
        must_change_password=False,
    )
    db.add(admin)
    db.commit()
    print(f"Admin created: {settings.first_admin_email}")


def _fake_doctor_email(index: int) -> str:
    return f"doctor{index}@{FAKE_DOCTOR_EMAIL_DOMAIN}"


def _fake_doctor_national_id(index: int) -> str:
    return str(FAKE_DOCTOR_NATIONAL_ID_BASE + index)


def _fake_patient_national_id(index: int) -> str:
    return str(FAKE_PATIENT_NATIONAL_ID_BASE + index)


def _fake_xray_path(index: int) -> str:
    return f"{FAKE_XRAY_PATH_PREFIX}{index:05d}.jpg"


def _list_fake_doctors(db: Session) -> list[Doctor]:
    return list(
        db.scalars(
            select(Doctor)
            .where(
                Doctor.email.like(f"doctor%@{FAKE_DOCTOR_EMAIL_DOMAIN}"),
                Doctor.role == DoctorRole.DOCTOR,
            )
            .order_by(Doctor.email.asc())
        ).all()
    )


def _count_fake_patients(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Patient)
            .where(
                Patient.national_id.between(
                    str(FAKE_PATIENT_NATIONAL_ID_BASE + 1),
                    str(FAKE_PATIENT_NATIONAL_ID_BASE + 999_999),
                )
            )
        )
        or 0
    )


def _count_fake_xrays(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(XrayImage)
            .where(XrayImage.image_path.like(f"{FAKE_XRAY_PATH_PREFIX}%"))
        )
        or 0
    )


def _count_fake_diagnoses(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DiagnosisResult)
            .join(XrayImage, DiagnosisResult.xray_image_id == XrayImage.id)
            .where(XrayImage.image_path.like(f"{FAKE_XRAY_PATH_PREFIX}%"))
        )
        or 0
    )


def _seed_doctors(db: Session) -> int:
    created = 0
    password_hash = get_password_hash(DOCTOR_PASSWORD)

    for index in range(1, TARGET_DOCTORS + 1):
        email = _fake_doctor_email(index)
        existing = db.scalar(select(Doctor).where(Doctor.email == email))
        if existing is not None:
            continue

        first_name = fake.first_name()
        last_name = fake.last_name()
        doctor = Doctor(
            full_name=f"Dr. {first_name} {last_name}",
            email=email,
            password_hash=password_hash,
            specialization=SPECIALIZATIONS[(index - 1) % len(SPECIALIZATIONS)],
            date_of_birth=fake.date_of_birth(minimum_age=30, maximum_age=65),
            national_id=_fake_doctor_national_id(index),
            certificate=f"CERT-FAKE-{index:05d}",
            phone_number=fake.numerify(text="09########"),
            governorate=random.choice(list(SyrianGovernorate)),
            area=fake.city(),
            role=DoctorRole.DOCTOR,
            status=DoctorStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(doctor)
        created += 1

    if created:
        db.commit()
    return created


def _seed_patients(db: Session, doctors: list[Doctor]) -> int:
    if not doctors:
        return 0

    created = 0
    next_index = _count_fake_patients(db) + 1

    while _count_fake_patients(db) < TARGET_PATIENTS:
        national_id = _fake_patient_national_id(next_index)
        existing = db.scalar(select(Patient).where(Patient.national_id == national_id))
        if existing is not None:
            next_index += 1
            continue

        doctor = doctors[(next_index - 1) % len(doctors)]
        gender = random.choice(list(Gender))
        if gender == Gender.MALE:
            first_name = fake.first_name_male()
        elif gender == Gender.FEMALE:
            first_name = fake.first_name_female()
        else:
            first_name = fake.first_name()

        father_name = fake.first_name_male()
        mother_name = fake.first_name_female()
        last_name = fake.last_name()

        patient = Patient(
            first_name=first_name,
            father_name=father_name,
            mother_name=mother_name,
            last_name=last_name,
            date_of_birth=fake.date_of_birth(minimum_age=1, maximum_age=90),
            gender=gender,
            phone_number=fake.numerify(text="09########"),
            governorate=random.choice(list(SyrianGovernorate)),
            area=fake.city(),
            national_id=national_id,
            created_by_doctor_id=doctor.id,
        )
        db.add(patient)
        db.commit()
        created += 1
        next_index += 1

    return created


def _list_fake_patients(db: Session) -> list[Patient]:
    return list(
        db.scalars(
            select(Patient)
            .where(
                Patient.national_id.between(
                    str(FAKE_PATIENT_NATIONAL_ID_BASE + 1),
                    str(FAKE_PATIENT_NATIONAL_ID_BASE + 999_999),
                )
            )
            .order_by(Patient.national_id.asc())
        ).all()
    )


def _seed_xrays(db: Session, patients: list[Patient]) -> int:
    if not patients:
        return 0

    created = 0
    next_index = _count_fake_xrays(db) + 1

    while _count_fake_xrays(db) < TARGET_XRAYS:
        image_path = _fake_xray_path(next_index)
        existing = db.scalar(select(XrayImage).where(XrayImage.image_path == image_path))
        if existing is not None:
            next_index += 1
            continue

        patient = patients[(next_index - 1) % len(patients)]
        taken_at = datetime.now(UTC) - timedelta(days=random.randint(1, 365))
        label = random.choice(DIAGNOSIS_LABELS)

        xray = XrayImage(
            patient_id=patient.id,
            doctor_id=patient.created_by_doctor_id,
            image_path=image_path,
            taken_at=taken_at,
            result=label,
            view_type=random.choice(list(XrayViewType)),
            notes=fake.sentence(nb_words=8),
        )
        db.add(xray)
        db.commit()
        created += 1
        next_index += 1

    return created


def _list_fake_xrays_without_diagnosis(db: Session) -> list[XrayImage]:
    return list(
        db.scalars(
            select(XrayImage)
            .outerjoin(DiagnosisResult, DiagnosisResult.xray_image_id == XrayImage.id)
            .where(
                XrayImage.image_path.like(f"{FAKE_XRAY_PATH_PREFIX}%"),
                DiagnosisResult.id.is_(None),
            )
            .order_by(XrayImage.image_path.asc())
        ).all()
    )


def _seed_diagnoses(db: Session) -> int:
    created = 0
    available_xrays = _list_fake_xrays_without_diagnosis(db)

    for xray in available_xrays:
        if _count_fake_diagnoses(db) >= TARGET_DIAGNOSES:
            break

        predicted_label = xray.result or random.choice(DIAGNOSIS_LABELS)
        confidence = Decimal(str(round(random.uniform(0.70, 0.98), 5)))

        diagnosis = DiagnosisResult(
            patient_id=xray.patient_id,
            doctor_id=xray.doctor_id,
            xray_image_id=xray.id,
            predicted_label=predicted_label,
            confidence_score=confidence,
            model_version=MODEL_VERSION,
            report_text=(
                f"Mock diagnosis for development: {predicted_label} "
                f"with confidence {confidence}."
            ),
            visual_map_path=None,
        )
        db.add(diagnosis)
        db.commit()
        created += 1

    return created


def seed_fake_data() -> None:
    """Create idempotent fake doctors, patients, x-rays, and diagnoses."""
    _print_warning()
    _ensure_not_production()

    settings = get_settings()
    print(f"Environment: {settings.environment}")
    print(f"Using database from project settings (DATABASE_URL / .env)")
    print(f"Doctor login password for seeded doctors: {DOCTOR_PASSWORD}")
    print()

    db = SessionLocal()
    try:
        _ensure_admin(db)

        doctors_created = _seed_doctors(db)
        doctors = _list_fake_doctors(db)
        if len(doctors) < TARGET_DOCTORS:
            raise RuntimeError(
                f"Expected at least {TARGET_DOCTORS} fake doctors, found {len(doctors)}"
            )

        patients_created = _seed_patients(db, doctors)
        patients = _list_fake_patients(db)

        xrays_created = _seed_xrays(db, patients)
        diagnoses_created = _seed_diagnoses(db)

        print()
        print("Fake data created successfully")
        print(f"Doctors created: {doctors_created}")
        print(f"Patients created: {patients_created}")
        print(f"X-ray records created: {xrays_created}")
        print(f"Diagnosis results created: {diagnoses_created}")
        print()
        print("Current fake totals:")
        print(f"  Fake doctors: {len(doctors)}")
        print(f"  Fake patients: {_count_fake_patients(db)}")
        print(f"  Fake x-rays: {_count_fake_xrays(db)}")
        print(f"  Fake diagnoses: {_count_fake_diagnoses(db)}")
        print()
        print("Example doctor login:")
        print(f"  email: {_fake_doctor_email(1)}")
        print(f"  password: {DOCTOR_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_fake_data()
