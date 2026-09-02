"""容器服务 ORM 模型 — 记录在容器内启动的常驻服务（opencode web/serve 等）.

为什么需要这张表：
容器内用「快速命令」起的服务是一个**运行态**，进程信息只存在于容器里。
后端重启、页面刷新、切换浏览器后就全丢了，AIDE 页面也没法知道有哪些可选源。
所以把「谁在哪个容器的哪个端口起了什么服务」落库，并定期回探真实状态。

状态真实性保证（关键设计）：
- DB 里存的是**声明 + 最近一次探测结果**，不是可信来源
- `last_checked_at` / `status` 由 `refresh_*` 主动探测刷新（容器是否还在 + 端口是否可连）
- 前端展示时一律带上 `last_checked_at`，避免把过期状态当实时
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.models.base import BaseModel


class ServiceKind(str, enum.Enum):
    """服务类型 —— 决定 AIDE 能不能拿它当嵌入源."""

    OPENCODE_WEB = "opencode_web"      # opencode web：仅前端 UI
    OPENCODE_SERVE = "opencode_serve"  # opencode serve：内置 UI + API
    DSH_WEB = "dsh_web"                # DeepSeek Harness Web UI（默认 3080）
    OTHER = "other"                    # 其它常驻服务（仅登记，不做 AIDE 源）


class ServiceStatus(str, enum.Enum):
    """服务状态 —— 由探测结果写入，不由用户指定."""

    RUNNING = "running"    # 容器在跑 + 端口可连
    STOPPED = "stopped"    # 容器在跑但端口连不上（进程挂了）
    UNREACHABLE = "unreachable"  # 容器不在了 / 节点连不上
    UNKNOWN = "unknown"    # 还没探测过


class ContainerService(BaseModel):
    """容器内启动的常驻服务登记表."""

    __tablename__ = "container_services"
    __table_args__ = (
        # 同一个容器的同一个容器内端口只登记一条，重复启动走 upsert
        UniqueConstraint("container_id", "container_port", name="uq_container_port"),
        {"comment": "容器服务登记表（opencode web/serve 等常驻服务）"},
    )

    # ---- 归属 ----
    node_id = Column(
        Integer,
        ForeignKey("compute_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属算力节点",
    )
    node_name = Column(String(128), nullable=False, comment="节点名称快照（避免每次 join）")
    container_id = Column(String(64), nullable=False, index=True, comment="容器 ID（短 ID）")
    container_name = Column(String(255), nullable=False, comment="容器名称")
    image = Column(String(512), nullable=True, comment="容器镜像")

    # ---- 服务定义 ----
    kind = Column(
        SAEnum(ServiceKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ServiceKind.OTHER,
        comment="服务类型: opencode_web / opencode_serve / dsh_web / other",
    )
    name = Column(String(128), nullable=False, comment="服务显示名")
    container_port = Column(Integer, nullable=False, comment="容器内监听端口")
    host_port = Column(Integer, nullable=True, comment="映射到宿主的端口（无映射则为 NULL）")
    # 宿主访问入口，如 http://localhost:14096 —— 无端口映射时为空
    access_url = Column(String(512), nullable=True, comment="宿主可访问 URL")
    command = Column(Text, nullable=True, comment="启动该服务的完整命令")
    log_path = Column(String(512), nullable=True, comment="容器内日志文件路径")
    exec_id = Column(String(32), nullable=True, comment="启动时的 exec 会话 ID")

    # ---- 探测出来的运行态 ----
    status = Column(
        SAEnum(ServiceStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ServiceStatus.UNKNOWN,
        index=True,
        comment="探测状态: running / stopped / unreachable / unknown",
    )
    status_detail = Column(String(512), nullable=True, comment="状态说明（失败原因等）")
    # 服务是否绑在 0.0.0.0 —— 绑 127.0.0.1 时宿主访问不到，是最常见的坑
    bind_address = Column(String(64), nullable=True, comment="实际监听地址（0.0.0.0 / 127.0.0.1）")
    host_reachable = Column(
        Boolean, nullable=False, default=False, comment="宿主能否访问（access_url 探测结果）",
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True, comment="最后探测时间")

    # ---- AIDE 相关 ----
    is_aide_source = Column(
        Boolean, nullable=False, default=False, index=True,
        comment="是否可作为 AIDE 嵌入源（opencode 类 + 宿主可达）",
    )

    created_by_user_id = Column(Integer, nullable=True, comment="登记人")
