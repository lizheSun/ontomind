"""T35 · AgentLooperWriterService tests.

- 文件系统全部走 tmp_path，绝不写入 ~/.config/opencode。
- DB 用 in-memory sqlite + inline DDL，独立于 T34 model 分支。
- 覆盖：atomic rename、只 emit opencode 字段、body=system_prompt、
        目标目录不可写时优雅报错、is_published 标记更新。
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.services.agent_looper_writer_service import (
    AgentLooperWriterError,
    AgentLooperWriterService,
)


_DDL = """
CREATE TABLE agent_looper_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'custom_looper',
    description TEXT,
    active_config_json TEXT,
    owner_user_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_published INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
)
"""


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text(_DDL))
    Session_ = sessionmaker(bind=engine, autoflush=False, future=True)
    sess = Session_()
    try:
        yield sess
    finally:
        sess.close()
        engine.dispose()


def _insert_config(
    db: Session,
    *,
    name: str,
    cfg: dict,
    description: str = "desc",
    owner_user_id: int = 1,
) -> int:
    result = db.execute(
        text(
            "INSERT INTO agent_looper_configs "
            "(name, type, description, active_config_json, owner_user_id, is_active, is_published) "
            "VALUES (:name, 'custom_looper', :description, :cfg, :owner, 1, 0)"
        ),
        {
            "name": name,
            "description": description,
            "cfg": json.dumps(cfg),
            "owner": owner_user_id,
        },
    )
    db.commit()
    return result.lastrowid


def _parse_md(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith("---\n"), raw[:20]
    _, front, body = raw.split("---", 2)
    return yaml.safe_load(front), body.lstrip("\n")


# ---------- happy path ----------

def test_publish_writes_md_and_atomic(tmp_path, db):
    cfg_id = _insert_config(
        db,
        name="planner",
        cfg={
            "description": "拆任务",
            "mode": "subagent",
            "model": "openai/gpt-4o",
            "temperature": 0.3,
            "steps": 5,
            "permission": {"bash": "allow"},
            "system_prompt": "You plan things.",
        },
    )
    svc = AgentLooperWriterService(db)

    # 追踪 os.replace 是否被调用（原子性保证）
    with mock.patch("app.services.agent_looper_writer_service.os.replace", wraps=__import__("os").replace) as spy:
        path = svc.publish(config_id=cfg_id, config_path=str(tmp_path))

    assert spy.called, "publish MUST use os.replace (atomic rename)"
    # 没有残留 tmp 文件
    assert not (tmp_path / "planner.md.tmp").exists()

    dst = Path(path)
    assert dst == tmp_path / "planner.md"
    assert dst.exists()

    meta, body = _parse_md(dst)
    assert meta["name"] == "planner"
    assert meta["description"] == "拆任务"
    assert meta["mode"] == "subagent"
    assert meta["model"] == "openai/gpt-4o"
    assert meta["temperature"] == 0.3
    assert meta["steps"] == 5
    assert meta["permission"] == {"bash": "allow"}
    assert body.rstrip("\n") == "You plan things."


def test_publish_only_emits_opencode_fields(tmp_path, db):
    """非 opencode 字段（loop_strategy/custom_tools/memory_window/resource_bindings/credential_ref/tools）
    必须 **不** 出现在生成的 .md frontmatter 中。"""
    cfg_id = _insert_config(
        db,
        name="rich",
        cfg={
            "description": "with extras",
            "mode": "subagent",
            "model": "m",
            "temperature": 0.1,
            "permission": {"bash": "allow"},
            "system_prompt": "body",
            # 以下字段绝不能出现在生成的 md 里
            "loop_strategy": "react",
            "custom_tools": ["foo", "bar"],
            "memory_window": 8000,
            "resource_bindings": [{"type": "dp_source", "id": 1}],
            "credential_ref": {"credential_id": 42},
            "tools": ["bash", "read"],
        },
    )
    svc = AgentLooperWriterService(db)
    path = svc.publish(config_id=cfg_id, config_path=str(tmp_path))

    meta, _ = _parse_md(Path(path))
    forbidden = {
        "loop_strategy", "custom_tools", "memory_window",
        "resource_bindings", "credential_ref", "tools",
    }
    for f in forbidden:
        assert f not in meta, f"forbidden field {f} leaked into .md: {meta}"

    # 白名单字段仍在
    for f in ("name", "description", "mode", "model", "temperature", "permission"):
        assert f in meta


def test_publish_body_is_system_prompt(tmp_path, db):
    cfg_id = _insert_config(
        db,
        name="p",
        cfg={
            "description": "d",
            "mode": "subagent",
            "system_prompt": "line1\nline2\nline3",
        },
    )
    svc = AgentLooperWriterService(db)
    path = svc.publish(config_id=cfg_id, config_path=str(tmp_path))
    _, body = _parse_md(Path(path))
    assert body.rstrip("\n") == "line1\nline2\nline3"


def test_publish_marks_is_published(tmp_path, db):
    cfg_id = _insert_config(
        db,
        name="p",
        cfg={"description": "d", "system_prompt": "b"},
    )
    svc = AgentLooperWriterService(db)
    svc.publish(config_id=cfg_id, config_path=str(tmp_path))

    row = db.execute(
        text("SELECT is_published FROM agent_looper_configs WHERE id = :id"),
        {"id": cfg_id},
    ).first()
    assert row.is_published == 1


def test_publish_unknown_id_raises(tmp_path, db):
    svc = AgentLooperWriterService(db)
    with pytest.raises(AgentLooperWriterError):
        svc.publish(config_id=999, config_path=str(tmp_path))


def test_publish_invalid_target_path_fails_cleanly(tmp_path, db):
    """给一个无法创建/写入的目标目录，应抛 AgentLooperWriterError 而不是 raw OSError。"""
    cfg_id = _insert_config(
        db,
        name="p",
        cfg={"description": "d", "system_prompt": "b"},
    )
    svc = AgentLooperWriterService(db)

    bad_path = tmp_path / "conflict"
    bad_path.write_text("i am a file, not a dir")

    # 试图 mkdir 一个已存在的普通文件路径 → OSError → 服务应包裹成 AgentLooperWriterError
    with pytest.raises(AgentLooperWriterError):
        svc.publish(config_id=cfg_id, config_path=str(bad_path))


def test_publish_default_uses_setting_path(tmp_path, db, monkeypatch):
    """未显式传 config_path 时，读取 settings.AGENT_CONFIG_PATH —— 用 monkeypatch 覆写。"""
    from app.core import config as cfg_mod

    monkeypatch.setattr(cfg_mod.settings, "AGENT_CONFIG_PATH", str(tmp_path))

    cfg_id = _insert_config(
        db,
        name="fromenv",
        cfg={"description": "d", "system_prompt": "b"},
    )
    svc = AgentLooperWriterService(db)
    path = svc.publish(config_id=cfg_id)
    assert Path(path) == tmp_path / "fromenv.md"


def test_publish_omits_null_optional_fields(tmp_path, db):
    """cfg 中未提供的字段（None）不应写入 md（避免 opencode 拒识别）。"""
    cfg_id = _insert_config(
        db,
        name="minimal",
        cfg={"description": "only d", "system_prompt": "hi"},
    )
    svc = AgentLooperWriterService(db)
    path = svc.publish(config_id=cfg_id, config_path=str(tmp_path))
    meta, _ = _parse_md(Path(path))
    assert meta.get("name") == "minimal"
    assert meta.get("description") == "only d"
    # 未提供的字段不应写
    for k in ("mode", "model", "temperature", "steps", "permission"):
        assert k not in meta
