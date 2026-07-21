"""Domain enumerations for PulmoScan database models."""

import enum


class DoctorRole(str, enum.Enum):
    """Access role assigned to a doctor account."""

    ADMIN = "admin"
    DOCTOR = "doctor"


class DoctorStatus(str, enum.Enum):
    """Lifecycle status of a doctor account."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class Gender(str, enum.Enum):
    """Patient gender values."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class XrayViewType(str, enum.Enum):
    """Chest X-ray projection or view type."""

    PA = "pa"
    AP = "ap"
    LATERAL = "lateral"
