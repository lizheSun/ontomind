"""Audit log repository."""
from sqlalchemy.orm import Session

from app.db.models.audit_log_model import AuditLog
from app.db.repositories.base_repo import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

    def list_recent(self, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


__all__ = ["AuditLogRepository"]
