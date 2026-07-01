"""Project repository."""
from sqlalchemy.orm import Session
from app.db.models.project_model import Project


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 50):
        return self.db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, pid: int):
        return self.db.query(Project).filter(Project.id == pid).first()

    def get_by_key(self, key: str):
        return self.db.query(Project).filter(Project.key == key).first()

    def create(self, data: dict) -> Project:
        obj = Project(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, pid: int, data: dict):
        self.db.query(Project).filter(Project.id == pid).update(data)
        self.db.commit()
        return self.get(pid)

    def delete(self, pid: int):
        self.db.query(Project).filter(Project.id == pid).delete()
        self.db.commit()
