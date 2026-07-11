"""知识库-子库定义仓储。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.kb_library_model import KbLibrary
from app.db.repositories.base_repo import BaseRepository


class KbLibraryRepository(BaseRepository[KbLibrary]):
    """KbLibrary 仓储：按 sort_order 排序、按 code 定位。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbLibrary, db)

    def list_ordered(self) -> List[KbLibrary]:
        return self.db.query(KbLibrary).order_by(KbLibrary.sort_order.asc()).all()

    def get_by_code(self, code: str) -> Optional[KbLibrary]:
        return self.db.query(KbLibrary).filter(KbLibrary.code == code).first()
