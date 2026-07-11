"""知识库-数据资产 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KbDataAssetBase(BaseModel):
    title_zh: str = Field(..., min_length=1, max_length=255)
    title_en: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=64)
    description_md: Optional[str] = None
    ref_meta_table_id: Optional[int] = None
    ref_data_source_id: Optional[int] = None
    tags: Optional[list[str]] = None


class KbDataAssetCreate(KbDataAssetBase):
    library_id: int


class KbDataAssetUpdate(BaseModel):
    title_zh: Optional[str] = Field(None, min_length=1, max_length=255)
    title_en: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=64)
    description_md: Optional[str] = None
    ref_meta_table_id: Optional[int] = None
    ref_data_source_id: Optional[int] = None
    tags: Optional[list[str]] = None


class KbDataAssetRead(KbDataAssetBase):
    id: int
    library_id: int
    owner_user_id: int
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
