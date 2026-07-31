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
    restart_policy: Optional[str] = Field(default=None, pattern=r"^(no|always|on-failure|unless-stopped)$")
    network: Optional[str] = Field(default=None, max_length=64)
    # docker run flags，追加在 image 之前，如 "--privileged --gpus all"
    extra_args: Optional[str] = Field(default=None, max_length=512, description="docker run 额外参数（置于镜像名之前）")
    # 启动命令，覆盖镜像 CMD，追加在 image 之后，如 "opencode web --port 4096"
    command: Optional[str] = Field(default=None, max_length=512, description="启动命令，覆盖镜像 CMD")


# ---------------------------------------------------------------------------
# 容器内一次性命令执行
# ---------------------------------------------------------------------------

class ExecRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=2048, description="要执行的命令，如 'ls -la' 或 'opencode --version'")
    workdir: Optional[str] = Field(default=None, max_length=512, description="工作目录（容器内绝对路径）")
    timeout: int = Field(default=30, ge=1, le=300, description="超时秒数")


class ExecResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


class ContainerInfo(BaseModel):
    id: str
    name: str
    nodeId: int
    expertSlug: Optional[str] = None
    image: str
    status: str
    ports: str = ""
    createdAt: str = ""
    network: str = ""
    volumes: str = ""


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
