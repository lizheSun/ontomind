"""Docker 节点模型 — 挂载的算力服务器（本地 / SSH / Docker API）.

与 T44 ComputeNode（资源平台元数据）不同：本模型面向"可执行 docker 的远程主机"，
承载连接方式与凭据引用，是算力调度页的挂载对象。
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db.models.base import BaseModel


class DockerHost(BaseModel):
    __tablename__ = "docker_nodes"

    name = Column(String(128), nullable=False, unique=True, comment="节点名称")
    address = Column(String(255), nullable=False, server_default="127.0.0.1", comment="节点地址")
    conn_type = Column(String(20), nullable=False, server_default="local",
                       comment="local / ssh / docker-api")
    ssh_port = Column(Integer, nullable=True, comment="SSH 端口（conn_type=ssh）")
    ssh_user = Column(String(64), nullable=True, comment="SSH 用户（conn_type=ssh）")
    tls_certs = Column(String(512), nullable=True,
                       comment="TLS 证书目录，后端侧路径（conn_type=docker-api）")
    remark = Column(String(512), nullable=True, comment="备注")

    online = Column(Boolean, nullable=False, server_default="0", comment="最近一次探测是否在线")
    cpu = Column(String(32), nullable=True, comment="CPU 展示串，如 8 核")
    mem = Column(String(32), nullable=True, comment="内存展示串，如 16 GB")
    disk = Column(String(32), nullable=True, comment="磁盘展示串")
    server_version = Column(String(64), nullable=True, comment="docker server 版本")
    last_check_at = Column(DateTime(timezone=True), nullable=True, comment="最近探测时间")

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


__all__ = ["DockerHost"]
