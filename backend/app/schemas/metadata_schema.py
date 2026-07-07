"""元数据 Schema."""
from typing import Optional, List
from pydantic import BaseModel, Field


class MetaTableUpdate(BaseModel):
    business_description: Optional[str] = None
    purpose: Optional[str] = Field(None, description="dim/fact/ods/dwd/dws/tmp/config/log/other")
    domain: Optional[str] = None
    entity_candidate: Optional[bool] = None
    table_comment_llm: Optional[str] = None


class MetaColumnUpdate(BaseModel):
    column_comment_llm: Optional[str] = None
    semantic_type: Optional[str] = Field(None, description="id/name/amount/time/status/category/description/count/ratio/flag/url/email/phone/code/other")
    business_description: Optional[str] = None
    is_entity_identifier: Optional[bool] = None
    is_relationship_key: Optional[bool] = None
    related_table: Optional[str] = None
    related_column: Optional[str] = None


class ExtractRequest(BaseModel):
    database: Optional[str] = Field(None, description="指定库名，不传则用数据源默认库")


class PreviewRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class AnnotateRequest(BaseModel):
    force: bool = Field(False, description="是否强制重新生成所有注释")
