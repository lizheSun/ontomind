"""知识库-业务经验仓储。"""
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.kb_experience_model import KbExperience
from app.db.repositories.base_repo import BaseRepository


class KbExperienceRepository(BaseRepository[KbExperience]):
    """KbExperience 仓储：owner scope + 多列 LIKE 搜索。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbExperience, db)

    def list_by_owner(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[KbExperience]:
        return (
            self.db.query(KbExperience)
            .filter(KbExperience.owner_user_id == user_id)
            .order_by(KbExperience.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    def search_like(self, q: str, limit: int = 20) -> List[KbExperience]:
        like = f"%{q}%"
        return (
            self.db.query(KbExperience)
            .filter(
                or_(
                    KbExperience.title_zh.ilike(like),
                    KbExperience.scenario.ilike(like),
                    KbExperience.content_md.ilike(like),
                    KbExperience.outcome.ilike(like),
                )
            )
            .limit(limit).all()
        )
