"""知识库-业务经验 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KbExperienceBase(BaseModel):
    title_zh: str = Field(..., min_length=1, max_length=255)
    scenario: Optional[str] = Field(None, max_length=255)
    content_md: str = Field(..., min_length=1)
    outcome: Optional[str] = Field(None, max_length=255)
    tags: Optional[list[str]] = None


class KbExperienceCreate(KbExperienceBase):
    library_id: int


class KbExperienceUpdate(BaseModel):
    title_zh: Optional[str] = Field(None, min_length=1, max_length=255)
    scenario: Optional[str] = Field(None, max_length=255)
    content_md: Optional[str] = None
    outcome: Optional[str] = Field(None, max_length=255)
    tags: Optional[list[str]] = None


class KbExperienceRead(KbExperienceBase):
    id: int
    library_id: int
    owner_user_id: int
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
