"""AgentRunJob 长任务 Job 模型（T44）.

长任务生命周期管理表，支持 pending/running/paused/completed/failed/cancelled
状态流转与步骤进度追踪。
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from app.db.models.base import BaseModel


class AgentRunJob(BaseModel):
    """Agent 长任务 Job"""

    __tablename__ = "agent_run_jobs"
    __table_args__ = {"comment": "Agent 长任务 Job"}

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="智能体 ID",
    )
    name = Column(String(256), nullable=False, comment="Job 名称")
    status = Column(
        String(32),
        nullable=False,
        server_default="pending",
        comment="pending/running/paused/completed/failed/cancelled",
    )
    steps = Column(
        JSON,
        nullable=True,
        comment="步骤列表 [{name, status, output, started_at, finished_at}]",
    )
    current_step = Column(
        Integer,
        nullable=False,
        server_default="0",
        comment="当前步骤索引",
    )
    total_steps = Column(
        Integer,
        nullable=False,
        server_default="1",
        comment="总步骤数",
    )
    progress = Column(
        Integer,
        nullable=False,
        server_default="0",
        comment="进度 0-100",
    )
    input_data = Column(JSON, nullable=True, comment="输入数据")
    output_data = Column(JSON, nullable=True, comment="输出数据")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="创建者用户 ID",
    )
