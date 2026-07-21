"""Verify password hashing and JWT utilities."""

from datetime import timedelta
from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing() -> None:
    password = "SecurePass123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_lifecycle() -> None:
    subject = uuid4()
    role = "doctor"

    token = create_access_token(
        subject=subject,
        additional_claims={"role": role},
        expires_delta=timedelta(minutes=5),
    )

    assert isinstance(token, str)
    assert token.count(".") == 2

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(subject)
    assert payload["role"] == role
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_decode_invalid_token() -> None:
    assert decode_access_token("invalid.token.value") is None


def main() -> None:
    test_password_hashing()
    test_jwt_lifecycle()
    test_jwt_decode_invalid_token()
    print("Security checks passed.")


if __name__ == "__main__":
    main()
