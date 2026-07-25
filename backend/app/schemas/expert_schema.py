"""Expert 校验模型."""
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExpertCreate(BaseModel):
    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=64, pattern=r"^[a-z0-9-]+$")
    avatar: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    sop: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    mcps: list[str] = Field(default_factory=list)
    tools: dict[str, Any] = Field(default_factory=dict)
    image: Optional[str] = None
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = 4096
    sort_order: Optional[int] = 0


class ExpertUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    sop: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[str] = None
    skills: Optional[list[str]] = None
    mcps: Optional[list[str]] = None
    tools: Optional[dict[str, Any]] = None
    image: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    sort_order: Optional[int] = None


class ExpertAutoDraftRequest(BaseModel):
    """让后端根据几段说明自动填充默认字段."""
    description: str = Field(..., min_length=1, max_length=512)