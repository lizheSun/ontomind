"""知识库-业务经验（T07 完整列定义）。"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from app.db.models.base import BaseModel


class KbExperience(BaseModel):
    """知识库-业务经验：一线经验沉淀（场景/内容/结果/标签）。"""

    __tablename__ = "kb_experiences"
    __table_args__ = {"comment": "知识库-业务经验"}

    library_id = Column(
        Integer, ForeignKey("kb_libraries.id"), nullable=False, comment="所属子库",
    )
    title_zh = Column(String(255), nullable=False, comment="标题")
    scenario = Column(String(255), nullable=True, comment="场景描述")
    content_md = Column(MEDIUMTEXT, nullable=False, comment="正文 markdown")
    outcome = Column(String(255), nullable=True, comment="结果 / 关键指标")
    tags = Column(JSON, nullable=True, comment="标签数组")
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="负责人",
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="创建者",
    )
