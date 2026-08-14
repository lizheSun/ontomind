"""发布记录 Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.deployment_model import Deployment
from app.db.repositories.base_repo import BaseRepository


class DeploymentRepository(BaseRepository[Deployment]):
    """发布记录数据访问。"""

    def __init__(self, db: Session):
        super().__init__(Deployment, db)

    def list_filtered(
        self,
        bundle_id: Optional[int] = None,
        node_id: Optional[int] = None,
        container_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Deployment]:
        q = self.db.query(self.model)
        if bundle_id is not None:
            q = q.filter(self.model.bundle_id == bundle_id)
        if node_id is not None:
            q = q.filter(self.model.node_id == node_id)
        if container_id:
            q = q.filter(self.model.container_id == container_id)
        if status:
            q = q.filter(self.model.status == status)
        return (
            q.order_by(self.model.id.desc()).offset(skip).limit(limit).all()
        )

    def latest_for_target(
        self, bundle_id: int, container_id: str, exclude_id: Optional[int] = None
    ) -> Optional[Deployment]:
        """某 bundle 在某容器上的最近一次发布 —— 用于幂等比对（sha256 是否变化）。

        `exclude_id`：排除本次正在进行的发布记录。
        发布流程会先建记录再解析产物，不排除的话会拿到自己（artifacts 还是空的），
        导致幂等判断永远失效。
        """
        q = self.db.query(self.model).filter(
            self.model.bundle_id == bundle_id,
            self.model.container_id == container_id,
        )
        if exclude_id is not None:
            q = q.filter(self.model.id != exclude_id)
        return q.order_by(self.model.id.desc()).first()

    def list_by_container(self, container_id: str) -> List[Deployment]:
        return (
            self.db.query(self.model)
            .filter(self.model.container_id == container_id)
            .order_by(self.model.id.desc())
            .all()
        )
