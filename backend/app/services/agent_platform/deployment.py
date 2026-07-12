"""Agent deployment lifecycle service."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_platform_model import AgentDeployment
from app.services.agent_platform.version import VersionService, _row
from app.services.audit_log_service import AuditService


class DeploymentService:
    _TRANSITIONS = {
        "draft": {"start": "deploying"},
        "pending": {"start": "deploying", "force_offline": "offline"},
        "validating": {
            "validated": "deploying",
            "fail": "failed",
            "force_offline": "offline",
        },
        "deploying": {
            "activate": "active",
            "fail": "failed",
            "stop": "offline",
            "force_offline": "offline",
        },
        "active": {
            "drain": "draining",
            "fail": "failed",
            "stop": "offline",
            "force_offline": "offline",
        },
        "draining": {"stop": "offline", "force_offline": "offline"},
        "failed": {"start": "deploying", "stop": "offline"},
        "offline": {"start": "deploying"},
        "stopped": {"start": "deploying"},
    }

    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def create(
        self,
        version_id: int,
        environment: str,
        runtime_config: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        version = VersionService(self.db).get(version_id)
        previous = (
            self.db.query(AgentDeployment)
            .filter(
                AgentDeployment.agent_id == version.agent_id,
                AgentDeployment.environment == environment,
            )
            .order_by(AgentDeployment.id.desc())
            .first()
        )
        deployment = AgentDeployment(
            agent_id=version.agent_id,
            agent_version_id=version.id,
            environment=environment,
            runtime_config=runtime_config,
            status="pending",
            previous_deployment_id=previous.id if previous else None,
            created_by_user_id=user_id,
        )
        self.db.add(deployment)
        self.db.flush()
        self.audit.record(
            actor_user_id=user_id,
            action="deployment.create",
            resource_type="agent_deployment",
            resource_id=deployment.id,
            details={
                "agent_id": version.agent_id,
                "version_id": version.id,
                "environment": environment,
            },
        )
        self.db.commit()
        self.db.refresh(deployment)
        return _row(deployment)

    def get_model(self, deployment_id: int) -> AgentDeployment:
        deployment = self.db.get(AgentDeployment, deployment_id)
        if not deployment:
            raise NotFoundException(f"部署不存在: {deployment_id}")
        return deployment

    def get(self, deployment_id: int) -> dict[str, Any]:
        return _row(self.get_model(deployment_id))

    def list(self, agent_id: int | None = None) -> list[dict[str, Any]]:
        query = self.db.query(AgentDeployment)
        if agent_id is not None:
            query = query.filter(AgentDeployment.agent_id == agent_id)
        return [_row(row) for row in query.order_by(AgentDeployment.id.desc()).all()]

    def transition(
        self,
        deployment_id: int,
        action: str,
        expected_version: int | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        deployment = self.get_model(deployment_id)
        if expected_version is not None and deployment.status_version != expected_version:
            raise ConflictException("部署状态已变化", code="DEPLOYMENT_VERSION_CONFLICT")
        target = self._TRANSITIONS.get(deployment.status, {}).get(action)
        if not target:
            raise ConflictException(
                f"非法部署状态转换: {deployment.status} -> {action}",
                code="INVALID_DEPLOYMENT_TRANSITION",
            )
        previous_status = deployment.status
        deployment.status = target
        deployment.status_version += 1
        now = datetime.now(timezone.utc)
        if target in {"validating", "deploying"} and deployment.started_at is None:
            deployment.started_at = now
        if target == "active":
            deployment.deployed_at = now
            deployment.activated_at = now
        if target in {"offline", "failed", "rolled_back"}:
            deployment.stopped_at = now
            deployment.finished_at = now
        self.audit.record(
            actor_user_id=actor_user_id,
            action="deployment.transition",
            resource_type="agent_deployment",
            resource_id=deployment.id,
            details={"action": action, "from": previous_status, "to": target},
        )
        self.db.commit()
        self.db.refresh(deployment)
        return _row(deployment)

    def drain(
        self,
        deployment_id: int,
        expected_version: int | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        return self.transition(
            deployment_id, "drain", expected_version, actor_user_id
        )

    def force_offline(
        self,
        deployment_id: int,
        expected_version: int | None = None,
        reason: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        deployment = self.get_model(deployment_id)
        if reason:
            deployment.failure_message = reason
        return self.transition(
            deployment_id, "force_offline", expected_version, actor_user_id
        )

    def rollback(
        self,
        deployment_id: int,
        user_id: int,
        expected_version: int | None = None,
        target_version_id: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_model(deployment_id)
        if expected_version is not None and current.status_version != expected_version:
            raise ConflictException(
                "部署状态已变化", code="DEPLOYMENT_VERSION_CONFLICT"
            )
        target = None
        if target_version_id is not None:
            target = VersionService(self.db).get(target_version_id)
            if target.agent_id != current.agent_id:
                raise ConflictException(
                    "回滚版本不属于该 Agent", code="ROLLBACK_VERSION_MISMATCH"
                )
        elif current.previous_deployment_id:
            previous = self.get_model(current.previous_deployment_id)
            target = VersionService(self.db).get(previous.agent_version_id)
        else:
            previous = (
                self.db.query(AgentDeployment)
                .filter(
                    AgentDeployment.agent_id == current.agent_id,
                    AgentDeployment.environment == current.environment,
                    AgentDeployment.id < current.id,
                )
                .order_by(AgentDeployment.id.desc())
                .first()
            )
            if previous:
                target = VersionService(self.db).get(previous.agent_version_id)
        if target is None:
            raise ConflictException("没有可回滚的部署版本", code="NO_ROLLBACK_TARGET")
        current.status = "rolled_back"
        current.status_version += 1
        current.finished_at = datetime.now(timezone.utc)
        rollback = AgentDeployment(
            agent_id=current.agent_id,
            agent_version_id=target.id,
            environment=current.environment,
            status="pending",
            runtime_config=current.runtime_config or {},
            status_version=1,
            previous_deployment_id=current.id,
            created_by_user_id=user_id,
        )
        self.db.add(rollback)
        self.db.flush()
        self.audit.record(
            actor_user_id=user_id,
            action="deployment.rollback",
            resource_type="agent_deployment",
            resource_id=rollback.id,
            details={
                "rolled_back_deployment_id": current.id,
                "target_version_id": target.id,
            },
        )
        self.db.commit()
        self.db.refresh(rollback)
        return {
            **_row(rollback),
            "operation": "rollback",
            "rolled_back_deployment_id": current.id,
        }
