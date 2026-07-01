"""Instance 校验模型."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class InstanceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    instance_type: str = Field(..., description="physical / docker / k8s_pod")
    protocol: str = Field(..., description="ssh / docker_api")
    credential: Optional[Dict[str, Any]] = Field(None, description="认证信息 JSON")
    os: Optional[str] = Field(None, max_length=64)
    cpu_cores: Optional[int] = Field(None, ge=0)
    memory_mb: Optional[int] = Field(None, ge=0)
    disk_gb: Optional[int] = Field(None, ge=0)
    labels: Optional[Dict[str, Any]] = Field(None, description="标签 JSON")
    description: Optional[str] = Field(None, max_length=2000)


class InstanceCreate(InstanceBase):
    pass


class InstanceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    instance_type: Optional[str] = None
    protocol: Optional[str] = None
    credential: Optional[Dict[str, Any]] = None
    os: Optional[str] = Field(None, max_length=64)
    cpu_cores: Optional[int] = Field(None, ge=0)
    memory_mb: Optional[int] = Field(None, ge=0)
    disk_gb: Optional[int] = Field(None, ge=0)
    labels: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)


class InstanceResponse(InstanceBase):
    id: int
    status: str = "offline"
    last_heartbeat: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}
