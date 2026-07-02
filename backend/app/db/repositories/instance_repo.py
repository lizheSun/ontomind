"""Instance 仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.instance_model import Instance


class InstanceRepository(BaseRepository[Instance]):
    def __init__(self, db: Session):
        super().__init__(Instance, db)

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Instance).filter(Instance.name == name)
        if exclude_id is not None:
            q = q.filter(Instance.id != exclude_id)
        return q.first() is not None

    def get_online(self) -> List[Instance]:
        return self.db.query(Instance).filter(Instance.status == "online").all()

    def update_heartbeat(self, instance_id: int):
        """刷新心跳时间，同时将实例状态设为 online"""
        from datetime import datetime, timezone
        self.db.query(Instance).filter(Instance.id == instance_id).update(
            {
                "last_heartbeat": datetime.now(timezone.utc),
                "status": "online",
            }
        )
        self.db.commit()
