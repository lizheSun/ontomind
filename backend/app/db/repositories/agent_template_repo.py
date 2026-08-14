"""Agent 模板 Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.agent_template_model import AgentTemplate, AgentTemplateVersion
from app.db.repositories.base_repo import BaseRepository


class AgentTemplateRepository(BaseRepository[AgentTemplate]):
    """Agent 模板数据访问。"""

    def __init__(self, db: Session):
        super().__init__(AgentTemplate, db)

    def get_by_name(self, name: str) -> Optional[AgentTemplate]:
        return self.db.query(self.model).filter(self.model.name == name).first()

    def get_by_names(self, names: List[str]) -> List[AgentTemplate]:
        if not names:
            return []
        return self.db.query(self.model).filter(self.model.name.in_(names)).all()

    def list_filtered(
        self,
        category: Optional[str] = None,
        mode: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
    ) -> List[AgentTemplate]:
        q = self.db.query(self.model)
        if category:
            q = q.filter(self.model.category == category)
        if mode:
            q = q.filter(self.model.mode == mode)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(
                self.model.name.like(like) | self.model.description.like(like)
            )
        return (
            q.order_by(self.model.category, self.model.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_categories(self) -> List[str]:
        rows = (
            self.db.query(self.model.category)
            .filter(self.model.category.isnot(None))
            .distinct()
            .all()
        )
        return sorted({r[0] for r in rows if r[0]})


class AgentTemplateVersionRepository(BaseRepository[AgentTemplateVersion]):
    """Agent 模板版本数据访问。"""

    def __init__(self, db: Session):
        super().__init__(AgentTemplateVersion, db)

    def list_by_template(self, template_id: int) -> List[AgentTemplateVersion]:
        return (
            self.db.query(self.model)
            .filter(self.model.agent_template_id == template_id)
            .order_by(self.model.version.desc())
            .all()
        )

    def get_version(self, template_id: int, version: int) -> Optional[AgentTemplateVersion]:
        return (
            self.db.query(self.model)
            .filter(
                self.model.agent_template_id == template_id,
                self.model.version == version,
            )
            .first()
        )

    def max_version(self, template_id: int) -> int:
        """当前最大版本号；无版本时返回 0。"""
        row = (
            self.db.query(self.model.version)
            .filter(self.model.agent_template_id == template_id)
            .order_by(self.model.version.desc())
            .first()
        )
        return int(row[0]) if row else 0
