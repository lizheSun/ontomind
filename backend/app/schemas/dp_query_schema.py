"""数据平台-查询执行 & 保存 & 历史 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


HistoryStatus = Literal["running", "success", "error", "canceled", "timeout"]


class SqlExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="待执行 SQL（守卫拦截 DDL/DML）")
    max_rows: int = Field(1000, ge=1, le=100_000, description="LIMIT 上限")


class ColumnMeta(BaseModel):
    name: str
    db_type: Optional[str] = None
    generic_type: Optional[Literal["string", "numeric", "temporal", "boolean", "json"]] = None


class SqlExecuteResponse(BaseModel):
    columns: list[ColumnMeta]
    rows: list[list[Any]] = Field(..., description="行数据（列表顺序对应 columns）")
    row_count: int
    elapsed_ms: int
    truncated: bool = Field(False, description="是否被 max_rows 截断")


class SavedQueryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_id: int
    sql_text: str = Field(..., min_length=1)
    is_favorite: bool = False


class SavedQueryCreate(SavedQueryBase):
    pass


class SavedQueryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    sql_text: Optional[str] = None
    is_favorite: Optional[bool] = None


class SavedQueryRead(BaseModel):
    id: int
    name: str
    source_id: int
    sql_text: str
    is_favorite: bool
    owner_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QueryHistoryRead(BaseModel):
    """历史列表响应。sql_text 截断到 500 字符（列表用），详情端点可查全文。"""
    id: int
    source_id: int
    user_id: int
    sql_text: str = Field(..., description="列表页会被 service 层截断到 500 字符")
    status: HistoryStatus
    row_count: Optional[int] = None
    elapsed_ms: Optional[int] = None
    error_message: Optional[str] = None
    columns_json: Optional[Any] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
