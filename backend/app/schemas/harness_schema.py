"""Harness API schemas。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PluginInfoResponse(BaseModel):
    id: str
    label: str
    available: bool
    detail: str = ""
    binary: str = ""


class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=256)
    plugin_id: Literal["opencode", "dsh"] = "opencode"
    workspace_path: Optional[str] = Field(None, max_length=1024)


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    plugin_id: Optional[Literal["opencode", "dsh"]] = None
    workspace_path: Optional[str] = Field(None, min_length=1, max_length=1024)


class SessionResponse(BaseModel):
    id: int
    title: str
    plugin_id: str
    plugin_session_id: Optional[str] = None
    workspace_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    parts: list[dict[str, Any]]
    error_text: Optional[str] = None
    created_at: Optional[datetime] = None


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)
    plugin_id: Optional[Literal["opencode", "dsh"]] = None
    attachments: list[str] = Field(default_factory=list, max_length=12)


class PromptOptimizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8_000)
    plugin_id: Optional[Literal["opencode", "dsh"]] = None


class PromptOptimizeResponse(BaseModel):
    text: str


class WorkspaceItem(BaseModel):
    path: str
    label: str
    kind: str = "recent"


class WorkspaceListResponse(BaseModel):
    home: str
    recents: list[WorkspaceItem] = []


class UploadedFile(BaseModel):
    name: str
    rel: str
    size: int
