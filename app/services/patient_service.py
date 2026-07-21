"""Patient management business logic."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientNotFoundError(Exception):
    """Raised when a patient record cannot be found."""


class NationalIdAlreadyRegisteredError(Exception):
    """Raised when attempting to use a national ID that is already registered."""


def get_patient_by_id(db: Session, patient_id: UUID) -> Patient | None:
    """Return a patient by primary key, or None if not found."""
    return db.get(Patient, patient_id)


def get_patient_by_national_id(db: Session, national_id: str) -> Patient | None:
    """Return a patient by national ID, or None if not found."""
    return db.scalar(select(Patient).where(Patient.national_id == national_id))


def list_patients(
    db: Session,
    *,
    full_name: str | None = None,
    phone_number: str | None = None,
    national_id: str | None = None,
) -> list[Patient]:
    """Return patients ordered by creation time with optional search filters."""
    statement = select(Patient).order_by(Patient.created_at.desc())

    if full_name is not None:
        statement = statement.where(Patient.full_name.ilike(f"%{full_name}%"))
    if phone_number is not None:
        statement = statement.where(Patient.phone_number.ilike(f"%{phone_number}%"))
    if national_id is not None:
        statement = statement.where(Patient.national_id.ilike(f"%{national_id}%"))

    return list(db.scalars(statement).all())


def create_patient(
    db: Session,
    payload: PatientCreate,
    created_by_doctor_id: UUID,
) -> Patient:
    """Create a new patient record linked to the authenticated doctor."""
    if get_patient_by_national_id(db, payload.national_id) is not None:
        raise NationalIdAlreadyRegisteredError

    patient = Patient(
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        phone_number=payload.phone_number,
        address=payload.address,
        national_id=payload.national_id,
        created_by_doctor_id=created_by_doctor_id,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient_id: UUID, payload: PatientUpdate) -> Patient:
    """Apply partial updates to an existing patient record."""
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise PatientNotFoundError

    update_data = payload.model_dump(exclude_unset=True)

    if "national_id" in update_data and update_data["national_id"] != patient.national_id:
        existing_patient = get_patient_by_national_id(db, update_data["national_id"])
        if existing_patient is not None and existing_patient.id != patient.id:
            raise NationalIdAlreadyRegisteredError

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient_id: UUID) -> None:
    """Permanently delete a patient record."""
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise PatientNotFoundError

    db.delete(patient)
    db.commit()
