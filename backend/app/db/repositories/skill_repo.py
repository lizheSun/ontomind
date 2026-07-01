"""Skill 仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.skill_model import Skill


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, db: Session):
        super().__init__(Skill, db)

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Skill).filter(Skill.name == name)
        if exclude_id is not None:
            q = q.filter(Skill.id != exclude_id)
        return q.first() is not None

    def get_installed(self) -> List[Skill]:
        return self.db.query(Skill).filter(Skill.is_installed == True).all()

    def get_by_type(self, skill_type: str) -> List[Skill]:
        return self.db.query(Skill).filter(Skill.skill_type == skill_type).all()

    def get_by_tags(self, tags: List[str]) -> List[Skill]:
        from sqlalchemy import or_
        filters = [Skill.tags.contains(tag) for tag in tags]
        return self.db.query(Skill).filter(or_(*filters)).all() if filters else []
