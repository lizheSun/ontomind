"""dp: 数据平台-Text2SQL 消息 — 骨架（T04 占位，列由 T06/T07 补完）."""
from app.db.models.base import BaseModel


class DpChatMessage(BaseModel):
    """数据平台-Text2SQL 消息（列由后续任务补完）。"""

    __tablename__ = "dp_chat_messages"
    __table_args__ = {"comment": "数据平台-Text2SQL 消息"}

    # 列由 T06/T07 补完；BaseModel 已提供 id / created_at / updated_at
