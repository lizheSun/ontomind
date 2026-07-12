"""节点发现运行。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class DiscoveryRun(BaseModel):
    __tablename__ = "discovery_runs"

    node_id = Column(Integer, ForeignKey("compute_nodes.id", ondelete="CASCADE"), nullable=False)
    provider_type = Column(String(32), nullable=False, default="opencode")
    status = Column(String(24), nullable=False, default="queued")
    started_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    summary = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
