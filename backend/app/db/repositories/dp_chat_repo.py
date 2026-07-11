"""数据平台-Text2SQL 会话/消息仓储。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.dp_chat_message_model import DpChatMessage
from app.db.models.dp_chat_session_model import DpChatSession
from app.db.repositories.base_repo import BaseRepository


class DpChatSessionRepository(BaseRepository[DpChatSession]):
    """DpChatSession 仓储：owner scope。"""

    def __init__(self, db: Session) -> None:
        super().__init__(DpChatSession, db)

    def list_by_owner(self, user_id: int) -> List[DpChatSession]:
        return (
            self.db.query(DpChatSession)
            .filter(DpChatSession.user_id == user_id)
            .order_by(DpChatSession.updated_at.desc())
            .all()
        )


class DpChatMessageRepository(BaseRepository[DpChatMessage]):
    """DpChatMessage 仓储：按会话读取、追加、标记执行。"""

    def __init__(self, db: Session) -> None:
        super().__init__(DpChatMessage, db)

    def list_by_session(self, session_id: int) -> List[DpChatMessage]:
        return (
            self.db.query(DpChatMessage)
            .filter(DpChatMessage.session_id == session_id)
            .order_by(DpChatMessage.created_at.asc())
            .all()
        )

    def append(
        self,
        *,
        session_id: int,
        role: str,
        content: str,
        generated_sql: Optional[str] = None,
    ) -> DpChatMessage:
        row = DpChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            generated_sql=generated_sql,
            executed=False,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def mark_executed(self, id: int) -> Optional[DpChatMessage]:
        row = self.get_by_id(id)
        if row is None:
            return None
        row.executed = True
        self.db.flush()
        return row
