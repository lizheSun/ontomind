"""Read-only legacy adapter and one-way migration into AgentVersion."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.services.agent_platform.agent import AgentService


class LegacyAgentMigrationService:
    """Copies legacy Looper configuration without ever updating the old table."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def adapt(config: AgentLooperConfig) -> dict[str, Any]:
        try:
            versioned = json.loads(config.active_config_json or "{}")
        except (TypeError, json.JSONDecodeError):
            versioned = {}
        versioned.setdefault("settings", config.settings or {})
        versioned.setdefault("resource_bindings", config.resource_bindings or {})
        versioned.setdefault("credential_ref", config.credential_ref)
        return {
            "name": config.name,
            "agent_type": config.type,
            "description": config.description,
            "config": versioned,
            "user_id": config.owner_user_id,
            "version_note": f"migrated from agent_looper_configs:{config.id}",
        }

    def migrate(self, legacy_config_id: int, user_id: int | None = None) -> dict[str, Any]:
        legacy = self.db.get(AgentLooperConfig, legacy_config_id)
        if not legacy:
            raise NotFoundException(f"旧 Agent 配置不存在: {legacy_config_id}")
        if user_id is not None and legacy.owner_user_id != user_id:
            raise NotFoundException(f"旧 Agent 配置不存在: {legacy_config_id}")
        try:
            return AgentService(self.db).create(**self.adapt(legacy))
        except ConflictException as exc:
            if exc.code == "AGENT_NAME_EXISTS":
                raise ConflictException(
                    "同名 Agent 已存在，迁移未写入旧表", code="LEGACY_AGENT_ALREADY_MIGRATED"
                )
            raise
