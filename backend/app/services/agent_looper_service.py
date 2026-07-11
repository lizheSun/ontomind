"""Agent Looper 业务服务（T36 侧最小实现，合并 T34 时以其完整版为准）。

主要给 test 端点用：
- `get_by_id(id, user_id)`  返回配置 row（校验 owner）
- `get_version(version_id)` 返回版本 row
- `get_current_config_dict(config_id, user_id)` 便利方法：拿到 current_version 的 config_json（dict）
"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.db.models.agent_looper_version_model import AgentLooperVersion
from app.db.repositories.agent_looper_repo import (
    AgentLooperConfigRepository,
    AgentLooperVersionRepository,
)


class AgentLooperService:
    """Agent Looper CRUD + 版本管理 (T36 侧最小切片)。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AgentLooperConfigRepository(db)
        self.version_repo = AgentLooperVersionRepository(db)

    def get_by_id(self, id: int, user_id: int) -> AgentLooperConfig:
        row = self.repo.get_by_id(id)
        if row is None:
            raise NotFoundException(f"Agent 配置 id={id} 不存在", code="AGENT_LOOPER_NOT_FOUND")
        if row.owner_user_id != user_id:
            raise BusinessException(
                code="AGENT_LOOPER_FORBIDDEN",
                message="仅拥有者可访问该 Agent",
                status_code=403,
            )
        return row

    def get_version(self, version_id: Optional[int]) -> Optional[AgentLooperVersion]:
        if version_id is None:
            return None
        return self.version_repo.get_by_id(version_id)

    def get_current_config_dict(self, config_id: int, user_id: int) -> tuple[AgentLooperConfig, Optional[AgentLooperVersion], dict[str, Any]]:
        """加载 Agent + current version + 解析后的 config_json dict。

        兜底顺序：
        1. current_version_id 指向的版本的 config_json
        2. 顶层 active_config_json
        3. 空 dict
        """
        config = self.get_by_id(config_id, user_id)
        version = self.get_version(config.current_version_id)
        raw = None
        if version is not None:
            raw = version.config_json
        if not raw:
            raw = config.active_config_json
        if not raw:
            return config, version, {}
        if isinstance(raw, dict):
            return config, version, raw
        try:
            return config, version, json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return config, version, {}
