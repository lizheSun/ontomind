"""Plan repository."""
from sqlalchemy.orm import Session
from app.db.models.plan_model import Plan


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_project(self, project_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(Plan).filter(
            Plan.project_id == project_id
        ).order_by(Plan.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, pid: int):
        return self.db.query(Plan).filter(Plan.id == pid).first()

    def create(self, data: dict) -> Plan:
        obj = Plan(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, pid: int, data: dict):
        self.db.query(Plan).filter(Plan.id == pid).update(data)
        self.db.commit()
        return self.get(pid)

    def delete(self, pid: int):
        self.db.query(Plan).filter(Plan.id == pid).delete()
        self.db.commit()
