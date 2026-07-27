"""Docker 节点 repository."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.docker_node_model import DockerHost
from app.db.repositories.base_repo import BaseRepository


class DockerNodeRepository(BaseRepository[DockerHost]):
    def __init__(self, db: Session):
        super().__init__(DockerHost, db)

    def get_by_name(self, name: str) -> Optional[DockerHost]:
        return self.db.query(DockerHost).filter(DockerHost.name == name).first()

    def get_local_node(self) -> Optional[DockerHost]:
        """查找已挂载的本机节点（conn_type=local + address=127.0.0.1）."""
        return (
            self.db.query(DockerHost)
            .filter(DockerHost.conn_type == "local", DockerHost.address == "127.0.0.1")
            .first()
        )

    def list_ordered(self, skip: int = 0, limit: int = 200) -> List[DockerHost]:
        return (
            self.db.query(DockerHost)
            .order_by(DockerHost.id.asc())
            .offset(skip).limit(limit).all()
        )
