"""调度任务校验模型."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ScheduleTaskCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    task_type: str = Field(default="opencode", max_length=32)
    schedule_type: str = Field(default="manual", max_length=20,
                                pattern=r"^(manual|once|interval|cron)$")
    schedule_expr: Optional[str] = None
    docker_service_id: Optional[int] = None
    opencode_config: dict[str, Any] = Field(default_factory=dict)
    env: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=600, ge=1, le=86400)
    enabled: bool = True


class ScheduleTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_type: Optional[str] = Field(default=None, pattern=r"^(manual|once|interval|cron)$")
    schedule_expr: Optional[str] = None
    docker_service_id: Optional[int] = None
    opencode_config: Optional[dict[str, Any]] = None
    env: Optional[dict[str, Any]] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=86400)
    enabled: Optional[bool] = None
