"""Task repository."""
from sqlalchemy.orm import Session
from app.db.models.task_model import Task


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_project(self, project_id: int, skip: int = 0, limit: int = 500):
        return self.db.query(Task).filter(
            Task.project_id == project_id
        ).order_by(Task.position, Task.created_at.desc()).offset(skip).limit(limit).all()

    def list_by_requirement(self, requirement_id: int):
        return self.db.query(Task).filter(
            Task.requirement_id == requirement_id
        ).order_by(Task.position).all()

    def get_kanban(self, project_id: int):
        """Return tasks grouped by status for kanban view."""
        tasks = self.db.query(Task).filter(
            Task.project_id == project_id
        ).order_by(Task.position, Task.created_at.desc()).all()
        result = {"todo": [], "in_progress": [], "review": [], "done": []}
        for t in tasks:
            bucket = result.get(t.status, result["todo"])
            bucket.append(t)
        return result

    def get(self, tid: int):
        return self.db.query(Task).filter(Task.id == tid).first()

    def create(self, data: dict) -> Task:
        obj = Task(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, tid: int, data: dict):
        self.db.query(Task).filter(Task.id == tid).update(data)
        self.db.commit()
        return self.get(tid)

    def delete(self, tid: int):
        self.db.query(Task).filter(Task.id == tid).delete()
        self.db.commit()

    def batch_create(self, items: list[dict]) -> list[Task]:
        tasks = []
        for data in items:
            obj = Task(**data)
            self.db.add(obj)
            tasks.append(obj)
        self.db.commit()
        for t in tasks:
            self.db.refresh(t)
        return tasks
