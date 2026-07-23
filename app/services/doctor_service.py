"""Doctor account management business logic."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, validate_password_strength
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus
from app.schemas.doctor import DoctorCreate, DoctorPasswordResetRequest, DoctorUpdate


class DoctorNotFoundError(Exception):
    """Raised when a doctor account cannot be found."""


class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to use an email that is already registered."""


class DoctorNationalIdAlreadyRegisteredError(Exception):
    """Raised when a doctor national ID is already registered."""


class InvalidDoctorPasswordResetError(Exception):
    """Raised when an administrator attempts to reset a non-doctor account."""


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
        must_change_password=True,
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
        if doctor.role != DoctorRole.DOCTOR:
            raise InvalidDoctorPasswordResetError
        password = validate_password_strength(update_data.pop("password"))
        doctor.password_hash = get_password_hash(password)
        doctor.must_change_password = True

    for field, value in update_data.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor


def reset_doctor_password(
    db: Session,
    doctor_id: UUID,
    payload: DoctorPasswordResetRequest,
) -> Doctor:
    """Assign a temporary password and require the doctor to replace it."""
    doctor = get_doctor_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError
    if doctor.role != DoctorRole.DOCTOR:
        raise InvalidDoctorPasswordResetError

    password = validate_password_strength(payload.new_password)
    doctor.password_hash = get_password_hash(password)
    doctor.must_change_password = True
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
