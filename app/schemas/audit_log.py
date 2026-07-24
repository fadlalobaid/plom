"""Audit log request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AuditAction
from app.schemas.base import ORMSchema, UUIDSchema


class AuditLogResponse(UUIDSchema):
    """Audit log entry returned by the API."""

    user_id: UUID | None
    action: AuditAction
    entity_type: str | None
    entity_id: UUID | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class AuditLogListResponse(ORMSchema):
    """Paginated audit log collection."""

    items: list[AuditLogResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
