"""Centralized audit logging business logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import AuditAction, AuditEntityType

logger = logging.getLogger(__name__)

_SENSITIVE_DETAIL_KEYS = {
    "password",
    "password_hash",
    "current_password",
    "new_password",
    "access_token",
    "refresh_token",
    "refresh_token_hash",
    "token",
    "authorization",
    "secret_key",
    "secret",
    "supabase_service_role_key",
    "service_role_key",
    "signed_url",
    "signedURL",
}


def get_client_ip(request: Request | None) -> str | None:
    """Extract the best-effort client IP address from a request."""
    if request is None:
        return None

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None

    if request.client is None:
        return None
    return request.client.host


def sanitize_audit_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove sensitive keys before persisting audit details."""
    if details is None:
        return None

    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        if key.lower() in _SENSITIVE_DETAIL_KEYS:
            continue
        if isinstance(value, dict):
            nested = sanitize_audit_details(value)
            if nested:
                sanitized[key] = nested
            continue
        sanitized[key] = value
    return sanitized or None


def audit_operation(
    db: Session,
    *,
    action: AuditAction,
    success: bool,
    request: Request | None = None,
    user_id: UUID | None = None,
    entity_type: AuditEntityType | str | None = None,
    entity_id: UUID | None = None,
    reason: str | None = None,
    ip_address: str | None = None,
    **details: Any,
) -> AuditLog | None:
    """Record a security-sensitive operation with a normalized result payload."""
    payload: dict[str, Any] = {"result": "success" if success else "failure", **details}
    if reason is not None:
        payload["reason"] = reason
    return create_audit_log(
        db,
        action=action,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=payload,
        ip_address=ip_address,
        request=request,
    )


def create_audit_log(
    db: Session,
    *,
    action: AuditAction,
    user_id: UUID | None = None,
    entity_type: AuditEntityType | str | None = None,
    entity_id: UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    request: Request | None = None,
) -> AuditLog | None:
    """Persist an audit event for a business operation.

    Audit write failures are logged and swallowed so the primary API operation
    is not rolled back when audit persistence fails.
    """
    resolved_entity_type: str | None
    if isinstance(entity_type, AuditEntityType):
        resolved_entity_type = entity_type.value
    else:
        resolved_entity_type = entity_type

    resolved_ip = ip_address if ip_address is not None else get_client_ip(request)

    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=resolved_entity_type,
            entity_id=entity_id,
            details=sanitize_audit_details(details),
            ip_address=resolved_ip,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log
    except Exception:
        logger.exception(
            "Failed to create audit log action=%s user_id=%s entity_type=%s entity_id=%s",
            action,
            user_id,
            resolved_entity_type,
            entity_id,
        )
        db.rollback()
        return None


def _apply_audit_filters(
    stmt: Select[Any],
    *,
    user_id: UUID | None = None,
    action: AuditAction | None = None,
    entity_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> Select[Any]:
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if created_from is not None:
        stmt = stmt.where(AuditLog.created_at >= created_from)
    if created_to is not None:
        stmt = stmt.where(AuditLog.created_at <= created_to)
    return stmt


def list_audit_logs(
    db: Session,
    *,
    user_id: UUID | None = None,
    action: AuditAction | None = None,
    entity_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    """Return paginated audit logs matching the provided filters."""
    filters = {
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "created_from": created_from,
        "created_to": created_to,
    }
    count_stmt = _apply_audit_filters(select(func.count()).select_from(AuditLog), **filters)
    total = int(db.scalar(count_stmt) or 0)

    items_stmt = (
        _apply_audit_filters(select(AuditLog), **filters)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(db.scalars(items_stmt).all())
    return items, total
