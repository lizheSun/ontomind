"""算力节点 ORM 模型 — 存储 SSH 连接配置."""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, Enum as SAEnum
from app.db.models.base import BaseModel
import enum


class NodeStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class AuthType(str, enum.Enum):
    PASSWORD = "password"
    KEY = "key"


class ComputeNode(BaseModel):
    """算力节点 — SSH 可访问的计算节点"""

    __tablename__ = "compute_nodes"
    __table_args__ = {"comment": "算力节点表"}

    name = Column(String(128), nullable=False, unique=True, comment="节点名称")
    description = Column(String(512), nullable=True, comment="节点描述")
    host = Column(String(256), nullable=False, comment="主机地址/IP")
    port = Column(Integer, nullable=False, default=22, comment="SSH 端口")
    username = Column(String(128), nullable=False, comment="SSH 用户名")
    auth_type = Column(
        SAEnum(AuthType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AuthType.PASSWORD,
        comment="认证方式: password / key",
    )
    password = Column(Text, nullable=True, comment="SSH 密码（AES 加密存储）")
    private_key = Column(Text, nullable=True, comment="SSH 私钥（AES 加密存储）")
    is_local = Column(Boolean, nullable=False, default=False, comment="是否本地节点")
    status = Column(
        SAEnum(NodeStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=NodeStatus.UNKNOWN,
        comment="节点状态: online / offline / unknown",
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True, comment="最后探活时间")
