"""Agent session and ordered message service."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.agent_model import Agent
from app.db.models.agent_platform_model import (
    AgentDeployment,
    AgentMessage,
    AgentSession,
    AgentVersion,
)
from app.services.agent_platform.version import _row


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        agent_id: int,
        deployment_id: int | None,
        title: str | None,
        metadata: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        agent = self.db.get(Agent, agent_id)
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")
        version_id = agent.current_version_id
        if deployment_id:
            deployment = self.db.get(AgentDeployment, deployment_id)
            if not deployment or deployment.agent_id != agent_id:
                raise ConflictException("部署与 Agent 不匹配", code="DEPLOYMENT_AGENT_MISMATCH")
            version_id = deployment.agent_version_id
        if version_id is None:
            latest = (
                self.db.query(AgentVersion)
                .filter(AgentVersion.agent_id == agent_id)
                .order_by(AgentVersion.version_number.desc())
                .first()
            )
            version_id = latest.id if latest else None
        if version_id is None:
            raise ConflictException("Agent 尚无可用版本", code="AGENT_VERSION_REQUIRED")
        session = AgentSession(
            agent_id=agent_id,
            agent_version_id=version_id,
            deployment_id=deployment_id,
            owner_user_id=user_id,
            title=title,
            session_metadata=metadata,
            status="active",
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return _row(session)

    def get_model(self, session_id: int, user_id: int | None = None) -> AgentSession:
        query = self.db.query(AgentSession).filter(AgentSession.id == session_id)
        if user_id is not None and user_id > 0:
            query = query.filter(AgentSession.owner_user_id == user_id)
        session = query.first()
        if not session:
            raise NotFoundException(f"Session 不存在: {session_id}")
        return session

    def get(self, session_id: int, user_id: int) -> dict[str, Any]:
        session = self.get_model(session_id, user_id)
        messages = (
            self.db.query(AgentMessage)
            .filter(AgentMessage.session_id == session.id)
            .order_by(AgentMessage.sequence)
            .all()
        )
        return {**_row(session), "messages": [_row(item) for item in messages]}

    def list(self, user_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AgentSession)
            .filter(AgentSession.owner_user_id == user_id)
            .order_by(AgentSession.id.desc())
            .all()
        )
        return [_row(row) for row in rows]

    def list_messages(self, session_id: int, user_id: int) -> list[dict[str, Any]]:
        self.get_model(session_id, user_id)
        rows = (
            self.db.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.sequence)
            .all()
        )
        return [_row(row) for row in rows]

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        metadata: dict[str, Any],
        user_id: int,
        content_type: str = "text",
        run_id: int | None = None,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        self.get_model(session_id, user_id)
        sequence = (
            self.db.query(func.max(AgentMessage.sequence))
            .filter(AgentMessage.session_id == session_id)
            .scalar()
            or 0
        ) + 1
        message = AgentMessage(
            session_id=session_id,
            sequence=sequence,
            role=role,
            content=content,
            content_type=content_type,
            run_id=run_id,
            message_metadata=metadata,
        )
        self.db.add(message)
        if auto_commit:
            self.db.commit()
            self.db.refresh(message)
        else:
            self.db.flush()
        return _row(message)

    def send_message(
        self,
        session_id: int,
        content: str,
        content_type: str,
        metadata: dict[str, Any],
        user_id: int,
        *,
        sync: bool | None = None,
    ) -> dict[str, Any]:
        """发送用户消息并创建 Run。

        - force_stub / sync=True：同步执行（测试）
        - 默认：立刻返回 queued run_id，由后台流式跑 OpenCode + SSE 推送
        """
        session = self.get_model(session_id, user_id)
        message = self.add_message(
            session_id,
            "user",
            content,
            metadata,
            user_id,
            content_type=content_type,
            auto_commit=False,
        )
        from app.services.agent_platform.run import RunService

        force_stub = bool(metadata.get("force_stub"))
        run_service = RunService(self.db)
        run = run_service.create(
            version_id=session.agent_version_id,
            deployment_id=session.deployment_id,
            session_id=session.id,
            strategy=str(metadata.get("strategy", "single_shot")),
            kind="chat",
            input_data={
                "message_id": message["id"],
                "prompt": content,
                "content_type": content_type,
                "force_stub": force_stub,
            },
            user_id=user_id,
            auto_commit=False,
        )
        row = self.db.get(AgentMessage, message["id"])
        row.run_id = run["id"]
        self.db.commit()
        self.db.refresh(row)

        should_sync = force_stub if sync is None else sync
        if should_sync:
            completed = run_service.execute(run["id"])
            self.db.refresh(row)
            return {
                "message_id": row.id,
                "run_id": run["id"],
                "message": _row(row),
                "run": completed,
                "queued": False,
            }

        return {
            "message_id": row.id,
            "run_id": run["id"],
            "message": _row(row),
            "run": run_service.get(run["id"]),
            "queued": True,
        }


def execute_run_in_background(run_id: int) -> None:
    """独立 DB session 后台执行 OpenCode 流式 Run。"""
    from app.db.session import SessionLocal
    from app.services.agent_platform.run import RunService

    db = SessionLocal()
    try:
        RunService(db).execute(run_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
