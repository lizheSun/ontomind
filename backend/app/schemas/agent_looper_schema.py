"""Agent Looper Schemas（T36 侧最小实现：TestRunRequest + TestRunRead）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
