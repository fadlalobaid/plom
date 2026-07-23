"""Patient management business logic."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientNotFoundError(Exception):
    """Raised when a patient record cannot be found."""


class NationalIdAlreadyRegisteredError(Exception):
    """Raised when attempting to use a national ID that is already registered."""


def get_patient_by_id(
    db: Session,
    patient_id: UUID,
    doctor_id: UUID,
) -> Patient | None:
    """Return a patient only when it belongs to the specified doctor."""
    return db.scalar(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.created_by_doctor_id == doctor_id,
        )
    )


def get_patient_by_national_id(db: Session, national_id: str) -> Patient | None:
    """Return a patient by national ID, or None if not found."""
    return db.scalar(select(Patient).where(Patient.national_id == national_id))


def list_patients(
    db: Session,
    *,
    doctor_id: UUID,
    full_name: str | None = None,
    phone_number: str | None = None,
    national_id: str | None = None,
) -> list[Patient]:
    """Return the doctor's patients with optional search filters."""
    statement = (
        select(Patient)
        .where(Patient.created_by_doctor_id == doctor_id)
        .order_by(Patient.created_at.desc())
    )

    if full_name is not None:
        name_pattern = f"%{full_name}%"
        statement = statement.where(
            or_(
                Patient.full_name.ilike(name_pattern),
                Patient.first_name.ilike(name_pattern),
                Patient.father_name.ilike(name_pattern),
                Patient.mother_name.ilike(name_pattern),
                Patient.last_name.ilike(name_pattern),
            )
        )
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
        first_name=payload.first_name,
        father_name=payload.father_name,
        mother_name=payload.mother_name,
        last_name=payload.last_name,
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


def update_patient(
    db: Session,
    patient_id: UUID,
    payload: PatientUpdate,
    doctor_id: UUID,
) -> Patient:
    """Apply partial updates to a patient owned by the specified doctor."""
    patient = get_patient_by_id(db, patient_id, doctor_id)
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


def delete_patient(db: Session, patient_id: UUID, doctor_id: UUID) -> None:
    """Permanently delete a patient owned by the specified doctor."""
    patient = get_patient_by_id(db, patient_id, doctor_id)
    if patient is None:
        raise PatientNotFoundError

    db.delete(patient)
    db.commit()
