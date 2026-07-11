"""知识库-标签池 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KbTagRead(BaseModel):
    id: int
    name: str
    color: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KbTagUpsert(BaseModel):
    names: list[str] = Field(..., description="批量幂等 upsert")
