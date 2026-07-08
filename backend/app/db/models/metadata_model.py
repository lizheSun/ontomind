"""元数据模型 — 存储从数据源提取的表/字段元信息，用于本体提取."""
import json
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel


class MetaTable(BaseModel):
    """表级元数据 — 每条记录对应数据源中的一张表/视图."""

    __tablename__ = "meta_tables"
    __table_args__ = (
        Index("ix_meta_tables_ds_db_table", "datasource_id", "database_name", "table_name", unique=True),
    )

    datasource_id = Column(Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, comment="关联数据源 ID")
    database_name = Column(String(128), nullable=False, comment="库名/schema 名")
    table_name = Column(String(256), nullable=False, comment="表名")
    table_type = Column(String(32), default="table", comment="类型: table / view / materialized_view")
    table_comment = Column(Text, nullable=True, comment="表注释（从数据库提取）")
    table_comment_llm = Column(Text, nullable=True, comment="LLM 自动生成的表描述（无注释时补充）")

    # 业务元数据（人工或 LLM 填充）
    business_description = Column(Text, nullable=True, comment="业务描述：这张表在业务中做什么用")
    purpose = Column(String(256), nullable=True, comment="用途标签: dim(维度表) / fact(事实表) / ods(原始层) / dwd(明细层) / dws(汇总层) / tmp(临时) / config(配置) / log(日志) / other")
    domain = Column(String(128), nullable=True, comment="业务域: 用户/订单/商品/支付/营销/库存/财务/通用 等")
    entity_candidate = Column(Boolean, default=False, comment="是否为本体候选实体（可提取为本体中的 Entity）")

    # 技术元数据
    row_count = Column(Integer, nullable=True, comment="预估行数")
    column_count = Column(Integer, default=0, comment="字段数量")
    storage_size_mb = Column(Integer, nullable=True, comment="存储大小(MB)")
    engine = Column(String(64), nullable=True, comment="存储引擎: InnoDB/Doris/ClickHouse 等")
    collation = Column(String(64), nullable=True, comment="字符集排序规则")

    # 同步状态
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="最后同步时间")
    sync_status = Column(String(20), default="pending", comment="同步状态: pending/synced/error")

    # 关联字段
    columns = relationship("MetaColumn", back_populates="meta_table", cascade="all, delete-orphan")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "datasource_id": self.datasource_id,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "table_type": self.table_type,
            "table_comment": self.table_comment,
            "table_comment_llm": self.table_comment_llm,
            "business_description": self.business_description,
            "purpose": self.purpose,
            "domain": self.domain,
            "entity_candidate": bool(self.entity_candidate),
            "row_count": self.row_count,
            "column_count": self.column_count,
            "storage_size_mb": self.storage_size_mb,
            "engine": self.engine,
            "collation": self.collation,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "sync_status": self.sync_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MetaColumn(BaseModel):
    """字段级元数据 — 每条记录对应表中一个字段."""

    __tablename__ = "meta_columns"
    __table_args__ = (
        Index("ix_meta_columns_table_col", "meta_table_id", "column_name"),
    )

    meta_table_id = Column(Integer, ForeignKey("meta_tables.id", ondelete="CASCADE"), nullable=False, comment="关联表元数据 ID")
    column_name = Column(String(256), nullable=False, comment="字段名")
    ordinal_position = Column(Integer, default=0, comment="字段顺序（从 1 开始）")

    # 技术元数据（从数据库提取）
    data_type = Column(String(64), nullable=True, comment="数据类型: int/varchar/datetime/decimal 等")
    data_type_full = Column(String(128), nullable=True, comment="完整类型定义: varchar(255)/decimal(10,2) 等")
    is_nullable = Column(Boolean, default=True, comment="是否允许 NULL")
    is_primary_key = Column(Boolean, default=False, comment="是否主键")
    is_unique = Column(Boolean, default=False, comment="是否唯一")
    is_indexed = Column(Boolean, default=False, comment="是否有索引")
    default_value = Column(Text, nullable=True, comment="默认值")
    column_comment = Column(Text, nullable=True, comment="字段注释（从数据库提取）")

    # 业务元数据（LLM 或人工填充）
    column_comment_llm = Column(Text, nullable=True, comment="LLM 自动生成的字段描述")
    semantic_type = Column(String(64), nullable=True, comment="语义类型: id/name/amount/time/status/category/description/count/ratio/flag/url/email/phone/code/other")
    business_description = Column(Text, nullable=True, comment="业务含义描述")

    # 本体映射辅助
    is_entity_identifier = Column(Boolean, default=False, comment="是否为实体标识符（主键/外键 → 本体 Entity 的 key）")
    is_relationship_key = Column(Boolean, default=False, comment="是否为关系键（外键 → 本体 Relationship 的关联字段）")
    related_table = Column(String(256), nullable=True, comment="关联表名（外键指向的表，用于提取关系）")
    related_column = Column(String(256), nullable=True, comment="关联字段名（外键指向的字段）")

    meta_table = relationship("MetaTable", back_populates="columns")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "meta_table_id": self.meta_table_id,
            "column_name": self.column_name,
            "ordinal_position": self.ordinal_position,
            "data_type": self.data_type,
            "data_type_full": self.data_type_full,
            "is_nullable": bool(self.is_nullable),
            "is_primary_key": bool(self.is_primary_key),
            "is_unique": bool(self.is_unique),
            "is_indexed": bool(self.is_indexed),
            "default_value": self.default_value,
            "column_comment": self.column_comment,
            "column_comment_llm": self.column_comment_llm,
            "semantic_type": self.semantic_type,
            "business_description": self.business_description,
            "is_entity_identifier": bool(self.is_entity_identifier),
            "is_relationship_key": bool(self.is_relationship_key),
            "related_table": self.related_table,
            "related_column": self.related_column,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MetaProfile(BaseModel):
    """字段数据画像 — 对数据源中某字段抽样统计，识别空值率/唯一性/枚举/格式.

    每个字段一条记录（按 meta_column_id 唯一），由感知层 profile_data 写入，
    供认知层约束抽取直接使用（枚举 -> 值约束、唯一 -> 函数性、空值率 -> 基数）。
    """

    __tablename__ = "meta_profiles"
    __table_args__ = (
        Index("ix_meta_profiles_col", "meta_column_id", unique=True),
        Index("ix_meta_profiles_table", "meta_table_id"),
        Index("ix_meta_profiles_ds", "datasource_id"),
    )

    datasource_id = Column(Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, comment="关联数据源 ID")
    meta_table_id = Column(Integer, ForeignKey("meta_tables.id", ondelete="CASCADE"), nullable=False, comment="关联表元数据 ID")
    meta_column_id = Column(Integer, ForeignKey("meta_columns.id", ondelete="CASCADE"), nullable=False, comment="关联字段元数据 ID")

    # 基础统计
    row_count = Column(Integer, nullable=True, comment="总行数（采样基准）")
    null_count = Column(Integer, nullable=True, comment="NULL 行数")
    null_ratio = Column(Float, nullable=True, comment="NULL 占比 0~1")
    distinct_count = Column(Integer, nullable=True, comment="去重值数量")

    # 值域
    min_value = Column(Text, nullable=True, comment="最小采样值（数值/日期）")
    max_value = Column(Text, nullable=True, comment="最大采样值（数值/日期）")
    sample_values = Column(Text, nullable=True, comment="JSON 数组：前若干采样值")

    # 格式与枚举识别
    detected_format = Column(String(32), nullable=True, comment="识别格式: email/phone/url/date/id/number/enum/text/other")
    format_confidence = Column(Float, nullable=True, comment="格式识别置信度 0~1")
    is_enum = Column(Boolean, default=False, comment="是否低基数字典枚举")
    enum_values = Column(Text, nullable=True, comment="JSON 数组 [{value,count}]：Top-K 枚举候选")

    # 状态
    profile_status = Column(String(20), default="pending", comment="画像状态: pending/done/failed")
    error = Column(Text, nullable=True, comment="画像失败原因")

    def to_response_dict(self) -> dict:
        enum_vals = None
        if self.enum_values:
            try:
                enum_vals = json.loads(self.enum_values)
            except (json.JSONDecodeError, ValueError):
                enum_vals = None
        samples = None
        if self.sample_values:
            try:
                samples = json.loads(self.sample_values)
            except (json.JSONDecodeError, ValueError):
                samples = None
        return {
            "id": self.id,
            "datasource_id": self.datasource_id,
            "meta_table_id": self.meta_table_id,
            "meta_column_id": self.meta_column_id,
            "row_count": self.row_count,
            "null_count": self.null_count,
            "null_ratio": self.null_ratio,
            "distinct_count": self.distinct_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "sample_values": samples,
            "detected_format": self.detected_format,
            "format_confidence": self.format_confidence,
            "is_enum": bool(self.is_enum),
            "enum_values": enum_vals,
            "profile_status": self.profile_status,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
