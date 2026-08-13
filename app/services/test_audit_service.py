"""Unit tests for audit logging helpers."""

import unittest
from unittest.mock import MagicMock

from app.models.enums import AuditAction, AuditEntityType
from app.services.audit_service import audit_operation, create_audit_log, sanitize_audit_details


class AuditServiceTests(unittest.TestCase):
    def test_sanitize_audit_details_removes_sensitive_keys(self) -> None:
        details = sanitize_audit_details(
            {
                "password": "secret",
                "password_hash": "hash",
                "access_token": "token",
                "authorization": "Bearer x",
                "full_name": "Test Patient",
                "nested": {"new_password": "secret", "status": "active"},
            }
        )

        self.assertEqual(
            details,
            {
                "full_name": "Test Patient",
                "nested": {"status": "active"},
            },
        )

    def test_create_audit_log_failure_does_not_raise(self) -> None:
        db = MagicMock()
        db.commit.side_effect = RuntimeError("database unavailable")

        result = create_audit_log(
            db,
            action=AuditAction.CREATE_PATIENT,
            user_id=None,
            entity_type=AuditEntityType.PATIENT,
            details={"result": "success"},
        )

        self.assertIsNone(result)
        db.rollback.assert_called_once()

    def test_audit_operation_marks_failure_with_reason(self) -> None:
        db = MagicMock()
        audit_log = MagicMock()
        db.refresh.side_effect = lambda obj: obj

        def _add(obj: object) -> None:
            return None

        db.add.side_effect = _add

        with unittest.mock.patch("app.services.audit_service.AuditLog", return_value=audit_log):
            result = audit_operation(
                db,
                action=AuditAction.LOGIN_FAILED,
                success=False,
                reason="invalid_credentials",
                email="user@example.com",
            )

        self.assertIs(result, audit_log)
        added = db.add.call_args.args[0]
        self.assertEqual(added.details["result"], "failure")
        self.assertEqual(added.details["reason"], "invalid_credentials")
        self.assertEqual(added.details["email"], "user@example.com")


if __name__ == "__main__":
    unittest.main()
