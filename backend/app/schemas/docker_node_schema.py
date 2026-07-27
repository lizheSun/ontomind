"""Docker 节点 + 容器创建 校验模型 + 响应模型."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 节点 — 请求
# ---------------------------------------------------------------------------

class DockerHostCreate(BaseModel):
    name: str = Field(..., max_length=128)
    address: str = Field(..., max_length=255, description="IP 或主机名（local 时可留空）")
    conn_type: str = Field(..., pattern=r"^(local|ssh|docker-api)$")
    ssh_port: Optional[int] = Field(default=None, ge=1, le=65535)
    ssh_user: Optional[str] = Field(default=None, max_length=64)
    tls_certs: Optional[str] = Field(default=None, max_length=512, description="TLS 证书目录路径")
    remark: Optional[str] = Field(default=None, max_length=512)


# ---------------------------------------------------------------------------
# 节点 — 响应
# ---------------------------------------------------------------------------

class DockerHostResponse(BaseModel):
    id: int
    name: str
    address: str
    conn_type: str
    online: bool = False
    cpu: str = ""
    mem: str = ""
    disk: str = ""
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    tls_certs: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 容器
# ---------------------------------------------------------------------------

class ContainerCreate(BaseModel):
    name: str = Field(..., max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    image: str = Field(..., max_length=256)
    ports: List[str] = Field(default_factory=list, description="hostPort:containerPort")
    env_vars: List[str] = Field(default_factory=list, description="KEY=VALUE")
    volumes: List[str] = Field(default_factory=list, description="hostPath:containerPath")
    expert_slug: Optional[str] = Field(default=None, max_length=128)


class ContainerInfo(BaseModel):
    id: str
    name: str
    nodeId: int
    expertSlug: Optional[str] = None
    image: str
    status: str
    ports: str = ""
    createdAt: str = ""


# ---------------------------------------------------------------------------
# 节点测试结果
# ---------------------------------------------------------------------------

class NodeTestResult(BaseModel):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# 镜像
# ---------------------------------------------------------------------------

class ImageInfo(BaseModel):
    id: str
    repository: str
    tag: str
    size: str = ""
    created_at: str = ""


class PullImageRequest(BaseModel):
    image: str = Field(..., max_length=512, description="如 python:3.12 或 nginx:latest")
