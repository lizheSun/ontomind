"""会话 ORM：harness_sessions / harness_messages。"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class HarnessSession(BaseModel):
    __tablename__ = "harness_sessions"
    __table_args__ = {"comment": "统一会话（OpenCode / DSH 插件）"}

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), nullable=False, default="新会话")
    plugin_id = Column(String(32), nullable=False, default="opencode")
    plugin_session_id = Column(String(128), nullable=True)
    workspace_path = Column(String(1024), nullable=False, default="")


class HarnessMessage(BaseModel):
    __tablename__ = "harness_messages"
    __table_args__ = {"comment": "统一会话消息（parts JSON）"}

    session_id = Column(
        Integer, ForeignKey("harness_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(16), nullable=False)
    parts_json = Column(JSON, nullable=False)
    error_text = Column(Text, nullable=True)
