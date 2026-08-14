"""Agent Bundle（编排方案）Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.agent_bundle_model import AgentBundle, BundleMember
from app.db.repositories.base_repo import BaseRepository


class AgentBundleRepository(BaseRepository[AgentBundle]):
    """编排方案数据访问。"""

    def __init__(self, db: Session):
        super().__init__(AgentBundle, db)

    def get_by_name(self, name: str) -> Optional[AgentBundle]:
        return self.db.query(self.model).filter(self.model.name == name).first()

    def list_filtered(
        self,
        pattern: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
    ) -> List[AgentBundle]:
        q = self.db.query(self.model)
        if pattern:
            q = q.filter(self.model.pattern == pattern)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(
                self.model.name.like(like) | self.model.description.like(like)
            )
        return q.order_by(self.model.name).offset(skip).limit(limit).all()


class BundleMemberRepository(BaseRepository[BundleMember]):
    """Bundle 成员数据访问。"""

    def __init__(self, db: Session):
        super().__init__(BundleMember, db)

    def list_by_bundle(self, bundle_id: int) -> List[BundleMember]:
        return (
            self.db.query(self.model)
            .filter(self.model.bundle_id == bundle_id)
            .order_by(self.model.sort_order, self.model.id)
            .all()
        )

    def delete_by_bundle(self, bundle_id: int) -> int:
        """整批替换成员时先清空。"""
        rows = (
            self.db.query(self.model)
            .filter(self.model.bundle_id == bundle_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return int(rows or 0)

    def count_by_agent(self, agent_template_id: int) -> int:
        """某 agent 被多少个 bundle 引用（删除前检查）。"""
        return (
            self.db.query(self.model)
            .filter(self.model.agent_template_id == agent_template_id)
            .count()
        )

    def count_by_skill(self, skill_template_id: int) -> int:
        """某 skill 被多少个 bundle 引用（删除前检查）。"""
        return (
            self.db.query(self.model)
            .filter(self.model.skill_template_id == skill_template_id)
            .count()
        )
