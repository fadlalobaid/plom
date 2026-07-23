"""Doctor account management business logic."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus
from app.schemas.doctor import DoctorCreate, DoctorUpdate


class DoctorNotFoundError(Exception):
    """Raised when a doctor account cannot be found."""


class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to use an email that is already registered."""


class DoctorNationalIdAlreadyRegisteredError(Exception):
    """Raised when a doctor national ID is already registered."""


def get_doctor_by_id(db: Session, doctor_id: UUID) -> Doctor | None:
    """Return a doctor by primary key, or None if not found."""
    return db.get(Doctor, doctor_id)


def get_doctor_by_email(db: Session, email: str) -> Doctor | None:
    """Return a doctor by email address, or None if not found."""
    return db.scalar(select(Doctor).where(Doctor.email == email))


def get_doctor_by_national_id(db: Session, national_id: str) -> Doctor | None:
    """Return a doctor by national ID, or None if not found."""
    return db.scalar(select(Doctor).where(Doctor.national_id == national_id))


def list_doctors(db: Session) -> list[Doctor]:
    """Return all doctor accounts ordered by creation time."""
    return list(db.scalars(select(Doctor).order_by(Doctor.created_at.desc())).all())


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    """Create a new doctor account with role set to doctor."""
    if get_doctor_by_email(db, payload.email) is not None:
        raise EmailAlreadyRegisteredError
    if (
        payload.national_id is not None
        and get_doctor_by_national_id(db, payload.national_id) is not None
    ):
        raise DoctorNationalIdAlreadyRegisteredError

    doctor = Doctor(
        full_name=payload.full_name,
        email=payload.email,
        specialization=payload.specialization,
        date_of_birth=payload.date_of_birth,
        national_id=payload.national_id,
        certificate=payload.certificate,
        phone_number=payload.phone_number,
        password_hash=get_password_hash(payload.password),
        role=DoctorRole.DOCTOR,
        status=DoctorStatus.ACTIVE,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def update_doctor(db: Session, doctor_id: UUID, payload: DoctorUpdate) -> Doctor:
    """Apply partial updates to an existing doctor account."""
    doctor = get_doctor_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != doctor.email:
        existing_doctor = get_doctor_by_email(db, update_data["email"])
        if existing_doctor is not None and existing_doctor.id != doctor.id:
            raise EmailAlreadyRegisteredError

    if (
        "national_id" in update_data
        and update_data["national_id"] is not None
        and update_data["national_id"] != doctor.national_id
    ):
        existing_doctor = get_doctor_by_national_id(db, update_data["national_id"])
        if existing_doctor is not None and existing_doctor.id != doctor.id:
            raise DoctorNationalIdAlreadyRegisteredError

    if "password" in update_data:
        doctor.password_hash = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor


def deactivate_doctor(db: Session, doctor_id: UUID) -> Doctor:
    """Soft-delete a doctor account by marking it inactive."""
    doctor = get_doctor_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError

    doctor.status = DoctorStatus.INACTIVE
    db.commit()
    db.refresh(doctor)
    return doctor
