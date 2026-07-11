"""T35 · AgentLooperDiscoveryService tests.

隔离策略：T34 的 ORM 尚未合入本分支，因此本文件用 `sqlite:///:memory:` +
`CREATE TABLE` 内联建 `agent_looper_configs` 表；不依赖 T34 的 model 文件。
文件系统全部使用 pytest tmp_path，绝不触碰真实 ~/.config/opencode。
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.services.agent_looper_discovery_service import (
    AgentLooperDiscoveryService,
    _parse_frontmatter,
)


# ---------- fixtures ----------

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


# ---------- discover() ----------

def _write_agent(tmp_path, name: str, body: str) -> None:
    (tmp_path / f"{name}.md").write_text(body, encoding="utf-8")


def test_discover_missing_path_returns_empty(tmp_path):
    missing = tmp_path / "nope"
    assert AgentLooperDiscoveryService.discover(str(missing)) == []


def test_discover_empty_dir(tmp_path):
    assert AgentLooperDiscoveryService.discover(str(tmp_path)) == []


def test_discover_parses_valid_frontmatter(tmp_path):
    _write_agent(
        tmp_path,
        "planner",
        "---\n"
        "description: 拆任务专家\n"
        "mode: subagent\n"
        "model: openai/gpt-4o\n"
        "temperature: 0.2\n"
        "permission:\n"
        "  bash: allow\n"
        "---\n"
        "\n"
        "You are a planner. Break down big tasks.\n",
    )
    out = AgentLooperDiscoveryService.discover(str(tmp_path))
    assert len(out) == 1
    row = out[0]
    assert row["name"] == "planner"
    assert row["description"] == "拆任务专家"
    assert row["mode"] == "subagent"
    assert row["model"] == "openai/gpt-4o"
    assert row["temperature"] == 0.2
    assert row["permission"] == {"bash": "allow"}
    assert "You are a planner" in row["system_prompt"]


def test_discover_skips_invalid_yaml(tmp_path):
    # 有效
    _write_agent(
        tmp_path,
        "good",
        "---\nname: good\ndescription: ok\n---\nbody\n",
    )
    # 无效 YAML（未闭合括号）
    _write_agent(
        tmp_path,
        "bad_yaml",
        "---\ndescription: [unclosed\n---\nbody\n",
    )
    # 无 frontmatter
    _write_agent(tmp_path, "no_front", "just plain body\n")
    # 只一个 --- 分隔符
    _write_agent(tmp_path, "half", "---\ndescription: half\n")

    out = AgentLooperDiscoveryService.discover(str(tmp_path))
    names = {r["name"] for r in out}
    assert "good" in names
    assert "bad_yaml" not in names
    assert "no_front" not in names
    assert "half" not in names


def test_discover_multiple_agents_sorted(tmp_path):
    _write_agent(tmp_path, "b_agent", "---\ndescription: b\n---\nbody b\n")
    _write_agent(tmp_path, "a_agent", "---\ndescription: a\n---\nbody a\n")
    out = AgentLooperDiscoveryService.discover(str(tmp_path))
    assert [r["name"] for r in out] == ["a_agent", "b_agent"]


def test_parse_frontmatter_non_dict_yaml_rejected(tmp_path):
    p = tmp_path / "list.md"
    p.write_text("---\n- 1\n- 2\n---\nbody\n", encoding="utf-8")
    assert _parse_frontmatter(p) is None


def test_parse_frontmatter_unreadable_file_returns_none(tmp_path):
    # 不存在的路径
    assert _parse_frontmatter(tmp_path / "nope.md") is None


# ---------- upsert_discovered() ----------

def test_upsert_inserts_new_rows(db):
    svc = AgentLooperDiscoveryService(db)
    n = svc.upsert_discovered(
        [
            {"name": "planner", "description": "d1", "system_prompt": "sp1"},
            {"name": "critic", "description": "d2", "system_prompt": "sp2"},
        ],
        user_id=1,
    )
    assert n == 2
    rows = db.execute(text("SELECT name, type, is_published, is_active FROM agent_looper_configs ORDER BY name")).all()
    assert len(rows) == 2
    for r in rows:
        assert r.type == "opencode_native"
        assert r.is_published == 1
        assert r.is_active == 1


def test_upsert_updates_existing_rows(db):
    svc = AgentLooperDiscoveryService(db)
    svc.upsert_discovered(
        [{"name": "planner", "description": "old", "system_prompt": "sp"}],
        user_id=1,
    )
    # 第二次 upsert：description 变更
    svc.upsert_discovered(
        [{"name": "planner", "description": "new", "system_prompt": "sp2"}],
        user_id=1,
    )
    rows = db.execute(text("SELECT id, name, description FROM agent_looper_configs")).all()
    assert len(rows) == 1  # 仍然只有一行 = update 而非 insert
    assert rows[0].description == "new"


def test_upsert_ignores_entries_without_name(db):
    svc = AgentLooperDiscoveryService(db)
    n = svc.upsert_discovered(
        [{"description": "no name", "system_prompt": "x"}],
        user_id=1,
    )
    assert n == 0
    rows = db.execute(text("SELECT COUNT(*) c FROM agent_looper_configs")).first()
    assert rows.c == 0
