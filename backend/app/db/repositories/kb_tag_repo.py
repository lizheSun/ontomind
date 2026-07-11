"""知识库-标签池仓储。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.kb_tag_model import KbTag
from app.db.repositories.base_repo import BaseRepository


class KbTagRepository(BaseRepository[KbTag]):
    """KbTag 仓储：全量列出、按名定位、批量幂等 upsert。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbTag, db)

    def list_all(self) -> List[KbTag]:
        return self.db.query(KbTag).order_by(KbTag.name.asc()).all()

    def get_by_name(self, name: str) -> Optional[KbTag]:
        return self.db.query(KbTag).filter(KbTag.name == name).first()

    def upsert_names(self, names: List[str]) -> List[KbTag]:
        """批量幂等 upsert：已有跳过、缺失新建。"""
        result: List[KbTag] = []
        for n in names:
            row = self.get_by_name(n)
            if row is None:
                row = KbTag(name=n, color="blue")
                self.db.add(row)
                self.db.flush()
            result.append(row)
        return result
