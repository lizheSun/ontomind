"""数据平台-保存的查询（T06 完整列定义）。"""
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Integer
from app.db.models.base import BaseModel


class DpSqlQuery(BaseModel):
    """数据平台-保存的查询：命名 SQL 片段，可收藏，属主可见。"""

    __tablename__ = "dp_sql_queries"
    __table_args__ = {"comment": "数据平台-保存的 SQL 查询"}

    name = Column(String(128), nullable=False, comment="查询名称")
    source_id = Column(
        Integer, ForeignKey("dp_data_sources.id", ondelete="CASCADE"),
        nullable=False, comment="所属数据源",
    )
    sql_text = Column(Text, nullable=False, comment="SQL 文本")
    is_favorite = Column(
        Boolean, nullable=False, server_default="0", comment="是否收藏",
    )
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="拥有者 user_id",
    )
