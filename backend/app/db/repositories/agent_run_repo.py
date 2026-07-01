"""AgentRun 仓库."""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.repositories.base_repo import BaseRepository
from app.db.models.agent_run_model import AgentRun


class AgentRunRepository(BaseRepository[AgentRun]):
    def __init__(self, db: Session):
        super().__init__(AgentRun, db)

    def get_running(self) -> List[AgentRun]:
        return self.db.query(AgentRun).filter(AgentRun.status == "running").all()

    def get_by_agent(self, agent_id: int) -> List[AgentRun]:
        return (
            self.db.query(AgentRun)
            .filter(AgentRun.agent_id == agent_id)
            .order_by(desc(AgentRun.started_at))
            .all()
        )

    def get_by_instance(self, instance_id: int) -> List[AgentRun]:
        return (
            self.db.query(AgentRun)
            .filter(AgentRun.instance_id == instance_id)
            .order_by(desc(AgentRun.started_at))
            .all()
        )
