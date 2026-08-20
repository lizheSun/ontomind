"""元数据快照 + 自动标注 ORM."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum

from app.db.models.base import BaseModel


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobKind(str, enum.Enum):
    SCAN = "scan"
    ANNOTATE = "annotate"
    BRIEF = "brief"


class MetaStandardStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class MetaBindStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MetaBindSource(str, enum.Enum):
    RULE = "rule"
    LLM = "llm"
    HUMAN = "human"


class AnnotationTargetType(str, enum.Enum):
    TABLE = "table"
    COLUMN = "column"


class AnnotationLabelKind(str, enum.Enum):
    BIZ_NAME = "biz_name"
    BIZ_DESCRIPTION = "biz_description"
    DOMAIN = "domain"
    GLOSSARY = "glossary"
    PII_LEVEL = "pii_level"
    JOIN_KEY = "join_key"
    ENTITY_CANDIDATE = "entity_candidate"
    SEMANTIC_TYPE = "semantic_type"


class AnnotationSource(str, enum.Enum):
    RULE = "rule"
    LLM = "llm"
    HUMAN = "human"


class AnnotationStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class GlossarySource(str, enum.Enum):
    RULES = "rules"
    LLM = "llm"
    MANUAL = "manual"


class MetaScanJob(BaseModel):
    __tablename__ = "meta_scan_jobs"
    __table_args__ = {"comment": "元数据扫描/标注任务"}

    source_id = Column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    database = Column(String(128), nullable=False)
    job_kind = Column(
        SAEnum(JobKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=JobKind.SCAN,
    )
    status = Column(
        SAEnum(ScanStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ScanStatus.PENDING,
    )
    progress = Column(Float, nullable=False, default=0.0)
    with_profile = Column(Boolean, nullable=False, default=False)
    mode = Column(String(16), nullable=True)
    tables_json = Column(JSON, nullable=True)
    stats_json = Column(JSON, nullable=True)
    error_detail = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class MetaTable(BaseModel):
    __tablename__ = "meta_tables"
    __table_args__ = (
        UniqueConstraint("source_id", "database", "table_name", name="uq_meta_table"),
        {"comment": "元数据表快照"},
    )

    source_id = Column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    database = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False)
    table_type = Column(String(64), nullable=True)
    table_comment = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=True)
    engine = Column(String(64), nullable=True)
    biz_name = Column(String(128), nullable=True)
    biz_description = Column(Text, nullable=True)
    domain = Column(String(128), nullable=True)
    column_count = Column(Integer, nullable=True)
    profiled_at = Column(DateTime(timezone=True), nullable=True)


class MetaColumn(BaseModel):
    __tablename__ = "meta_columns"
    __table_args__ = (
        UniqueConstraint("table_id", "column_name", name="uq_meta_column"),
        {"comment": "元数据列快照"},
    )

    table_id = Column(
        Integer, ForeignKey("meta_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name = Column(String(128), nullable=False)
    ordinal = Column(Integer, nullable=False, default=0)
    data_type = Column(String(64), nullable=True)
    column_type = Column(String(128), nullable=True)
    nullable = Column(Boolean, nullable=False, default=True)
    column_key = Column(String(16), nullable=True)
    column_default = Column(Text, nullable=True)
    extra = Column(String(128), nullable=True)
    column_comment = Column(Text, nullable=True)
    biz_name = Column(String(128), nullable=True)
    biz_description = Column(Text, nullable=True)
    semantic_type = Column(String(64), nullable=True)
    pii_level = Column(String(8), nullable=True)
    profile_json = Column(JSON, nullable=True)


class GlossaryTerm(BaseModel):
    __tablename__ = "glossary_terms"
    __table_args__ = {"comment": "业务术语表"}

    name = Column(String(128), nullable=False, unique=True, index=True)
    aliases_json = Column(JSON, nullable=True)
    definition = Column(Text, nullable=True)
    domain = Column(String(128), nullable=True)
    source_type = Column(
        SAEnum(GlossarySource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=GlossarySource.MANUAL,
    )
    source_doc_id = Column(
        Integer, ForeignKey("wiki_documents.id", ondelete="SET NULL"), nullable=True
    )
    confidence = Column(Float, nullable=True)


class Annotation(BaseModel):
    __tablename__ = "annotations"
    __table_args__ = {"comment": "元数据自动/人工标注"}

    target_type = Column(
        SAEnum(AnnotationTargetType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    target_id = Column(Integer, nullable=False, index=True)
    label_kind = Column(
        SAEnum(AnnotationLabelKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    label_value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(AnnotationSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AnnotationSource.RULE,
    )
    status = Column(
        SAEnum(AnnotationStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AnnotationStatus.SUGGESTED,
        index=True,
    )
    evidence_json = Column(JSON, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class MetaStandard(BaseModel):
    __tablename__ = "meta_standards"
    __table_args__ = {"comment": "元数据标准项（一标准可绑多字段）"}

    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    aliases_json = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    semantic_type = Column(String(64), nullable=True)
    data_type_expect = Column(String(64), nullable=True)
    length_rule_json = Column(JSON, nullable=True)
    security_level = Column(String(8), nullable=False, default="L0")
    quality_rule_json = Column(JSON, nullable=True)
    mask_rule = Column(String(64), nullable=True)
    domain = Column(String(128), nullable=True)
    status = Column(
        SAEnum(MetaStandardStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=MetaStandardStatus.PUBLISHED,
    )
    current_version = Column(Integer, nullable=False, default=1)


class MetaStandardVersion(BaseModel):
    __tablename__ = "meta_standard_versions"
    __table_args__ = (
        UniqueConstraint("standard_id", "version", name="uq_meta_standard_version"),
        {"comment": "标准项版本快照"},
    )

    standard_id = Column(
        Integer, ForeignKey("meta_standards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    change_note = Column(String(512), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class MetaColumnStandard(BaseModel):
    __tablename__ = "meta_column_standards"
    __table_args__ = (
        UniqueConstraint("column_id", name="uq_meta_column_standard_column"),
        {"comment": "字段标准绑定（字段 1:1 标准；标准 1:N 字段）"},
    )

    column_id = Column(
        Integer, ForeignKey("meta_columns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    standard_id = Column(
        Integer, ForeignKey("meta_standards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    standard_version = Column(Integer, nullable=False, default=1)
    security_level_override = Column(String(8), nullable=True)
    status = Column(
        SAEnum(MetaBindStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=MetaBindStatus.ACCEPTED,
        index=True,
    )
    source = Column(
        SAEnum(MetaBindSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=MetaBindSource.HUMAN,
    )
    confidence = Column(Float, nullable=True)
    evidence_json = Column(JSON, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class MetaColumnStandardHistory(BaseModel):
    __tablename__ = "meta_column_standard_history"
    __table_args__ = {"comment": "字段标准绑定审计"}

    column_id = Column(
        Integer, ForeignKey("meta_columns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    standard_id = Column(Integer, nullable=True)
    standard_version = Column(Integer, nullable=True)
    action = Column(String(32), nullable=False)
    snapshot_json = Column(JSON, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class MetaDatabaseBrief(BaseModel):
    __tablename__ = "meta_database_briefs"
    __table_args__ = (
        UniqueConstraint("source_id", "database", name="uq_meta_database_brief"),
        {"comment": "库级智能/规则分析概况"},
    )

    source_id = Column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    database = Column(String(128), nullable=False)
    mode = Column(String(16), nullable=False, default="rules")
    content_md = Column(Text, nullable=True)
    stats_json = Column(JSON, nullable=True)
    job_id = Column(
        Integer, ForeignKey("meta_scan_jobs.id", ondelete="SET NULL"), nullable=True
    )


class PlatformLlmSetting(BaseModel):
    __tablename__ = "platform_llm_settings"
    __table_args__ = {"comment": "平台 LLM 配置（支持多套，is_default 标记当前生效）"}

    name = Column(String(128), nullable=False, default="")
    base_url = Column(String(512), nullable=False, default="")
    model = Column(String(128), nullable=False, default="")
    api_key_encrypted = Column(Text, nullable=True)
    timeout = Column(Integer, nullable=False, default=120)
    max_concurrency = Column(Integer, nullable=False, default=4)
    enabled = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
