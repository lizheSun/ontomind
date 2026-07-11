"""知识库-代码库仓储。"""
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.kb_code_repo_model import KbCodeRepo
from app.db.repositories.base_repo import BaseRepository


class KbCodeRepoRepository(BaseRepository[KbCodeRepo]):
    """KbCodeRepo 仓储：owner scope + LIKE 搜索。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbCodeRepo, db)

    def list_by_owner(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[KbCodeRepo]:
        return (
            self.db.query(KbCodeRepo)
            .filter(KbCodeRepo.owner_user_id == user_id)
            .order_by(KbCodeRepo.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    def search_like(self, q: str, limit: int = 20) -> List[KbCodeRepo]:
        like = f"%{q}%"
        return (
            self.db.query(KbCodeRepo)
            .filter(
                or_(
                    KbCodeRepo.title_zh.ilike(like),
                    KbCodeRepo.repo_url.ilike(like),
                    KbCodeRepo.description_md.ilike(like),
                )
            )
            .limit(limit).all()
        )
