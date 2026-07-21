"""X-ray image upload and management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_doctor
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.enums import XrayViewType
from app.models.xray_image import XrayImage
from app.schemas.xray_image import XrayImageResponse, XrayImageUpdate
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.xray_service import (
    InvalidXrayFileError,
    XrayImageNotFoundError,
    create_xray_image,
    delete_xray_image,
    get_xray_image_by_id,
    list_xray_images_by_patient,
    save_xray_file,
    update_xray_image,
)

router = APIRouter(
    prefix="/xray-images",
    tags=["xray-images"],
    dependencies=[Depends(get_current_active_doctor)],
)


@router.post("/upload", response_model=XrayImageResponse, status_code=status.HTTP_201_CREATED)
def upload_xray_image(
    patient_id: Annotated[UUID, Form(description="Patient UUID")],
    view_type: Annotated[XrayViewType, Form(description="Chest X-ray view type")],
    file: Annotated[UploadFile, File(description="Chest X-ray image file")],
    db: Annotated[Session, Depends(get_db)],
    current_doctor: Annotated[Doctor, Depends(get_current_active_doctor)],
    notes: Annotated[str | None, Form(description="Optional notes")] = None,
) -> XrayImage:
    """Upload a chest X-ray image for a patient."""
    if get_patient_by_id(db, patient_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    try:
        image_path = save_xray_file(file)
        return create_xray_image(
            db,
            patient_id=patient_id,
            doctor_id=current_doctor.id,
            image_path=image_path,
            view_type=view_type,
            notes=notes,
        )
    except InvalidXrayFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        ) from exc


@router.get("/patient/{patient_id}", response_model=list[XrayImageResponse])
def get_patient_xray_images(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[XrayImage]:
    """List all X-ray images uploaded for a patient."""
    if get_patient_by_id(db, patient_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return list_xray_images_by_patient(db, patient_id)


@router.get("/{xray_image_id}", response_model=XrayImageResponse)
def get_xray_image_record(
    xray_image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> XrayImage:
    """Retrieve an X-ray image record by ID."""
    xray_image = get_xray_image_by_id(db, xray_image_id)
    if xray_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-ray image not found",
        )
    return xray_image


@router.patch("/{xray_image_id}", response_model=XrayImageResponse)
def update_xray_image_record(
    xray_image_id: UUID,
    payload: XrayImageUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> XrayImage:
    """Update X-ray image metadata."""
    try:
        return update_xray_image(db, xray_image_id, payload)
    except XrayImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-ray image not found",
        ) from exc


@router.delete("/{xray_image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_xray_image_record(
    xray_image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an X-ray image record and its stored file."""
    try:
        delete_xray_image(db, xray_image_id)
    except XrayImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-ray image not found",
        ) from exc
