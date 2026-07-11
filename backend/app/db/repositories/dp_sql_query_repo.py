"""数据平台-保存的查询仓储。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.dp_sql_query_model import DpSqlQuery
from app.db.repositories.base_repo import BaseRepository


class DpSqlQueryRepository(BaseRepository[DpSqlQuery]):
    """DpSqlQuery 仓储：owner scope + 收藏切换。"""

    def __init__(self, db: Session) -> None:
        super().__init__(DpSqlQuery, db)

    def list_by_owner(
        self,
        user_id: int,
        source_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DpSqlQuery]:
        q = self.db.query(DpSqlQuery).filter(DpSqlQuery.owner_user_id == user_id)
        if source_id is not None:
            q = q.filter(DpSqlQuery.source_id == source_id)
        return q.order_by(DpSqlQuery.created_at.desc()).offset(skip).limit(limit).all()

    def toggle_favorite(self, id: int) -> Optional[DpSqlQuery]:
        obj = self.get_by_id(id)
        if obj is None:
            return None
        obj.is_favorite = not obj.is_favorite
        self.db.flush()
        return obj
