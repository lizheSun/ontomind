"""知识库-文档库 Schema。附件通过 multipart 上传；元数据用本 schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KbDocumentMetaCreate(BaseModel):
    """单独走 JSON 时的元数据；文件上传接口另有 multipart form 解包。"""
    title_zh: str = Field(..., min_length=1, max_length=255)
    library_id: int
    description_md: Optional[str] = None
    tags: Optional[list[str]] = None


class KbDocumentUpdate(BaseModel):
    title_zh: Optional[str] = Field(None, min_length=1, max_length=255)
    description_md: Optional[str] = None
    tags: Optional[list[str]] = None


class KbDocumentRead(BaseModel):
    id: int
    library_id: int
    title_zh: str
    filename: str
    storage_path: str = Field(..., description="相对 UPLOAD_DIR")
    mime_type: str
    size_bytes: int
    description_md: Optional[str] = None
    tags: Optional[list[str]] = None
    owner_user_id: int
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
