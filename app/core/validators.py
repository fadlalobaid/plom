"""Shared input validation helpers for Pydantic schemas."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, EmailStr, Field

_PHONE_PATTERN = re.compile(r"^\d{10}$")
_NATIONAL_ID_PATTERN = re.compile(r"^[0-9]+$")
_NAME_ALLOWED_SEPARATORS = set(" .'-")
_SEARCH_MAX_LENGTH = 100
_NAME_MIN_LENGTH = 2
_NAME_MAX_LENGTH = 100
_FULL_NAME_MAX_LENGTH = 255
_NATIONAL_ID_MIN_LENGTH = 10
_NATIONAL_ID_MAX_LENGTH = 50
_AREA_MAX_LENGTH = 255
_NOTES_MAX_LENGTH = 2000
_SPECIALIZATION_MAX_LENGTH = 255
_CERTIFICATE_MAX_LENGTH = 500


def _empty_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


def normalize_required_text(value: object, *, field_name: str) -> str:
    """Strip surrounding whitespace and reject blank required text."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def validate_person_name(
    value: object,
    *,
    field_name: str = "Name",
    max_length: int = _NAME_MAX_LENGTH,
) -> str:
    """Validate Arabic/English person names without digits or symbols."""
    cleaned = normalize_required_text(value, field_name=field_name)
    if len(cleaned) < _NAME_MIN_LENGTH:
        raise ValueError(f"{field_name} must be at least {_NAME_MIN_LENGTH} characters")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    if any(character.isdigit() for character in cleaned):
        raise ValueError(f"{field_name} must not contain numbers")
    if not any(character.isalpha() for character in cleaned):
        raise ValueError(f"{field_name} must contain letters")
    if any(
        not (character.isalpha() or character in _NAME_ALLOWED_SEPARATORS)
        for character in cleaned
    ):
        raise ValueError(f"{field_name} contains invalid characters")
    return cleaned


def validate_full_name(value: object) -> str:
    """Validate a user display name with a larger maximum length."""
    return validate_person_name(
        value,
        field_name="Full name",
        max_length=_FULL_NAME_MAX_LENGTH,
    )


def validate_optional_person_name(
    value: object,
    *,
    field_name: str = "Name",
) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return validate_person_name(normalized, field_name=field_name)


def normalize_email(value: object) -> object:
    """Strip and lowercase emails before EmailStr validation."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return value.strip().lower()


def validate_phone_number(value: object) -> str:
    """Validate a phone number as exactly 10 digits with no symbols."""
    cleaned = normalize_required_text(value, field_name="Phone number")
    cleaned = cleaned.replace(" ", "")
    if not _PHONE_PATTERN.fullmatch(cleaned):
        raise ValueError("Phone number must be exactly 10 digits")
    return cleaned


def validate_optional_phone_number(value: object) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return validate_phone_number(normalized)


def validate_national_id(value: object) -> str:
    """Validate national ID as digits only with at least 10 digits."""
    cleaned = normalize_required_text(value, field_name="National ID")
    cleaned = cleaned.replace(" ", "")
    if not _NATIONAL_ID_PATTERN.fullmatch(cleaned):
        raise ValueError("National ID must contain digits only")
    if len(cleaned) < _NATIONAL_ID_MIN_LENGTH:
        raise ValueError("National ID must contain at least 10 digits")
    if len(cleaned) > _NATIONAL_ID_MAX_LENGTH:
        raise ValueError(
            f"National ID must contain at most {_NATIONAL_ID_MAX_LENGTH} digits"
        )
    return cleaned


def validate_optional_national_id(value: object) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return validate_national_id(normalized)


def validate_date_of_birth(value: object) -> date:
    """Reject unparsable or future dates of birth."""
    if value is None:
        raise ValueError("Date of birth is required")
    if not isinstance(value, date):
        raise ValueError("Invalid date of birth")
    if value > date.today():
        raise ValueError("Date of birth cannot be in the future")
    if value.year < 1900:
        raise ValueError("Date of birth is invalid")
    return value


def validate_optional_date_of_birth(value: object) -> date | None:
    if value is None:
        return None
    return validate_date_of_birth(value)


def validate_area(value: object) -> str:
    """Validate a required non-empty area value."""
    cleaned = normalize_required_text(value, field_name="Area")
    if len(cleaned) > _AREA_MAX_LENGTH:
        raise ValueError(f"Area must be at most {_AREA_MAX_LENGTH} characters")
    return cleaned


def validate_optional_area(value: object) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return validate_area(normalized)


def validate_specialization(value: object) -> str:
    cleaned = normalize_required_text(value, field_name="Specialization")
    if len(cleaned) > _SPECIALIZATION_MAX_LENGTH:
        raise ValueError(
            f"Specialization must be at most {_SPECIALIZATION_MAX_LENGTH} characters"
        )
    return cleaned


def validate_optional_specialization(value: object) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return validate_specialization(normalized)


def validate_optional_text(
    value: object,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    if not isinstance(normalized, str):
        raise ValueError(f"{field_name} must be a string")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return normalized


def validate_optional_certificate(value: object) -> str | None:
    return validate_optional_text(
        value,
        field_name="Certificate",
        max_length=_CERTIFICATE_MAX_LENGTH,
    )


def validate_optional_notes(value: object) -> str | None:
    return validate_optional_text(
        value,
        field_name="Notes",
        max_length=_NOTES_MAX_LENGTH,
    )


def normalize_search_query(value: object) -> str | None:
    """Normalize optional search query parameters."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Search query must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Search query cannot be empty")
    if len(cleaned) > _SEARCH_MAX_LENGTH:
        raise ValueError(
            f"Search query must be at most {_SEARCH_MAX_LENGTH} characters"
        )
    return cleaned


def _person_name(field_name: str):
    return Annotated[
        str,
        AfterValidator(lambda value: validate_person_name(value, field_name=field_name)),
    ]


def _optional_person_name(field_name: str):
    return Annotated[
        str | None,
        BeforeValidator(_empty_to_none),
        AfterValidator(
            lambda value: validate_optional_person_name(value, field_name=field_name)
        ),
    ]


FirstName = _person_name("First name")
FatherName = _person_name("Father name")
MotherName = _person_name("Mother name")
LastName = _person_name("Last name")
OptionalFirstName = _optional_person_name("First name")
OptionalFatherName = _optional_person_name("Father name")
OptionalMotherName = _optional_person_name("Mother name")
OptionalLastName = _optional_person_name("Last name")
FullName = Annotated[str, AfterValidator(validate_full_name)]
OptionalFullName = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(
        lambda value: None if value is None else validate_full_name(value)
    ),
]
NormalizedEmail = Annotated[EmailStr, BeforeValidator(normalize_email)]
OptionalNormalizedEmail = Annotated[
    EmailStr | None,
    BeforeValidator(normalize_email),
]
PhoneNumber = Annotated[
    str,
    Field(min_length=10, max_length=10, pattern=r"^\d{10}$"),
    AfterValidator(validate_phone_number),
]
OptionalPhoneNumber = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_phone_number),
]
NationalId = Annotated[str, AfterValidator(validate_national_id)]
OptionalNationalId = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_national_id),
]
DateOfBirth = Annotated[date, AfterValidator(validate_date_of_birth)]
OptionalDateOfBirth = Annotated[
    date | None,
    AfterValidator(validate_optional_date_of_birth),
]
Area = Annotated[str, AfterValidator(validate_area)]
OptionalArea = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_area),
]
Specialization = Annotated[str, AfterValidator(validate_specialization)]
OptionalSpecialization = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_specialization),
]
OptionalCertificate = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_certificate),
]
OptionalNotes = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_optional_notes),
]
SearchQuery = Annotated[
    str | None,
    AfterValidator(normalize_search_query),
]
