"""数据源仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.data_source_model import DataSource


class DataSourceRepository(BaseRepository[DataSource]):
    """数据源仓库"""

    def __init__(self, db: Session):
        super().__init__(DataSource, db)

    def get_by_name(self, name: str) -> Optional[DataSource]:
        return self.db.query(DataSource).filter(DataSource.name == name).first()

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(DataSource).filter(DataSource.name == name)
        if exclude_id is not None:
            q = q.filter(DataSource.id != exclude_id)
        return q.first() is not None

    def get_active_sources(self) -> List[DataSource]:
        return self.db.query(DataSource).filter(DataSource.is_active == True).all()

    def get_by_type(self, source_type: str) -> List[DataSource]:
        return self.db.query(DataSource).filter(DataSource.source_type == source_type).all()
