"""Docker 服务校验模型."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class DockerServiceCreate(BaseModel):
    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=64, pattern=r"^[a-z0-9-]+$")
    expert_id: Optional[int] = None
    image: str = Field(..., max_length=256)
    host: Optional[str] = "127.0.0.1"
    host_port: Optional[int] = None
    container_port: Optional[int] = 4096
    opencode_args: list[str] = Field(default_factory=list)
    env: dict[str, Any] = Field(default_factory=dict)
    volumes: list[dict[str, Any]] = Field(default_factory=list)
    description: Optional[str] = None


class DockerServiceUpdate(BaseModel):
    name: Optional[str] = None
    expert_id: Optional[int] = None
    image: Optional[str] = None
    host: Optional[str] = None
    host_port: Optional[int] = None
    container_port: Optional[int] = None
    opencode_args: Optional[list[str]] = None
    env: Optional[dict[str, Any]] = None
    volumes: Optional[list[dict[str, Any]]] = None
    description: Optional[str] = None
