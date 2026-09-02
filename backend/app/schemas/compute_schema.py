"""算力管理 Pydantic Schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---- 节点 ----

class ComputeNodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="节点名称")
    description: Optional[str] = Field(None, max_length=512)
    host: str = Field(..., min_length=1, max_length=256, description="主机地址")
    port: int = Field(22, ge=1, le=65535, description="SSH 端口")
    username: str = Field(..., min_length=1, max_length=128, description="SSH 用户名")
    auth_type: str = Field("password", pattern="^(password|key)$", description="认证方式")
    password: Optional[str] = Field(None, description="SSH 密码")
    private_key: Optional[str] = Field(None, description="SSH 私钥 PEM")


class ComputeNodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    host: Optional[str] = Field(None, min_length=1, max_length=256)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=128)
    auth_type: Optional[str] = Field(None, pattern="^(password|key)$")
    password: Optional[str] = None
    private_key: Optional[str] = None


class ComputeNodeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    host: str
    port: int
    username: str
    auth_type: str
    is_local: bool
    status: str
    last_checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Docker 镜像 ----

class ImageInfo(BaseModel):
    id: str
    tags: List[str] = []
    size: str = ""          # 人类可读大小
    created: str = ""       # 人类可读时间


# ---- Docker 容器 ----

class PortMapping(BaseModel):
    """端口映射：宿主端口 → 容器端口。"""
    host_port: int = Field(..., ge=1, le=65535, description="宿主机端口")
    container_port: int = Field(..., ge=1, le=65535, description="容器内端口")
    protocol: str = Field("tcp", pattern="^(tcp|udp)$", description="协议")

    def to_docker_key(self) -> str:
        """docker SDK 的 ports key 形式：'<containerPort>/<proto>'。"""
        return f"{self.container_port}/{self.protocol}"

    def to_cli(self) -> str:
        """docker run -p 的实参：'<hostPort>:<containerPort>[/proto]'。"""
        base = f"{self.host_port}:{self.container_port}"
        return base if self.protocol == "tcp" else f"{base}/{self.protocol}"

    def display(self) -> str:
        base = f"{self.host_port}->{self.container_port}"
        return base if self.protocol == "tcp" else f"{base}/{self.protocol}"


class VolumeMapping(BaseModel):
    """卷挂载：宿主路径（或命名卷） → 容器路径。"""
    host_path: str = Field(..., min_length=1, max_length=1024, description="宿主机路径或命名卷名")
    container_path: str = Field(..., min_length=1, max_length=1024, description="容器内绝对路径")
    read_only: bool = Field(False, description="是否只读挂载")

    def to_cli(self) -> str:
        base = f"{self.host_path}:{self.container_path}"
        return f"{base}:ro" if self.read_only else base

    def display(self) -> str:
        suffix = " (ro)" if self.read_only else ""
        return f"{self.host_path} → {self.container_path}{suffix}"


class EnvVar(BaseModel):
    """环境变量键值对。"""
    key: str = Field(..., min_length=1, max_length=256, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value: str = Field("", max_length=4096)

    def to_cli(self) -> str:
        return f"{self.key}={self.value}"


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str
    # 展示用的端口摘要，如 "4096->14096, 8080->80/udp"
    ports: str = ""
    created: str = ""
    # 结构化字段（前端表单回填用）
    port_mappings: List[PortMapping] = []
    volume_mappings: List[VolumeMapping] = []
    env_vars: List[EnvVar] = []
    command: str = ""
    restart: str = "no"
    network: str = ""
    # 运行细节
    state_detail: str = ""      # docker 原始 Status 文本，如 "Up 5 minutes"
    exit_code: Optional[int] = None
    # 该容器内可用的 shell（供控制台自动选择），如 ["/bin/bash", "/bin/sh"]
    shells: List[str] = []


class ContainerCreateRequest(BaseModel):
    image: str = Field(..., min_length=1, max_length=512, description="镜像名/ID，如 nginx:1.27")
    name: Optional[str] = Field(
        None, max_length=128,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
        description="容器名称，仅字母数字与 _ . -",
    )
    command: Optional[str] = Field(None, max_length=2048, description="启动命令，覆盖镜像 CMD")
    entrypoint: Optional[List[str]] = Field(
        None, description="覆盖镜像 ENTRYPOINT（一般留空；重建容器时用于保留原有覆盖）",
    )
    ports: List[PortMapping] = Field(default_factory=list, description="端口映射列表")
    envs: List[EnvVar] = Field(default_factory=list, description="环境变量列表")
    volumes: List[VolumeMapping] = Field(default_factory=list, description="卷挂载列表")
    restart: str = Field(
        "no", pattern="^(no|always|on-failure|unless-stopped)$", description="重启策略",
    )
    network: Optional[str] = Field(
        None, max_length=64, description="网络模式：bridge/host/none 或自定义网络名",
    )
    auto_pull: bool = Field(True, description="镜像不存在时是否自动拉取")
    start: bool = Field(True, description="创建后是否立即启动")


class ContainerLogsResponse(BaseModel):
    logs: str


class ContainerInspectResponse(BaseModel):
    data: dict


# ---- 容器修改 ----

class ContainerUpdateRequest(BaseModel):
    """容器配置修改 —— 会走 stop → remove → recreate 流程。

    所有字段均为 Optional：不传表示「沿用当前容器的值」，
    传空列表表示「清空该项」（例如 ports=[] 会移除所有端口映射）。
    """
    image: Optional[str] = Field(None, max_length=512, description="新镜像（不填则沿用当前）")
    name: Optional[str] = Field(
        None, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
        description="新容器名（不填则沿用当前）",
    )
    command: Optional[str] = Field(None, max_length=2048, description="启动命令")
    ports: Optional[List[PortMapping]] = Field(None, description="端口映射（传 [] 表示清空）")
    envs: Optional[List[EnvVar]] = Field(None, description="环境变量（传 [] 表示清空）")
    volumes: Optional[List[VolumeMapping]] = Field(None, description="卷挂载（传 [] 表示清空）")
    restart: Optional[str] = Field(
        None, pattern="^(no|always|on-failure|unless-stopped)$", description="重启策略",
    )
    network: Optional[str] = Field(None, max_length=64, description="网络模式")


# ---- 镜像拉取 ----

class ImagePullRequest(BaseModel):
    image: str = Field(..., min_length=1, max_length=512, description="镜像名，如 nginx:1.27")


class ImagePullResponse(BaseModel):
    image: str
    success: bool
    message: str


# ---- 快速命令 ----

class ContainerExecRequest(BaseModel):
    """在容器内执行命令。

    mode:
    - "sync"  同步执行，直接返回 stdout/stderr（适合 ls / cat / echo 这类快命令）
    - "async" 后台执行，返回 exec_id，用日志接口轮询（适合 serve / 长任务）
    """
    command: str = Field("", max_length=8192, description="要执行的命令")
    params: Optional[dict] = Field(None, description="命令模板参数，如 {'port': 4096}")
    template_id: Optional[str] = Field(None, description="命令模板 ID，传入则用模板拼接 command")
    mode: str = Field("async", pattern="^(sync|async)$", description="执行模式")
    workdir: Optional[str] = Field(None, max_length=1024, description="工作目录")
    timeout: int = Field(30, ge=1, le=600, description="sync 模式超时秒数")


class ContainerExecResponse(BaseModel):
    exec_id: str
    container_id: str
    command: str
    started: bool
    mode: str = "async"
    # sync 模式下直接带回结果
    logs: str = ""
    exit_code: Optional[int] = None
    running: bool = False


class ContainerExecLogsResponse(BaseModel):
    exec_id: str
    logs: str
    running: bool
    exit_code: Optional[int] = None


class CommandTemplate(BaseModel):
    id: str
    name: str
    description: str
    command: str
    params: dict


class CommandTemplateListResponse(BaseModel):
    templates: List[dict]


# ---- 命令模板常量 ----

COMMAND_TEMPLATES: List[dict] = [
    {
        "id": "opencode-serve",
        "name": "opencode serve（含 Web UI）",
        "description": (
            "后台启动 opencode serve —— 内置 Web UI + API。"
            "已带 --hostname 0.0.0.0：容器内服务必须绑 0.0.0.0，"
            "否则只监听容器 loopback，宿主通过端口映射访问不到。"
            "日志写入 /var/log/opencode/serve-{port}.log"
        ),
        "command": (
            "mkdir -p /var/log/opencode && "
            "nohup opencode serve --port {port} --hostname {hostname} --cors {cors} "
            "> /var/log/opencode/serve-{port}.log 2>&1 &"
        ),
        "mode": "async",
        "params": {
            "port": {"type": "number", "default": 4096, "label": "监听端口", "example": "4096"},
            "hostname": {
                "type": "string", "default": "0.0.0.0",
                "label": "绑定地址", "example": "0.0.0.0（不要用 127.0.0.1）",
            },
            "cors": {
                "type": "string", "default": "http://localhost:5173",
                "label": "CORS 允许源", "example": "http://localhost:5173",
            },
        },
    },
    {
        "id": "opencode-web",
        "name": "opencode web（仅前端）",
        "description": (
            "后台启动独立 opencode Web UI。"
            "已带 --hostname 0.0.0.0：opencode 默认只绑 127.0.0.1，"
            "在容器里那样跑宿主是访问不到的。日志写入 /var/log/opencode/web-{port}.log"
        ),
        "command": (
            "mkdir -p /var/log/opencode && "
            "nohup opencode web --port {port} --hostname {hostname} "
            "> /var/log/opencode/web-{port}.log 2>&1 &"
        ),
        "mode": "async",
        "params": {
            "port": {"type": "number", "default": 4096, "label": "Web 端口", "example": "4096"},
            "hostname": {
                "type": "string", "default": "0.0.0.0",
                "label": "绑定地址", "example": "0.0.0.0（不要用 127.0.0.1）",
            },
        },
    },
    {
        "id": "dsh-web",
        "name": "DeepSeek Harness web",
        "description": (
            "后台启动 DeepSeek Harness Web UI（dsh web）。"
            "默认端口 3080。容器内务必 --host 0.0.0.0，否则宿主访问不到。"
            "日志写入 /var/log/dsh/web-{port}.log"
        ),
        "command": (
            "mkdir -p /var/log/dsh && "
            "nohup dsh web --host {hostname} --port {port} --no-open "
            "> /var/log/dsh/web-{port}.log 2>&1 &"
        ),
        "mode": "async",
        "params": {
            "port": {"type": "number", "default": 3080, "label": "Web 端口", "example": "3080"},
            "hostname": {
                "type": "string", "default": "0.0.0.0",
                "label": "绑定地址", "example": "0.0.0.0（不要用 127.0.0.1）",
            },
        },
    },
    {
        "id": "check-bind-address",
        "name": "检查端口绑定地址（排查宿主访问不到）",
        "description": (
            "列出容器内所有 LISTEN 端口及其绑定地址。"
            "宿主访问不到容器服务时先跑这个：绑 127.0.0.1 的服务，"
            "Docker 端口映射一定失效，必须改成 0.0.0.0。"
        ),
        "command": (
            "echo '=== LISTEN 端口（0.0.0.0 才能被宿主访问）==='; "
            "(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) || "
            "awk 'NR>1 && $4==\"0A\" {split($2,a,\":\"); "
            "ip=a[1]; port=strtonum(\"0x\" a[2]); "
            "bind=(ip==\"0100007F\" ? \"127.0.0.1 [仅容器内可访问]\" : "
            "(ip==\"00000000\" ? \"0.0.0.0 [宿主可访问]\" : ip)); "
            "print \"port \" port \"  bind \" bind}' /proc/net/tcp"
        ),
        "mode": "sync",
        "params": {},
    },
    {
        "id": "opencode-version",
        "name": "opencode 版本",
        "description": "查看容器内 opencode 版本，用于确认镜像与 CLI 是否可用",
        "command": "opencode --version",
        "mode": "sync",
        "params": {},
    },
    {
        "id": "list-ports",
        "name": "查看监听端口",
        "description": "列出容器内正在监听的 TCP 端口，排查服务是否起来了",
        "command": "(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | head -30",
        "mode": "sync",
        "params": {},
    },
    {
        "id": "tail-log",
        "name": "查看日志尾部",
        "description": "查看指定日志文件的最后若干行",
        "command": "tail -n {lines} {path}",
        "mode": "sync",
        "params": {
            "path": {
                "type": "string", "default": "/var/log/opencode/serve-4096.log",
                "label": "日志路径", "example": "/var/log/opencode/serve-4096.log",
            },
            "lines": {"type": "number", "default": 100, "label": "行数", "example": "100"},
        },
    },
    {
        "id": "disk-usage",
        "name": "磁盘占用",
        "description": "查看容器内各挂载点的磁盘使用情况",
        "command": "df -h",
        "mode": "sync",
        "params": {},
    },
    {
        "id": "process-list",
        "name": "进程列表",
        "description": "查看容器内运行的进程，确认后台任务是否存活",
        "command": "ps aux 2>/dev/null || ps -ef",
        "mode": "sync",
        "params": {},
    },
]


# ---- AIDE 容器源 ----

class AideContainerSource(BaseModel):
    """可作为 AIDE 嵌入源的容器信息"""
    node_id: int
    node_name: str
    container_id: str
    container_name: str
    port: int               # 宿主机映射端口
    container_port: int     # 容器内端口
    image: str


# ---- 连接测试 ----

class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    node_id: int


# ---- 容器预设（新建容器时的「案例」，避免用户手写） ----

class ContainerPreset(BaseModel):
    id: str
    name: str
    description: str
    image: str
    command: Optional[str] = None
    ports: List[PortMapping] = []
    envs: List[EnvVar] = []
    volumes: List[VolumeMapping] = []
    restart: str = "no"
    network: Optional[str] = None


CONTAINER_PRESETS: List[dict] = [
    {
        "id": "opencode",
        "name": "OpenCode（AI 编码 Agent）",
        "description": "启动 opencode serve，暴露 Web UI + API，可直接作为 AIDE 的嵌入源",
        "image": "openeuler/opencode:1.1.48-oe2403sp4",
        "command": None,
        "ports": [{"host_port": 4096, "container_port": 4096, "protocol": "tcp"}],
        "envs": [],
        "volumes": [],
        "restart": "unless-stopped",
        "network": "bridge",
    },
    {
        "id": "nginx",
        "name": "Nginx（静态站点 / 反代）",
        "description": "经典 Web 服务器，宿主 8080 映射到容器 80，挂载本地目录作为站点根",
        "image": "nginx:1.27-alpine",
        "command": None,
        "ports": [{"host_port": 8080, "container_port": 80, "protocol": "tcp"}],
        "envs": [],
        "volumes": [
            {"host_path": "/tmp/site", "container_path": "/usr/share/nginx/html", "read_only": True},
        ],
        "restart": "unless-stopped",
        "network": "bridge",
    },
    {
        "id": "postgres",
        "name": "PostgreSQL 16",
        "description": "关系型数据库，用命名卷持久化数据，宿主 5432 直连",
        "image": "postgres:16-alpine",
        "command": None,
        "ports": [{"host_port": 5432, "container_port": 5432, "protocol": "tcp"}],
        "envs": [
            {"key": "POSTGRES_PASSWORD", "value": "changeme"},
            {"key": "POSTGRES_DB", "value": "appdb"},
        ],
        "volumes": [
            {"host_path": "pgdata", "container_path": "/var/lib/postgresql/data", "read_only": False},
        ],
        "restart": "unless-stopped",
        "network": "bridge",
    },
    {
        "id": "redis",
        "name": "Redis 7",
        "description": "内存缓存 / 队列，开启 AOF 持久化",
        "image": "redis:7-alpine",
        "command": "redis-server --appendonly yes",
        "ports": [{"host_port": 6379, "container_port": 6379, "protocol": "tcp"}],
        "envs": [],
        "volumes": [
            {"host_path": "redisdata", "container_path": "/data", "read_only": False},
        ],
        "restart": "unless-stopped",
        "network": "bridge",
    },
    {
        "id": "python-dev",
        "name": "Python 3.12 开发容器",
        "description": "常驻的 Python 环境，挂载本地代码目录，进控制台即可开发调试",
        "image": "python:3.12-slim",
        "command": "sleep infinity",
        "ports": [],
        "envs": [{"key": "PYTHONUNBUFFERED", "value": "1"}],
        "volumes": [
            {"host_path": "/tmp/workspace", "container_path": "/workspace", "read_only": False},
        ],
        "restart": "no",
        "network": "bridge",
    },
    {
        "id": "blank",
        "name": "空白（自定义）",
        "description": "什么都不预填，全部自己配置",
        "image": "",
        "command": None,
        "ports": [],
        "envs": [],
        "volumes": [],
        "restart": "no",
        "network": "bridge",
    },
]


# ---- 容器服务登记（container_services 表） ----

class ContainerServiceResponse(BaseModel):
    """容器内常驻服务 —— DB 登记 + 最近一次探测结果。

    ⚠️ `status` / `host_reachable` 是**探测快照**，不是实时值。
    前端务必同时展示 `last_checked_at`，并提供「刷新」入口。
    """
    id: int
    node_id: int
    node_name: str
    container_id: str
    container_name: str
    image: Optional[str] = None

    kind: str                      # opencode_web / opencode_serve / dsh_web / other
    name: str
    container_port: int
    host_port: Optional[int] = None
    access_url: Optional[str] = None
    command: Optional[str] = None
    log_path: Optional[str] = None
    exec_id: Optional[str] = None

    status: str                    # running / stopped / unreachable / unknown
    status_detail: Optional[str] = None
    bind_address: Optional[str] = None
    host_reachable: bool = False
    last_checked_at: Optional[datetime] = None
    is_aide_source: bool = False

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContainerServiceCreate(BaseModel):
    """手工登记一个已在容器里跑着的服务。"""
    container_id: str = Field(..., min_length=1, max_length=64, description="容器 ID")
    container_port: int = Field(..., ge=1, le=65535, description="容器内监听端口")
    kind: str = Field(
        "other",
        pattern="^(opencode_web|opencode_serve|dsh_web|other)$",
        description="服务类型",
    )
    name: Optional[str] = Field(None, max_length=128, description="显示名，留空自动生成")
    command: Optional[str] = Field(None, max_length=2048, description="启动命令（备注用）")
    log_path: Optional[str] = Field(None, max_length=512, description="容器内日志路径")


class ServiceRefreshResult(BaseModel):
    """批量刷新结果。"""
    total: int
    running: int
    stopped: int
    unreachable: int
    services: List[ContainerServiceResponse] = []


# ---- 服务启动预设（在容器里一键起服务，自动登记到 DB） ----

class ServiceLaunchRequest(BaseModel):
    """在容器内启动一个常驻服务并登记到 DB。"""
    kind: str = Field(
        ...,
        pattern="^(opencode_web|opencode_serve|dsh_web)$",
        description="要启动的服务类型",
    )
    container_port: int = Field(
        4096, ge=1, le=65535, description="容器内监听端口（需已做端口映射才能被宿主访问）",
    )
    cors: Optional[str] = Field(
        None, max_length=512, description="CORS 允许源，留空用平台前端地址",
    )
    # 绑定地址固定 0.0.0.0：绑 127.0.0.1 时宿主访问不到（Docker 头号坑）
    hostname: str = Field(
        "0.0.0.0",
        pattern=r"^[0-9.]+$",
        description="监听地址，务必 0.0.0.0，否则宿主访问不到",
    )
