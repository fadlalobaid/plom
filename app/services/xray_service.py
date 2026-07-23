"""X-ray image upload and management business logic."""

import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.enums import XrayViewType
from app.models.patient import Patient
from app.models.xray_image import XrayImage
from app.schemas.xray_image import XrayImageUpdate
from app.services.patient_service import PatientNotFoundError, get_patient_by_id

ALLOWED_XRAY_EXTENSIONS = {".jpg", ".jpeg", ".png", ".dcm"}
XRAY_IMAGES_SUBDIR = "xray_images"


class XrayImageNotFoundError(Exception):
    """Raised when an X-ray image record cannot be found."""


class InvalidXrayFileError(Exception):
    """Raised when an uploaded file has an unsupported type."""


def get_xray_upload_directory() -> Path:
    """Return the directory used to store uploaded X-ray image files."""
    upload_directory = get_settings().upload_dir / XRAY_IMAGES_SUBDIR
    upload_directory.mkdir(parents=True, exist_ok=True)
    return upload_directory


def validate_xray_file(filename: str | None) -> str:
    """Validate the uploaded file extension and return the normalized suffix."""
    if not filename:
        raise InvalidXrayFileError("Uploaded file must include a filename")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_XRAY_EXTENSIONS:
        raise InvalidXrayFileError(
            "Unsupported file type. Allowed extensions: .jpg, .jpeg, .png, .dcm"
        )
    return extension


def save_xray_file(file: UploadFile) -> str:
    """Persist an uploaded X-ray file and return its relative storage path."""
    extension = validate_xray_file(file.filename)
    upload_directory = get_xray_upload_directory()
    stored_filename = f"{uuid4()}{extension}"
    destination = upload_directory / stored_filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return destination.as_posix()


def get_xray_image_by_id(
    db: Session,
    xray_image_id: UUID,
    doctor_id: UUID,
) -> XrayImage | None:
    """Return an X-ray image only when its patient belongs to the doctor."""
    return db.scalar(
        select(XrayImage)
        .join(Patient, XrayImage.patient_id == Patient.id)
        .where(
            XrayImage.id == xray_image_id,
            Patient.created_by_doctor_id == doctor_id,
        )
    )


def list_xray_images_by_patient(
    db: Session,
    patient_id: UUID,
    doctor_id: UUID,
) -> list[XrayImage]:
    """Return X-ray images only when the patient belongs to the doctor."""
    statement = (
        select(XrayImage)
        .options(selectinload(XrayImage.diagnosis_result))
        .join(Patient, XrayImage.patient_id == Patient.id)
        .where(
            XrayImage.patient_id == patient_id,
            Patient.created_by_doctor_id == doctor_id,
        )
        .order_by(XrayImage.uploaded_at.desc())
    )
    return list(db.scalars(statement).all())


def create_xray_image(
    db: Session,
    *,
    patient_id: UUID,
    doctor_id: UUID,
    image_path: str,
    view_type: XrayViewType,
    notes: str | None,
    taken_at: datetime | None,
) -> XrayImage:
    """Create a database record for an uploaded X-ray image."""
    if get_patient_by_id(db, patient_id, doctor_id) is None:
        raise PatientNotFoundError

    xray_image = XrayImage(
        patient_id=patient_id,
        doctor_id=doctor_id,
        image_path=image_path,
        taken_at=taken_at,
        view_type=view_type,
        notes=notes,
    )
    db.add(xray_image)
    db.commit()
    db.refresh(xray_image)
    return xray_image


def update_xray_image(
    db: Session,
    xray_image_id: UUID,
    payload: XrayImageUpdate,
    doctor_id: UUID,
) -> XrayImage:
    """Update an X-ray image whose patient belongs to the doctor."""
    xray_image = get_xray_image_by_id(db, xray_image_id, doctor_id)
    if xray_image is None:
        raise XrayImageNotFoundError

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(xray_image, field, value)

    db.commit()
    db.refresh(xray_image)
    return xray_image


def delete_xray_image(db: Session, xray_image_id: UUID, doctor_id: UUID) -> None:
    """Delete an X-ray image whose patient belongs to the doctor."""
    xray_image = get_xray_image_by_id(db, xray_image_id, doctor_id)
    if xray_image is None:
        raise XrayImageNotFoundError

    image_path = Path(xray_image.image_path)
    if image_path.is_file():
        image_path.unlink()

    db.delete(xray_image)
    db.commit()
