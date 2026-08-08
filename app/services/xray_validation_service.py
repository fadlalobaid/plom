"""Layered chest X-ray upload validation gate (separate from disease AI)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path

from app.ai.xray_validator import (
    ContentValidationResult,
    ValidatorUnavailableError,
    validate_chest_xray_content,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

PUBLIC_INVALID_XRAY_DETAIL = (
    "الصورة المرفوعة ليست صورة أشعة صدر صالحة للتحليل."
)

ALLOWED_XRAY_EXTENSIONS = {".jpg", ".jpeg", ".png", ".dcm"}
ALLOWED_XRAY_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/dicom",
    "application/octet-stream",
}
EXTENSION_CONTENT_TYPE_MAP = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".dcm": {"application/dicom", "application/octet-stream"},
}

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_DICOM_MAGIC = b"DICM"
_MIN_IMAGE_DIMENSION = 32
_MAX_IMAGE_DIMENSION = 8192


class XrayValidationReason(str, Enum):
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CORRUPTED_IMAGE = "CORRUPTED_IMAGE"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    INVALID_DICOM = "INVALID_DICOM"
    NOT_CHEST_XRAY = "NOT_CHEST_XRAY"
    VALIDATOR_UNAVAILABLE = "VALIDATOR_UNAVAILABLE"
    VALIDATOR_INFERENCE_ERROR = "VALIDATOR_INFERENCE_ERROR"


class XrayValidationError(Exception):
    """Raised when an uploaded file fails the X-ray validation gate."""

    def __init__(
        self,
        reason: XrayValidationReason,
        message: str,
        *,
        public_detail: str | None = None,
    ) -> None:
        self.reason = reason
        self.message = message
        self.public_detail = public_detail or PUBLIC_INVALID_XRAY_DETAIL
        super().__init__(message)


@dataclass(frozen=True)
class XrayValidationResult:
    """Accepted upload after layered validation."""

    file_bytes: bytes
    extension: str
    content_type: str
    width: int | None
    height: int | None
    content_validation: ContentValidationResult


def validate_xray_upload(
    *,
    filename: str | None,
    content_type: str | None,
    file_bytes: bytes,
) -> XrayValidationResult:
    """Run file-type, size, integrity, optional DICOM, and content gates."""
    started = time.perf_counter()
    extension = _validate_declared_type(filename, content_type)
    normalized_content_type = (content_type or "").split(";")[0].strip().lower()

    _validate_size(file_bytes)
    _validate_magic_bytes(file_bytes, extension)

    width: int | None = None
    height: int | None = None
    if extension in {".jpg", ".jpeg", ".png"}:
        width, height = _validate_raster_integrity(file_bytes, extension)
    else:
        _validate_dicom_container(file_bytes)

    try:
        content_result = validate_chest_xray_content(
            file_bytes=file_bytes,
            extension=extension,
        )
    except ValidatorUnavailableError as exc:
        logger.error(
            "xray_validation rejected reason=%s stage=content_validator",
            XrayValidationReason.VALIDATOR_UNAVAILABLE.value,
        )
        raise XrayValidationError(
            XrayValidationReason.VALIDATOR_UNAVAILABLE,
            str(exc),
            public_detail="تعذر التحقق من صلاحية صورة الأشعة حالياً. حاول لاحقاً.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "xray_validation rejected reason=%s stage=content_validator",
            XrayValidationReason.VALIDATOR_INFERENCE_ERROR.value,
        )
        raise XrayValidationError(
            XrayValidationReason.VALIDATOR_INFERENCE_ERROR,
            "Chest X-ray content validator failed",
            public_detail="تعذر التحقق من صلاحية صورة الأشعة حالياً. حاول لاحقاً.",
        ) from exc

    if content_result.status == "rejected" or content_result.is_chest_xray is False:
        logger.info(
            "xray_validation rejected reason=%s mime=%s dims=%sx%s confidence=%s",
            XrayValidationReason.NOT_CHEST_XRAY.value,
            normalized_content_type,
            width,
            height,
            content_result.confidence,
        )
        raise XrayValidationError(
            XrayValidationReason.NOT_CHEST_XRAY,
            "Uploaded image is not a suitable chest X-ray for analysis",
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "xray_validation accepted stage=complete mime=%s extension=%s "
        "dims=%sx%s bytes=%s content_status=%s duration_ms=%s",
        normalized_content_type,
        extension,
        width,
        height,
        len(file_bytes),
        content_result.status,
        elapsed_ms,
    )
    return XrayValidationResult(
        file_bytes=file_bytes,
        extension=extension,
        content_type=normalized_content_type,
        width=width,
        height=height,
        content_validation=content_result,
    )


def _validate_declared_type(filename: str | None, content_type: str | None) -> str:
    if not filename:
        raise XrayValidationError(
            XrayValidationReason.INVALID_FILE_TYPE,
            "Uploaded file must include a filename",
        )

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_XRAY_EXTENSIONS:
        raise XrayValidationError(
            XrayValidationReason.INVALID_FILE_TYPE,
            "Unsupported file type. Allowed extensions: .jpg, .jpeg, .png, .dcm",
        )

    normalized_content_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_content_type not in ALLOWED_XRAY_CONTENT_TYPES:
        raise XrayValidationError(
            XrayValidationReason.INVALID_FILE_TYPE,
            "Unsupported media type. Allowed types: image/jpeg, image/png, application/dicom",
        )

    allowed_for_extension = EXTENSION_CONTENT_TYPE_MAP[extension]
    if normalized_content_type not in allowed_for_extension:
        raise XrayValidationError(
            XrayValidationReason.INVALID_FILE_TYPE,
            "File extension does not match the declared media type",
        )
    return extension


def _validate_size(file_bytes: bytes) -> None:
    max_bytes = get_settings().max_xray_upload_bytes
    if len(file_bytes) == 0:
        raise XrayValidationError(
            XrayValidationReason.INVALID_FILE_TYPE,
            "Uploaded file is empty",
        )
    if len(file_bytes) > max_bytes:
        raise XrayValidationError(
            XrayValidationReason.FILE_TOO_LARGE,
            f"File exceeds the maximum allowed size of {max_bytes} bytes",
            public_detail=f"حجم الملف يتجاوز الحد الأقصى المسموح ({max_bytes} بايت).",
        )


def _validate_magic_bytes(file_bytes: bytes, extension: str) -> None:
    if extension in {".jpg", ".jpeg"}:
        if not file_bytes.startswith(_JPEG_MAGIC):
            raise XrayValidationError(
                XrayValidationReason.CORRUPTED_IMAGE,
                "File content is not a valid JPEG image",
            )
        return
    if extension == ".png":
        if not file_bytes.startswith(_PNG_MAGIC):
            raise XrayValidationError(
                XrayValidationReason.CORRUPTED_IMAGE,
                "File content is not a valid PNG image",
            )
        return
    if extension == ".dcm":
        if len(file_bytes) < 132 or file_bytes[128:132] != _DICOM_MAGIC:
            raise XrayValidationError(
                XrayValidationReason.INVALID_DICOM,
                "File content is not a valid DICOM container",
            )
        return
    raise XrayValidationError(
        XrayValidationReason.UNSUPPORTED_IMAGE,
        f"Unsupported image extension for integrity checks: {extension}",
    )


def _validate_raster_integrity(file_bytes: bytes, extension: str) -> tuple[int, int]:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise XrayValidationError(
            XrayValidationReason.VALIDATOR_UNAVAILABLE,
            "Pillow is required for image integrity validation",
            public_detail="تعذر التحقق من صلاحية صورة الأشعة حالياً. حاول لاحقاً.",
        ) from exc

    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(file_bytes)) as image:
            image.load()
            width, height = image.size
            detected_format = (image.format or "").upper()
    except UnidentifiedImageError as exc:
        raise XrayValidationError(
            XrayValidationReason.CORRUPTED_IMAGE,
            "Uploaded image could not be decoded",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise XrayValidationError(
            XrayValidationReason.CORRUPTED_IMAGE,
            "Uploaded image is truncated or corrupt",
        ) from exc

    expected_format = {"JPEG"} if extension in {".jpg", ".jpeg"} else {"PNG"}
    if detected_format not in expected_format:
        raise XrayValidationError(
            XrayValidationReason.CORRUPTED_IMAGE,
            "Decoded image format does not match the declared file type",
        )

    if width < _MIN_IMAGE_DIMENSION or height < _MIN_IMAGE_DIMENSION:
        raise XrayValidationError(
            XrayValidationReason.UNSUPPORTED_IMAGE,
            "Image dimensions are too small for chest X-ray analysis",
        )
    if width > _MAX_IMAGE_DIMENSION or height > _MAX_IMAGE_DIMENSION:
        raise XrayValidationError(
            XrayValidationReason.UNSUPPORTED_IMAGE,
            "Image dimensions exceed the supported maximum",
        )
    return int(width), int(height)


def _validate_dicom_container(file_bytes: bytes) -> None:
    """Validate DICOM preamble/magic; optional soft metadata if pydicom exists."""
    if len(file_bytes) < 132 or file_bytes[128:132] != _DICOM_MAGIC:
        raise XrayValidationError(
            XrayValidationReason.INVALID_DICOM,
            "File content is not a valid DICOM container",
        )

    try:
        import pydicom  # type: ignore[import-untyped]
    except ImportError:
        logger.info(
            "xray_validation dicom_metadata=skipped reason=pydicom_not_installed"
        )
        return

    try:
        dataset = pydicom.dcmread(BytesIO(file_bytes), force=True, stop_before_pixels=True)
    except Exception:  # noqa: BLE001
        # Magic already validated the container. Missing/broken optional metadata
        # must not reject the file by itself.
        logger.info(
            "xray_validation dicom_metadata=skipped reason=unreadable_optional_tags"
        )
        return

    modality = str(getattr(dataset, "Modality", "") or "").upper().strip()
    # Soft signal only when modality is present and clearly non-radiography.
    if modality in {"CT", "MR", "US", "MG", "PT", "NM"}:
        raise XrayValidationError(
            XrayValidationReason.INVALID_DICOM,
            f"DICOM modality {modality} is not an accepted chest radiograph modality",
        )

    body_part = str(getattr(dataset, "BodyPartExamined", "") or "").upper()
    study = str(getattr(dataset, "StudyDescription", "") or "").upper()
    series = str(getattr(dataset, "SeriesDescription", "") or "").upper()
    chest_hint = any("CHEST" in value for value in (body_part, study, series) if value)
    logger.info(
        "xray_validation dicom_metadata modality=%s body_part=%s chest_hint=%s",
        modality or None,
        body_part or None,
        chest_hint,
    )
