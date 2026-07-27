"""调度任务 & 运行记录校验模型 + 响应模型（v2 — 日志落盘方案）."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

_SCHEDULE_TYPE = r"^(manual|once|interval|cron)$"


# ---------------------------------------------------------------------------
# 任务 — 请求
# ---------------------------------------------------------------------------

class ScheduleTaskCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    command: str = Field(..., min_length=1, description="执行命令（shell）")
    log_dir: str = Field(default="/var/log/ontomind/tasks", max_length=512)
    schedule_type: str = Field(default="manual", pattern=_SCHEDULE_TYPE)
    schedule_expr: Optional[str] = Field(default=None, max_length=256)
    enabled: bool = True


class ScheduleTaskUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = None
    command: Optional[str] = Field(default=None, min_length=1)
    log_dir: Optional[str] = Field(default=None, max_length=512)
    schedule_type: Optional[str] = Field(default=None, pattern=_SCHEDULE_TYPE)
    schedule_expr: Optional[str] = Field(default=None, max_length=256)
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# 任务 — 响应
# ---------------------------------------------------------------------------

class ScheduleTaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    command: str
    log_dir: str
    schedule_type: str
    schedule_expr: Optional[str] = None
    enabled: bool
    status: str = "idle"
    total_runs: int = 0
    success_runs: int = 0
    failed_runs: int = 0
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 运行记录 — 响应
# ---------------------------------------------------------------------------

class TaskRunResponse(BaseModel):
    id: int
    task_id: int
    trigger: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    log_file: str

    model_config = {"from_attributes": True}
