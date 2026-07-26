"""Patient ORM model."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Gender, SyrianGovernorate
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Patient registered in the PulmoScan system."""

    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    father_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mother_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SAEnum(Gender, name="gender", native_enum=False),
        nullable=False,
    )
    phone_number: Mapped[str | None] = mapped_column(String(10))
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
    national_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    created_by_doctor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
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
        return (
            f"Patient(id={self.id!s}, "
            f"first_name={self.first_name!r}, last_name={self.last_name!r})"
        )


from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.xray_image import XrayImage
