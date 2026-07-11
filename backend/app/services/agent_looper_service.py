"""AgentLooperService — CRUD + 版本链 + 回滚 + 软删除（T34）。

事务模型：与 dp_ 系服务一致，使用 `with self.db.begin():` 显式提交。

版本链规则：
- create → 首版本 version_number=1，current_version_id 指向该版本
- update（且 payload 含 config_json）→ 追加新版本 max+1，current_version_id 更新
- rollback(target_version_number) → 拷贝目标版本 config_json 为新版本（max+1），current_version_id 更新
- 未含 config_json 的 update 只改元字段，不新增版本
- soft_delete → is_active=False（不物理删除）
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
    AgentLooperTestRunRepository,
    AgentLooperVersionRepository,
)
from app.schemas.agent_looper_schema import (
    AgentLooperConfigCreate,
    AgentLooperConfigRead,
    AgentLooperConfigUpdate,
    AgentLooperVersionRead,
)


class AgentLooperService:
    """AgentLooper 配置服务：CRUD + 版本管理 + 回滚 + 软删除。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.config_repo = AgentLooperConfigRepository(db)
        self.version_repo = AgentLooperVersionRepository(db)
        self.test_run_repo = AgentLooperTestRunRepository(db)

    # ==== CRUD =========================================================

    def create(
        self, payload: AgentLooperConfigCreate, user_id: int,
    ) -> AgentLooperConfigRead:
        self._reset_autobegin()
        with self.db.begin():
            if self.config_repo.name_exists_for_owner(payload.name, user_id):
                raise BusinessException(
                    message=f"AgentLooper 名称 {payload.name!r} 已存在",
                    code="AGENT_LOOPER_NAME_EXISTS",
                    status_code=409,
                )

            config_json = payload.config_json or {}
            config_json_text = json.dumps(config_json, ensure_ascii=False)

            cfg = self.config_repo.create({
                "name": payload.name,
                "type": payload.type,
                "description": payload.description,
                "current_version_id": None,
                "active_config_json": config_json_text,
                "owner_user_id": user_id,
                "is_active": True,
                "is_published": payload.is_published,
                "settings": payload.settings,
                "resource_bindings": payload.resource_bindings,
                "credential_ref": payload.credential_ref,
            })

            version = self.version_repo.create({
                "config_id": cfg.id,
                "version_number": 1,
                "config_json": config_json_text,
                "model_snapshot": payload.model_snapshot,
                "prompt_snapshot": payload.prompt_snapshot,
                "note": payload.note or "初始版本",
                "created_by_user_id": user_id,
            })

            cfg.current_version_id = version.id
            self.db.flush()

        return self._to_read(self._require_config(cfg.id))

    def get_by_id(self, id: int) -> AgentLooperConfigRead:
        cfg = self._require_config(id)
        return self._to_read(cfg)

    def list_by_owner(
        self,
        user_id: int,
        *,
        type: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> list[AgentLooperConfigRead]:
        """默认只返回 is_active=True 的配置；显式传 None 才返回全部。"""
        rows = self.config_repo.list_by_owner(user_id, type=type, is_active=is_active)
        return [self._to_read(r) for r in rows]

    def update(
        self, id: int, payload: AgentLooperConfigUpdate, user_id: int,
    ) -> AgentLooperConfigRead:
        self._reset_autobegin()
        with self.db.begin():
            cfg = self._require_owner_writable(id, user_id)

            patch: dict[str, Any] = {}
            for field in (
                "name", "type", "description", "settings",
                "resource_bindings", "credential_ref", "is_published",
            ):
                val = getattr(payload, field)
                if val is not None:
                    patch[field] = val

            new_name = patch.get("name")
            if new_name and self.config_repo.name_exists_for_owner(
                new_name, user_id, exclude_id=id,
            ):
                raise BusinessException(
                    message=f"AgentLooper 名称 {new_name!r} 已存在",
                    code="AGENT_LOOPER_NAME_EXISTS",
                    status_code=409,
                )

            new_version_id: Optional[int] = None
            if payload.config_json is not None:
                config_json_text = json.dumps(payload.config_json, ensure_ascii=False)
                next_num = self.version_repo.next_version_number(id)
                version = self.version_repo.create({
                    "config_id": id,
                    "version_number": next_num,
                    "config_json": config_json_text,
                    "model_snapshot": payload.model_snapshot,
                    "prompt_snapshot": payload.prompt_snapshot,
                    "note": payload.note,
                    "created_by_user_id": user_id,
                })
                new_version_id = version.id
                patch["current_version_id"] = new_version_id
                patch["active_config_json"] = config_json_text

            if patch:
                self.config_repo.update(id, patch)

        return self.get_by_id(id)

    def rollback(
        self, id: int, target_version_number: int, user_id: int,
    ) -> AgentLooperConfigRead:
        self._reset_autobegin()
        with self.db.begin():
            self._require_owner_writable(id, user_id)
            target = self.version_repo.get_by_number(id, target_version_number)
            if target is None:
                raise NotFoundException(
                    message=(
                        f"版本 version_number={target_version_number} "
                        f"不存在于 config id={id}"
                    ),
                    code="AGENT_LOOPER_VERSION_NOT_FOUND",
                )

            next_num = self.version_repo.next_version_number(id)
            version = self.version_repo.create({
                "config_id": id,
                "version_number": next_num,
                "config_json": target.config_json,
                "model_snapshot": target.model_snapshot,
                "prompt_snapshot": target.prompt_snapshot,
                "note": f"回滚自 v{target_version_number}",
                "created_by_user_id": user_id,
            })
            self.config_repo.update(id, {
                "current_version_id": version.id,
                "active_config_json": target.config_json,
            })

        return self.get_by_id(id)

    def soft_delete(self, id: int, user_id: int) -> None:
        self._reset_autobegin()
        with self.db.begin():
            self._require_owner_writable(id, user_id)
            self.config_repo.update(id, {"is_active": False})

    # ==== version history =============================================

    def get_version_history(self, config_id: int) -> list[AgentLooperVersionRead]:
        self._require_config(config_id)
        rows = self.version_repo.list_by_config(config_id)
        return [AgentLooperVersionRead.model_validate(r) for r in rows]

    def get_version(
        self, config_id: int, version_number: int,
    ) -> AgentLooperVersionRead:
        self._require_config(config_id)
        row = self.version_repo.get_by_number(config_id, version_number)
        if row is None:
            raise NotFoundException(
                message=(
                    f"版本 version_number={version_number} "
                    f"不存在于 config id={config_id}"
                ),
                code="AGENT_LOOPER_VERSION_NOT_FOUND",
            )
        return AgentLooperVersionRead.model_validate(row)

    # ==== helpers =====================================================

    def _reset_autobegin(self) -> None:
        if self.db.in_transaction():
            self.db.rollback()

    def _require_config(self, id: int) -> AgentLooperConfig:
        row = self.config_repo.get_by_id(id)
        if row is None:
            raise NotFoundException(
                message=f"AgentLooper 配置 id={id} 不存在",
                code="AGENT_LOOPER_NOT_FOUND",
            )
        return row

    def _require_owner_writable(self, id: int, user_id: int) -> AgentLooperConfig:
        row = self._require_config(id)
        if row.owner_user_id != user_id:
            raise BusinessException(
                message="仅配置创建者可操作",
                code="AGENT_LOOPER_FORBIDDEN",
                status_code=403,
            )
        return row

    def _to_read(self, cfg: AgentLooperConfig) -> AgentLooperConfigRead:
        current_version_number: Optional[int] = None
        if cfg.current_version_id is not None:
            version = self.version_repo.get_by_id(cfg.current_version_id)
            if version is not None:
                current_version_number = version.version_number

        data = {
            "id": cfg.id,
            "name": cfg.name,
            "type": cfg.type,
            "description": cfg.description,
            "current_version_id": cfg.current_version_id,
            "current_version_number": current_version_number,
            "active_config_json": cfg.active_config_json,
            "owner_user_id": cfg.owner_user_id,
            "is_active": bool(cfg.is_active),
            "is_published": bool(cfg.is_published),
            "settings": cfg.settings,
            "resource_bindings": cfg.resource_bindings,
            "credential_ref": cfg.credential_ref,
            "created_at": cfg.created_at,
            "updated_at": cfg.updated_at,
        }
        return AgentLooperConfigRead.model_validate(data)
