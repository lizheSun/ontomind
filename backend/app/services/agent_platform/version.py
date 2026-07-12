"""Append-only AgentVersion service."""
import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_model import Agent
from app.db.models.agent_platform_model import AgentVersion
from app.services.audit_log_service import AuditService


def _row(row: Any) -> dict[str, Any]:
    data = row.to_dict()
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


def _version_row(version: AgentVersion) -> dict[str, Any]:
    data = _row(version)
    data.update(
        {
            "config_snapshot": data["config"],
            "content_hash": data["config_hash"],
            "change_summary": data["note"],
        }
    )
    return data


class VersionService:
    """Creates immutable snapshots; publishing only moves the Agent pointer."""

    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def create(
        self,
        agent_id: int,
        config: dict[str, Any],
        user_id: int | None,
        note: str | None = None,
    ) -> dict[str, Any]:
        agent = self.db.get(Agent, agent_id)
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        if agent.owner_user_id is not None and user_id != agent.owner_user_id:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        number = (
            self.db.query(func.max(AgentVersion.version_number))
            .filter(AgentVersion.agent_id == agent_id)
            .scalar()
            or 0
        ) + 1
        version = AgentVersion(
            agent_id=agent_id,
            version_number=number,
            config=json.loads(canonical),
            config_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            note=note,
            status="draft",
            config_schema_version=str(config.get("config_schema_version", "1")),
            source=str(config.get("source", "manual")),
            created_by_user_id=user_id,
        )
        self.db.add(version)
        self.db.flush()
        self.audit.record(
            actor_user_id=user_id,
            action="agent.version.create",
            resource_type="agent_version",
            resource_id=version.id,
            details={"agent_id": agent_id, "version_number": number},
        )
        self.db.commit()
        self.db.refresh(version)
        return _version_row(version)

    def get(self, version_id: int) -> AgentVersion:
        version = self.db.get(AgentVersion, version_id)
        if not version:
            raise NotFoundException(f"AgentVersion 不存在: {version_id}")
        return version

    def list(self, agent_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AgentVersion)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .all()
        )
        return [_version_row(item) for item in rows]

    def validate(self, agent_id: int, version_id: int) -> dict[str, Any]:
        version = self.get(version_id)
        if version.agent_id != agent_id:
            raise NotFoundException("版本不存在")
        config = version.config or {}
        required_fields = ("model", "system_prompt")
        missing_fields = [
            field for field in required_fields if not config.get(field)
        ]
        dependency_fields = ("skills", "mcps", "subagents")
        invalid_dependencies = [
            field
            for field in dependency_fields
            if field in config and not isinstance(config[field], list)
        ]
        eval_bindings = config.get("eval_bindings", [])
        eval_valid = isinstance(eval_bindings, list)
        checks = [
            {
                "name": "config.completeness",
                "status": "passed" if not missing_fields else "failed",
                "details": {"missing_fields": missing_fields},
            },
            {
                "name": "dependencies.shape",
                "status": "passed" if not invalid_dependencies else "failed",
                "details": {"invalid_fields": invalid_dependencies},
            },
            {
                "name": "eval.bindings",
                "status": "passed" if eval_valid else "failed",
                "details": {
                    "configured": len(eval_bindings) if eval_valid else 0,
                    "executed": 0,
                },
            },
        ]
        valid = not missing_fields and not invalid_dependencies and eval_valid
        return {
            "valid": valid,
            "agent_id": agent_id,
            "version_id": version_id,
            "content_hash": version.config_hash,
            "config": {
                "valid": not missing_fields,
                "missing_fields": missing_fields,
                "schema_version": version.config_schema_version,
            },
            "dependencies": {
                "valid": not invalid_dependencies,
                "invalid_fields": invalid_dependencies,
                "counts": {
                    field: len(config.get(field, []))
                    if isinstance(config.get(field, []), list)
                    else 0
                    for field in dependency_fields
                },
            },
            "eval": {
                "valid": eval_valid,
                "configured": len(eval_bindings) if eval_valid else 0,
                "executed": 0,
                "blocking_failures": [],
            },
            "checks": checks,
        }

    def load(
        self,
        agent_id: int,
        version_id: int,
        environment: str,
        runtime_config: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        validation = self.validate(agent_id, version_id)
        if not validation["valid"]:
            raise ConflictException(
                "AgentVersion 校验未通过", code="VERSION_VALIDATION_FAILED"
            )
        from app.services.agent_platform.deployment import DeploymentService

        deployments = DeploymentService(self.db)
        deployment = deployments.create(
            version_id, environment, runtime_config, user_id
        )
        deployment = deployments.transition(
            deployment["id"], "start", deployment["status_version"]
        )
        return {
            "version": _version_row(self.get(version_id)),
            "validation": validation,
            "deployment": deployment,
        }

    def publish(self, agent_id: int, version_id: int, user_id: int | None) -> dict[str, Any]:
        agent = self.db.get(Agent, agent_id)
        version = self.get(version_id)
        if not agent or version.agent_id != agent_id:
            raise NotFoundException("Agent 或版本不存在")
        if agent.owner_user_id is not None and agent.owner_user_id != user_id:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        agent.current_version_id = version.id
        agent.is_published = True
        agent.version = version.version_number
        self.audit.record(
            actor_user_id=user_id,
            action="agent.version.publish",
            resource_type="agent_version",
            resource_id=version.id,
            details={"agent_id": agent_id, "version_number": version.version_number},
        )
        self.db.commit()
        return _version_row(version)

    def update(self, *_args: Any, **_kwargs: Any) -> None:
        raise ConflictException("AgentVersion 不可修改，请创建新版本", code="VERSION_IMMUTABLE")
