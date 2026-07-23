"""Doctor ORM model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Enum as SAEnum, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DoctorRole, DoctorStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Doctor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registered doctor or administrator account."""

    __tablename__ = "doctors"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(255))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    national_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )
    certificate: Mapped[str | None] = mapped_column(String(500))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[DoctorRole] = mapped_column(
        SAEnum(DoctorRole, name="doctor_role", native_enum=False),
        nullable=False,
        default=DoctorRole.DOCTOR,
    )
    status: Mapped[DoctorStatus] = mapped_column(
        SAEnum(DoctorStatus, name="doctor_status", native_enum=False),
        nullable=False,
        default=DoctorStatus.ACTIVE,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=false(),
    )

    patients_created: Mapped[list[Patient]] = relationship(
        back_populates="created_by_doctor",
    )
    xray_images: Mapped[list[XrayImage]] = relationship(
        back_populates="doctor",
    )
    diagnosis_results: Mapped[list[DiagnosisResult]] = relationship(
        back_populates="doctor",
    )

    def __repr__(self) -> str:
        return f"Doctor(id={self.id!s}, email={self.email!r}, role={self.role.value})"


from app.models.diagnosis_result import DiagnosisResult
from app.models.patient import Patient
from app.models.xray_image import XrayImage
