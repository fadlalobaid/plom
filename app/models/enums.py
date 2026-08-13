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


class AuditAction(str, enum.Enum):
    """Auditable operations recorded by the system."""

    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    REFRESH_FAILED = "REFRESH_FAILED"
    LOGOUT = "LOGOUT"
    CREATE_DOCTOR = "CREATE_DOCTOR"
    UPDATE_DOCTOR = "UPDATE_DOCTOR"
    DELETE_DOCTOR = "DELETE_DOCTOR"
    CREATE_PATIENT = "CREATE_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    DELETE_PATIENT = "DELETE_PATIENT"
    UPLOAD_XRAY = "UPLOAD_XRAY"
    DELETE_XRAY = "DELETE_XRAY"
    CREATE_DIAGNOSIS = "CREATE_DIAGNOSIS"
    DELETE_DIAGNOSIS = "DELETE_DIAGNOSIS"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"


class AuditEntityType(str, enum.Enum):
    """Entity types referenced by audit log entries."""

    DOCTOR = "Doctor"
    PATIENT = "Patient"
    XRAY_IMAGE = "XrayImage"
    DIAGNOSIS_RESULT = "DiagnosisResult"


class SyrianGovernorate(str, enum.Enum):
    """Syrian governorates used for user and patient location.

    Includes an explicit ``خارج سوريا`` option for non-Syrian locations.
    Clients should send the Arabic value strings, not the enum member names.
    """

    IDLIB = "إدلب"
    AL_HASAKAH = "الحسكة"
    ALEPPO = "حلب"
    HAMA = "حماة"
    HOMS = "حمص"
    DAMASCUS = "دمشق"
    DARA = "درعا"
    DEIR_EZ_ZOR = "دير الزور"
    AL_RAQQAH = "الرقة"
    RIF_DIMASHQ = "ريف دمشق"
    AS_SUWAYDA = "السويداء"
    TARTOUS = "طرطوس"
    AL_QUNEITRA = "القنيطرة"
    LATAKIA = "اللاذقية"
    OUTSIDE_SYRIA = "خارج سوريا"
