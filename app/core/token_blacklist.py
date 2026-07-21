"""In-memory JWT revocation store for logout support."""

from datetime import UTC, datetime

_revoked_jtis: dict[str, int] = {}


def revoke_jti(jti: str, expires_at: int) -> None:
    """Mark a JWT ID as revoked until its original expiration time."""
    _cleanup_expired()
    _revoked_jtis[jti] = expires_at


def is_jti_revoked(jti: str) -> bool:
    """Return True when the JWT ID has been revoked."""
    _cleanup_expired()
    return jti in _revoked_jtis


def _cleanup_expired() -> None:
    """Remove expired entries from the in-memory revocation store."""
    now = int(datetime.now(UTC).timestamp())
    expired_jtis = [jti for jti, exp in _revoked_jtis.items() if exp <= now]
    for jti in expired_jtis:
        del _revoked_jtis[jti]
