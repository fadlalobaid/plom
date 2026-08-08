"""Focused tests for the chest X-ray upload validation gate."""

from __future__ import annotations

import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from app.ai.xray_validator import is_content_validator_available
from app.core.config import get_settings
from app.services.xray_validation_service import (
    XrayValidationError,
    XrayValidationReason,
    validate_xray_upload,
)


def _png_bytes(size: tuple[int, int] = (64, 64), color: tuple[int, ...] = (20, 20, 20)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes(size: tuple[int, int] = (64, 64), color: tuple[int, ...] = (20, 20, 20)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _minimal_dicom_bytes() -> bytes:
    # 128-byte preamble + DICM magic. Enough for container magic validation.
    return (b"\x00" * 128) + b"DICM" + b"\x00" * 64


class FileValidationTests(unittest.TestCase):
    def test_valid_png_is_accepted(self) -> None:
        result = validate_xray_upload(
            filename="scan.png",
            content_type="image/png",
            file_bytes=_png_bytes(),
        )
        self.assertEqual(result.extension, ".png")
        self.assertEqual(result.width, 64)
        self.assertEqual(result.height, 64)
        self.assertEqual(result.content_validation.status, "skipped")

    def test_valid_jpeg_is_accepted(self) -> None:
        result = validate_xray_upload(
            filename="scan.jpg",
            content_type="image/jpeg",
            file_bytes=_jpeg_bytes(),
        )
        self.assertEqual(result.extension, ".jpg")
        self.assertEqual(result.content_type, "image/jpeg")

    def test_valid_dicom_magic_is_accepted(self) -> None:
        result = validate_xray_upload(
            filename="scan.dcm",
            content_type="application/dicom",
            file_bytes=_minimal_dicom_bytes(),
        )
        self.assertEqual(result.extension, ".dcm")

    def test_txt_renamed_to_jpg_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="image.jpg",
                content_type="image/jpeg",
                file_bytes=b"this is not an image",
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.CORRUPTED_IMAGE)

    def test_random_binary_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="scan.png",
                content_type="image/png",
                file_bytes=b"\x00\x01\x02\x03random-binary",
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.CORRUPTED_IMAGE)

    def test_corrupted_jpeg_is_rejected(self) -> None:
        bad = _jpeg_bytes()[:20] + bytes([0xFF, 0xFF])
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="broken.jpg",
                content_type="image/jpeg",
                file_bytes=bad,
            )
        self.assertIn(
            ctx.exception.reason,
            {
                XrayValidationReason.CORRUPTED_IMAGE,
                XrayValidationReason.UNSUPPORTED_IMAGE,
            },
        )

    def test_corrupted_png_is_rejected(self) -> None:
        bad = _png_bytes()[:16] + b"XXXX"
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="broken.png",
                content_type="image/png",
                file_bytes=bad,
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.CORRUPTED_IMAGE)

    def test_zero_byte_file_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="empty.jpg",
                content_type="image/jpeg",
                file_bytes=b"",
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.INVALID_FILE_TYPE)

    def test_unsupported_extension_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="notes.txt",
                content_type="text/plain",
                file_bytes=b"hello",
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.INVALID_FILE_TYPE)

    def test_mime_mismatch_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="scan.png",
                content_type="image/jpeg",
                file_bytes=_png_bytes(),
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.INVALID_FILE_TYPE)

    def test_oversized_file_is_rejected(self) -> None:
        settings = get_settings()
        original = settings.max_xray_upload_bytes
        settings.max_xray_upload_bytes = 32
        try:
            with self.assertRaises(XrayValidationError) as ctx:
                validate_xray_upload(
                    filename="big.png",
                    content_type="image/png",
                    file_bytes=_png_bytes(size=(128, 128)),
                )
            self.assertEqual(ctx.exception.reason, XrayValidationReason.FILE_TOO_LARGE)
        finally:
            settings.max_xray_upload_bytes = original

    def test_tiny_image_is_rejected(self) -> None:
        with self.assertRaises(XrayValidationError) as ctx:
            validate_xray_upload(
                filename="tiny.png",
                content_type="image/png",
                file_bytes=_png_bytes(size=(8, 8)),
            )
        self.assertEqual(ctx.exception.reason, XrayValidationReason.UNSUPPORTED_IMAGE)


class ContentValidatorGateTests(unittest.TestCase):
    def test_no_dedicated_validator_model_exists(self) -> None:
        self.assertFalse(is_content_validator_available())

    def test_strict_content_validation_fails_closed_when_model_missing(self) -> None:
        settings = get_settings()
        original = settings.xray_content_validation_enabled
        settings.xray_content_validation_enabled = True
        try:
            with self.assertRaises(XrayValidationError) as ctx:
                validate_xray_upload(
                    filename="scan.png",
                    content_type="image/png",
                    file_bytes=_png_bytes(),
                )
            self.assertEqual(
                ctx.exception.reason,
                XrayValidationReason.VALIDATOR_UNAVAILABLE,
            )
        finally:
            settings.xray_content_validation_enabled = original

    def test_content_validation_disabled_skips_model_stage(self) -> None:
        settings = get_settings()
        original = settings.xray_content_validation_enabled
        settings.xray_content_validation_enabled = False
        try:
            result = validate_xray_upload(
                filename="scan.jpg",
                content_type="image/jpeg",
                file_bytes=_jpeg_bytes(),
            )
            self.assertEqual(result.content_validation.status, "skipped")
            self.assertIsNone(result.content_validation.is_chest_xray)
        finally:
            settings.xray_content_validation_enabled = original

    def test_disease_model_is_not_used_for_content_validation(self) -> None:
        with patch("app.ai.inference.predict_xray") as disease_predict:
            result = validate_xray_upload(
                filename="scan.png",
                content_type="image/png",
                file_bytes=_png_bytes(),
            )
            self.assertEqual(result.content_validation.status, "skipped")
            disease_predict.assert_not_called()


class DiagnosisEligibilityTests(unittest.TestCase):
    def test_fake_seed_path_is_rejected_for_diagnosis(self) -> None:
        from uuid import uuid4
        from unittest.mock import MagicMock

        from app.services.diagnosis_service import (
            InvalidDiagnosisRequestError,
            validate_diagnosis_request,
        )

        db = MagicMock()
        patient_id = uuid4()
        doctor_id = uuid4()
        xray_id = uuid4()

        xray = MagicMock()
        xray.patient_id = patient_id
        xray.image_path = "fake/seed_xray_001.png"

        with (
            patch(
                "app.services.diagnosis_service.get_patient_by_id",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.diagnosis_service.get_xray_image_by_id",
                return_value=xray,
            ),
        ):
            with self.assertRaises(InvalidDiagnosisRequestError):
                validate_diagnosis_request(db, patient_id, xray_id, doctor_id)


if __name__ == "__main__":
    unittest.main()
