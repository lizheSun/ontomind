"""Expert repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.expert_model import Expert
from app.db.repositories.base_repo import BaseRepository


class ExpertRepository(BaseRepository[Expert]):
    def __init__(self, db: Session):
        super().__init__(Expert, db)

    def get_by_slug(self, slug: str) -> Optional[Expert]:
        return self.db.query(Expert).filter(Expert.slug == slug).first()

    def list_ordered(self, skip: int = 0, limit: int = 200) -> List[Expert]:
        return (
            self.db.query(Expert)
            .order_by(Expert.sort_order.asc(), Expert.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_online(self) -> List[Expert]:
        return (
            self.db.query(Expert)
            .filter(Expert.status == "online")
            .order_by(Expert.sort_order.asc(), Expert.id.asc())
            .all()
        )
