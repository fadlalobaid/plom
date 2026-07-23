"""X-ray image ORM model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import XrayViewType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class XrayImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Chest X-ray image uploaded for a patient."""

    __tablename__ = "xray_images"

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
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[str | None] = mapped_column(String(100))
    view_type: Mapped[XrayViewType] = mapped_column(
        SAEnum(XrayViewType, name="xray_view_type", native_enum=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    patient: Mapped[Patient] = relationship(
        back_populates="xray_images",
    )
    doctor: Mapped[Doctor] = relationship(
        back_populates="xray_images",
    )
    diagnosis_result: Mapped[DiagnosisResult | None] = relationship(
        back_populates="xray_image",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"XrayImage(id={self.id!s}, patient_id={self.patient_id!s})"


from app.models.diagnosis_result import DiagnosisResult
from app.models.doctor import Doctor
from app.models.patient import Patient
