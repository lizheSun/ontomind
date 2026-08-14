"""DataOps 数据源 Schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SourceType = Literal["doris", "mysql", "hive"]


class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_type: SourceType
    host: str = Field(..., min_length=1, max_length=256)
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = None
    database: Optional[str] = Field(None, max_length=128)
    charset: str = Field("utf8mb4", max_length=32)
    description: Optional[str] = Field(None, max_length=512)


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    host: Optional[str] = Field(None, min_length=1, max_length=256)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=128)
    password: Optional[str] = None
    database: Optional[str] = Field(None, max_length=128)
    charset: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=512)


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: SourceType
    host: str
    port: int
    username: str
    database: Optional[str] = None
    charset: str
    description: Optional[str] = None
    status: str
    is_default: bool = False
    has_password: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConnectionTestRequest(BaseModel):
    """可对已保存源或临时表单探活。"""

    source_id: Optional[int] = None
    source_type: Optional[SourceType] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    charset: Optional[str] = "utf8mb4"


class ConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    latency_ms: Optional[float] = None
    server_info: Optional[str] = None


class SampleQueryRequest(BaseModel):
    database: Optional[str] = None
    table: str = Field(..., min_length=1, max_length=256)
    limit: int = Field(10, ge=1, le=50)


class SampleQueryResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool = False
    sql: str


class ExecuteSqlRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    database: Optional[str] = Field(None, max_length=128)
    max_rows: int = Field(200, ge=1, le=1000)


class ExecuteSqlLog(BaseModel):
    level: Literal["info", "success", "error", "warn"] = "info"
    message: str


class ExecuteSqlResponse(BaseModel):
    ok: bool
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    truncated: bool = False
    affected_rows: Optional[int] = None
    sql: str
    latency_ms: Optional[float] = None
    logs: list[ExecuteSqlLog] = Field(default_factory=list)
    message: Optional[str] = None
