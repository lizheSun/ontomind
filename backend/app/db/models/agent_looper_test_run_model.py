"""Agent Looper 测试运行记录（用于 SSE test 端点持久化）。"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from app.db.models.base import BaseModel


class AgentLooperTestRun(BaseModel):
    """Agent 联通测试运行：每次 POST /configs/{id}/test 写一行。"""

    __tablename__ = "agent_looper_test_runs"
    __table_args__ = {"comment": "Agent Looper 测试运行记录"}

    config_id = Column(
        Integer,
        ForeignKey("agent_looper_configs.id", ondelete="CASCADE"),
        nullable=False, comment="所属配置",
    )
    version_id = Column(
        Integer, ForeignKey("agent_looper_versions.id"),
        nullable=True, comment="测试时的版本",
    )
    prompt = Column(Text, nullable=False, comment="测试 prompt")
    response = Column(Text, nullable=True, comment="LLM 回复")
    latency_ms = Column(Integer, nullable=True, comment="耗时（毫秒）")
    status = Column(
        String(32), nullable=False, server_default="running",
        comment="running/success/error",
    )
    error = Column(Text, nullable=True, comment="错误信息")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="发起用户")
