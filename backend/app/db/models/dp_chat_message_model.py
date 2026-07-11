"""数据平台-Text2SQL 消息（T06 完整列定义）。"""
from sqlalchemy import Column, Text, Integer, Boolean, ForeignKey, Enum as SAEnum
from app.db.models.base import BaseModel


class DpChatMessage(BaseModel):
    """数据平台-Text2SQL 消息：会话中一条 user/assistant/system 消息。"""

    __tablename__ = "dp_chat_messages"
    __table_args__ = {"comment": "数据平台-Text2SQL 消息"}

    session_id = Column(
        Integer, ForeignKey("dp_chat_sessions.id", ondelete="CASCADE"),
        nullable=False, comment="所属会话",
    )
    role = Column(
        SAEnum("user", "assistant", "system", name="dp_msg_role"),
        nullable=False, comment="消息角色",
    )
    content = Column(Text, nullable=False, comment="消息内容")
    generated_sql = Column(Text, nullable=True, comment="LLM 生成的 SQL（仅 assistant）")
    executed = Column(
        Boolean, nullable=False, server_default="0", comment="生成的 SQL 是否已被用户 apply 执行",
    )
