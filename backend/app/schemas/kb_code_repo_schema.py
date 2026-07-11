"""知识库-代码库 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KbCodeRepoBase(BaseModel):
    title_zh: str = Field(..., min_length=1, max_length=255)
    repo_url: str = Field(..., min_length=1, max_length=512)
    branch: str = Field("main", max_length=128)
    language: Optional[str] = Field(None, max_length=32)
    description_md: Optional[str] = None
    tags: Optional[list[str]] = None


class KbCodeRepoCreate(KbCodeRepoBase):
    library_id: int


class KbCodeRepoUpdate(BaseModel):
    title_zh: Optional[str] = Field(None, min_length=1, max_length=255)
    repo_url: Optional[str] = Field(None, max_length=512)
    branch: Optional[str] = Field(None, max_length=128)
    language: Optional[str] = Field(None, max_length=32)
    description_md: Optional[str] = None
    tags: Optional[list[str]] = None


class KbCodeRepoRead(KbCodeRepoBase):
    id: int
    library_id: int
    owner_user_id: int
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
