"""Agent Looper 仓储：Config / Version / TestRun.

T36 侧最小实现（合并 T34 时以其完整版为准）。此处仅需 TestRun 有完整 CRUD，
Config/Version 提供 get_by_id / create 供集成引用。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun
from app.db.models.agent_looper_version_model import AgentLooperVersion


class AgentLooperConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, id: int) -> Optional[AgentLooperConfig]:
        return self.db.query(AgentLooperConfig).filter(AgentLooperConfig.id == id).first()

    def create(self, data: dict[str, Any]) -> AgentLooperConfig:
        row = AgentLooperConfig(**data)
        self.db.add(row)
        self.db.flush()
        return row

    def update(self, id: int, data: dict[str, Any]) -> Optional[AgentLooperConfig]:
        row = self.get_by_id(id)
        if row is None:
            return None
        for k, v in data.items():
            setattr(row, k, v)
        self.db.flush()
        return row


class AgentLooperVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, id: int) -> Optional[AgentLooperVersion]:
        return self.db.query(AgentLooperVersion).filter(AgentLooperVersion.id == id).first()

    def create(self, data: dict[str, Any]) -> AgentLooperVersion:
        payload = dict(data)
        cj = payload.get("config_json")
        if isinstance(cj, dict):
            payload["config_json"] = json.dumps(cj, ensure_ascii=False)
        row = AgentLooperVersion(**payload)
        self.db.add(row)
        self.db.flush()
        return row


class AgentLooperTestRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        config_id: int,
        version_id: Optional[int],
        prompt: str,
        user_id: int,
        status: str = "running",
    ) -> AgentLooperTestRun:
        row = AgentLooperTestRun(
            config_id=config_id,
            version_id=version_id,
            prompt=prompt,
            user_id=user_id,
            status=status,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(
        self,
        id: int,
        *,
        status: Optional[str] = None,
        response: Optional[str] = None,
        error: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> Optional[AgentLooperTestRun]:
        row = self.db.query(AgentLooperTestRun).filter(AgentLooperTestRun.id == id).first()
        if row is None:
            return None
        if status is not None:
            row.status = status
        if response is not None:
            row.response = response
        if error is not None:
            row.error = error
        if latency_ms is not None:
            row.latency_ms = latency_ms
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_config(self, config_id: int, limit: int = 50) -> list[AgentLooperTestRun]:
        return (
            self.db.query(AgentLooperTestRun)
            .filter(AgentLooperTestRun.config_id == config_id)
            .order_by(AgentLooperTestRun.created_at.desc())
            .limit(limit)
            .all()
        )


# 便于测试/服务层用相同名字导入
TestRunRepository = AgentLooperTestRunRepository
