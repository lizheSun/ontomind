"""知识库-标签池（T07 完整列定义）。"""
from sqlalchemy import Column, String
from app.db.models.base import BaseModel


class KbTag(BaseModel):
    """知识库-标签池：跨 4 个子库共享的标签词汇表。"""

    __tablename__ = "kb_tags"
    __table_args__ = {"comment": "知识库-标签池（跨子库共享）"}

    name = Column(String(64), nullable=False, unique=True, comment="标签名")
    color = Column(String(32), nullable=False, server_default="blue", comment="展示色（blue/purple/…）")
