"""Skill 模板 Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.skill_template_model import SkillFile, SkillTemplate
from app.db.repositories.base_repo import BaseRepository


class SkillTemplateRepository(BaseRepository[SkillTemplate]):
    """Skill 模板数据访问。"""

    def __init__(self, db: Session):
        super().__init__(SkillTemplate, db)

    def get_by_name(self, name: str) -> Optional[SkillTemplate]:
        return self.db.query(self.model).filter(self.model.name == name).first()

    def get_by_names(self, names: List[str]) -> List[SkillTemplate]:
        if not names:
            return []
        return self.db.query(self.model).filter(self.model.name.in_(names)).all()

    def list_filtered(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
    ) -> List[SkillTemplate]:
        q = self.db.query(self.model)
        if category:
            q = q.filter(self.model.category == category)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(
                self.model.name.like(like) | self.model.description.like(like)
            )
        return (
            q.order_by(self.model.category, self.model.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_categories(self) -> List[str]:
        rows = (
            self.db.query(self.model.category)
            .filter(self.model.category.isnot(None))
            .distinct()
            .all()
        )
        return sorted({r[0] for r in rows if r[0]})


class SkillFileRepository(BaseRepository[SkillFile]):
    """Skill 附属文件数据访问。"""

    def __init__(self, db: Session):
        super().__init__(SkillFile, db)

    def list_by_skill(self, skill_id: int) -> List[SkillFile]:
        return (
            self.db.query(self.model)
            .filter(self.model.skill_template_id == skill_id)
            .order_by(self.model.rel_path)
            .all()
        )

    def get_by_path(self, skill_id: int, rel_path: str) -> Optional[SkillFile]:
        return (
            self.db.query(self.model)
            .filter(
                self.model.skill_template_id == skill_id,
                self.model.rel_path == rel_path,
            )
            .first()
        )

    def delete_by_skill(self, skill_id: int) -> int:
        """整批替换文件时先清空（调用方随后重建）。"""
        rows = (
            self.db.query(self.model)
            .filter(self.model.skill_template_id == skill_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return int(rows or 0)
