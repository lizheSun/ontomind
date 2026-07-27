"""调度任务模型.

一个任务 = 定时/一次性 触发的 opencode CLI 调用规则.
- schedule_type: manual / once / interval / cron
- 一个 ScheduleTask 有多个 TaskRun 运行记录
- TaskRun 有多个 TaskLogEntry 日志行（可实时流式追加）
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.models.base import BaseModel


class ScheduleTask(BaseModel):
    __tablename__ = "schedule_tasks"

    name = Column(String(128), nullable=False, comment="任务名称")
    description = Column(Text, nullable=True)

    # 类型 & 调度
    task_type = Column(String(32), nullable=False, server_default="opencode",
                       comment="opencode / shell / http_probe（预留）")
    schedule_type = Column(String(20), nullable=False, server_default="manual",
                           comment="manual / once / interval / cron")
    schedule_expr = Column(String(256), nullable=True,
                           comment="cron 表达式 或 interval 秒数 或 once 的 ISO 时间戳")

    # 执行目标：跑在哪个 docker service
    docker_service_id = Column(
        Integer, ForeignKey("docker_services.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # opencode 具体调用配置（system prompt / agent / message / model）
    opencode_config = Column(JSON, nullable=False, default=dict,
                             comment='{"agent":"data-analyst","model":"","prompt":"...","system":"..."}')
    # 环境变量、超时
    env = Column(JSON, nullable=False, default=dict)
    timeout_seconds = Column(Integer, nullable=False, server_default="600")

    # 状态
    enabled = Column(Boolean, nullable=False, server_default="1", comment="是否启用调度")
    status = Column(String(20), nullable=False, server_default="idle",
                    comment="idle / running / paused / disabled")

    # 运行统计
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    total_runs = Column(Integer, nullable=False, server_default="0")
    success_runs = Column(Integer, nullable=False, server_default="0")
    failed_runs = Column(Integer, nullable=False, server_default="0")

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TaskRun(BaseModel):
    __tablename__ = "task_runs"

    task_id = Column(Integer, ForeignKey("schedule_tasks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    trigger = Column(String(20), nullable=False, server_default="manual",
                     comment="manual / schedule / retry")

    status = Column(String(20), nullable=False, server_default="pending",
                    comment="pending / running / success / failed / cancelled / timeout")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # 执行上下文快照
    snapshot = Column(JSON, nullable=False, default=dict, comment="任务快照（防任务后续修改）")
    # 结果
    exit_code = Column(Integer, nullable=True)
    output_summary = Column(Text, nullable=True, comment="最后一段输出（前端列表快速看）")
    error_message = Column(Text, nullable=True)

    # opencode session id（用于跳转 workspace 查看完整对话）
    opencode_session_id = Column(String(64), nullable=True)

    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TaskLogEntry(BaseModel):
    __tablename__ = "task_log_entries"

    run_id = Column(Integer, ForeignKey("task_runs.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    sequence = Column(Integer, nullable=False, comment="同一 run 内的顺序")
    level = Column(String(10), nullable=False, server_default="info",
                   comment="info / warn / error / stdout / stderr / event")
    message = Column(Text, nullable=False)


__all__ = ["ScheduleTask", "TaskRun", "TaskLogEntry"]
