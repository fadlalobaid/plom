"""Persistent refresh-session ORM model for secure login continuity."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class AuthSession(UUIDPrimaryKeyMixin, Base):
    """Server-side refresh session bound to a doctor account.

    Only a SHA-256 hash of the opaque refresh token is stored. The raw token
    is returned to the client once and never persisted.
    """

    __tablename__ = "auth_sessions"

    doctor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_created: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_last_used: Mapped[str | None] = mapped_column(String(45), nullable=True)

    doctor: Mapped[Doctor] = relationship(back_populates="auth_sessions")

    @property
    def is_revoked(self) -> bool:
        """Return True when this refresh session has been revoked."""
        return self.revoked_at is not None

    def __repr__(self) -> str:
        return (
            f"AuthSession(id={self.id!s}, doctor_id={self.doctor_id!s}, "
            f"revoked={self.is_revoked})"
        )


from app.models.doctor import Doctor  # noqa: E402  # circular import for typing
