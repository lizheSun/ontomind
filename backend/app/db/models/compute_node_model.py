"""ComputeNode 计算节点模型（T44）.

物理机 / 虚拟机 / 容器宿主机等计算节点的元数据表。
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from app.db.models.base import BaseModel


class ComputeNode(BaseModel):
    """计算节点（物理机/虚拟机/宿主机）"""

    __tablename__ = "compute_nodes"
    __table_args__ = {"comment": "计算节点（物理机/虚拟机）"}

    name = Column(String(128), nullable=False, unique=True, comment="节点名称")
    hostname = Column(String(255), nullable=True, comment="主机名")
    platform = Column(String(64), nullable=True, comment="操作系统（简化）: linux/darwin/windows")
    platform_raw = Column(String(128), nullable=True, comment="操作系统原始字符串")
    cpu_cores = Column(Integer, nullable=True, comment="CPU 核心数")
    memory_mb = Column(Integer, nullable=True, comment="内存 MB")
    disk_gb = Column(Integer, nullable=True, comment="磁盘 GB")
    ip = Column(String(64), nullable=True, comment="IP 地址")
    os_version = Column(String(128), nullable=True, comment="操作系统版本")
    status = Column(
        String(32),
        nullable=False,
        server_default="online",
        comment="online/offline/maintenance",
    )
    last_heartbeat = Column(DateTime, nullable=True, comment="最后心跳时间")
    labels = Column(JSON, nullable=True, comment="标签 JSON")
