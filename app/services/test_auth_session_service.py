"""Integration tests for persistent refresh-session authentication."""

from __future__ import annotations

import unittest
from datetime import date
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import decode_access_token, get_password_hash
from app.core.token_blacklist import _revoked_jtis
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus, SyrianGovernorate
from app.services.auth_service import (
    hash_refresh_token,
    revoke_all_sessions,
)

PASSWORD = "SecurePass1"
PASSWORD_HASH = get_password_hash(PASSWORD)


class PersistentLoginSessionTests(unittest.TestCase):
    """Cover login, refresh rotation, logout, and multi-device sessions."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.doctor = Doctor(
            full_name="Session Doctor",
            email="session@example.com",
            password_hash=PASSWORD_HASH,
            specialization="Pulmonology",
            date_of_birth=date(1990, 1, 1),
            phone_number="0911111111",
            governorate=SyrianGovernorate.DAMASCUS,
            area="المزة",
            role=DoctorRole.DOCTOR,
            status=DoctorStatus.ACTIVE,
            must_change_password=False,
        )
        self.admin = Doctor(
            full_name="Session Admin",
            email="session-admin@example.com",
            password_hash=PASSWORD_HASH,
            specialization="Administration",
            date_of_birth=date(1980, 1, 1),
            phone_number="0922222222",
            governorate=SyrianGovernorate.DAMASCUS,
            area="المزة",
            role=DoctorRole.ADMIN,
            status=DoctorStatus.ACTIVE,
            must_change_password=False,
        )
        self.db.add_all([self.doctor, self.admin])
        self.db.commit()
        self.db.refresh(self.doctor)
        self.db.refresh(self.admin)

        def override_get_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        _revoked_jtis.clear()

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        _revoked_jtis.clear()

    def login(self, email: str | None = None, password: str = PASSWORD) -> dict:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email or self.doctor.email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def authorization(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def open_db(self) -> Session:
        return Session(self.engine)

    def test_login_returns_access_and_refresh_tokens(self) -> None:
        data = self.login()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertFalse(data["must_change_password"])

    def test_access_token_has_expiration_near_configured_lifetime(self) -> None:
        data = self.login()
        payload = decode_access_token(data["access_token"])
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)
        self.assertIn("jti", payload)
        self.assertIn("sid", payload)

        settings = get_settings()
        lifetime = payload["exp"] - payload["iat"]
        expected = settings.access_token_expire_minutes * 60
        self.assertAlmostEqual(lifetime, expected, delta=5)

    def test_refresh_issues_new_access_token_and_rotates_refresh(self) -> None:
        login_data = self.login()
        old_refresh = login_data["refresh_token"]

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        self.assertEqual(response.status_code, 200, response.text)
        refreshed = response.json()

        self.assertIn("access_token", refreshed)
        self.assertIn("refresh_token", refreshed)
        self.assertNotEqual(refreshed["access_token"], login_data["access_token"])
        self.assertNotEqual(refreshed["refresh_token"], old_refresh)

        me = self.client.get(
            "/api/v1/auth/me",
            headers=self.authorization(refreshed["access_token"]),
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], self.doctor.email)

    def test_old_refresh_token_fails_after_rotation(self) -> None:
        login_data = self.login()
        old_refresh = login_data["refresh_token"]

        first = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        self.assertEqual(second.status_code, 401)

    def test_new_refresh_token_works_after_rotation(self) -> None:
        login_data = self.login()
        first = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        ).json()
        second = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first["refresh_token"]},
        )
        self.assertEqual(second.status_code, 200)

    def test_logout_revokes_refresh_and_blacklists_access(self) -> None:
        login_data = self.login()
        access = login_data["access_token"]
        refresh = login_data["refresh_token"]

        logout = self.client.post(
            "/api/v1/auth/logout",
            headers=self.authorization(access),
        )
        self.assertEqual(logout.status_code, 200)

        me = self.client.get("/api/v1/auth/me", headers=self.authorization(access))
        self.assertEqual(me.status_code, 401)

        refresh_response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_inactive_doctor_cannot_refresh(self) -> None:
        login_data = self.login()
        with self.open_db() as db:
            doctor = db.get(Doctor, self.doctor.id)
            assert doctor is not None
            doctor.status = DoctorStatus.INACTIVE
            db.commit()

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        self.assertEqual(response.status_code, 401)

    def test_soft_deleted_doctor_sessions_revoked_on_deactivate(self) -> None:
        login_data = self.login()
        admin_login = self.login(self.admin.email)

        deactivate = self.client.delete(
            f"/api/v1/doctors/{self.doctor.id}",
            headers=self.authorization(admin_login["access_token"]),
        )
        self.assertEqual(deactivate.status_code, 200)
        self.assertEqual(deactivate.json()["status"], DoctorStatus.INACTIVE.value)

        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        self.assertEqual(response.status_code, 401)

    def test_multiple_device_sessions_are_independent(self) -> None:
        phone = self.login()
        tablet = self.login()
        self.assertNotEqual(phone["refresh_token"], tablet["refresh_token"])

        logout_phone = self.client.post(
            "/api/v1/auth/logout",
            headers=self.authorization(phone["access_token"]),
        )
        self.assertEqual(logout_phone.status_code, 200)

        phone_refresh = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": phone["refresh_token"]},
        )
        self.assertEqual(phone_refresh.status_code, 401)

        tablet_refresh = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tablet["refresh_token"]},
        )
        self.assertEqual(tablet_refresh.status_code, 200)

    def test_revoke_all_sessions_invalidates_every_session(self) -> None:
        first = self.login()
        second = self.login()

        with self.open_db() as db:
            revoked = revoke_all_sessions(db, self.doctor.id)
        self.assertEqual(revoked, 2)

        for token in (first["refresh_token"], second["refresh_token"]):
            response = self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": token},
            )
            self.assertEqual(response.status_code, 401)

    def test_raw_refresh_token_is_never_persisted(self) -> None:
        login_data = self.login()
        raw = login_data["refresh_token"]
        expected_hash = hash_refresh_token(raw)

        with self.open_db() as db:
            sessions = list(db.scalars(select(AuthSession)).all())
            self.assertEqual(len(sessions), 1)
            stored = sessions[0]
            self.assertEqual(stored.refresh_token_hash, expected_hash)
            self.assertNotEqual(stored.refresh_token_hash, raw)
            row_values = [
                getattr(stored, column.name)
                for column in AuthSession.__table__.columns
            ]
            self.assertNotIn(raw, row_values)

    def test_refresh_token_not_accepted_via_query_parameters(self) -> None:
        login_data = self.login()
        response = self.client.post(
            f"/api/v1/auth/refresh?refresh_token={login_data['refresh_token']}",
        )
        self.assertEqual(response.status_code, 422)

    def test_concurrent_refresh_allows_only_one_success(self) -> None:
        login_data = self.login()
        refresh_token = login_data["refresh_token"]

        def attempt_refresh() -> int:
            result = self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            return result.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: attempt_refresh(), range(2)))

        self.assertEqual(statuses.count(200), 1)
        self.assertEqual(statuses.count(401), 1)

    def test_admin_role_permissions_unchanged(self) -> None:
        admin_login = self.login(self.admin.email)
        doctors = self.client.get(
            "/api/v1/doctors/",
            headers=self.authorization(admin_login["access_token"]),
        )
        self.assertEqual(doctors.status_code, 200)

        doctor_login = self.login()
        forbidden = self.client.get(
            "/api/v1/doctors/",
            headers=self.authorization(doctor_login["access_token"]),
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_password_change_revokes_refresh_sessions(self) -> None:
        login_data = self.login()
        change = self.client.post(
            "/api/v1/auth/change-password",
            headers=self.authorization(login_data["access_token"]),
            json={
                "current_password": PASSWORD,
                "new_password": "Replacement9",
            },
        )
        self.assertEqual(change.status_code, 200)

        refresh_response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_login_to_logout_api_sequence(self) -> None:
        login_data = self.login()
        refreshed = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        ).json()
        me = self.client.get(
            "/api/v1/auth/me",
            headers=self.authorization(refreshed["access_token"]),
        )
        self.assertEqual(me.status_code, 200)

        logout = self.client.post(
            "/api/v1/auth/logout",
            headers=self.authorization(refreshed["access_token"]),
        )
        self.assertEqual(logout.status_code, 200)

        rejected = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refreshed["refresh_token"]},
        )
        self.assertEqual(rejected.status_code, 401)


if __name__ == "__main__":
    unittest.main()
