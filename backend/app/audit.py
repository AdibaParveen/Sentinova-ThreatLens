from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    user=None,
    resource: str = "",
    resource_id: str = "",
    ip: str = "",
    correlation_id: str | None = None,
    result: str = "SUCCESS",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=getattr(user, "id", None),
        user_name=getattr(user, "full_name", None) or getattr(user, "email", "system"),
        role=getattr(user, "role", "") or "",
        action=action,
        resource=resource,
        resource_id=str(resource_id or ""),
        ip_address=ip or "",
        correlation_id=correlation_id or str(uuid.uuid4()),
        result=result,
        metadata_json=metadata or {},
    )
    db.add(entry)
    db.flush()
    return entry
