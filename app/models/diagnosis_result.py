"""Diagnosis result ORM model."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DiagnosisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI-assisted diagnosis output linked to a chest X-ray image."""

    __tablename__ = "diagnosis_results"

    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    xray_image_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("xray_images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    predicted_label: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    report_text: Mapped[str | None] = mapped_column(Text)
    visual_map_path: Mapped[str | None] = mapped_column(String(500))

    patient: Mapped[Patient] = relationship(
        back_populates="diagnosis_results",
    )
    doctor: Mapped[Doctor] = relationship(
        back_populates="diagnosis_results",
    )
    xray_image: Mapped[XrayImage] = relationship(
        back_populates="diagnosis_result",
    )

    def __repr__(self) -> str:
        return (
            f"DiagnosisResult(id={self.id!s}, predicted_label={self.predicted_label!r}, "
            f"confidence_score={self.confidence_score})"
        )


from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.xray_image import XrayImage
