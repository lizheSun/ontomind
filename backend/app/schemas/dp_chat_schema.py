"""数据平台-Text2SQL 会话/消息 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant", "system"]


class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_id: int
    model_config_id: Optional[int] = None


class SessionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    model_config_id: Optional[int] = None


class SessionRead(BaseModel):
    id: int
    name: str
    source_id: int
    user_id: int
    model_config_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="用户提问自然语言")


class MessageRead(BaseModel):
    id: int
    session_id: int
    role: ChatRole
    content: str
    generated_sql: Optional[str] = None
    executed: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
