"""T44 · 数据模型冒烟测试 — 12 张新表可导入、可 create_all、字段/枚举/外键正确。"""
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


def test_all_12_models_importable() -> None:
    from app.db.models import (
        Agent,
        AgentContainer,
        AgentMCP,
        AgentRunJob,
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
        AgentSkill, AgentMCP, AgentRunJob,
    ):
        assert cls.__tablename__


def test_all_12_tables_created(sqlite_engine) -> None:
    insp = inspect(sqlite_engine)
    tables = set(insp.get_table_names())
    expected = {
        "compute_nodes", "agent_containers", "agents", "skills", "mcps",
        "node_containers", "container_agents", "container_skills",
        "container_mcps", "agent_skills", "agent_mcps", "agent_run_jobs",
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


def test_agent_run_job_status_column(sqlite_engine) -> None:
    insp = inspect(sqlite_engine)
    cols = {c["name"]: c for c in insp.get_columns("agent_run_jobs")}
    assert "status" in cols
    assert "steps" in cols
    assert "progress" in cols
    assert "created_by_user_id" in cols


def test_agent_run_job_status_lifecycle(sqlite_engine) -> None:
    from app.db.models import Agent, AgentRunJob
    from app.db.models.user_model import User

    SessionLocal = sessionmaker(bind=sqlite_engine, future=True)
    session = SessionLocal()
    try:
        user = User(username="t44", email="t44@t.io", password_hash="x")
        session.add(user)
        session.flush()
        agent = Agent(name="t44-agent", type="custom_looper")
        session.add(agent)
        session.flush()

        job = AgentRunJob(
            agent_id=agent.id,
            name="job-1",
            status="pending",
            created_by_user_id=user.id,
        )
        session.add(job)
        session.commit()
        assert job.id is not None
        assert job.status == "pending"

        for s in ("running", "paused", "completed", "failed", "cancelled"):
            job.status = s
            session.commit()
            assert job.status == s
    finally:
        session.close()


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
