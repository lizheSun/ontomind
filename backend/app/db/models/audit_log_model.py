"""Append-oriented security audit log model."""
from sqlalchemy import Column, ForeignKey, Integer, JSON, String

from app.db.models.base import BaseModel


class AuditLog(BaseModel):
    """Security-relevant action recorded without secret material."""

    __tablename__ = "audit_logs"
    __table_args__ = {"comment": "Agent 平台安全审计日志"}

    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(128), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(128), nullable=True, index=True)
    outcome = Column(String(32), nullable=False, default="success", index=True)
    details = Column(JSON, nullable=True)
    request_id = Column(String(128), nullable=True, index=True)
    source_ip = Column(String(64), nullable=True)

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "actor_user_id": self.actor_user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "details": self.details,
            "request_id": self.request_id,
            "source_ip": self.source_ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


__all__ = ["AuditLog"]
