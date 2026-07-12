"""T48 · OpencodeSyncService tests.

覆盖：
- sync_from_opencode / sync_to_opencode 单向流
- dry-run 不落盘、不写库
- 覆写 opencode.json 时保留其它顶层字段
- 备份文件生成
- diff 输出可读
- API endpoints 通过 FastAPI TestClient
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.mcp_model import MCPConfig, MCPType
from app.db.models.skill_model import Skill, SkillType
from app.services.opencode_sync_service import (
    OpencodeSyncService,
    _mcp_row_to_opencode,
    _mcp_type_to_opencode,
)


# ---------------- helpers ----------------

def _write_opencode_json(root: Path, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "opencode.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_skill_md(root: Path, folder: str, name: str, description: str) -> Path:
    d = root / "skills" / folder
    d.mkdir(parents=True, exist_ok=True)
    md = d / "SKILL.md"
    md.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nbody\n", encoding="utf-8"
    )
    return md


def _make_mcp(db: Session, **kwargs) -> MCPConfig:
    row = MCPConfig(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_skill(db: Session, **kwargs) -> Skill:
    row = Skill(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------- pure helpers ----------------

def test_mcp_type_to_opencode_mapping():
    assert _mcp_type_to_opencode(MCPType.stdio) == "local"
    assert _mcp_type_to_opencode(MCPType.sse) == "remote"
    assert _mcp_type_to_opencode(MCPType.http) == "remote"
    assert _mcp_type_to_opencode("stdio") == "local"
    assert _mcp_type_to_opencode(None) == "remote"


def test_mcp_row_to_opencode_serializes_list_command(db: Session):
    row = _make_mcp(
        db,
        name="m1",
        mcp_type=MCPType.stdio,
        command="arkcli mcp web-search",
        env_vars={"K": "v"},
        description="d",
        is_active=True,
    )
    payload = _mcp_row_to_opencode(row)
    assert payload["type"] == "local"
    assert payload["command"] == ["arkcli", "mcp", "web-search"]
    assert payload["environment"] == {"K": "v"}
    assert payload["enabled"] is True
    assert payload["description"] == "d"


def test_mcp_row_to_opencode_single_word_command_stays_string(db: Session):
    row = _make_mcp(db, name="m2", mcp_type=MCPType.stdio, command="cmd", is_active=True)
    payload = _mcp_row_to_opencode(row)
    assert payload["command"] == "cmd"


# ---------------- sync_from_opencode ----------------

def test_sync_from_opencode_all_upserts_mcps_and_skills(db: Session, tmp_path):
    _write_opencode_json(
        tmp_path,
        {"mcp": {"m1": {"type": "local", "command": "run", "enabled": True}}},
    )
    _write_skill_md(tmp_path, "s1", "s1", "desc-1")
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_from_opencode(dry_run=False)
    assert result["mcps_found"] == 1
    assert result["skills_found"] == 1
    assert result["mcp_created"] == 1
    assert result["skill_created"] == 1
    assert db.query(MCPConfig).count() == 1
    assert db.query(Skill).count() == 1


def test_sync_from_opencode_dry_run_writes_nothing(db: Session, tmp_path):
    _write_opencode_json(
        tmp_path, {"mcp": {"m1": {"type": "local", "command": "run"}}}
    )
    _write_skill_md(tmp_path, "s1", "s1", "d")
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_from_opencode(dry_run=True)
    assert result["dry_run"] is True
    assert result["mcps_found"] == 1
    assert result["skills_found"] == 1
    assert db.query(MCPConfig).count() == 0
    assert db.query(Skill).count() == 0


def test_sync_from_opencode_target_mcps_only(db: Session, tmp_path):
    _write_opencode_json(
        tmp_path, {"mcp": {"m1": {"type": "local", "command": "run"}}}
    )
    _write_skill_md(tmp_path, "s1", "s1", "d")
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_from_opencode(dry_run=False, target="mcps")
    assert result["mcps_found"] == 1
    assert result["skills_found"] == 0
    assert db.query(MCPConfig).count() == 1
    assert db.query(Skill).count() == 0


# ---------------- sync_to_opencode ----------------

def test_sync_to_opencode_writes_mcp_section(db: Session, tmp_path):
    _make_mcp(
        db,
        name="m1",
        mcp_type=MCPType.stdio,
        command="run once",
        env_vars={"A": "1"},
        is_active=True,
    )
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_to_opencode(dry_run=False)
    assert result["mcps_written"] == 1
    written = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert "mcp" in written
    assert "m1" in written["mcp"]
    assert written["mcp"]["m1"]["command"] == ["run", "once"]
    assert written["mcp"]["m1"]["environment"] == {"A": "1"}


def test_sync_to_opencode_preserves_other_top_level_fields(db: Session, tmp_path):
    _write_opencode_json(
        tmp_path,
        {
            "$schema": "https://opencode.ai/schema.json",
            "theme": "dracula",
            "mcp": {"legacy": {"type": "local", "command": "old"}},
        },
    )
    _make_mcp(db, name="m1", mcp_type=MCPType.stdio, command="new-cmd", is_active=True)
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    svc.sync_to_opencode(dry_run=False)
    written = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert written["$schema"] == "https://opencode.ai/schema.json"
    assert written["theme"] == "dracula"
    # legacy 应被 DB 内容替换
    assert "legacy" not in written["mcp"]
    assert "m1" in written["mcp"]


def test_sync_to_opencode_creates_backup_when_file_exists(db: Session, tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"old": {"type": "local"}}})
    _make_mcp(db, name="m1", mcp_type=MCPType.stdio, command="c", is_active=True)
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_to_opencode(dry_run=False)
    assert result["backup_path"] is not None
    backup = Path(result["backup_path"])
    assert backup.is_file()
    assert ".bak." in backup.name


def test_sync_to_opencode_no_backup_when_no_prior_file(db: Session, tmp_path):
    _make_mcp(db, name="m1", mcp_type=MCPType.stdio, command="c", is_active=True)
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_to_opencode(dry_run=False)
    assert result["backup_path"] is None
    assert (tmp_path / "opencode.json").is_file()


def test_sync_to_opencode_dry_run_produces_diff_and_no_write(db: Session, tmp_path):
    _make_mcp(db, name="m1", mcp_type=MCPType.stdio, command="c", is_active=True)
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_to_opencode(dry_run=True)
    assert result["dry_run"] is True
    assert result["mcps_written"] == 1
    assert not (tmp_path / "opencode.json").exists()
    diff = result["diffs"]["opencode.json"]
    assert "m1" in diff


def test_sync_to_opencode_writes_skill_md(db: Session, tmp_path):
    _make_skill(
        db,
        name="my-skill",
        skill_type=SkillType.script,
        description="does things",
        tags=["a", "b"],
        is_installed=True,
        is_active=True,
    )
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    result = svc.sync_to_opencode(dry_run=False, target="skills")
    assert result["skills_written"] == 1
    md = tmp_path / "skills" / "my-skill" / "SKILL.md"
    assert md.is_file()
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: my-skill" in text
    assert "does things" in text


def test_sync_to_opencode_skips_inactive_mcps(db: Session, tmp_path):
    _make_mcp(db, name="on", mcp_type=MCPType.stdio, command="c", is_active=True)
    _make_mcp(db, name="off", mcp_type=MCPType.stdio, command="c", is_active=False)
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    svc.sync_to_opencode(dry_run=False)
    written = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert "on" in written["mcp"]
    assert "off" not in written["mcp"]


# ---------------- roundtrip ----------------

def test_roundtrip_file_to_db_to_file(db: Session, tmp_path):
    _write_opencode_json(
        tmp_path,
        {"mcp": {"m1": {"type": "local", "command": "run once", "enabled": True}}},
    )
    svc = OpencodeSyncService(db=db, config_path=str(tmp_path))
    svc.sync_from_opencode(dry_run=False)
    row = db.query(MCPConfig).filter(MCPConfig.name == "m1").one()
    assert row.command == "run once"
    # 写回
    svc.sync_to_opencode(dry_run=False)
    written = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert written["mcp"]["m1"]["command"] == ["run", "once"]


# ---------------- init guard ----------------

def test_service_requires_db():
    with pytest.raises(ValueError):
        OpencodeSyncService(db=None)  # type: ignore[arg-type]


# ---------------- API endpoints ----------------

def test_endpoint_skills_sync_in(db: Session, tmp_path, monkeypatch):
    _write_skill_md(tmp_path, "s1", "s1", "desc")
    from app.core.config import settings as _settings
    from app.api.v1 import resources as resources_module
    monkeypatch.setattr(_settings, "OPENCODE_CONFIG_PATH", str(tmp_path))
    body = resources_module.sync_skills({"direction": "in"}, db=db)
    assert body["code"] == "SUCCESS"
    assert body["data"]["skills_found"] == 1
    assert db.query(Skill).count() == 1


def test_endpoint_mcps_sync_out(db: Session, tmp_path, monkeypatch):
    _make_mcp(db, name="m1", mcp_type=MCPType.stdio, command="c", is_active=True)
    from app.core.config import settings as _settings
    from app.api.v1 import resources as resources_module
    monkeypatch.setattr(_settings, "OPENCODE_CONFIG_PATH", str(tmp_path))
    body = resources_module.sync_mcps({"direction": "out"}, db=db)
    assert body["code"] == "SUCCESS"
    assert body["data"]["mcps_written"] == 1
    assert (tmp_path / "opencode.json").is_file()


def test_endpoint_invalid_direction_rejected(db: Session, tmp_path, monkeypatch):
    from app.core.config import settings as _settings
    from app.api.v1 import resources as resources_module
    monkeypatch.setattr(_settings, "OPENCODE_CONFIG_PATH", str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        resources_module.sync_skills({"direction": "sideways"}, db=db)
    assert exc.value.status_code == 400
