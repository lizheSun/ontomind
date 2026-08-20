"""本体 Schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---- Ontology ----

class OntologyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=512)
    domain: Optional[str] = Field(None, max_length=128)


class OntologyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    domain: Optional[str] = Field(None, max_length=128)


class OntologyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    domain: Optional[str] = None
    current_version: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Build Job ----

class OntologyBuildJobCreate(BaseModel):
    mode: Literal["rules", "llm", "hybrid"] = "rules"
    scope: dict[str, Any] = Field(default_factory=dict)
    batch_size: int = Field(8, ge=1, le=50)
    reuse_domain_fragment: Optional[str] = None


class OntologyBuildJobResponse(BaseModel):
    id: int
    ontology_id: int
    status: str
    phase: str
    mode: str
    scope_json: Optional[dict[str, Any]] = None
    batch_size: int = 8
    progress: float = 0.0
    delta_json: Optional[Any] = None
    error_detail: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Object Type ----

class ObjectTypeCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    definition: Optional[str] = None
    parent_key: Optional[str] = None
    aliases: Optional[list[str]] = None
    confidence: float = 1.0
    source: Literal["rule", "llm", "human"] = "human"
    status: Literal["draft", "accepted", "rejected"] = "accepted"


class ObjectTypeUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=256)
    definition: Optional[str] = None
    parent_key: Optional[str] = None
    aliases: Optional[list[str]] = None
    confidence: Optional[float] = None
    status: Optional[Literal["draft", "accepted", "rejected"]] = None


class ObjectTypeResponse(BaseModel):
    id: int
    ontology_id: int
    key: str
    display_name: str
    definition: Optional[str] = None
    parent_key: Optional[str] = None
    aliases: Optional[list[str]] = None
    confidence: float = 0.0
    source: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Property ----

class PropertyCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    data_type: Optional[str] = None
    definition: Optional[str] = None
    confidence: float = 1.0
    source: Literal["rule", "llm", "human"] = "human"
    status: Literal["draft", "accepted", "rejected"] = "accepted"


class PropertyUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=256)
    data_type: Optional[str] = None
    definition: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[Literal["draft", "accepted", "rejected"]] = None


class PropertyResponse(BaseModel):
    id: int
    ontology_id: int
    object_type_id: int
    key: str
    display_name: str
    data_type: Optional[str] = None
    definition: Optional[str] = None
    confidence: float = 0.0
    source: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Link Type ----

class LinkTypeCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    from_key: str = Field(..., min_length=1, max_length=128)
    to_key: str = Field(..., min_length=1, max_length=128)
    cardinality: Optional[str] = None
    definition: Optional[str] = None
    confidence: float = 1.0
    source: Literal["rule", "llm", "human"] = "human"
    status: Literal["draft", "accepted", "rejected"] = "accepted"
    evidence: Optional[dict[str, Any]] = None


class LinkTypeUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=256)
    from_key: Optional[str] = None
    to_key: Optional[str] = None
    cardinality: Optional[str] = None
    definition: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[Literal["draft", "accepted", "rejected"]] = None
    evidence: Optional[dict[str, Any]] = None


class LinkTypeResponse(BaseModel):
    id: int
    ontology_id: int
    key: str
    display_name: str
    from_key: str
    to_key: str
    cardinality: Optional[str] = None
    definition: Optional[str] = None
    confidence: float = 0.0
    source: str
    status: str
    evidence: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Mapping ----

class MappingCreate(BaseModel):
    element_type: Literal["object_type", "property", "link_type"]
    element_key: str = Field(..., min_length=1, max_length=128)
    source_id: int
    database: str = Field(..., min_length=1, max_length=128)
    table_name: str = Field(..., min_length=1, max_length=128)
    column_name: Optional[str] = None
    confidence: float = 1.0
    source: Literal["rule", "llm", "human"] = "human"
    status: Literal["draft", "accepted", "rejected"] = "accepted"


class MappingUpdate(BaseModel):
    column_name: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[Literal["draft", "accepted", "rejected"]] = None


class MappingResponse(BaseModel):
    id: int
    ontology_id: int
    element_type: str
    element_key: str
    source_id: int
    database: str
    table_name: str
    column_name: Optional[str] = None
    confidence: float = 0.0
    source: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Metric ----

class MetricCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    definition: Optional[str] = None
    sql_expr: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 1.0
    source: Literal["rule", "llm", "human"] = "human"
    status: Literal["draft", "accepted", "rejected"] = "accepted"


class MetricUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=256)
    definition: Optional[str] = None
    sql_expr: Optional[str] = None
    unit: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[Literal["draft", "accepted", "rejected"]] = None


class MetricResponse(BaseModel):
    id: int
    ontology_id: int
    key: str
    display_name: str
    definition: Optional[str] = None
    sql_expr: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 0.0
    source: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- CQ ----

class CQCreate(BaseModel):
    question: str = Field(..., min_length=1)
    category: Optional[str] = None
    related_keys: Optional[list[str]] = None


class CQResponse(BaseModel):
    id: int
    ontology_id: int
    question: str
    category: Optional[str] = None
    verify_status: str
    verify_note: Optional[str] = None
    related_keys: Optional[list[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Version / Review / Misc ----

class PublishRequest(BaseModel):
    change_note: Optional[str] = Field(None, max_length=512)


class RollbackRequest(BaseModel):
    version: int = Field(..., ge=1)


class ReviewItem(BaseModel):
    element_type: Literal["object_type", "property", "link_type", "mapping", "metric"]
    element_id: int
    action: Literal["accept", "reject"]


class ReviewRequest(BaseModel):
    items: list[ReviewItem] = Field(default_factory=list)
    accept_all_drafts: bool = False
    reject_all_drafts: bool = False


class InferRelationsRequest(BaseModel):
    scope: dict[str, Any] = Field(default_factory=dict)


class OntologyVersionResponse(BaseModel):
    id: int
    ontology_id: int
    version: int
    snapshot_json: dict[str, Any]
    diff_json: Optional[dict[str, Any]] = None
    change_note: Optional[str] = None
    author_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GraphDataResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
