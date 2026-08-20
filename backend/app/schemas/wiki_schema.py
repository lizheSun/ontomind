"""Wiki Schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class WikiSpaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=512)
    icon: Optional[str] = Field(None, max_length=32)
    sort_order: int = 0


class WikiSpaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    icon: Optional[str] = Field(None, max_length=32)
    sort_order: Optional[int] = None


class WikiSpaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WikiDocumentCreate(BaseModel):
    space_id: int
    parent_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=256)
    slug: Optional[str] = Field(None, max_length=128)
    content_md: str = ""
    source_type: Literal["paste", "markdown", "url", "manual"] = "manual"
    source_url: Optional[str] = None
    source_meta: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    status: Literal["draft", "published"] = "draft"


class WikiDocumentUpdate(BaseModel):
    parent_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    content_md: Optional[str] = None
    source_url: Optional[str] = None
    source_meta: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    status: Optional[Literal["draft", "published"]] = None
    change_note: Optional[str] = Field(None, max_length=512)


class WikiDocumentListItem(BaseModel):
    id: int
    space_id: int
    parent_id: Optional[int] = None
    title: str
    slug: str
    source_type: str
    source_url: Optional[str] = None
    tags: Optional[list[str]] = None
    status: str
    current_version: int
    word_count: int
    author_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WikiDocumentResponse(WikiDocumentListItem):
    content_md: str = ""
    source_meta: Optional[dict[str, Any]] = None


class WikiDocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version: int
    title: str
    content_md: str
    change_note: Optional[str] = None
    author_user_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WikiImportRequest(BaseModel):
    source_type: Literal["paste", "markdown", "url", "manual"] = "paste"
    title: Optional[str] = None
    content_md: str = Field(..., min_length=1)
    source_url: Optional[str] = None
    source_meta: Optional[dict[str, Any]] = None
    space_id: Optional[int] = None
    parent_id: Optional[int] = None
    tags: Optional[list[str]] = None
    status: Literal["draft", "published"] = "draft"


class WikiRollbackRequest(BaseModel):
    version: int = Field(..., ge=1)


class WikiFetchUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
