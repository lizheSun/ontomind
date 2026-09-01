"""Harness Repository — 仅 flush。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.harness_model import HarnessMessage, HarnessSession


class HarnessRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_sessions(self, user_id: int, limit: int = 80) -> list[HarnessSession]:
        return (
            self.db.query(HarnessSession)
            .filter(HarnessSession.user_id == user_id)
            .order_by(HarnessSession.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )

    def get_session(self, session_id: int) -> Optional[HarnessSession]:
        return self.db.get(HarnessSession, session_id)

    def add_session(self, row: HarnessSession) -> HarnessSession:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_session(self, row: HarnessSession) -> None:
        self.db.query(HarnessMessage).filter(HarnessMessage.session_id == row.id).delete()
        self.db.delete(row)
        self.db.flush()

    def list_messages(self, session_id: int) -> list[HarnessMessage]:
        return (
            self.db.query(HarnessMessage)
            .filter(HarnessMessage.session_id == session_id)
            .order_by(HarnessMessage.id.asc())
            .all()
        )

    def add_message(self, row: HarnessMessage) -> HarnessMessage:
        self.db.add(row)
        self.db.flush()
        return row
