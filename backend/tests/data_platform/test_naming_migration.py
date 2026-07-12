"""T45 · Naming migration — Instance→ComputeNode, AgentLooperConfig→Agent, MCPConfig→MCP.

Verifies that:
  1. Legacy `/api/v1/resources/instances*` paths return **HTTP 308 Permanent
     Redirect** to the new canonical `/api/v1/resources/compute-nodes*` paths.
  2. Legacy `/api/v1/resources/mcp-configs*` paths return 308 to `/api/v1/resources/mcps*`.
  3. Legacy `/api/v1/agent-looper/configs*` paths return 308 to `/api/v1/resources/agents*`.
  4. New `/compute-nodes` canonical routes work end-to-end (CRUD + register-local).
  5. Backwards-compat service aliases still resolve
     (`InstanceService is ComputeNodeService`, `AgentLooperService` present).

308 (not 301) is required so POST/PUT/DELETE bodies survive the redirect.
Tests explicitly pass `follow_redirects=False` to observe the redirect status
rather than the resolved 2xx that TestClient would show by default.
"""
from __future__ import annotations

import sys
import types
from typing import Any

import pytest


# --- Fake service used by /register-local so tests avoid real port scans ---


def _install_fake_agent_looper_discovery():
    mod = types.ModuleType("app.services.agent_looper_discovery_service")

    class _FakeService:
        def discover(self):  # noqa: D401 - test double
            return []

        def upsert_discovered(self, db, configs, user_id):  # noqa: D401
            return []

    mod.AgentLooperDiscoveryService = _FakeService
    sys.modules["app.services.agent_looper_discovery_service"] = mod


def _uninstall_fake_agent_looper_discovery():
    sys.modules.pop("app.services.agent_looper_discovery_service", None)


def _patch_agent_discovery(monkeypatch):
    from app.services import agent_discovery as ad_mod

    class _FakeResult:
        agents: list[Any] = []
        total_ports_scanned = 0
        errors: list[str] = []

        def __init__(self, host, instance_id=None):
            pass

    def _fake_discover(host, instance_id=None, scan_processes=True):
        return _FakeResult(host, instance_id)

    monkeypatch.setattr(ad_mod, "discover_agents", _fake_discover)


# --- 1. Legacy /instances → 308 → /compute-nodes ----------------------------


@pytest.mark.parametrize(
    "method, legacy_path, canonical_path",
    [
        ("GET", "/api/v1/resources/instances", "/api/v1/resources/compute-nodes"),
        ("POST", "/api/v1/resources/instances", "/api/v1/resources/compute-nodes"),
        ("GET", "/api/v1/resources/instances/7", "/api/v1/resources/compute-nodes/7"),
        ("PUT", "/api/v1/resources/instances/7", "/api/v1/resources/compute-nodes/7"),
        (
            "DELETE",
            "/api/v1/resources/instances/7",
            "/api/v1/resources/compute-nodes/7",
        ),
        (
            "POST",
            "/api/v1/resources/instances/7/heartbeat",
            "/api/v1/resources/compute-nodes/7/heartbeat",
        ),
        (
            "POST",
            "/api/v1/resources/instances/register-local",
            "/api/v1/resources/compute-nodes/register-local",
        ),
        (
            "POST",
            "/api/v1/resources/instances/7/scan-agents",
            "/api/v1/resources/compute-nodes/7/scan-agents",
        ),
    ],
)
def test_legacy_instance_paths_redirect_308_to_compute_nodes(
    client, method: str, legacy_path: str, canonical_path: str
):
    resp = client.request(method, legacy_path, follow_redirects=False)
    assert resp.status_code == 308, (
        f"{method} {legacy_path} expected 308, got {resp.status_code}"
    )
    assert resp.headers["location"].startswith(canonical_path), (
        f"{method} {legacy_path} redirected to {resp.headers['location']}, "
        f"expected prefix {canonical_path}"
    )


# --- 2. Legacy /mcp-configs → 308 → /mcps -----------------------------------


@pytest.mark.parametrize(
    "method, legacy_path, canonical_path",
    [
        ("GET", "/api/v1/resources/mcp-configs", "/api/v1/resources/mcps"),
        ("POST", "/api/v1/resources/mcp-configs", "/api/v1/resources/mcps"),
        ("GET", "/api/v1/resources/mcp-configs/3", "/api/v1/resources/mcps/3"),
        ("PUT", "/api/v1/resources/mcp-configs/3", "/api/v1/resources/mcps/3"),
        ("DELETE", "/api/v1/resources/mcp-configs/3", "/api/v1/resources/mcps/3"),
    ],
)
def test_legacy_mcp_config_paths_redirect_308_to_mcps(
    client, method: str, legacy_path: str, canonical_path: str
):
    resp = client.request(method, legacy_path, follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"].startswith(canonical_path)


# --- 3. Legacy /agent-looper/configs → 308 → /resources/agents --------------


@pytest.mark.parametrize(
    "method, legacy_path",
    [
        ("GET", "/api/v1/agent-looper/configs"),
        ("POST", "/api/v1/agent-looper/configs"),
    ],
)
def test_legacy_agent_looper_configs_redirect_308_to_resources_agents(
    client, method: str, legacy_path: str
):
    resp = client.request(method, legacy_path, follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"].startswith("/api/v1/resources/agents")


# --- 4. New /compute-nodes canonical routes work end-to-end -----------------


def test_compute_nodes_crud_roundtrip(client):
    """POST → GET-list → GET-one → PUT → DELETE all succeed on the new prefix."""
    payload = {
        "name": "canonical-node-1",
        "host": "10.0.0.7",
        "port": 22,
        "instance_type": "physical",
        "protocol": "ssh",
    }
    create = client.post("/api/v1/resources/compute-nodes", json=payload)
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["code"] == "SUCCESS"
    node_id = body["data"]["id"]

    listed = client.get("/api/v1/resources/compute-nodes")
    assert listed.status_code == 200
    names = [n["name"] for n in listed.json()["data"]]
    assert "canonical-node-1" in names

    got = client.get(f"/api/v1/resources/compute-nodes/{node_id}")
    assert got.status_code == 200
    assert got.json()["data"]["host"] == "10.0.0.7"

    upd = client.put(
        f"/api/v1/resources/compute-nodes/{node_id}",
        json={"description": "canonical rename"},
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["description"] == "canonical rename"

    dele = client.delete(f"/api/v1/resources/compute-nodes/{node_id}")
    assert dele.status_code == 200
    assert dele.json()["code"] == "SUCCESS"


def test_legacy_instances_post_follow_redirect_lands_on_canonical_and_creates(
    client,
):
    """POST /instances (with follow_redirects=True) creates a row via the
    canonical /compute-nodes handler — proves 308 preserves method + body."""
    payload = {
        "name": "legacy-follow-node",
        "host": "10.0.0.8",
        "port": 22,
        "instance_type": "physical",
        "protocol": "ssh",
    }
    resp = client.post(
        "/api/v1/resources/instances", json=payload, follow_redirects=True
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["name"] == "legacy-follow-node"

    listed = client.get("/api/v1/resources/compute-nodes")
    names = [n["name"] for n in listed.json()["data"]]
    assert "legacy-follow-node" in names


def test_register_local_reachable_via_new_canonical_path(client, monkeypatch):
    _install_fake_agent_looper_discovery()
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/compute-nodes/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert "agent_looper_count" in body
        assert "hostname" in body
    finally:
        _uninstall_fake_agent_looper_discovery()


# --- 5. Service-layer backwards-compat aliases ------------------------------


def test_instance_service_alias_points_at_compute_node_service():
    from app.services.instance_service import (
        ComputeNodeService,
        InstanceService,
    )

    assert InstanceService is ComputeNodeService, (
        "InstanceService must remain importable as an alias of ComputeNodeService"
    )


def test_agent_looper_service_still_importable_from_agent_service():
    """The renamed facade must not break `from app.services.agent_service import
    AgentLooperService` for downstream callers."""
    from app.services.agent_service import (
        AgentConfigService,
        AgentLooperService,
        AgentService,
    )

    assert AgentService is not None
    assert AgentConfigService is not None
    assert AgentLooperService is not None
    assert issubclass(AgentConfigService, AgentLooperService)


def test_mcp_config_model_alias_still_resolves():
    """`MCPConfig` remains importable as an alias of `MCP` (T44 alias)."""
    from app.db.models import MCP, MCPConfig

    assert MCPConfig is MCP
