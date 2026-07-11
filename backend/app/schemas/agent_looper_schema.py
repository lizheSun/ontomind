"""AgentLooper 配置/版本/试跑 Pydantic Schema（T34）。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


AgentLooperType = Literal["custom_looper", "opencode_native", "mcp_agent", "imported"]


class AgentLooperConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: AgentLooperType = "custom_looper"
    description: Optional[str] = None
    config_json: dict[str, Any] = Field(
        default_factory=dict, description="完整配置 JSON schema（第 1 版快照内容）",
    )
    settings: Optional[dict[str, Any]] = None
    resource_bindings: Optional[dict[str, Any]] = None
    credential_ref: Optional[dict[str, Any]] = None
    is_published: bool = False
    model_snapshot: Optional[str] = Field(None, max_length=256)
    prompt_snapshot: Optional[str] = None
    note: Optional[str] = Field(None, max_length=256)


class AgentLooperConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    type: Optional[AgentLooperType] = None
    description: Optional[str] = None
    config_json: Optional[dict[str, Any]] = Field(
        None, description="新版本快照 JSON；不传则不新增版本",
    )
    settings: Optional[dict[str, Any]] = None
    resource_bindings: Optional[dict[str, Any]] = None
    credential_ref: Optional[dict[str, Any]] = None
    is_published: Optional[bool] = None
    model_snapshot: Optional[str] = Field(None, max_length=256)
    prompt_snapshot: Optional[str] = None
    note: Optional[str] = Field(None, max_length=256)


class AgentLooperConfigRead(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str] = None
    current_version_id: Optional[int] = None
    current_version_number: Optional[int] = None
    active_config_json: Optional[dict[str, Any]] = None
    owner_user_id: int
    is_active: bool
    is_published: bool
    settings: Optional[dict[str, Any]] = None
    resource_bindings: Optional[dict[str, Any]] = None
    credential_ref: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("active_config_json", mode="before")
    @classmethod
    def _parse_active_config_json(cls, v: Any) -> Any:
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, str):
            if not v:
                return None
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class AgentLooperVersionRead(BaseModel):
    id: int
    config_id: int
    version_number: int
    config_json: dict[str, Any]
    model_snapshot: Optional[str] = None
    prompt_snapshot: Optional[str] = None
    note: Optional[str] = None
    created_by_user_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("config_json", mode="before")
    @classmethod
    def _parse_config_json(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return {}


class AgentLooperTestRunRead(BaseModel):
    id: int
    config_id: int
    version_id: Optional[int] = None
    prompt: str
    response: Optional[str] = None
    latency_ms: Optional[int] = None
    status: str
    error: Optional[str] = None
    user_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TestRunRequest(BaseModel):
    """POST /agent-looper/configs/{id}/test 请求体。"""
    prompt: str = Field(..., min_length=1, max_length=8000, description="用户测试 prompt")


class TestRunRead(BaseModel):
    id: int
    config_id: int
    version_id: Optional[int] = None
    prompt: str
    response: Optional[str] = None
    latency_ms: Optional[int] = None
    status: str
    error: Optional[str] = None
    user_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
