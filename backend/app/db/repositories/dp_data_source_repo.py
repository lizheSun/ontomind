"""数据平台-数据源仓储。"""
from typing import Optional, List

from sqlalchemy.orm import Session

from app.db.models.dp_data_source_model import DpDataSource
from app.db.repositories.base_repo import BaseRepository


class DpDataSourceRepository(BaseRepository[DpDataSource]):
    """DpDataSource 仓储：CRUD + owner scope + 名称唯一性检查。"""

    def __init__(self, db: Session) -> None:
        super().__init__(DpDataSource, db)

    def list_by_owner(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DpDataSource]:
        return (
            self.db.query(DpDataSource)
            .filter(DpDataSource.owner_user_id == user_id)
            .order_by(DpDataSource.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    def get_by_name(self, name: str) -> Optional[DpDataSource]:
        return self.db.query(DpDataSource).filter(DpDataSource.name == name).first()

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(DpDataSource).filter(DpDataSource.name == name)
        if exclude_id is not None:
            q = q.filter(DpDataSource.id != exclude_id)
        return q.first() is not None
