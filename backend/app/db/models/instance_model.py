"""计算节点实例模型."""
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SAEnum, JSON
import enum
from app.db.models.base import BaseModel


class InstanceType(str, enum.Enum):
    physical = "physical"
    docker = "docker"
    k8s_pod = "k8s_pod"


class InstanceProtocol(str, enum.Enum):
    ssh = "ssh"
    docker_api = "docker_api"


class InstanceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class Instance(BaseModel):
    """计算节点实例表"""

    __tablename__ = "instances"

    name = Column(String(128), nullable=False, comment="节点名称")
    host = Column(String(255), nullable=False, comment="IP/域名")
    port = Column(Integer, nullable=False, comment="管理端口（SSH/Docker API）")
    instance_type = Column(
        SAEnum(InstanceType, name="instance_type_enum", create_type=False),
        nullable=False,
        comment="节点类型: physical / docker / k8s_pod",
    )
    protocol = Column(
        SAEnum(InstanceProtocol, name="instance_protocol_enum", create_type=False),
        nullable=False,
        comment="管理协议: ssh / docker_api",
    )
    credential = Column(JSON, nullable=True, comment="认证信息（SSH密钥/密码/docker socket等）")
    os = Column(String(64), nullable=True, comment="操作系统")
    cpu_cores = Column(Integer, nullable=True, comment="CPU 核数")
    memory_mb = Column(Integer, nullable=True, comment="内存 MB")
    disk_gb = Column(Integer, nullable=True, comment="磁盘 GB")
    labels = Column(JSON, nullable=True, comment="标签（用于调度匹配）")
    status = Column(
        SAEnum(InstanceStatus, name="instance_status_enum", create_type=False),
        default=InstanceStatus.offline,
        comment="状态: online / offline / maintenance",
    )
    last_heartbeat = Column(DateTime(timezone=True), nullable=True, comment="最后心跳时间")
    description = Column(Text, nullable=True, comment="描述")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "instance_type": self.instance_type.value if hasattr(self.instance_type, "value") else self.instance_type,
            "protocol": self.protocol.value if hasattr(self.protocol, "value") else self.protocol,
            "credential": self.credential,
            "os": self.os,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "disk_gb": self.disk_gb,
            "labels": self.labels,
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
