"""T46 · OpencodeConfigDiscoveryService tests.

隔离策略：
- 用 conftest 的 `db` fixture（in-memory sqlite + create_all），确保 mcp_configs / skills 表存在。
- 文件系统全部使用 pytest `tmp_path`；service 用 `config_path=` 覆盖默认路径，绝不触碰真实 ~/.config/opencode。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db.models.mcp_model import MCPConfig, MCPType
from app.db.models.skill_model import Skill
from app.services.opencode_config_discovery_service import (
    OpencodeConfigDiscoveryService,
    _split_frontmatter,
)


# ---------------- helpers ----------------

def _write_opencode_json(root: Path, payload: dict) -> None:
    (root / "opencode.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_skill(root: Path, folder: str, frontmatter: str, body: str = "body content") -> Path:
    d = root / "skills" / folder
    d.mkdir(parents=True, exist_ok=True)
    md = d / "SKILL.md"
    md.write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
    return md


# ---------------- discover_mcps ----------------

def test_discover_mcps_missing_config_returns_empty(tmp_path):
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    mcps, errors = svc.discover_mcps()
    assert mcps == []
    assert errors == []


def test_discover_mcps_local_and_remote(tmp_path):
    _write_opencode_json(tmp_path, {
        "mcp": {
            "byted-web-search": {
                "type": "local",
                "command": ["arkcli", "mcp", "web-search"],
                "environment": {"ARK_API_KEY": "xxx"},
                "enabled": True,
            },
            "dataPro-search": {
                "type": "remote",
                "url": "https://mcp.example.com/v1",
                "headers": {"Authorization": "Bearer yyy"},
                "enabled": True,
            },
        }
    })
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    mcps, errors = svc.discover_mcps()
    assert errors == []
    by_name = {m["name"]: m for m in mcps}
    assert set(by_name) == {"byted-web-search", "dataPro-search"}

    local = by_name["byted-web-search"]
    assert local["mcp_type"] == MCPType.stdio
    assert local["command"] == "arkcli mcp web-search"
    assert local["env_vars"] == {"ARK_API_KEY": "xxx"}
    assert local["is_active"] is True

    remote = by_name["dataPro-search"]
    assert remote["mcp_type"] == MCPType.sse
    assert remote["url"] == "https://mcp.example.com/v1"
    assert remote["headers"] == {"Authorization": "Bearer yyy"}


def test_discover_mcps_disabled_flag_preserved(tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "local", "command": "x", "enabled": False}}})
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    mcps, _ = svc.discover_mcps()
    assert mcps[0]["is_active"] is False


def test_discover_mcps_invalid_json_captured_as_error(tmp_path):
    (tmp_path / "opencode.json").write_text("{ this is not json", encoding="utf-8")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    mcps, errors = svc.discover_mcps()
    assert mcps == []
    assert len(errors) == 1
    assert "invalid JSON" in errors[0]


def test_discover_mcps_bad_entry_skipped(tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"good": {"type": "local", "command": "x"}, "bad": "not-a-dict"}})
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    mcps, errors = svc.discover_mcps()
    assert [m["name"] for m in mcps] == ["good"]
    assert any("bad" in e for e in errors)


# ---------------- discover_skills ----------------

def test_discover_skills_missing_dir_returns_empty(tmp_path):
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    skills, errors = svc.discover_skills()
    assert skills == []
    assert errors == []


def test_discover_skills_parses_frontmatter(tmp_path):
    _write_skill(
        tmp_path,
        "sql-writer",
        "name: sql-writer\ndescription: writes SQL queries\ntags:\n  - sql\n  - db",
        body="# Body\nsome content",
    )
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    skills, errors = svc.discover_skills()
    assert errors == []
    assert len(skills) == 1
    row = skills[0]
    assert row["name"] == "sql-writer"
    assert row["description"] == "writes SQL queries"
    assert row["tags"] == ["sql", "db"]
    assert row["is_installed"] is True
    assert row["entrypoint"].endswith("SKILL.md")


def test_discover_skills_broken_frontmatter_collected_as_error(tmp_path):
    (tmp_path / "skills" / "broken").mkdir(parents=True)
    (tmp_path / "skills" / "broken" / "SKILL.md").write_text(
        "---\ndescription: [unclosed\n---\nbody\n",
        encoding="utf-8",
    )
    _write_skill(tmp_path, "ok", "name: ok\ndescription: fine")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    skills, errors = svc.discover_skills()
    assert [s["name"] for s in skills] == ["ok"]
    assert any("broken" in e for e in errors)


def test_discover_skills_ignores_dir_without_skill_md(tmp_path):
    (tmp_path / "skills" / "empty-dir").mkdir(parents=True)
    _write_skill(tmp_path, "real", "name: real\ndescription: real one")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    skills, _ = svc.discover_skills()
    assert [s["name"] for s in skills] == ["real"]


def test_split_frontmatter_edge_cases():
    assert _split_frontmatter("no frontmatter")[0] is None
    assert _split_frontmatter("---\nno close")[0] is None
    assert _split_frontmatter("---\n- 1\n- 2\n---\nbody")[0] is None
    meta, body = _split_frontmatter("---\nname: x\n---\nhello")
    assert meta == {"name": "x"}
    assert body.startswith("hello")


# ---------------- upsert ----------------

def test_upsert_mcps_creates_and_is_idempotent(db: Session, tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "local", "command": "run", "enabled": True}}})
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    mcps, _ = svc.discover_mcps()
    created, updated = svc.upsert_mcps(mcps)
    assert (created, updated) == (1, 0)

    created2, updated2 = svc.upsert_mcps(mcps)
    assert (created2, updated2) == (0, 1)

    rows = db.query(MCPConfig).all()
    assert len(rows) == 1
    assert rows[0].name == "m1"
    assert rows[0].mcp_type == MCPType.stdio


def test_upsert_mcps_updates_changed_fields(db: Session, tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "local", "command": "old"}}})
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    mcps, _ = svc.discover_mcps()
    svc.upsert_mcps(mcps)

    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "remote", "url": "https://x", "enabled": False}}})
    mcps2, _ = svc.discover_mcps()
    svc.upsert_mcps(mcps2)

    row = db.query(MCPConfig).filter(MCPConfig.name == "m1").one()
    assert row.mcp_type == MCPType.sse
    assert row.url == "https://x"
    assert bool(row.is_active) is False


def test_upsert_skills_creates_and_is_idempotent(db: Session, tmp_path):
    _write_skill(tmp_path, "s1", "name: s1\ndescription: first")
    _write_skill(tmp_path, "s2", "name: s2\ndescription: second")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    skills, _ = svc.discover_skills()
    created, updated = svc.upsert_skills(skills)
    assert (created, updated) == (2, 0)

    created2, updated2 = svc.upsert_skills(skills)
    assert (created2, updated2) == (0, 2)

    rows = db.query(Skill).order_by(Skill.name).all()
    assert [r.name for r in rows] == ["s1", "s2"]
    assert all(r.is_installed for r in rows)


def test_discover_all_dry_run_does_not_write(db: Session, tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "local", "command": "run"}}})
    _write_skill(tmp_path, "s1", "name: s1\ndescription: d")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    result = svc.discover_all(dry_run=True)
    assert result["mcps_found"] == 1
    assert result["skills_found"] == 1
    assert result["dry_run"] is True
    assert result["created"] == 0
    assert result["updated"] == 0
    assert db.query(MCPConfig).count() == 0
    assert db.query(Skill).count() == 0


def test_discover_all_writes_when_not_dry(db: Session, tmp_path):
    _write_opencode_json(tmp_path, {"mcp": {"m1": {"type": "local", "command": "run"}}})
    _write_skill(tmp_path, "s1", "name: s1\ndescription: d")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    result = svc.discover_all(dry_run=False)
    assert result["created"] == 2
    assert result["updated"] == 0
    assert db.query(MCPConfig).count() == 1
    assert db.query(Skill).count() == 1

    result2 = svc.discover_all(dry_run=False)
    assert result2["created"] == 0
    assert result2["updated"] == 2


def test_discover_all_errors_do_not_break_flow(db: Session, tmp_path):
    (tmp_path / "opencode.json").write_text("{not-json", encoding="utf-8")
    _write_skill(tmp_path, "ok", "name: ok\ndescription: d")
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path), db=db)
    result = svc.discover_all(dry_run=False)
    assert result["mcps_found"] == 0
    assert result["skills_found"] == 1
    assert len(result["errors"]) >= 1
    assert db.query(Skill).count() == 1


def test_upsert_without_db_raises(tmp_path):
    svc = OpencodeConfigDiscoveryService(config_path=str(tmp_path))
    with pytest.raises(RuntimeError):
        svc.upsert_mcps([{"name": "x"}])
    with pytest.raises(RuntimeError):
        svc.upsert_skills([{"name": "x"}])
