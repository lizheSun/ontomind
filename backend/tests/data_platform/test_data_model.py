"""T44 · 数据模型冒烟测试 — 核心资源表可导入、可 create_all。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def sqlite_engine():
    import app.db.models  # noqa: F401 — populate metadata
    from app.db.session import Base

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_core_models_importable() -> None:
    from app.db.models import (
        Agent,
        AgentContainer,
        AgentMCP,
        AgentSkill,
        ComputeNode,
        ContainerAgent,
        ContainerMCP,
        ContainerSkill,
        MCP,
        NodeContainer,
        Skill,
    )

    for cls in (
        ComputeNode, AgentContainer, Agent, Skill, MCP,
        NodeContainer, ContainerAgent, ContainerSkill, ContainerMCP,
        AgentSkill, AgentMCP,
    ):
        assert cls.__tablename__


def test_core_tables_created(sqlite_engine) -> None:
    insp = inspect(sqlite_engine)
    tables = set(insp.get_table_names())
    expected = {
        "compute_nodes", "agent_containers", "agents", "skills", "mcps",
        "node_containers", "container_agents", "container_skills",
        "container_mcps", "agent_skills", "agent_mcps",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"


def test_association_tables_have_binding_type(sqlite_engine) -> None:
    insp = inspect(sqlite_engine)
    for tbl in (
        "node_containers", "container_agents", "container_skills",
        "container_mcps", "agent_skills", "agent_mcps",
    ):
        cols = {c["name"] for c in insp.get_columns(tbl)}
        assert "binding_type" in cols, f"{tbl} missing binding_type"


def test_agent_has_expected_columns(sqlite_engine) -> None:
    insp = inspect(sqlite_engine)
    cols = {c["name"] for c in insp.get_columns("agents")}
    for expected in (
        "name", "type", "container_id", "description", "model", "temperature",
        "loop_strategy", "system_prompt", "tool_permissions", "custom_tools",
        "memory_window", "guardrails", "resource_bindings", "credential_ref",
        "is_active", "is_published", "version", "published_path",
    ):
        assert expected in cols, f"agents missing {expected}"


def test_mcp_backward_compat_alias() -> None:
    from app.db.models import MCP, MCPConfig
    from app.db.models.mcp_model import MCPConfig as ModuleAlias

    assert MCPConfig is MCP
    assert ModuleAlias is MCP


def test_opencode_config_path_setting() -> None:
    from app.core.config import settings

    assert hasattr(settings, "OPENCODE_CONFIG_PATH")
    assert settings.OPENCODE_CONFIG_PATH == "~/.config/opencode"