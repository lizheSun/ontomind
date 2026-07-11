"""AgentLooper 试跑记录模型 — 一次 prompt→response 的观测（T34）。

配合 AGENT_LOOPER_TEST_RUNS_TTL_DAYS 做 TTL 清理（created_at 为 BaseModel 提供）。
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from app.db.models.base import BaseModel


class AgentLooperTestRun(BaseModel):
    """AgentLooper 试跑记录：一次自然语言问答的执行观测。"""

    __tablename__ = "agent_looper_test_runs"
    __table_args__ = {"comment": "AgentLooper 试跑记录（TTL 清理）"}

    config_id = Column(
        Integer,
        ForeignKey("agent_looper_configs.id", ondelete="CASCADE"),
        nullable=False, comment="所属 config id",
    )
    version_id = Column(
        Integer,
        ForeignKey("agent_looper_versions.id"),
        nullable=True, comment="使用的版本 id（可能已被 TTL 清理时保留 NULL）",
    )
    prompt = Column(Text, nullable=False, comment="用户提问 prompt")
    response = Column(Text, nullable=True, comment="agent 回复")
    latency_ms = Column(Integer, nullable=True, comment="端到端耗时 ms")
    status = Column(
        String(32), nullable=False, server_default="running",
        comment="running/success/failed/timeout",
    )
    error = Column(Text, nullable=True, comment="失败原因")
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False,
        comment="发起试跑的 user_id",
    )
    # created_at from BaseModel used for TTL purge
