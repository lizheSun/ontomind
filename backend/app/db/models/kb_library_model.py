"""知识库-子库定义（T07 完整列定义 + 种子数据由 seed_kb.py 处理）。"""
from sqlalchemy import Column, String, Integer, Text, Enum as SAEnum
from app.db.models.base import BaseModel


class KbLibrary(BaseModel):
    """知识库-子库定义：四条种子行（data_asset/code_repo/document/experience）。"""

    __tablename__ = "kb_libraries"
    __table_args__ = {"comment": "知识库-子库定义（4 条种子行）"}

    code = Column(
        SAEnum("data_asset", "code_repo", "document", "experience", name="kb_lib_code"),
        nullable=False, unique=True, comment="子库编码",
    )
    name_zh = Column(String(64), nullable=False, comment="子库中文名")
    icon = Column(String(64), nullable=False, comment="antd icon 名（DatabaseOutlined 等）")
    description = Column(Text, nullable=True, comment="子库描述")
    sort_order = Column(
        Integer, nullable=False, server_default="0", comment="排序（升序）",
    )
