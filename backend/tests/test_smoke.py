"""冒烟测试：验证 4 个路由域可用、已删模块确实 404、认证闸门有效。

当前路由域（2026-08-03）：
- `/api/v1/auth`     登录 / 注册 / me
- `/api/v1/users`    用户 CRUD
- `/api/v1/opencode` AIDE 探活 + 启停
- `/api/v1/compute`  算力管理（节点 + Docker + 容器终端）
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 基础健康检查
# ---------------------------------------------------------------------------

def test_root_and_health(anon_client):
    """/ 与 /health 无需认证，始终可用."""
    r = anon_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}

    r = anon_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "running"
    assert "name" in body and "version" in body


def test_openapi_exposes_expected_domains(anon_client):
    """OpenAPI 里只应出现约定的 /api/v1 域，多出来说明有未登记的模块。"""
    r = anon_client.get("/api/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]

    v1_domains = {
        p.split("/")[3]
        for p in paths
        if p.startswith("/api/v1/") and len(p.split("/")) > 3
    }
    assert v1_domains == {
        "auth", "users", "opencode", "compute",
        "agent-factory",
        "skill-platform",
        "dataops",
        "wiki",
        "metadata",
        "ontology",
        "harness",
        "kanban",
    }, f"实际: {v1_domains}"


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

def test_login_success_and_me(anon_client, test_user, override_db):
    """登录拿 token → 用 token 调 /auth/me."""
    from app.main import app

    override_db(app)
    try:
        r = anon_client.post(
            "/api/v1/auth/login",
            json={"username": "tester", "password": "test-pw"},
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["token_type"] == "bearer"
        token = data["access_token"]

        r = anon_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 200
        assert r.json()["data"]["username"] == "tester"
    finally:
        app.dependency_overrides.clear()


def test_login_wrong_password_401(anon_client, test_user, override_db):
    from app.main import app

    override_db(app)
    try:
        r = anon_client.post(
            "/api/v1/auth/login",
            json={"username": "tester", "password": "wrong-pw"},
        )
        assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("header", [None, "Bearer garbage", "Basic zzz", "nonsense"])
def test_users_requires_valid_token(anon_client, header):
    """/users 必须要有效 JWT，缺失或伪造都应 401."""
    headers = {"Authorization": header} if header else {}
    r = anon_client.get("/api/v1/users", headers=headers)
    assert r.status_code == 401, f"header={header!r} → {r.status_code}"


# ---------------------------------------------------------------------------
# AIDE（opencode）探活
# ---------------------------------------------------------------------------

def test_opencode_web_status_shape(client):
    """/opencode/web/status?fast=1 应返回统一响应壳 + 关键字段.

    不断言 healthy 真假（取决于本机有没有跑 opencode），只校验协议。
    """
    r = client.get("/api/v1/opencode/web/status", params={"fast": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == "SUCCESS"
    d = body["data"]
    for key in (
        "healthy", "embed_url", "embed_source",
        "serve_port", "serve_healthy", "web_port", "web_healthy",
    ):
        assert key in d, f"缺字段 {key}"
    assert d["embed_source"] in ("serve", "web", "none")


# ---------------------------------------------------------------------------
# 已删模块必须 404（防止回归时误恢复）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    [
        # 第一批删除
        "/api/v1/perception/datasources",
        "/api/v1/cognition/versions",
        "/api/v1/decision/models",
        "/api/v1/execution/monitor/status",
        "/api/v1/resources/skills",
        "/api/v1/agent-looper/configs",
        "/api/v1/agent-platform/agents",
        "/api/v1/opencode/health",
        "/api/v1/opencode/session-link",
        # 第二批删除（compute 已恢复，勿加回此列表）
        "/api/v1/experts",
        "/api/v1/experts/skill-mcp/skills",
        "/api/v1/data-platform/sources",
        "/api/v1/knowledge-base/libraries",
        "/api/v1/llm",
    ],
)
def test_deleted_endpoints_are_gone(client, path):
    assert client.get(path).status_code == 404, f"{path} 竟然还活着"


# ---------------------------------------------------------------------------
# ORM 应 5 张表（用户 4 + 算力节点 1）
# ---------------------------------------------------------------------------

def test_orm_has_expected_tables():
    import app.db.models  # noqa: F401
    from app.db.session import Base

    assert {t.name for t in Base.metadata.sorted_tables} == {
        "users", "roles", "user_roles", "audit_logs", "compute_nodes",
        "container_services",
        "agent_templates", "agent_template_versions",
        "skill_templates", "skill_files",
        "agent_bundles", "bundle_members",
        "deployments",
        "skill_meta", "skill_params",
        "skill_exec_prompt", "skill_exec_api", "skill_exec_flow_nodes",
        "skill_policy",
        "skill_versions", "skill_audit_logs",
        "skill_invocations",
        "data_sources",
        "wiki_spaces", "wiki_documents", "wiki_document_versions",
        "meta_scan_jobs", "meta_tables", "meta_columns",
        "glossary_terms", "annotations",
        "meta_standards", "meta_standard_versions",
        "meta_column_standards", "meta_column_standard_history",
        "meta_database_briefs", "platform_llm_settings",
        "ontologies", "ontology_build_jobs",
        "ontology_object_types", "ontology_properties", "ontology_link_types",
        "ontology_mappings", "ontology_metrics", "ontology_cqs", "ontology_versions",
        "harness_sessions", "harness_messages",
        "kanban_boards", "kanban_columns", "kanban_tasks",
    }
