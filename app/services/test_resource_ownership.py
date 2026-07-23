"""Regression tests for doctor-scoped patient resource access."""

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import DiagnosisResult, Doctor, Patient, XrayImage
from app.models.enums import Gender, XrayViewType
from app.schemas.patient import (
    PatientMedicalRecordResponse,
    PatientResponse,
    PatientXrayHistoryResponse,
)
from app.services.diagnosis_service import (
    analyze_and_create_diagnosis_result,
    delete_diagnosis_result,
    get_diagnosis_result_by_id,
)
from app.services.patient_service import get_patient_by_id, list_patients
from app.services.xray_service import get_xray_image_by_id, list_xray_images_by_patient


class ResourceOwnershipTests(unittest.TestCase):
    """Ensure one doctor cannot retrieve another doctor's resources."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.owner = Doctor(
            full_name="Owner Doctor",
            email="owner@example.com",
            password_hash="hash",
        )
        self.other_doctor = Doctor(
            full_name="Other Doctor",
            email="other@example.com",
            password_hash="hash",
        )
        self.db.add_all([self.owner, self.other_doctor])
        self.db.flush()

        self.patient = Patient(
            full_name="Owned Patient",
            date_of_birth=date(1990, 1, 1),
            gender=Gender.MALE,
            national_id="patient-1",
            created_by_doctor_id=self.owner.id,
        )
        self.db.add(self.patient)
        self.db.flush()

        self.xray = XrayImage(
            patient_id=self.patient.id,
            doctor_id=self.owner.id,
            image_path="unused.png",
            view_type=XrayViewType.PA,
        )
        self.db.add(self.xray)
        self.db.flush()

        self.diagnosis = DiagnosisResult(
            patient_id=self.patient.id,
            doctor_id=self.owner.id,
            xray_image_id=self.xray.id,
            predicted_label="normal",
            confidence_score=Decimal("0.90000"),
            model_version="test",
        )
        self.db.add(self.diagnosis)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_patient_access_is_scoped_to_owner(self) -> None:
        self.assertIsNotNone(get_patient_by_id(self.db, self.patient.id, self.owner.id))
        self.assertIsNone(get_patient_by_id(self.db, self.patient.id, self.other_doctor.id))
        self.assertEqual(list_patients(self.db, doctor_id=self.other_doctor.id), [])

    def test_structured_patient_names_are_searchable(self) -> None:
        self.patient.first_name = "StructuredGiven"
        self.patient.father_name = "StructuredFather"
        self.patient.mother_name = "StructuredMother"
        self.patient.last_name = "StructuredFamily"
        self.db.commit()

        matches = list_patients(
            self.db,
            doctor_id=self.owner.id,
            full_name="StructuredFather",
        )

        self.assertEqual([patient.id for patient in matches], [self.patient.id])

    def test_xray_access_is_scoped_to_patient_owner(self) -> None:
        self.assertIsNotNone(get_xray_image_by_id(self.db, self.xray.id, self.owner.id))
        self.assertIsNone(
            get_xray_image_by_id(self.db, self.xray.id, self.other_doctor.id)
        )
        self.assertEqual(
            list_xray_images_by_patient(
                self.db,
                self.patient.id,
                self.other_doctor.id,
            ),
            [],
        )

    def test_diagnosis_access_is_scoped_to_patient_owner(self) -> None:
        self.assertIsNotNone(
            get_diagnosis_result_by_id(self.db, self.diagnosis.id, self.owner.id)
        )
        self.assertIsNone(
            get_diagnosis_result_by_id(
                self.db,
                self.diagnosis.id,
                self.other_doctor.id,
            )
        )

    def test_medical_record_pairs_each_xray_with_its_diagnosis(self) -> None:
        xray_images = list_xray_images_by_patient(
            self.db,
            self.patient.id,
            self.owner.id,
        )
        record = PatientMedicalRecordResponse(
            patient=PatientResponse.model_validate(self.patient),
            xray_history=[
                PatientXrayHistoryResponse(
                    xray_image=xray_image,
                    diagnosis_result=xray_image.diagnosis_result,
                )
                for xray_image in xray_images
            ],
        )

        self.assertEqual(record.patient.id, self.patient.id)
        self.assertEqual(len(record.xray_history), 1)
        diagnosis_result = record.xray_history[0].diagnosis_result
        self.assertIsNotNone(diagnosis_result)
        assert diagnosis_result is not None
        self.assertEqual(diagnosis_result.id, self.diagnosis.id)

    @patch("app.services.diagnosis_service.analyze_xray_image")
    def test_diagnosis_updates_xray_summary_result(self, analyze_mock) -> None:
        xray = XrayImage(
            patient_id=self.patient.id,
            doctor_id=self.owner.id,
            image_path="unused-second.png",
            taken_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            view_type=XrayViewType.AP,
        )
        self.db.add(xray)
        self.db.commit()
        analyze_mock.return_value = {
            "predicted_label": "Pneumonia",
            "confidence_score": Decimal("0.87500"),
            "model_version": "test",
            "report_text": "Test report",
            "visual_map_path": None,
        }

        diagnosis = analyze_and_create_diagnosis_result(
            self.db,
            patient_id=self.patient.id,
            xray_image_id=xray.id,
            doctor_id=self.owner.id,
        )

        self.assertEqual(xray.result, "Pneumonia")
        delete_diagnosis_result(self.db, diagnosis.id, self.owner.id)
        self.assertIsNone(xray.result)


if __name__ == "__main__":
    unittest.main()
