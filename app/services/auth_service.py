"""Authentication business logic."""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.token_blacklist import is_jti_revoked, revoke_jti
from app.models.doctor import Doctor
from app.services.doctor_service import get_doctor_by_email, get_doctor_by_id


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
