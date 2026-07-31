"""Expert 校验模型 — OALP v1.0."""
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
    top_p: Optional[str] = None
    mode: Optional[str] = Field(default="subagent", pattern=r"^(primary|subagent|all)$")
    subagent_depth: Optional[int] = Field(default=1, ge=0, le=5)
    max_steps: Optional[int] = Field(default=None, ge=1, le=10000)
    system_prompt: Optional[str] = None
    permission: dict[str, Any] = Field(default_factory=dict)
    hooks: list[Any] = Field(default_factory=list)
    evals: list[Any] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    mcps: list[str] = Field(default_factory=list)
    tools: dict[str, Any] = Field(default_factory=dict)
    image: Optional[str] = None
    container_template_id: Optional[int] = None
    bind_skills_to_container: Optional[bool] = None
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
    top_p: Optional[str] = None
    mode: Optional[str] = Field(default=None, pattern=r"^(primary|subagent|all)$")
    subagent_depth: Optional[int] = Field(default=None, ge=0, le=5)
    max_steps: Optional[int] = Field(default=None, ge=1, le=10000)
    system_prompt: Optional[str] = None
    permission: Optional[dict[str, Any]] = None
    hooks: Optional[list[Any]] = None
    evals: Optional[list[Any]] = None
    skills: Optional[list[str]] = None
    mcps: Optional[list[str]] = None
    tools: Optional[dict[str, Any]] = None
    image: Optional[str] = None
    container_template_id: Optional[int] = None
    bind_skills_to_container: Optional[bool] = None
    host: Optional[str] = None
    port: Optional[int] = None
    sort_order: Optional[int] = None


class ExpertAutoDraftRequest(BaseModel):
    """让后端根据几段说明自动填充默认字段."""
    description: str = Field(..., min_length=1, max_length=512)


class ExpertAutoDraftResponse(BaseModel):
    """后端 LLM 自动填充后的草稿（不落库）."""
    name: str
    slug: str
    avatar: str
    description: str
    role: str
    sop: str
    provider: str
    model: str
    temperature: str
    skills: list[str] = []
    mcps: list[str] = []
    tools: dict[str, bool] = {}
    permission: dict[str, Any] = {}


class ExpertDeployContainerRequest(BaseModel):
    """容器化部署请求."""
    node_id: int = Field(..., description="Docker 节点 ID（local / ssh / docker-api）")
    container_template_id: Optional[int] = Field(default=None, description="容器模板 ID，留空用内置 opencode-agent")
    host_port: Optional[int] = Field(default=None, description="宿主机映射端口，留空自动选")
    extra_env: dict[str, str] = Field(default_factory=dict, description="额外环境变量")
    auto_start: bool = Field(default=True, description="创建后自动启动")


class ExpertCloneRequest(BaseModel):
    new_slug: str = Field(..., max_length=64, pattern=r"^[a-z0-9-]+$")
    new_name: Optional[str] = None


# ---- AgentRelation ----

class AgentRelationCreate(BaseModel):
    parent_expert_id: int
    child_expert_id: int
    relation: str = Field(default="delegate", pattern=r"^(delegate|fan_out|review)$")
    condition: Optional[str] = None
    sort_order: int = 0


__all__ = [
    "ExpertCreate", "ExpertUpdate",
    "ExpertAutoDraftRequest", "ExpertAutoDraftResponse",
    "ExpertDeployContainerRequest", "ExpertCloneRequest",
    "AgentRelationCreate",
]
