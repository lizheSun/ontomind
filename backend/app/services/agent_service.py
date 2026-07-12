"""Agent business service (T45: consolidates Agent + AgentLooperConfig).

Before T45 there were two separate services:
    - `AgentService`            → agent definitions (this file, formerly)
    - `AgentLooperService`      → agent looper *configs* (agent_looper_service.py)

T45 renames `AgentLooperConfig → Agent` at the product/API level. To avoid
churning callers this module now exposes BOTH:

    - `AgentService`            — the original CRUD over the `agents` table
                                  (agent definitions / container images).
    - `AgentConfigService`      — the AgentLooperConfig service, re-exported
                                  under its new name.
    - `AgentLooperService`      — kept as a backwards-compat alias.

The underlying repositories / ORM models are UNCHANGED — this is a facade
rename. Callers can migrate to the new names on their own schedule.
"""
from sqlalchemy.orm import Session
from app.db.repositories.agent_repo import AgentRepository
from app.schemas.agent_schema import AgentCreate, AgentUpdate
from app.core.exceptions import ConflictException, NotFoundException


class AgentService:
    """CRUD service for agent definitions (the `agents` table).

    Not to be confused with `AgentConfigService`, which manages
    `agent_looper_configs` rows (renamed to `Agent` at the API layer per
    T45). The two live in separate tables and are separate concerns.
    """

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


# --- T45: AgentLooperConfig → Agent facade rename ---------------------------
# Import the AgentLooperService lazily so a missing/broken looper module does
# not prevent AgentService from loading (used widely across the codebase).
try:  # pragma: no cover - trivial import guard
    from app.services.agent_looper_service import (
        AgentLooperService as _AgentLooperService,
    )

    class AgentConfigService(_AgentLooperService):  # type: ignore[misc,valid-type]
        """T45 rename: AgentLooperConfig service exposed as `AgentConfigService`.

        Subclass (not alias) so callers that `isinstance(...)` against either
        name keep working during the transition.
        """

    # Backwards-compat: legacy `AgentLooperService` still importable.
    AgentLooperService = _AgentLooperService
except Exception:  # noqa: BLE001 — degrade gracefully if looper service absent
    AgentConfigService = None  # type: ignore[assignment]
    AgentLooperService = None  # type: ignore[assignment]
