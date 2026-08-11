"""X-ray image upload and management API endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor, require_password_change_completed
from app.core import messages
from app.core.validators import validate_optional_notes
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import AuditAction, AuditEntityType, XrayViewType
from app.models.xray_image import XrayImage
from app.schemas.xray_image import (
    XrayImageResponse,
    XrayImageUpdate,
    XraySignedUrlResponse,
)
from app.services.audit_service import create_audit_log
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.xray_service import (
    InvalidXrayFileError,
    UnsupportedXrayMediaTypeError,
    XrayFileTooLargeError,
    XrayImageNotFoundError,
    XrayStorageError,
    delete_xray_image,
    get_xray_image_by_id,
    get_xray_signed_url,
    list_xray_images_by_patient,
    update_xray_image,
    upload_and_create_xray_image,
)
from app.services.xray_validation_service import (
    XrayValidationError,
    XrayValidationReason,
)

router = APIRouter(
    prefix="/xray-images",
    tags=["xray-images"],
    dependencies=[Depends(require_password_change_completed)],
)


@router.post("/upload", response_model=XrayImageResponse, status_code=status.HTTP_201_CREATED)
def upload_xray_image(
    patient_id: Annotated[UUID, Form(description="Patient UUID")],
    view_type: Annotated[XrayViewType, Form(description="Chest X-ray view type")],
    file: Annotated[UploadFile, File(description="Chest X-ray image file")],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
    notes: Annotated[str | None, Form(description="Optional notes")] = None,
    taken_at: Annotated[
        datetime | None,
        Form(description="When the medical X-ray was captured"),
    ] = None,
) -> XrayImage:
    """Upload a chest X-ray image for a patient to private Supabase Storage."""
    if get_patient_by_id(db, patient_id, current_doctor.id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.PATIENT_NOT_FOUND,
        )

    try:
        cleaned_notes = validate_optional_notes(notes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        xray_image = upload_and_create_xray_image(
            db,
            patient_id=patient_id,
            doctor_id=current_doctor.id,
            file=file,
            view_type=view_type,
            notes=cleaned_notes,
            taken_at=taken_at,
        )
    except UnsupportedXrayMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=messages.INVALID_CHEST_XRAY,
        ) from exc
    except XrayFileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc) or messages.INVALID_CHEST_XRAY,
        ) from exc
    except XrayValidationError as exc:
        if exc.reason == XrayValidationReason.VALIDATOR_UNAVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=exc.public_detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.public_detail,
        ) from exc
    except InvalidXrayFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc) or messages.INVALID_CHEST_XRAY,
        ) from exc
    except XrayStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or messages.XRAY_STORAGE_UNAVAILABLE,
        ) from exc
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.PATIENT_NOT_FOUND,
        ) from exc

    create_audit_log(
        db,
        action=AuditAction.UPLOAD_XRAY,
        user_id=current_doctor.id,
        entity_type=AuditEntityType.XRAY_IMAGE,
        entity_id=xray_image.id,
        details={
            "result": "success",
            "patient_id": str(patient_id),
            "xray_image_id": str(xray_image.id),
            "storage_path": xray_image.image_path,
            "file_extension": Path(xray_image.image_path).suffix.lower(),
            "view_type": view_type.value,
        },
        request=request,
    )
    return xray_image


@router.get("/patient/{patient_id}", response_model=list[XrayImageResponse])
def get_patient_xray_images(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> list[XrayImage]:
    """List all X-ray images uploaded for a patient."""
    if get_patient_by_id(db, patient_id, current_doctor.id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.PATIENT_NOT_FOUND,
        )
    return list_xray_images_by_patient(db, patient_id, current_doctor.id)


@router.get("/{xray_image_id}/signed-url", response_model=XraySignedUrlResponse)
def get_xray_image_signed_url(
    xray_image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> XraySignedUrlResponse:
    """Return a temporary signed URL for a private X-ray object."""
    try:
        signed_url, expires_in = get_xray_signed_url(
            db,
            xray_image_id,
            current_doctor.id,
        )
    except XrayImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.XRAY_NOT_FOUND,
        ) from exc
    except XrayStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or messages.XRAY_STORAGE_UNAVAILABLE,
        ) from exc

    return XraySignedUrlResponse(signed_url=signed_url, expires_in=expires_in)


@router.get("/{xray_image_id}", response_model=XrayImageResponse)
def get_xray_image_record(
    xray_image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> XrayImage:
    """Retrieve an X-ray image record by ID."""
    xray_image = get_xray_image_by_id(db, xray_image_id, current_doctor.id)
    if xray_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.XRAY_NOT_FOUND,
        )
    return xray_image


@router.patch("/{xray_image_id}", response_model=XrayImageResponse)
def update_xray_image_record(
    xray_image_id: UUID,
    payload: XrayImageUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> XrayImage:
    """Update X-ray image metadata."""
    try:
        return update_xray_image(db, xray_image_id, payload, current_doctor.id)
    except XrayImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.XRAY_NOT_FOUND,
        ) from exc


@router.delete("/{xray_image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_xray_image_record(
    xray_image_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
) -> None:
    """Delete an X-ray image record and its stored file from Supabase."""
    try:
        storage_path = delete_xray_image(db, xray_image_id, current_doctor.id)
    except XrayImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.XRAY_NOT_FOUND,
        ) from exc
    except XrayStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or messages.XRAY_STORAGE_UNAVAILABLE,
        ) from exc

    create_audit_log(
        db,
        action=AuditAction.DELETE_XRAY,
        user_id=current_doctor.id,
        entity_type=AuditEntityType.XRAY_IMAGE,
        entity_id=xray_image_id,
        details={
            "result": "success",
            "xray_image_id": str(xray_image_id),
            "storage_path": storage_path,
            "file_extension": Path(storage_path).suffix.lower(),
        },
        request=request,
    )
