"""知识库-数据资产（T07 完整列定义）。"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from app.db.models.base import BaseModel


class KbDataAsset(BaseModel):
    """知识库-数据资产：按业务域整理，可关联 meta_tables 与 data_sources。"""

    __tablename__ = "kb_data_assets"
    __table_args__ = (
        # FULLTEXT 索引仅在 InnoDB+MySQL 5.7+ 生效；SQLite/PG 会被忽略。
        Index("ft_kb_data_assets_title_desc", "title_zh", "description_md",
              mysql_prefix="FULLTEXT"),
        {"comment": "知识库-数据资产（按业务域整理）"},
    )

    library_id = Column(
        Integer, ForeignKey("kb_libraries.id"), nullable=False, comment="所属子库",
    )
    title_zh = Column(String(255), nullable=False, comment="中文标题")
    title_en = Column(String(255), nullable=True, comment="英文标题")
    domain = Column(String(64), nullable=True, comment="业务域")
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="责任人 user_id",
    )
    description_md = Column(MEDIUMTEXT, nullable=True, comment="描述 markdown")
    ref_meta_table_id = Column(
        Integer, ForeignKey("meta_tables.id"), nullable=True,
        comment="关联感知层 meta_tables.id",
    )
    ref_data_source_id = Column(
        Integer, ForeignKey("data_sources.id"), nullable=True,
        comment="关联感知层 data_sources.id",
    )
    tags = Column(JSON, nullable=True, comment="标签数组")
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="创建者",
    )
