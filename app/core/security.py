"""Password hashing and JWT utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_strength(password: str) -> str:
    """Validate the shared password policy and return the accepted password."""
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must be between 8 and 128 characters")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    if not any(character.isalpha() for character in password):
        raise ValueError("Password must contain at least one letter")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must contain at least one number")
    return password


def validate_admin_seed_password(password: str) -> str:
    """Reject known default credentials before creating an administrator."""
    validate_password_strength(password)
    if password == "admin0021":
        raise ValueError(
            "FIRST_ADMIN_PASSWORD must be configured before seeding an admin"
        )
    return password


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash for the given plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the plain-text password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | UUID,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for the given subject."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token, returning its payload or None."""
    settings = get_settings()

    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
