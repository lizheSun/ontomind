"""Docker 服务模型 — 每个 Expert 对应一个 docker 容器（承载 opencode server）.

生命周期：
- 未启动 → docker run → started_at 记录 → status=running
- 关闭：docker stop → status=stopped
- 探测：定时 socket 检查 host_port，同步 status
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class DockerService(BaseModel):
    __tablename__ = "docker_services"

    name = Column(String(128), nullable=False, comment="服务名称（通常与 expert.slug 相同）")
    slug = Column(String(64), nullable=False, unique=True, comment="唯一标识符")
    expert_id = Column(
        Integer, ForeignKey("experts.id", ondelete="SET NULL"), nullable=True,
        comment="关联专家（可空 — 允许独立 docker 服务）"
    )

    image = Column(String(256), nullable=False, comment="Docker 镜像名")
    container_name = Column(String(128), nullable=True, comment="容器名")
    container_id = Column(String(64), nullable=True, comment="Docker 容器 ID")

    host = Column(String(64), nullable=False, server_default="127.0.0.1")
    host_port = Column(Integer, nullable=True, comment="本机映射端口")
    container_port = Column(Integer, nullable=False, server_default="4096", comment="容器内 opencode 端口")

    # opencode CLI 参数配置
    opencode_args = Column(JSON, nullable=False, default=list, comment="opencode serve 启动参数")
    env = Column(JSON, nullable=False, default=dict, comment="环境变量")
    volumes = Column(JSON, nullable=False, default=list, comment="卷映射 [{host: '', container: ''}]")

    status = Column(String(20), nullable=False, server_default="stopped",
                    comment="stopped / starting / running / error")
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    description = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


__all__ = ["DockerService"]
