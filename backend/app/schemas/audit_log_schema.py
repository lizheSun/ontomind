"""Audit log schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    actor_user_id: int | None = None
    action: str = Field(..., min_length=1, max_length=128)
    resource_type: str = Field(..., min_length=1, max_length=64)
    resource_id: str | None = Field(default=None, max_length=128)
    outcome: str = Field(default="success", min_length=1, max_length=32)
    details: dict[str, Any] | None = None
    request_id: str | None = Field(default=None, max_length=128)
    source_ip: str | None = Field(default=None, max_length=64)


class AuditLogResponse(AuditLogCreate):
    id: int
    created_at: str | None = None


__all__ = ["AuditLogCreate", "AuditLogResponse"]
