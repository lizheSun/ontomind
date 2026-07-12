"""Agent identity service; versioned configuration lives in AgentVersion."""
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_model import Agent
from app.services.agent_platform.version import VersionService, _row


class AgentService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        name: str,
        agent_type: str,
        description: str | None,
        config: dict[str, Any],
        user_id: int,
        version_note: str | None = None,
    ) -> dict[str, Any]:
        if self.db.query(Agent).filter(Agent.name == name).first():
            raise ConflictException("Agent 名称已存在", code="AGENT_NAME_EXISTS")
        agent = Agent(
            name=name,
            type=agent_type,
            description=description,
            owner_user_id=user_id,
            is_active=True,
            is_published=False,
        )
        self.db.add(agent)
        self.db.flush()
        version = VersionService(self.db).create(agent.id, config, user_id, version_note)
        self.db.refresh(agent)
        return {**_row(agent), "latest_version": version}

    def get_model(self, agent_id: int, user_id: int | None = None) -> Agent:
        query = self.db.query(Agent).filter(Agent.id == agent_id)
        if user_id is not None:
            query = query.filter((Agent.owner_user_id == user_id) | (Agent.owner_user_id.is_(None)))
        agent = query.first()
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        return agent

    def get(self, agent_id: int, user_id: int) -> dict[str, Any]:
        return _row(self.get_model(agent_id, user_id))

    def list(self, user_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(Agent)
            .filter((Agent.owner_user_id == user_id) | (Agent.owner_user_id.is_(None)))
            .order_by(Agent.id.desc())
            .all()
        )
        return [_row(item) for item in rows]

    def update(self, agent_id: int, values: dict[str, Any], user_id: int) -> dict[str, Any]:
        agent = self.get_model(agent_id, user_id)
        allowed = {"name", "description", "is_active"}
        unknown = set(values) - allowed
        if unknown:
            raise ConflictException(
                "版本化配置只能通过 AgentVersion 修改", code="CONFIG_REQUIRES_VERSION"
            )
        if "name" in values:
            duplicate = (
                self.db.query(Agent)
                .filter(Agent.name == values["name"], Agent.id != agent.id)
                .first()
            )
            if duplicate:
                raise ConflictException("Agent 名称已存在", code="AGENT_NAME_EXISTS")
        for key, value in values.items():
            setattr(agent, key, value)
        self.db.commit()
        self.db.refresh(agent)
        return _row(agent)
