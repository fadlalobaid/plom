"""Verify password hashing and JWT utilities."""

from datetime import timedelta
from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    validate_admin_seed_password,
    validate_password_strength,
    verify_password,
)


def test_password_hashing() -> None:
    password = "SecurePass123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_password_strength_policy() -> None:
    assert validate_password_strength("SecurePass1") == "SecurePass1"

    for weak_password in (
        "short1",
        "lettersOnly",
        "12345678",
        f"{'أ' * 40}A1",
    ):
        try:
            validate_password_strength(weak_password)
        except ValueError:
            continue
        raise AssertionError(f"Weak password was accepted: {weak_password}")


def test_known_admin_seed_password_is_rejected() -> None:
    try:
        validate_admin_seed_password("admin0021")
    except ValueError:
        return
    raise AssertionError("Known default admin password was accepted")


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
    test_password_strength_policy()
    test_known_admin_seed_password_is_rejected()
    test_jwt_lifecycle()
    test_jwt_decode_invalid_token()
    print("Security checks passed.")


if __name__ == "__main__":
    main()
