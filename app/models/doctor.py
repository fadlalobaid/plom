"""User ORM model persisted in the `users` table.

The Python class remains `Doctor` to preserve the existing API/service layer
naming while the database table is named `users`.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Enum as SAEnum, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DoctorRole, DoctorStatus, SyrianGovernorate
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Doctor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registered doctor or administrator account."""

    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    national_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )
    certificate: Mapped[date | None] = mapped_column(Date)
    phone_number: Mapped[str] = mapped_column(String(10), nullable=False)
    governorate: Mapped[SyrianGovernorate] = mapped_column(
        SAEnum(
            SyrianGovernorate,
            name="syrian_governorate",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    area: Mapped[str] = mapped_column(String(255), nullable=False)
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
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Doctor(id={self.id!s}, email={self.email!r}, role={self.role.value})"


from app.models.auth_session import AuthSession
from app.models.diagnosis_result import DiagnosisResult
from app.models.patient import Patient
from app.models.xray_image import XrayImage
