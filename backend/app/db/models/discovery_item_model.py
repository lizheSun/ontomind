"""只读发现预览项；正式资源仅在显式 apply 后写入。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint

from app.db.models.base import BaseModel


class DiscoveryItem(BaseModel):
    __tablename__ = "discovery_items"
    __table_args__ = (
        UniqueConstraint(
            "discovery_run_id", "resource_type", "external_key",
            name="uq_discovery_item_external_key",
        ),
    )

    discovery_run_id = Column(
        Integer, ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False
    )
    resource_type = Column(String(24), nullable=False, comment="runtime/agent/skill/mcp")
    external_key = Column(String(512), nullable=False)
    source_path = Column(String(1024), nullable=True)
    fingerprint = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="new")
    remote_snapshot = Column(JSON, nullable=False)
    platform_resource_id = Column(Integer, nullable=True)
    platform_snapshot = Column(JSON, nullable=True)
    diff = Column(JSON, nullable=True)
    decision = Column(String(24), nullable=False, default="pending")
    decided_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
