"""Patient ORM model."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Gender
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Patient registered in the PulmoScan system."""

    __tablename__ = "patients"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SAEnum(Gender, name="gender", native_enum=False),
        nullable=False,
    )
    phone_number: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    national_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    created_by_doctor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_by_doctor: Mapped[Doctor] = relationship(
        back_populates="patients_created",
    )
    xray_images: Mapped[list[XrayImage]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    diagnosis_results: Mapped[list[DiagnosisResult]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Patient(id={self.id!s}, full_name={self.full_name!r})"


from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.xray_image import XrayImage
