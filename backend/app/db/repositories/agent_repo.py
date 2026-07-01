"""Agent 仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.repositories.base_repo import BaseRepository
from app.db.models.agent_model import Agent


class AgentRepository(BaseRepository[Agent]):
    def __init__(self, db: Session):
        super().__init__(Agent, db)

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Agent).filter(Agent.name == name)
        if exclude_id is not None:
            q = q.filter(Agent.id != exclude_id)
        return q.first() is not None

    def get_active(self) -> List[Agent]:
        return self.db.query(Agent).filter(Agent.is_active == True).all()

    def get_by_type(self, agent_type: str) -> List[Agent]:
        return self.db.query(Agent).filter(Agent.agent_type == agent_type).all()
