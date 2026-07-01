"""Agent 业务服务."""
from sqlalchemy.orm import Session
from app.db.repositories.agent_repo import AgentRepository
from app.schemas.agent_schema import AgentCreate, AgentUpdate
from app.core.exceptions import ConflictException, NotFoundException


class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgentRepository(db)

    def create(self, data: AgentCreate) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("Agent 名称已存在", code="AGENT_NAME_EXISTS")
        agent = self.repo.create(data.model_dump())
        self.db.commit()
        return agent.to_response_dict()

    def get(self, agent_id: int) -> dict:
        agent = self.repo.get_by_id(agent_id)
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        return agent.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        items = self.repo.get_all(skip, limit)
        return [a.to_response_dict() for a in items]

    def update(self, agent_id: int, data: AgentUpdate) -> dict:
        agent = self.repo.get_by_id(agent_id)
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != agent.name:
            if self.repo.name_exists(update_data["name"], exclude_id=agent_id):
                raise ConflictException("Agent 名称已存在", code="AGENT_NAME_EXISTS")
        updated = self.repo.update(agent_id, update_data)
        self.db.commit()
        return updated.to_response_dict()

    def delete(self, agent_id: int) -> bool:
        if not self.repo.delete(agent_id):
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        self.db.commit()
        return True
