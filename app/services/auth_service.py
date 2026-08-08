"""Authentication business logic."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.core.token_blacklist import is_jti_revoked, revoke_jti
from app.models.auth_session import AuthSession
from app.models.doctor import Doctor
from app.models.enums import DoctorStatus
from app.services.doctor_service import get_doctor_by_email, get_doctor_by_id


class IncorrectCurrentPasswordError(Exception):
    """Raised when password confirmation does not match the stored hash."""


class PasswordReuseError(Exception):
    """Raised when the replacement password matches the current password."""


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token cannot be validated or rotated."""


def authenticate_doctor(db: Session, email: str, password: str) -> Doctor | None:
    """Validate credentials and return the doctor account when successful."""
    doctor = get_doctor_by_email(db, email)
    if doctor is None or not verify_password(password, doctor.password_hash):
        return None
    return doctor


def generate_refresh_token() -> str:
    """Return a cryptographically secure opaque refresh token."""
    settings = get_settings()
    return secrets.token_urlsafe(settings.refresh_token_bytes)


def hash_refresh_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of the raw refresh token for storage/lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_doctor_access_token(doctor: Doctor, session_id: UUID) -> str:
    """Create a short-lived JWT access token bound to a refresh session."""
    return create_access_token(
        subject=doctor.id,
        additional_claims={
            "role": doctor.role.value,
            "jti": str(uuid4()),
            "sid": str(session_id),
        },
    )


def create_auth_session(
    db: Session,
    doctor: Doctor,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[AuthSession, str]:
    """Persist a hashed refresh session and return ``(session, raw_refresh_token)``.

    The raw refresh token is returned only to the caller and is never stored.
    Refresh sessions intentionally have no absolute expiry so the product can
    keep users signed in until logout or security-driven revocation. The access
    token remains short-lived (~30 minutes). Tradeoff: a stolen refresh token
    remains usable until rotation, logout, password change, or account disable;
    mitigated by hashing, rotation, and revoke-all on security events.
    """
    raw_refresh_token = generate_refresh_token()
    session = AuthSession(
        doctor_id=doctor.id,
        refresh_token_hash=hash_refresh_token(raw_refresh_token),
        user_agent=_truncate_user_agent(user_agent),
        ip_created=ip_address,
        ip_last_used=ip_address,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_refresh_token


def issue_login_tokens(
    db: Session,
    doctor: Doctor,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str]:
    """Create a refresh session and return ``(access_token, refresh_token)``."""
    session, raw_refresh_token = create_auth_session(
        db,
        doctor,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    access_token = create_doctor_access_token(doctor, session.id)
    return access_token, raw_refresh_token


def refresh_auth_session(
    db: Session,
    raw_refresh_token: str,
    *,
    ip_address: str | None = None,
) -> tuple[Doctor, str, str]:
    """Rotate a refresh session and return ``(doctor, access_token, refresh_token)``.

    Concurrent reuse of the same refresh token is rejected: only one rotation
    can succeed for a given stored hash.
    """
    if not raw_refresh_token or not raw_refresh_token.strip():
        raise InvalidRefreshTokenError

    token_hash = hash_refresh_token(raw_refresh_token)
    session = db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
    )
    if session is None or session.revoked_at is not None:
        raise InvalidRefreshTokenError

    doctor = get_doctor_by_id(db, session.doctor_id)
    if doctor is None or doctor.status != DoctorStatus.ACTIVE:
        raise InvalidRefreshTokenError

    new_raw_refresh_token = generate_refresh_token()
    new_token_hash = hash_refresh_token(new_raw_refresh_token)
    now = datetime.now(UTC)

    result = db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session.id,
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
        )
        .values(
            refresh_token_hash=new_token_hash,
            last_used_at=now,
            ip_last_used=ip_address,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise InvalidRefreshTokenError

    db.commit()
    access_token = create_doctor_access_token(doctor, session.id)
    return doctor, access_token, new_raw_refresh_token


def revoke_auth_session(db: Session, session_id: UUID) -> bool:
    """Revoke a single refresh session. Return True when a row was updated."""
    now = datetime.now(UTC)
    result = db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return result.rowcount == 1


def revoke_auth_session_by_refresh_token(db: Session, raw_refresh_token: str) -> bool:
    """Revoke the session matching a raw refresh token, if any."""
    if not raw_refresh_token:
        return False
    token_hash = hash_refresh_token(raw_refresh_token)
    now = datetime.now(UTC)
    result = db.execute(
        update(AuthSession)
        .where(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return result.rowcount == 1


def revoke_all_sessions(db: Session, doctor_id: UUID) -> int:
    """Revoke every active refresh session for a doctor. Return revoked count."""
    now = datetime.now(UTC)
    result = db.execute(
        update(AuthSession)
        .where(
            AuthSession.doctor_id == doctor_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return int(result.rowcount or 0)


def change_doctor_password(
    db: Session,
    doctor: Doctor,
    current_password: str,
    new_password: str,
) -> Doctor:
    """Replace a doctor's password after verifying the current credential.

    All persistent refresh sessions are revoked so stolen sessions cannot
    continue after a security-sensitive password change. The caller must
    re-authenticate (existing access token is also blacklisted by the endpoint).
    """
    if not verify_password(current_password, doctor.password_hash):
        raise IncorrectCurrentPasswordError
    if verify_password(new_password, doctor.password_hash):
        raise PasswordReuseError

    validate_password_strength(new_password)
    doctor.password_hash = get_password_hash(new_password)
    doctor.must_change_password = False
    db.commit()
    db.refresh(doctor)
    revoke_all_sessions(db, doctor.id)
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


def extract_session_id(token: str) -> UUID | None:
    """Return the auth-session id claim from an access token when present."""
    payload = decode_access_token(token)
    if payload is None:
        return None
    sid = payload.get("sid")
    if not isinstance(sid, str):
        return None
    try:
        return UUID(sid)
    except ValueError:
        return None


def _truncate_user_agent(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    cleaned = user_agent.strip()
    if not cleaned:
        return None
    return cleaned[:512]
