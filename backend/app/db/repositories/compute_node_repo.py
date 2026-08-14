"""算力节点 Repository."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.compute_node_model import ComputeNode


class ComputeNodeRepository(BaseRepository[ComputeNode]):
    """算力节点数据访问"""

    def __init__(self, db: Session):
        super().__init__(ComputeNode, db)

    def get_by_name(self, name: str) -> Optional[ComputeNode]:
        """按名称查询"""
        return self.db.query(self.model).filter(self.model.name == name).first()

    def get_local_node(self) -> Optional[ComputeNode]:
        """获取本地节点"""
        return self.db.query(self.model).filter(self.model.is_local == True).first()

    def list_active(self) -> List[ComputeNode]:
        """列出所有非离线节点"""
        return (
            self.db.query(self.model)
            .filter(self.model.status != "offline")
            .all()
        )
