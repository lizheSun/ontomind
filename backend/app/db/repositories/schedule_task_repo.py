"""Schedule task + task run + log repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.schedule_task_model import ScheduleTask, TaskLogEntry, TaskRun
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

    def list_enabled_due(self) -> List[ScheduleTask]:
        """返回需要触发的已启用任务."""
        from sqlalchemy import func
        return (
            self.db.query(ScheduleTask)
            .filter(ScheduleTask.enabled == True)
            .filter(
                (ScheduleTask.next_run_at <= func.now()) | (ScheduleTask.next_run_at.is_(None))
            )
            .filter(ScheduleTask.status != "running")
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


class TaskLogEntryRepository(BaseRepository[TaskLogEntry]):
    def __init__(self, db: Session):
        super().__init__(TaskLogEntry, db)

    def list_by_run(self, run_id: int, skip: int = 0, limit: int = 500) -> List[TaskLogEntry]:
        return (
            self.db.query(TaskLogEntry)
            .filter(TaskLogEntry.run_id == run_id)
            .order_by(TaskLogEntry.sequence.asc())
            .offset(skip).limit(limit).all()
        )

    def get_last_sequence(self, run_id: int) -> int:
        row = (
            self.db.query(TaskLogEntry)
            .filter(TaskLogEntry.run_id == run_id)
            .order_by(TaskLogEntry.sequence.desc())
            .first()
        )
        return row.sequence if row else 0