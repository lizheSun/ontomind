"""Agent 校验模型."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    agent_type: str = Field(..., description="openclaw / opencode / harness / custom")
    version: str = Field("latest", max_length=32)
    runtime: str = Field(..., description="docker / python / node / binary")
    docker_image: Optional[str] = Field(None, max_length=256)
    entrypoint: Optional[str] = Field(None, max_length=2000)
    env_template: Optional[Dict[str, Any]] = Field(None, description="环境变量模板")
    config_template: Optional[str] = Field(None, max_length=10000)
    ports: Optional[List[int]] = Field(None, description="端口列表")
    volume_mounts: Optional[Dict[str, Any]] = Field(None, description="挂载卷")
    resource_limit: Optional[Dict[str, Any]] = Field(None, description="资源限制")
    skill_ids: Optional[List[int]] = Field(None, description="关联技能 ID 列表")
    description: Optional[str] = Field(None, max_length=2000)
    is_active: bool = Field(True)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    agent_type: Optional[str] = None
    version: Optional[str] = Field(None, max_length=32)
    runtime: Optional[str] = None
    docker_image: Optional[str] = Field(None, max_length=256)
    entrypoint: Optional[str] = Field(None, max_length=2000)
    env_template: Optional[Dict[str, Any]] = None
    config_template: Optional[str] = Field(None, max_length=10000)
    ports: Optional[List[int]] = None
    volume_mounts: Optional[Dict[str, Any]] = None
    resource_limit: Optional[Dict[str, Any]] = None
    skill_ids: Optional[List[int]] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class AgentResponse(AgentBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}
