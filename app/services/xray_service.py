"""X-ray image upload and management business logic."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.enums import XrayViewType
from app.models.patient import Patient
from app.models.xray_image import XrayImage
from app.schemas.xray_image import XrayImageUpdate
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.storage_service import (
    StorageDeleteError,
    StorageError,
    StorageUploadError,
    create_signed_xray_url,
    delete_xray_file,
    upload_xray_file,
)
from app.services.xray_validation_service import (
    ALLOWED_XRAY_CONTENT_TYPES,
    ALLOWED_XRAY_EXTENSIONS,
    EXTENSION_CONTENT_TYPE_MAP,
    XrayValidationError,
    XrayValidationReason,
    validate_xray_upload,
)

logger = logging.getLogger(__name__)

_READ_CHUNK_SIZE = 1024 * 1024

# Re-export constants for existing imports/tests.
__all__ = [
    "ALLOWED_XRAY_CONTENT_TYPES",
    "ALLOWED_XRAY_EXTENSIONS",
    "EXTENSION_CONTENT_TYPE_MAP",
    "InvalidXrayFileError",
    "UnsupportedXrayMediaTypeError",
    "XrayFileTooLargeError",
    "XrayImageNotFoundError",
    "XrayStorageError",
    "XrayValidationError",
    "create_xray_image",
    "delete_xray_image",
    "get_xray_image_by_id",
    "get_xray_signed_url",
    "list_xray_images_by_patient",
    "read_validated_xray_bytes",
    "update_xray_image",
    "upload_and_create_xray_image",
    "validate_xray_file",
]


class XrayImageNotFoundError(Exception):
    """Raised when an X-ray image record cannot be found."""


class InvalidXrayFileError(Exception):
    """Raised when an uploaded file fails validation."""


class UnsupportedXrayMediaTypeError(InvalidXrayFileError):
    """Raised when an uploaded file has an unsupported media type."""


class XrayFileTooLargeError(InvalidXrayFileError):
    """Raised when an uploaded file exceeds the configured size limit."""


class XrayStorageError(Exception):
    """Raised when Supabase Storage operations fail for an X-ray file."""


def validate_xray_file(filename: str | None, content_type: str | None) -> str:
    """Validate filename extension and MIME type, returning the normalized suffix."""
    try:
        from app.services.xray_validation_service import _validate_declared_type

        return _validate_declared_type(filename, content_type)
    except XrayValidationError as exc:
        _raise_legacy_validation_error(exc)
        raise  # pragma: no cover


def read_validated_xray_bytes(file: UploadFile) -> tuple[bytes, str, str]:
    """Validate type/size/integrity/content gate and return file payload."""
    chunks: list[bytes] = []
    total_bytes = 0
    max_bytes = get_settings().max_xray_upload_bytes
    try:
        while True:
            chunk = file.file.read(_READ_CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise XrayFileTooLargeError(
                    f"File exceeds the maximum allowed size of {max_bytes} bytes"
                )
            chunks.append(chunk)
    finally:
        file.file.seek(0)

    file_bytes = b"".join(chunks)
    try:
        result = validate_xray_upload(
            filename=file.filename,
            content_type=file.content_type,
            file_bytes=file_bytes,
        )
    except XrayValidationError as exc:
        _raise_legacy_validation_error(exc)

    return result.file_bytes, result.extension, result.content_type


def _raise_legacy_validation_error(exc: XrayValidationError) -> None:
    """Map validation-service errors to legacy xray_service exceptions."""
    if exc.reason == XrayValidationReason.FILE_TOO_LARGE:
        raise XrayFileTooLargeError(exc.message) from exc
    if exc.reason == XrayValidationReason.INVALID_FILE_TYPE:
        raise UnsupportedXrayMediaTypeError(exc.message) from exc
    # Preserve structured reasons needed by the API layer (e.g. 503).
    if exc.reason in {
        XrayValidationReason.VALIDATOR_UNAVAILABLE,
        XrayValidationReason.VALIDATOR_INFERENCE_ERROR,
        XrayValidationReason.NOT_CHEST_XRAY,
    }:
        raise exc
    raise InvalidXrayFileError(exc.public_detail) from exc


def _is_legacy_local_path(image_path: str) -> bool:
    return image_path.startswith("uploads/") or Path(image_path).is_absolute()


def _remove_stored_xray_file(image_path: str) -> None:
    """Remove a stored X-ray from Supabase, with legacy local-path fallback."""
    if _is_legacy_local_path(image_path):
        local_path = Path(image_path)
        if local_path.is_file():
            local_path.unlink()
        return
    delete_xray_file(image_path)


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


def upload_and_create_xray_image(
    db: Session,
    *,
    patient_id: UUID,
    doctor_id: UUID,
    file: UploadFile,
    view_type: XrayViewType,
    notes: str | None,
    taken_at: datetime | None,
) -> XrayImage:
    """Validate gate first, then upload to Supabase Storage and persist."""
    if get_patient_by_id(db, patient_id, doctor_id) is None:
        raise PatientNotFoundError

    # Validation happens BEFORE storage/DB so rejected files never remain stored.
    file_bytes, extension, content_type = read_validated_xray_bytes(file)

    try:
        storage_path = upload_xray_file(
            doctor_id=doctor_id,
            patient_id=patient_id,
            file_bytes=file_bytes,
            extension=extension,
            content_type=content_type,
        )
    except StorageUploadError as exc:
        raise XrayStorageError("Failed to upload X-ray file to storage") from exc
    except StorageError as exc:
        raise XrayStorageError("X-ray storage is unavailable") from exc

    try:
        return create_xray_image(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            image_path=storage_path,
            view_type=view_type,
            notes=notes,
            taken_at=taken_at,
        )
    except Exception:
        try:
            delete_xray_file(storage_path)
        except Exception:
            logger.exception(
                "Failed to delete orphaned X-ray object after database error: %s",
                storage_path,
            )
        raise


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


def delete_xray_image(db: Session, xray_image_id: UUID, doctor_id: UUID) -> str:
    """Delete storage object then database record. Returns the storage path."""
    xray_image = get_xray_image_by_id(db, xray_image_id, doctor_id)
    if xray_image is None:
        raise XrayImageNotFoundError

    storage_path = xray_image.image_path

    try:
        _remove_stored_xray_file(storage_path)
    except StorageDeleteError as exc:
        raise XrayStorageError("Failed to delete X-ray file from storage") from exc
    except StorageError as exc:
        raise XrayStorageError("X-ray storage is unavailable") from exc

    db.delete(xray_image)
    db.commit()
    return storage_path


def get_xray_signed_url(
    db: Session,
    xray_image_id: UUID,
    doctor_id: UUID,
) -> tuple[str, int]:
    """Return a temporary signed URL when the doctor owns the X-ray patient."""
    xray_image = get_xray_image_by_id(db, xray_image_id, doctor_id)
    if xray_image is None:
        raise XrayImageNotFoundError

    if _is_legacy_local_path(xray_image.image_path):
        raise XrayStorageError("Legacy local X-ray files cannot be signed")

    expires_in = get_settings().supabase_signed_url_expire_seconds
    try:
        signed_url = create_signed_xray_url(
            xray_image.image_path,
            expires_in=expires_in,
        )
    except StorageError as exc:
        raise XrayStorageError("Failed to create signed URL") from exc
    return signed_url, expires_in
