"""Security audit logging service."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.schemas.audit_log_schema import AuditLogCreate

_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "credential",
    "encrypted_payload",
    "password",
    "payload",
    "secret",
    "token",
}


def _sanitize(value: Any, key: str | None = None) -> Any:
    if key and any(marker in key.lower() for marker in _SENSITIVE_KEYS):
        return "********"
    if isinstance(value, dict):
        return {str(k): _sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


class AuditLogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditLogRepository(db)

    def record(
        self,
        data: AuditLogCreate | None = None,
        *,
        actor_user_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        source_ip: str | None = None,
    ) -> dict:
        """Record an audit event in the caller's current transaction."""
        if data is None:
            if not action or not resource_type:
                raise ValueError("action and resource_type are required")
            data = AuditLogCreate(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                outcome=outcome,
                details=details,
                request_id=request_id,
                source_ip=source_ip,
            )
        values = data.model_dump()
        values["details"] = _sanitize(values.get("details"))
        row = self.repo.create(values)
        return row.to_response_dict()

    def list_logs(self, skip: int = 0, limit: int = 100) -> list[dict]:
        return [row.to_response_dict() for row in self.repo.list_recent(skip, limit)]


AuditService = AuditLogService


__all__ = ["AuditLogService", "AuditService"]
