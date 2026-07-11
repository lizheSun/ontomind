"""AgentLooperService 测试（T34）— 覆盖 CRUD/版本链/回滚/软删除/所有权。"""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.user_model import User
from app.schemas.agent_looper_schema import (
    AgentLooperConfigCreate,
    AgentLooperConfigUpdate,
)
from app.services.agent_looper_service import AgentLooperService


@pytest.fixture
def other_user_id(db) -> int:
    u = User(
        username="mallory",
        email="m@e.f",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.flush()
    uid = int(u.id)
    db.commit()
    return uid


@pytest.fixture
def service(db) -> AgentLooperService:
    return AgentLooperService(db)


def _base_payload(**kw) -> AgentLooperConfigCreate:
    data = {
        "name": "looper-a",
        "type": "custom_looper",
        "description": "初始描述",
        "config_json": {"model": "gpt-4o", "prompt": "hello", "tools": []},
        "model_snapshot": "gpt-4o",
        "prompt_snapshot": "hello",
        "note": "v1",
    }
    data.update(kw)
    return AgentLooperConfigCreate(**data)


# ---- create ----------------------------------------------------------

def test_create_config_creates_version_one_and_sets_current(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    assert cfg.id > 0
    assert cfg.owner_user_id == user_id
    assert cfg.is_active is True
    assert cfg.is_published is False
    assert cfg.current_version_id is not None
    assert cfg.current_version_number == 1
    assert cfg.active_config_json == {
        "model": "gpt-4o", "prompt": "hello", "tools": [],
    }

    history = service.get_version_history(cfg.id)
    assert len(history) == 1
    assert history[0].version_number == 1
    assert history[0].config_json["model"] == "gpt-4o"


def test_create_default_type_is_custom_looper(service, user_id):
    # 只传必需字段，type 走默认值
    payload = AgentLooperConfigCreate(
        name="looper-default",
        config_json={"model": "gpt-4o", "prompt": "hi"},
    )
    cfg = service.create(payload, user_id=user_id)
    assert cfg.type == "custom_looper"


def test_create_resource_bindings_stored(service, user_id):
    bindings = {"llm_config_id": 42, "knowledge_base_ids": [1, 2]}
    creds = {"credential_type": "dp_source", "credential_id": 7}
    cfg = service.create(
        _base_payload(
            name="looper-bind",
            resource_bindings=bindings,
            credential_ref=creds,
            is_published=True,
        ),
        user_id=user_id,
    )
    assert cfg.resource_bindings == bindings
    assert cfg.credential_ref == creds
    assert cfg.is_published is True


def test_create_duplicate_name_same_owner_conflicts(service, user_id):
    service.create(_base_payload(name="dupe"), user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        service.create(_base_payload(name="dupe"), user_id=user_id)
    assert exc.value.code == "AGENT_LOOPER_NAME_EXISTS"


# ---- update ----------------------------------------------------------

def test_update_config_creates_version_two_and_updates_current(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    updated = service.update(
        cfg.id,
        AgentLooperConfigUpdate(
            description="v2 描述",
            config_json={"model": "gpt-4o-mini", "prompt": "new", "tools": ["web"]},
            note="迭代 v2",
        ),
        user_id=user_id,
    )
    assert updated.description == "v2 描述"
    assert updated.current_version_number == 2
    assert updated.active_config_json["prompt"] == "new"

    history = service.get_version_history(cfg.id)
    assert [v.version_number for v in history] == [1, 2]
    assert history[1].note == "迭代 v2"


def test_update_meta_only_does_not_create_new_version(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    updated = service.update(
        cfg.id,
        AgentLooperConfigUpdate(description="仅改元信息", is_published=True),
        user_id=user_id,
    )
    assert updated.description == "仅改元信息"
    assert updated.is_published is True
    # 版本仍然是 1
    assert updated.current_version_number == 1
    history = service.get_version_history(cfg.id)
    assert len(history) == 1


# ---- rollback --------------------------------------------------------

def test_rollback_creates_new_version_with_target_snapshot(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)  # v1
    service.update(
        cfg.id,
        AgentLooperConfigUpdate(
            config_json={"model": "x", "prompt": "v2-prompt"},
            note="v2",
        ),
        user_id=user_id,
    )
    rolled = service.rollback(cfg.id, target_version_number=1, user_id=user_id)

    assert rolled.current_version_number == 3
    # active_config_json 应该复原到 v1
    assert rolled.active_config_json == {
        "model": "gpt-4o", "prompt": "hello", "tools": [],
    }
    history = service.get_version_history(cfg.id)
    assert [v.version_number for v in history] == [1, 2, 3]
    # v3 note 记录回滚来源
    assert "回滚自 v1" in (history[2].note or "")
    # v3 的 config_json 与 v1 相同
    assert history[2].config_json == history[0].config_json


def test_rollback_to_missing_version_raises_not_found(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    with pytest.raises(NotFoundException) as exc:
        service.rollback(cfg.id, target_version_number=99, user_id=user_id)
    assert exc.value.code == "AGENT_LOOPER_VERSION_NOT_FOUND"


# ---- list / soft-delete ---------------------------------------------

def test_list_by_owner_filters_by_user(service, user_id, other_user_id):
    a = service.create(_base_payload(name="mine"), user_id=user_id)
    b = service.create(_base_payload(name="theirs"), user_id=other_user_id)
    mine = service.list_by_owner(user_id=user_id)
    theirs = service.list_by_owner(user_id=other_user_id)
    assert [c.id for c in mine] == [a.id]
    assert [c.id for c in theirs] == [b.id]


def test_soft_delete_hides_from_default_list(service, user_id):
    cfg = service.create(_base_payload(name="tobedeleted"), user_id=user_id)
    service.soft_delete(cfg.id, user_id=user_id)
    active = service.list_by_owner(user_id=user_id)
    assert cfg.id not in [c.id for c in active]
    all_ = service.list_by_owner(user_id=user_id, is_active=None)
    assert cfg.id in [c.id for c in all_]
    row = service.get_by_id(cfg.id)
    assert row.is_active is False


# ---- ownership ACL ---------------------------------------------------

def test_non_owner_cannot_update(service, user_id, other_user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        service.update(
            cfg.id,
            AgentLooperConfigUpdate(description="hack"),
            user_id=other_user_id,
        )
    assert exc.value.code == "AGENT_LOOPER_FORBIDDEN"


def test_non_owner_cannot_delete(service, user_id, other_user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        service.soft_delete(cfg.id, user_id=other_user_id)
    assert exc.value.code == "AGENT_LOOPER_FORBIDDEN"


def test_non_owner_cannot_rollback(service, user_id, other_user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    service.update(
        cfg.id,
        AgentLooperConfigUpdate(config_json={"a": 1}),
        user_id=user_id,
    )
    with pytest.raises(BusinessException) as exc:
        service.rollback(cfg.id, 1, user_id=other_user_id)
    assert exc.value.code == "AGENT_LOOPER_FORBIDDEN"


# ---- version history ordering --------------------------------------

def test_version_history_returns_ordered_rows(service, user_id):
    cfg = service.create(_base_payload(), user_id=user_id)
    for i in range(2, 5):
        service.update(
            cfg.id,
            AgentLooperConfigUpdate(config_json={"v": i}, note=f"v{i}"),
            user_id=user_id,
        )
    history = service.get_version_history(cfg.id)
    assert [v.version_number for v in history] == [1, 2, 3, 4]
    # get_version 精确定位
    v3 = service.get_version(cfg.id, 3)
    assert v3.config_json == {"v": 3}
