"""元数据 / 标注 Schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MetaScanCreate(BaseModel):
    source_id: int
    database: str = Field(..., min_length=1, max_length=128)
    tables: Optional[list[str]] = None
    with_profile: bool = False


class MetaScanJobResponse(BaseModel):
    id: int
    source_id: int
    database: str
    job_kind: str
    status: str
    progress: float
    with_profile: bool = False
    mode: Optional[str] = None
    tables_json: Optional[Any] = None
    stats_json: Optional[Any] = None
    error_detail: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MetaColumnResponse(BaseModel):
    id: int
    table_id: int
    column_name: str
    ordinal: int = 0
    data_type: Optional[str] = None
    column_type: Optional[str] = None
    nullable: bool = True
    column_key: Optional[str] = None
    column_default: Optional[str] = None
    extra: Optional[str] = None
    column_comment: Optional[str] = None
    biz_name: Optional[str] = None
    biz_description: Optional[str] = None
    semantic_type: Optional[str] = None
    pii_level: Optional[str] = None
    profile_json: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MetaTableResponse(BaseModel):
    id: int
    source_id: int
    database: str
    table_name: str
    table_type: Optional[str] = None
    table_comment: Optional[str] = None
    row_count: Optional[int] = None
    engine: Optional[str] = None
    biz_name: Optional[str] = None
    biz_description: Optional[str] = None
    domain: Optional[str] = None
    column_count: Optional[int] = None
    profiled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    columns: Optional[list[MetaColumnResponse]] = None

    model_config = {"from_attributes": True}


class MetaTableUpdate(BaseModel):
    biz_name: Optional[str] = Field(None, max_length=128)
    biz_description: Optional[str] = None
    domain: Optional[str] = Field(None, max_length=128)


class MetaColumnUpdate(BaseModel):
    biz_name: Optional[str] = Field(None, max_length=128)
    biz_description: Optional[str] = None
    semantic_type: Optional[str] = Field(None, max_length=64)
    pii_level: Optional[str] = Field(None, max_length=8)


class GlossaryTermCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    aliases: Optional[list[str]] = None
    definition: Optional[str] = None
    domain: Optional[str] = Field(None, max_length=128)
    source_type: Literal["rules", "llm", "manual"] = "manual"
    source_doc_id: Optional[int] = None
    confidence: Optional[float] = None


class GlossaryTermUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    aliases: Optional[list[str]] = None
    definition: Optional[str] = None
    domain: Optional[str] = Field(None, max_length=128)
    confidence: Optional[float] = None


class GlossaryTermResponse(BaseModel):
    id: int
    name: str
    aliases_json: Optional[Any] = None
    definition: Optional[str] = None
    domain: Optional[str] = None
    source_type: str
    source_doc_id: Optional[int] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GlossaryExtractRequest(BaseModel):
    doc_ids: Optional[list[int]] = None
    mode: Literal["rules", "llm"] = "rules"


class AnnotateJobCreate(BaseModel):
    source_id: int
    database: str = Field(..., min_length=1, max_length=128)
    tables: Optional[list[str]] = None
    mode: Literal["rules", "llm", "hybrid"] = "rules"
    label_kinds: Optional[list[str]] = None


class AnnotationResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    label_kind: str
    label_value: str
    confidence: float
    source: str
    status: str
    evidence_json: Optional[Any] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnnotationReviewRequest(BaseModel):
    action: Literal["accept", "reject"]
    value_override: Optional[str] = None


class AnnotationBatchReviewRequest(BaseModel):
    ann_ids: list[int] = Field(..., min_length=1)
    action: Literal["accept", "reject"]


class AnnotateStatsResponse(BaseModel):
    table_count: int = 0
    column_count: int = 0
    table_biz_name_coverage: float = 0.0
    column_biz_name_coverage: float = 0.0
    table_comment_coverage: float = 0.0
    column_comment_coverage: float = 0.0
    accepted_count: int = 0
    suggested_count: int = 0
    rejected_count: int = 0
    pii_distribution: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    standard_coverage: float = 0.0


class MetaStandardCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    aliases: Optional[list[str]] = None
    description: Optional[str] = None
    semantic_type: Optional[str] = Field(None, max_length=64)
    data_type_expect: Optional[str] = Field(None, max_length=64)
    length_rule: Optional[dict[str, Any]] = None
    security_level: str = Field("L0", max_length=8)
    quality_rule: Optional[dict[str, Any]] = None
    mask_rule: Optional[str] = Field(None, max_length=64)
    domain: Optional[str] = Field(None, max_length=128)
    status: Literal["draft", "published"] = "published"


class MetaStandardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    aliases: Optional[list[str]] = None
    description: Optional[str] = None
    semantic_type: Optional[str] = Field(None, max_length=64)
    data_type_expect: Optional[str] = Field(None, max_length=64)
    length_rule: Optional[dict[str, Any]] = None
    security_level: Optional[str] = Field(None, max_length=8)
    quality_rule: Optional[dict[str, Any]] = None
    mask_rule: Optional[str] = Field(None, max_length=64)
    domain: Optional[str] = Field(None, max_length=128)
    status: Optional[Literal["draft", "published"]] = None
    bump_version: bool = False
    change_note: Optional[str] = Field(None, max_length=512)


class MetaStandardResponse(BaseModel):
    id: int
    code: str
    name: str
    aliases_json: Optional[Any] = None
    description: Optional[str] = None
    semantic_type: Optional[str] = None
    data_type_expect: Optional[str] = None
    length_rule_json: Optional[Any] = None
    security_level: str
    quality_rule_json: Optional[Any] = None
    mask_rule: Optional[str] = None
    domain: Optional[str] = None
    status: str
    current_version: int
    bound_column_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ColumnBindRequest(BaseModel):
    standard_id: int
    security_level_override: Optional[str] = Field(None, max_length=8)
    status: Literal["suggested", "accepted"] = "accepted"
    source: Literal["rule", "llm", "human"] = "human"
    confidence: Optional[float] = None
    evidence: Optional[dict[str, Any]] = None


class ColumnBindBatchRequest(BaseModel):
    column_ids: list[int] = Field(..., min_length=1)
    standard_id: int
    security_level_override: Optional[str] = Field(None, max_length=8)


class ColumnWorkspaceItem(BaseModel):
    id: int
    table_id: int
    table_name: str
    column_name: str
    data_type: Optional[str] = None
    column_type: Optional[str] = None
    nullable: bool = True
    column_key: Optional[str] = None
    column_comment: Optional[str] = None
    biz_name: Optional[str] = None
    pii_level: Optional[str] = None
    semantic_type: Optional[str] = None
    profile_json: Optional[Any] = None
    bind_id: Optional[int] = None
    standard_id: Optional[int] = None
    standard_code: Optional[str] = None
    standard_name: Optional[str] = None
    standard_version: Optional[int] = None
    bind_status: Optional[str] = None
    effective_security_level: Optional[str] = None
    length_rule_json: Optional[Any] = None
    quality_rule_json: Optional[Any] = None


class DatabaseBriefCreate(BaseModel):
    source_id: int
    database: str = Field(..., min_length=1, max_length=128)
    mode: Literal["rules", "llm"] = "rules"


class DatabaseBriefResponse(BaseModel):
    id: int
    source_id: int
    database: str
    mode: str
    content_md: Optional[str] = None
    stats_json: Optional[Any] = None
    job_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LlmSettingCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    base_url: str = Field(..., max_length=512)
    model: str = Field(..., max_length=128)
    api_key: str = Field(..., min_length=1)
    timeout: Optional[int] = Field(120, ge=5, le=600)
    max_concurrency: Optional[int] = Field(4, ge=1, le=32)
    enabled: bool = True
    is_default: bool = False


class LlmSettingUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    base_url: Optional[str] = Field(None, max_length=512)
    model: Optional[str] = Field(None, max_length=128)
    api_key: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=5, le=600)
    max_concurrency: Optional[int] = Field(None, ge=1, le=32)
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class LlmSettingTestRequest(BaseModel):
    base_url: str = Field(..., max_length=512)
    model: str = Field(..., max_length=128)
    api_key: str = Field(..., min_length=1)
    timeout: Optional[int] = Field(120, ge=5, le=600)


class LlmSettingResponse(BaseModel):
    id: int = 0
    name: str = ""
    base_url: str = ""
    model: str = ""
    api_key_masked: Optional[str] = None
    has_api_key: bool = False
    timeout: int = 120
    max_concurrency: int = 4
    enabled: bool = True
    is_default: bool = False
    source: Literal["db", "env", "none"] = "none"
    configured: bool = False
