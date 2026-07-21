"""Shared Pydantic schema utilities."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMSchema(BaseModel):
    """Base schema with ORM attribute loading enabled."""

    model_config = ConfigDict(from_attributes=True)


class UUIDSchema(ORMSchema):
    """Schema with a UUID primary key."""

    id: UUID


class TimestampSchema(ORMSchema):
    """Schema with audit timestamps."""

    created_at: datetime
    updated_at: datetime
