"""OpenCode 对话工作台的业务侧会话映射表.

前端直连本机 opencode serve (127.0.0.1:4096) 拿到 session.id 后，
调用 POST /api/v1/opencode/session-link 把 (opencode_session_id, user) 落到本表，
供业务审计使用。

⚠️ 本表不是 opencode 的会话数据源，opencode session 元数据/消息仍以
opencode server 为准；此处只做业务映射。
"""
from sqlalchemy import Column, ForeignKey, Integer, String

from app.db.models.base import BaseModel


class OpencodeSession(BaseModel):
    __tablename__ = "opencode_sessions"

    opencode_session_id = Column(
        String(64), nullable=False, unique=True,
        comment="opencode server 侧的 session.id"
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="业务侧用户"
    )
    title = Column(String(255), nullable=True, comment="会话标题（冗余字段，便于列表查询）")


__all__ = ["OpencodeSession"]