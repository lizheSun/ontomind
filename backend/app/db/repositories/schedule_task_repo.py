"""调度任务 + 运行记录 repository（v2 — 日志落盘，不再有 TaskLogEntry 表）."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.schedule_task_model import ScheduleTask, TaskRun
from app.db.repositories.base_repo import BaseRepository


class ScheduleTaskRepository(BaseRepository[ScheduleTask]):
    def __init__(self, db: Session):
        super().__init__(ScheduleTask, db)

    def list_ordered(self, skip: int = 0, limit: int = 200) -> List[ScheduleTask]:
        return (
            self.db.query(ScheduleTask)
            .order_by(ScheduleTask.id.desc())
            .offset(skip).limit(limit).all()
        )

    def list_due(self) -> List[ScheduleTask]:
        """返回已启用、非 running、已到期的非 manual 任务."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ScheduleTask)
            .filter(ScheduleTask.enabled == True)
            .filter(ScheduleTask.status != "running")
            .filter(ScheduleTask.schedule_type.in_(["interval", "cron", "once"]))
            .filter(ScheduleTask.next_run_at != None)
            .filter(ScheduleTask.next_run_at <= now)
            .all()
        )


class TaskRunRepository(BaseRepository[TaskRun]):
    def __init__(self, db: Session):
        super().__init__(TaskRun, db)

    def list_by_task(self, task_id: int, skip: int = 0, limit: int = 50) -> List[TaskRun]:
        return (
            self.db.query(TaskRun)
            .filter(TaskRun.task_id == task_id)
            .order_by(TaskRun.id.desc())
            .offset(skip).limit(limit).all()
        )

    def list_all(self, skip: int = 0, limit: int = 50,
                 task_id: Optional[int] = None,
                 status: Optional[str] = None,
                 trigger: Optional[str] = None) -> List[TaskRun]:
        q = self.db.query(TaskRun)
        if task_id is not None:
            q = q.filter(TaskRun.task_id == task_id)
        if status:
            q = q.filter(TaskRun.status == status)
        if trigger:
            q = q.filter(TaskRun.trigger == trigger)
        return q.order_by(TaskRun.id.desc()).offset(skip).limit(limit).all()
