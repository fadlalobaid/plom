"""Integration tests for forced first-login password changes."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus

TEMPORARY_PASSWORD = "Temporary1"
ADMIN_PASSWORD = "AdminPass1"
TEMPORARY_PASSWORD_HASH = get_password_hash(TEMPORARY_PASSWORD)
ADMIN_PASSWORD_HASH = get_password_hash(ADMIN_PASSWORD)


class ForcedPasswordChangeTests(unittest.TestCase):
    """Verify login, route gating, password change, and admin reset flows."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.doctor = Doctor(
            full_name="Temporary Doctor",
            email="temporary@example.com",
            password_hash=TEMPORARY_PASSWORD_HASH,
            role=DoctorRole.DOCTOR,
            status=DoctorStatus.ACTIVE,
            must_change_password=True,
        )
        self.admin = Doctor(
            full_name="System Admin",
            email="admin@example.com",
            password_hash=ADMIN_PASSWORD_HASH,
            role=DoctorRole.ADMIN,
            status=DoctorStatus.ACTIVE,
            must_change_password=False,
        )
        self.db.add_all([self.doctor, self.admin])
        self.db.commit()

        def override_get_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def login(self, email: str, password: str) -> dict:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    @staticmethod
    def authorization(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_flagged_doctor_can_login_and_get_me_but_not_patients(self) -> None:
        login_data = self.login(self.doctor.email, TEMPORARY_PASSWORD)
        headers = self.authorization(login_data["access_token"])

        self.assertTrue(login_data["must_change_password"])
        me_response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.json()["must_change_password"])

        protected_paths = (
            "/api/v1/patients/",
            f"/api/v1/xray-images/patient/{self.doctor.id}",
            f"/api/v1/diagnosis/patient/{self.doctor.id}",
        )
        for path in protected_paths:
            response = self.client.get(path, headers=headers)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"], "Password change required")

    def test_change_password_rejects_incorrect_current_password(self) -> None:
        token = self.login(self.doctor.email, TEMPORARY_PASSWORD)["access_token"]
        response = self.client.post(
            "/api/v1/auth/change-password",
            headers=self.authorization(token),
            json={
                "current_password": "Incorrect1",
                "new_password": "Replacement2",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Current password is incorrect")

    def test_flagged_doctor_can_logout(self) -> None:
        token = self.login(self.doctor.email, TEMPORARY_PASSWORD)["access_token"]
        response = self.client.post(
            "/api/v1/auth/logout",
            headers=self.authorization(token),
        )

        self.assertEqual(response.status_code, 200)

    def test_change_password_rejects_password_reuse(self) -> None:
        token = self.login(self.doctor.email, TEMPORARY_PASSWORD)["access_token"]
        response = self.client.post(
            "/api/v1/auth/change-password",
            headers=self.authorization(token),
            json={
                "current_password": TEMPORARY_PASSWORD,
                "new_password": TEMPORARY_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "New password must be different from the current password",
        )

    def test_successful_change_clears_flag_and_unlocks_patients(self) -> None:
        token = self.login(self.doctor.email, TEMPORARY_PASSWORD)["access_token"]
        headers = self.authorization(token)
        response = self.client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": TEMPORARY_PASSWORD,
                "new_password": "Replacement2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password changed successfully")
        self.db.expire_all()
        updated_doctor = self.db.get(Doctor, self.doctor.id)
        assert updated_doctor is not None
        self.assertFalse(updated_doctor.must_change_password)
        self.assertTrue(verify_password("Replacement2", updated_doctor.password_hash))
        self.assertEqual(
            self.client.get("/api/v1/patients/", headers=headers).status_code,
            401,
        )
        new_login = self.login(self.doctor.email, "Replacement2")
        self.assertFalse(new_login["must_change_password"])
        self.assertEqual(
            self.client.get(
                "/api/v1/patients/",
                headers=self.authorization(new_login["access_token"]),
            ).status_code,
            200,
        )

    def test_admin_reset_sets_temporary_password_and_flag(self) -> None:
        admin_token = self.login(self.admin.email, ADMIN_PASSWORD)["access_token"]
        response = self.client.post(
            f"/api/v1/doctors/{self.doctor.id}/reset-password",
            headers=self.authorization(admin_token),
            json={"new_password": "ResetPass3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password reset successfully")
        self.db.expire_all()
        updated_doctor = self.db.get(Doctor, self.doctor.id)
        assert updated_doctor is not None
        self.assertTrue(updated_doctor.must_change_password)
        self.assertTrue(verify_password("ResetPass3", updated_doctor.password_hash))

    def test_admin_created_doctor_requires_password_change(self) -> None:
        admin_token = self.login(self.admin.email, ADMIN_PASSWORD)["access_token"]
        response = self.client.post(
            "/api/v1/doctors/",
            headers=self.authorization(admin_token),
            json={
                "full_name": "New Doctor",
                "email": "new-doctor@example.com",
                "password": "NewDoctor1",
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue(response.json()["must_change_password"])
        self.assertNotIn("password_hash", response.json())

    def test_generic_patch_cannot_reset_an_admin_password(self) -> None:
        admin_token = self.login(self.admin.email, ADMIN_PASSWORD)["access_token"]
        response = self.client.patch(
            f"/api/v1/doctors/{self.admin.id}",
            headers=self.authorization(admin_token),
            json={"password": "AnotherAdmin2"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Password reset is only available for doctor accounts",
        )


if __name__ == "__main__":
    unittest.main()
