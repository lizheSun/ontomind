"""知识库-数据资产仓储。"""
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.kb_data_asset_model import KbDataAsset
from app.db.repositories.base_repo import BaseRepository


class KbDataAssetRepository(BaseRepository[KbDataAsset]):
    """KbDataAsset 仓储：owner scope + 多列 LIKE 搜索。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbDataAsset, db)

    def list_by_owner(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[KbDataAsset]:
        return (
            self.db.query(KbDataAsset)
            .filter(KbDataAsset.owner_user_id == user_id)
            .order_by(KbDataAsset.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    def search_like(self, q: str, limit: int = 20) -> List[KbDataAsset]:
        like = f"%{q}%"
        return (
            self.db.query(KbDataAsset)
            .filter(
                or_(
                    KbDataAsset.title_zh.ilike(like),
                    KbDataAsset.title_en.ilike(like),
                    KbDataAsset.description_md.ilike(like),
                )
            )
            .limit(limit).all()
        )
