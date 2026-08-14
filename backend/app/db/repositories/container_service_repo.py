"""容器服务 Repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.container_service_model import ContainerService
from app.db.repositories.base_repo import BaseRepository


class ContainerServiceRepository(BaseRepository[ContainerService]):
    """容器服务数据访问."""

    def __init__(self, db: Session):
        super().__init__(ContainerService, db)

    def get_by_container_port(
        self, container_id: str, container_port: int
    ) -> Optional[ContainerService]:
        """按「容器 + 容器内端口」查唯一记录（upsert 用）."""
        return (
            self.db.query(self.model)
            .filter(
                self.model.container_id == container_id,
                self.model.container_port == container_port,
            )
            .first()
        )

    def list_all_ordered(self) -> List[ContainerService]:
        """列出全部，按节点 + 容器名排序."""
        return (
            self.db.query(self.model)
            .order_by(self.model.node_id, self.model.container_name, self.model.container_port)
            .all()
        )

    def list_by_node(self, node_id: int) -> List[ContainerService]:
        return (
            self.db.query(self.model)
            .filter(self.model.node_id == node_id)
            .order_by(self.model.container_name, self.model.container_port)
            .all()
        )

    def list_by_container(self, container_id: str) -> List[ContainerService]:
        return (
            self.db.query(self.model)
            .filter(self.model.container_id == container_id)
            .order_by(self.model.container_port)
            .all()
        )

    def list_aide_sources(self) -> List[ContainerService]:
        """AIDE 可用源：opencode 类 + 宿主可达 + 运行中."""
        return (
            self.db.query(self.model)
            .filter(
                self.model.is_aide_source.is_(True),
                self.model.host_reachable.is_(True),
            )
            .order_by(self.model.node_id, self.model.container_name)
            .all()
        )

    def delete_by_container(self, container_id: str) -> int:
        """容器被删除时清理其所有服务登记."""
        rows = (
            self.db.query(self.model)
            .filter(self.model.container_id == container_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return int(rows or 0)
