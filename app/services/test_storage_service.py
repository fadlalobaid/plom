"""Unit tests for Supabase X-ray storage helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.services.storage_service import (
    StorageUploadError,
    build_xray_storage_path,
    create_signed_xray_url,
    upload_xray_file,
)
from app.services.xray_service import (
    UnsupportedXrayMediaTypeError,
    validate_xray_file,
)


class StoragePathTests(unittest.TestCase):
    def test_build_path_uses_doctor_patient_and_uuid(self) -> None:
        doctor_id = UUID("2b310000-0000-4000-8000-000000000001")
        patient_id = UUID("08ae0000-0000-4000-8000-000000000002")
        path = build_xray_storage_path(doctor_id, patient_id, ".DCM")
        parts = path.split("/")
        self.assertEqual(parts[0], str(doctor_id))
        self.assertEqual(parts[1], str(patient_id))
        self.assertTrue(parts[2].endswith(".dcm"))
        self.assertEqual(len(parts), 3)

    def test_extension_case_is_normalized(self) -> None:
        extension = validate_xray_file("scan.JPG", "image/jpeg")
        self.assertEqual(extension, ".jpg")

    def test_mismatched_mime_is_rejected(self) -> None:
        with self.assertRaises(UnsupportedXrayMediaTypeError):
            validate_xray_file("scan.png", "image/jpeg")


class StorageServiceTests(unittest.TestCase):
    @patch("app.services.storage_service.get_supabase_client")
    @patch("app.services.storage_service.get_settings")
    def test_upload_returns_storage_path(
        self,
        mock_settings: MagicMock,
        mock_client_factory: MagicMock,
    ) -> None:
        mock_settings.return_value.supabase_xray_bucket = "xray-images"
        bucket = MagicMock()
        mock_client_factory.return_value.storage.from_.return_value = bucket

        doctor_id = UUID("2b310000-0000-4000-8000-000000000001")
        patient_id = UUID("08ae0000-0000-4000-8000-000000000002")
        path = upload_xray_file(
            doctor_id=doctor_id,
            patient_id=patient_id,
            file_bytes=b"fake-bytes",
            extension=".png",
            content_type="image/png",
        )

        self.assertTrue(path.startswith(f"{doctor_id}/{patient_id}/"))
        self.assertTrue(path.endswith(".png"))
        bucket.upload.assert_called_once()
        kwargs = bucket.upload.call_args.kwargs
        self.assertEqual(kwargs["path"], path)
        self.assertEqual(kwargs["file"], b"fake-bytes")

    @patch("app.services.storage_service.get_supabase_client")
    @patch("app.services.storage_service.get_settings")
    def test_upload_failure_is_wrapped(
        self,
        mock_settings: MagicMock,
        mock_client_factory: MagicMock,
    ) -> None:
        mock_settings.return_value.supabase_xray_bucket = "xray-images"
        bucket = MagicMock()
        bucket.upload.side_effect = RuntimeError("network")
        mock_client_factory.return_value.storage.from_.return_value = bucket

        with self.assertRaises(StorageUploadError):
            upload_xray_file(
                doctor_id=UUID("2b310000-0000-4000-8000-000000000001"),
                patient_id=UUID("08ae0000-0000-4000-8000-000000000002"),
                file_bytes=b"x",
                extension=".png",
                content_type="image/png",
            )

    @patch("app.services.storage_service.get_supabase_client")
    @patch("app.services.storage_service.get_settings")
    def test_signed_url_extracts_response(
        self,
        mock_settings: MagicMock,
        mock_client_factory: MagicMock,
    ) -> None:
        mock_settings.return_value.supabase_xray_bucket = "xray-images"
        mock_settings.return_value.supabase_signed_url_expire_seconds = 600
        bucket = MagicMock()
        bucket.create_signed_url.return_value = {
            "signedURL": "https://example.supabase.co/storage/v1/object/sign/xray-images/a.png?token=abc"
        }
        mock_client_factory.return_value.storage.from_.return_value = bucket

        url = create_signed_xray_url("a/b/c.png", expires_in=600)
        self.assertIn("token=abc", url)


if __name__ == "__main__":
    unittest.main()
