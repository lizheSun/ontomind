"""计算节点连接配置；凭据仅通过独立 Credential 引用。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint

from app.db.models.base import BaseModel


class NodeConnection(BaseModel):
    __tablename__ = "node_connections"
    __table_args__ = (UniqueConstraint("node_id", name="uq_node_connections_node"),)

    node_id = Column(Integer, ForeignKey("compute_nodes.id", ondelete="CASCADE"), nullable=False)
    connector_type = Column(String(16), nullable=False, comment="local/ssh")
    address = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String(128), nullable=True)
    credential_id = Column(
        Integer, ForeignKey("credentials.id", ondelete="RESTRICT"), nullable=True
    )
    host_key_algorithm = Column(String(64), nullable=True)
    host_key_fingerprint = Column(String(255), nullable=True)
    host_key_status = Column(
        String(16), nullable=False, default="pending", comment="pending/confirmed"
    )
    host_key_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    connect_timeout_seconds = Column(Integer, nullable=False, default=10)
    command_timeout_seconds = Column(Integer, nullable=False, default=30)
    max_concurrency = Column(Integer, nullable=False, default=2)
    managed_roots = Column(JSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
