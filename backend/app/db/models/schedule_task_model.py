"""调度任务模型（v2 — 命令执行 + 日志文件落盘）.

ScheduleTask: 任务定义（shell 命令 + 日志目录 + 调度规则）
TaskRun:      运行记录（一个任务多条），日志 = 磁盘文件而非 DB 行
日志落盘规则: {log_dir}/{task_id}/{yyyyMMdd}/{task_id}-{HHmmss}-{seed}.log
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.db.models.base import BaseModel


class ScheduleTask(BaseModel):
    __tablename__ = "compute_tasks"

    name = Column(String(128), nullable=False, comment="任务名称")
    description = Column(Text, nullable=True)

    command = Column(Text, nullable=False, comment="执行命令（shell），如 docker run …")
    log_dir = Column(String(512), nullable=False, server_default="/var/log/ontomind/tasks",
                     comment="日志根目录")

    schedule_type = Column(String(20), nullable=False, server_default="manual",
                           comment="manual / once / interval / cron")
    schedule_expr = Column(String(256), nullable=True,
                           comment="cron 表达式 / interval 秒数 / once ISO 时间")

    enabled = Column(Boolean, nullable=False, server_default="1", comment="是否启用调度")
    status = Column(String(20), nullable=False, server_default="idle",
                    comment="idle / running（运行中禁止并发触发同一任务）")

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    total_runs = Column(Integer, nullable=False, server_default="0")
    success_runs = Column(Integer, nullable=False, server_default="0")
    failed_runs = Column(Integer, nullable=False, server_default="0")

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TaskRun(BaseModel):
    __tablename__ = "compute_runs"

    task_id = Column(Integer, ForeignKey("compute_tasks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    trigger = Column(String(20), nullable=False, server_default="manual",
                     comment="manual / schedule")

    status = Column(String(20), nullable=False, server_default="pending",
                    comment="pending / running / success / failed / canceled")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    log_file = Column(String(1024), nullable=True, comment="日志文件完整路径")
    pid = Column(Integer, nullable=True, comment="执行进程 pid（用于停止）")

    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


__all__ = ["ScheduleTask", "TaskRun"]
