"""AgentLooper 仓储：Config / Version / TestRun 三层（T34）。"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun
from app.db.models.agent_looper_version_model import AgentLooperVersion
from app.db.repositories.base_repo import BaseRepository


class AgentLooperConfigRepository(BaseRepository[AgentLooperConfig]):
    """AgentLooperConfig 仓储：owner scope + 软删除感知的列表查询。"""

    def __init__(self, db: Session) -> None:
        super().__init__(AgentLooperConfig, db)

    def list_by_owner(
        self,
        user_id: int,
        *,
        type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[AgentLooperConfig]:
        q = self.db.query(AgentLooperConfig).filter(
            AgentLooperConfig.owner_user_id == user_id
        )
        if type is not None:
            q = q.filter(AgentLooperConfig.type == type)
        if is_active is not None:
            q = q.filter(AgentLooperConfig.is_active == is_active)
        return q.order_by(AgentLooperConfig.id.desc()).all()

    def name_exists_for_owner(
        self, name: str, owner_user_id: int, *, exclude_id: Optional[int] = None,
    ) -> bool:
        q = self.db.query(AgentLooperConfig).filter(
            AgentLooperConfig.name == name,
            AgentLooperConfig.owner_user_id == owner_user_id,
        )
        if exclude_id is not None:
            q = q.filter(AgentLooperConfig.id != exclude_id)
        return q.first() is not None


class AgentLooperVersionRepository(BaseRepository[AgentLooperVersion]):
    """AgentLooperVersion 仓储：按 config 组织的顺序快照。"""

    def __init__(self, db: Session) -> None:
        super().__init__(AgentLooperVersion, db)

    def next_version_number(self, config_id: int) -> int:
        """`SELECT COALESCE(MAX(version_number), 0) + 1`."""
        current = (
            self.db.query(func.coalesce(func.max(AgentLooperVersion.version_number), 0))
            .filter(AgentLooperVersion.config_id == config_id)
            .scalar()
        )
        return int(current or 0) + 1

    def list_by_config(self, config_id: int) -> List[AgentLooperVersion]:
        return (
            self.db.query(AgentLooperVersion)
            .filter(AgentLooperVersion.config_id == config_id)
            .order_by(AgentLooperVersion.version_number.asc())
            .all()
        )

    def get_by_number(
        self, config_id: int, version_number: int,
    ) -> Optional[AgentLooperVersion]:
        return (
            self.db.query(AgentLooperVersion)
            .filter(
                AgentLooperVersion.config_id == config_id,
                AgentLooperVersion.version_number == version_number,
            )
            .first()
        )


class AgentLooperTestRunRepository(BaseRepository[AgentLooperTestRun]):
    """AgentLooperTestRun 仓储：按 config 顺序记录 + TTL 清理。"""

    def __init__(self, db: Session) -> None:
        super().__init__(AgentLooperTestRun, db)

    def list_by_config(self, config_id: int, *, limit: int = 100) -> List[AgentLooperTestRun]:
        return (
            self.db.query(AgentLooperTestRun)
            .filter(AgentLooperTestRun.config_id == config_id)
            .order_by(AgentLooperTestRun.id.desc())
            .limit(limit)
            .all()
        )

    def purge_older_than(self, cutoff) -> int:
        """删除 created_at < cutoff 的记录，返回删除条数。"""
        n = (
            self.db.query(AgentLooperTestRun)
            .filter(AgentLooperTestRun.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return int(n or 0)


# Backwards-friendly aliases matching the task spec wording
ConfigRepo = AgentLooperConfigRepository
VersionRepo = AgentLooperVersionRepository
TestRunRepo = AgentLooperTestRunRepository
