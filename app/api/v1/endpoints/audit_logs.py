"""Admin-only audit log API endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.enums import AuditAction
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import list_audit_logs

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit-logs"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_model=AuditLogListResponse)
def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[UUID | None, Query(description="Filter by actor user ID")] = None,
    action: Annotated[AuditAction | None, Query(description="Filter by audit action")] = None,
    entity_type: Annotated[
        str | None,
        Query(description="Filter by entity type, e.g. Patient"),
    ] = None,
    created_from: Annotated[
        datetime | None,
        Query(description="Include logs created at or after this timestamp"),
    ] = None,
    created_to: Annotated[
        datetime | None,
        Query(description="Include logs created at or before this timestamp"),
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Maximum number of records to return"),
    ] = 50,
) -> AuditLogListResponse:
    """List audit logs with optional filters and pagination (admin only)."""
    items, total = list_audit_logs(
        db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/user/{user_id}", response_model=AuditLogListResponse)
def get_user_audit_logs(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    action: Annotated[AuditAction | None, Query(description="Filter by audit action")] = None,
    entity_type: Annotated[
        str | None,
        Query(description="Filter by entity type, e.g. Patient"),
    ] = None,
    created_from: Annotated[
        datetime | None,
        Query(description="Include logs created at or after this timestamp"),
    ] = None,
    created_to: Annotated[
        datetime | None,
        Query(description="Include logs created at or before this timestamp"),
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Maximum number of records to return"),
    ] = 50,
) -> AuditLogListResponse:
    """List audit logs for a specific user (admin only)."""
    items, total = list_audit_logs(
        db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
