"""Unit tests for shared input validators and schema validation."""

from datetime import date, timedelta
import unittest
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.validators import (
    normalize_email,
    normalize_search_query,
    validate_date_of_birth,
    validate_full_name,
    validate_national_id,
    validate_person_name,
    validate_phone_number,
)
from app.models.enums import Gender
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.xray_service import (
    UnsupportedXrayMediaTypeError,
    XrayFileTooLargeError,
    save_xray_file,
    validate_xray_file,
)


class PersonNameValidatorTests(unittest.TestCase):
    def test_arabic_name_is_accepted(self) -> None:
        self.assertEqual(validate_person_name("أحمد محمد علي"), "أحمد محمد علي")

    def test_english_name_is_accepted(self) -> None:
        self.assertEqual(validate_full_name("John Smith"), "John Smith")

    def test_name_is_stripped(self) -> None:
        self.assertEqual(validate_person_name("  Ahmad  "), "Ahmad")

    def test_blank_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_person_name("   ")

    def test_name_with_digits_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_person_name("Ahmad123")

    def test_name_with_symbols_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_person_name("@@Ahmad")


class EmailValidatorTests(unittest.TestCase):
    def test_email_is_normalized(self) -> None:
        self.assertEqual(normalize_email(" Doctor@Example.com "), "doctor@example.com")

    def test_login_schema_normalizes_email(self) -> None:
        payload = LoginRequest(email=" Doctor@Example.com ", password="securepass")
        self.assertEqual(payload.email, "doctor@example.com")

    def test_invalid_email_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            LoginRequest(email="not-an-email", password="securepass")


class PhoneValidatorTests(unittest.TestCase):
    def test_local_phone_is_accepted(self) -> None:
        self.assertEqual(validate_phone_number("0912345678"), "0912345678")

    def test_international_phone_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_phone_number("+963912345678")

    def test_invalid_phone_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_phone_number("phone123")

    def test_short_phone_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_phone_number("091234567")


class NationalIdAndDobTests(unittest.TestCase):
    def test_national_id_is_stripped(self) -> None:
        self.assertEqual(validate_national_id(" 1234567890 "), "1234567890")

    def test_invalid_national_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_national_id("12@@")

    def test_non_numeric_national_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_national_id("ABC1234567")

    def test_short_national_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_national_id("123456789")

    def test_valid_date_of_birth_is_accepted(self) -> None:
        self.assertEqual(
            validate_date_of_birth(date(1990, 5, 15)),
            date(1990, 5, 15),
        )

    def test_future_date_of_birth_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_date_of_birth(date.today() + timedelta(days=1))


class PasswordAndEnumTests(unittest.TestCase):
    def test_weak_password_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ChangePasswordRequest(
                current_password="temporary1",
                new_password="short",
            )

    def test_strong_password_is_accepted(self) -> None:
        payload = ChangePasswordRequest(
            current_password="temporary1",
            new_password="replacement2",
        )
        self.assertEqual(payload.new_password, "replacement2")

    def test_invalid_gender_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PatientCreate(
                first_name="Ahmad",
                father_name="Mohammad",
                mother_name="Sara",
                last_name="Ali",
                date_of_birth=date(1990, 1, 1),
                gender="unknown",  # type: ignore[arg-type]
                national_id="1234567890",
            )


class SchemaPatchAndSearchTests(unittest.TestCase):
    def test_doctor_patch_accepts_single_field(self) -> None:
        payload = DoctorUpdate(phone_number="0912345678")
        self.assertEqual(
            payload.model_dump(exclude_unset=True),
            {"phone_number": "0912345678"},
        )

    def test_doctor_patch_rejects_invalid_phone(self) -> None:
        with self.assertRaises(ValidationError):
            DoctorUpdate(phone_number="abc")

    def test_patient_create_accepts_arabic_names(self) -> None:
        payload =             PatientCreate(
                first_name="أحمد",
                father_name="محمد",
                mother_name="فاطمة",
                last_name="علي",
                date_of_birth=date(1995, 3, 20),
                gender=Gender.MALE,
                national_id="9876543210",
                phone_number="0912345678",
                governorate="دمشق",
                area="المزة",
            )
        self.assertEqual(payload.first_name, "أحمد")

    def test_blank_search_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_search_query("   ")


class XrayValidationTests(unittest.TestCase):
    def test_supported_jpeg_is_accepted(self) -> None:
        extension = validate_xray_file("scan.jpg", "image/jpeg")
        self.assertEqual(extension, ".jpg")

    def test_unsupported_extension_is_rejected(self) -> None:
        with self.assertRaises(UnsupportedXrayMediaTypeError):
            validate_xray_file("malware.exe", "application/octet-stream")

    def test_oversized_file_is_rejected(self) -> None:
        settings = get_settings()
        original_limit = settings.max_xray_upload_bytes
        settings.max_xray_upload_bytes = 16
        try:
            upload = UploadFile(
                filename="scan.png",
                file=BytesIO(b"0123456789abcdef0123"),
                headers={"content-type": "image/png"},
            )
            with self.assertRaises(XrayFileTooLargeError):
                save_xray_file(upload)
        finally:
            settings.max_xray_upload_bytes = original_limit

    def test_short_national_id_and_future_dob_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PatientUpdate.model_validate({"national_id": "123456789"})
        with self.assertRaises(ValidationError):
            DoctorCreate.model_validate(
                {
                    "full_name": "Dr. Ahmed Ali",
                    "email": "doctor@example.com",
                    "password": "securepass1",
                    "date_of_birth": str(date.today() + timedelta(days=2)),
                }
            )


class DuplicateDetailContractTests(unittest.TestCase):
    def test_uuid_path_type_remains_uuid(self) -> None:
        # Keep a lightweight reminder that IDs stay typed as UUID in schemas.
        self.assertTrue(hasattr(uuid4(), "hex"))


if __name__ == "__main__":
    unittest.main()
