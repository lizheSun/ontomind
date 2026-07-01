"""Requirement repository."""
from sqlalchemy.orm import Session
from app.db.models.requirement_model import Requirement


class RequirementRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_project(self, project_id: int, skip: int = 0, limit: int = 200):
        return self.db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).order_by(Requirement.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, rid: int):
        return self.db.query(Requirement).filter(Requirement.id == rid).first()

    def create(self, data: dict) -> Requirement:
        obj = Requirement(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, rid: int, data: dict):
        self.db.query(Requirement).filter(Requirement.id == rid).update(data)
        self.db.commit()
        return self.get(rid)

    def delete(self, rid: int):
        self.db.query(Requirement).filter(Requirement.id == rid).delete()
        self.db.commit()
