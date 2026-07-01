"""AgentRun 校验模型."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentRunBase(BaseModel):
    agent_id: Optional[int] = None
    instance_id: Optional[int] = None
    run_name: str = Field(..., min_length=1, max_length=128)
    config_override: Optional[Dict[str, Any]] = Field(None, description="运行时配置覆盖")
    env_override: Optional[Dict[str, Any]] = Field(None, description="运行时环境变量覆盖")


class AgentRunCreate(AgentRunBase):
    pass


class AgentRunUpdate(BaseModel):
    status: Optional[str] = None
    container_id: Optional[str] = None
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None


class AgentRunResponse(AgentRunBase):
    id: int
    status: str = "initializing"
    container_id: Optional[str] = None
    pid: Optional[int] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentRunLogEntry(BaseModel):
    timestamp: str
    level: str = "info"
    message: str
