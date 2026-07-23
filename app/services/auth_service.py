"""Authentication business logic."""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.core.token_blacklist import is_jti_revoked, revoke_jti
from app.models.doctor import Doctor
from app.services.doctor_service import get_doctor_by_email


class IncorrectCurrentPasswordError(Exception):
    """Raised when password confirmation does not match the stored hash."""


class PasswordReuseError(Exception):
    """Raised when the replacement password matches the current password."""


def authenticate_doctor(db: Session, email: str, password: str) -> Doctor | None:
    """Validate credentials and return the doctor account when successful."""
    doctor = get_doctor_by_email(db, email)
    if doctor is None or not verify_password(password, doctor.password_hash):
        return None
    return doctor


def create_doctor_access_token(doctor: Doctor) -> str:
    """Create a JWT access token for the authenticated doctor."""
    return create_access_token(
        subject=doctor.id,
        additional_claims={
            "role": doctor.role.value,
            "jti": str(uuid4()),
        },
    )


def change_doctor_password(
    db: Session,
    doctor: Doctor,
    current_password: str,
    new_password: str,
) -> Doctor:
    """Replace a doctor's password after verifying the current credential."""
    if not verify_password(current_password, doctor.password_hash):
        raise IncorrectCurrentPasswordError
    if verify_password(new_password, doctor.password_hash):
        raise PasswordReuseError

    validate_password_strength(new_password)
    doctor.password_hash = get_password_hash(new_password)
    doctor.must_change_password = False
    db.commit()
    db.refresh(doctor)
    return doctor


def is_access_token_revoked(payload: dict) -> bool:
    """Return True when the decoded token payload has been revoked."""
    jti = payload.get("jti")
    if not isinstance(jti, str):
        return False
    return is_jti_revoked(jti)


def revoke_access_token(token: str) -> None:
    """Revoke a JWT access token so it can no longer be used."""
    payload = decode_access_token(token)
    if payload is None:
        return

    jti = payload.get("jti")
    exp = payload.get("exp")
    if isinstance(jti, str) and isinstance(exp, int):
        revoke_jti(jti, exp)
