"""Kanban API schemas。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "waiting", "completed", "failed"]
PluginId = Literal["opencode", "dsh"]


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    icon: Optional[str] = Field(None, max_length=32)
    color: Optional[str] = Field(None, max_length=20)
    from_template: bool = True


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    icon: Optional[str] = None
    color: Optional[str] = None


class ColumnCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    icon: Optional[str] = None
    color: Optional[str] = None


class ColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    icon: Optional[str] = None
    color: Optional[str] = None
    collapsed: Optional[bool] = None


class ColumnReorder(BaseModel):
    column_ids: list[int] = Field(..., min_length=1)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    column_id: Optional[int] = None
    plugin_id: PluginId = "opencode"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    plugin_id: Optional[PluginId] = None
    run_status: Optional[RunStatus] = None
    summary: Optional[str] = None


class TaskMove(BaseModel):
    column_id: int
    position: int = Field(..., ge=1)


class ColumnResponse(BaseModel):
    id: int
    board_id: int
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    position: int
    collapsed: bool = False
    task_count: int = 0


class TaskResponse(BaseModel):
    id: int
    board_id: int
    column_id: Optional[int] = None
    session_id: Optional[int] = None
    title: str
    plugin_id: str
    run_status: str
    position: int
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BoardResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    position: int
    task_count: int = 0
    columns: list[ColumnResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
