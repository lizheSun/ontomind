"""LLM 配置数据仓库."""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.llm_config_model import LLMConfig


class LLMConfigRepository(BaseRepository[LLMConfig]):
    """LLM 配置仓库"""

    def __init__(self, db: Session):
        super().__init__(LLMConfig, db)

    def get_by_name(self, name: str) -> Optional[LLMConfig]:
        return self.db.query(LLMConfig).filter(LLMConfig.name == name).first()

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(LLMConfig).filter(LLMConfig.name == name)
        if exclude_id is not None:
            q = q.filter(LLMConfig.id != exclude_id)
        return q.first() is not None

    def get_active(self) -> Optional[LLMConfig]:
        return self.db.query(LLMConfig).filter(LLMConfig.is_active == True).first()

    def deactivate_all(self):
        self.db.query(LLMConfig).filter(LLMConfig.is_active == True).update(
            {"is_active": False}
        )
