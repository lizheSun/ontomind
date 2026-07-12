"""T47 · Node + container auto-discovery.

Coverage:
  A. AgentContainerDiscoveryService unit tests (scan_container / discover / discover_running)
  B. register-local integration — payload includes mcp_count / skill_count / container_count
  C. Graceful degradation for T46 + T47 hooks (missing service, raising service)
  D. Idempotency preserved (single instance row, hooks still run twice)
"""
from __future__ import annotations

import sys
import types
from typing import Any

import pytest


# ==========================================================================
# A. AgentContainerDiscoveryService unit tests
# ==========================================================================

from app.services.agent_container_discovery_service import (
    AgentContainerDiscoveryService,
    ContainerRecord,
    _CONTAINER_SPECS,
)


class _StubService(AgentContainerDiscoveryService):
    """Deterministic subclass — no real filesystem / subprocess / network."""

    def __init__(
        self,
        which_map: dict[str, str | None] | None = None,
        pgrep_map: dict[str, list[int]] | None = None,
        open_ports: set[int] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._which_map = which_map or {}
        self._pgrep_map = pgrep_map or {}
        self._open_ports = open_ports or set()

    def _which(self, name: str) -> str | None:
        return self._which_map.get(name)

    def _run_pgrep(self, pattern: str) -> list[int]:
        return list(self._pgrep_map.get(pattern, []))

    def _port_open(self, port: int) -> bool:
        return port in self._open_ports


def test_scan_container_all_signals_hit():
    svc = _StubService(
        which_map={"opencode": "/usr/local/bin/opencode"},
        pgrep_map={"opencode": [1234, 5678]},
        open_ports={5173},
    )
    rec = svc.scan_container("opencode")
    assert rec.is_running is True
    assert rec.cli_path == "/usr/local/bin/opencode"
    assert 1234 in rec.pids and 5678 in rec.pids
    assert 5173 in rec.open_ports
    assert rec.kind == "opencode"


def test_scan_container_no_signal():
    svc = _StubService()
    rec = svc.scan_container("harness")
    assert rec.is_running is False
    assert rec.cli_path is None
    assert rec.pids == []
    assert rec.open_ports == []


def test_scan_container_only_cli_counts_as_running():
    svc = _StubService(which_map={"claw": "/opt/bin/claw"})
    rec = svc.scan_container("openclaw")
    assert rec.is_running is True
    assert rec.cli_path == "/opt/bin/claw"


def test_scan_container_only_port_counts_as_running():
    svc = _StubService(open_ports={4000})
    rec = svc.scan_container("harness")
    assert rec.is_running is True
    assert rec.open_ports == [4000]


def test_scan_container_only_pgrep_counts_as_running():
    svc = _StubService(pgrep_map={"openclaw": [999]})
    rec = svc.scan_container("openclaw")
    assert rec.is_running is True
    assert rec.pids == [999]


def test_scan_container_deduplicates_pids_across_proc_names():
    svc = _StubService(pgrep_map={"openclaw": [10, 20], "claw": [20, 30]})
    rec = svc.scan_container("openclaw")
    assert sorted(rec.pids) == [10, 20, 30]


def test_discover_returns_all_kinds():
    svc = _StubService()
    recs = svc.discover()
    kinds = {r.kind for r in recs}
    assert kinds == set(_CONTAINER_SPECS.keys())


def test_discover_running_filters_out_absent():
    svc = _StubService(which_map={"opencode": "/x/opencode"})
    running = svc.discover_running()
    assert len(running) == 1
    assert running[0].kind == "opencode"


def test_container_record_to_dict_shape():
    rec = ContainerRecord(kind="opencode", label="OpenCode", icon="💻",
                          cli_path="/x", pids=[1], open_ports=[5173], is_running=True)
    d = rec.to_dict()
    assert d == {
        "kind": "opencode",
        "label": "OpenCode",
        "icon": "💻",
        "cli_path": "/x",
        "pids": [1],
        "open_ports": [5173],
        "is_running": True,
    }


def test_discover_survives_single_kind_failure(monkeypatch):
    """One kind blowing up in scan_container does not stop the others."""
    svc = _StubService(which_map={"opencode": "/x/opencode"})
    real_scan = svc.scan_container

    def _boom_for_harness(kind: str):
        if kind == "harness":
            raise RuntimeError("boom")
        return real_scan(kind)

    monkeypatch.setattr(svc, "scan_container", _boom_for_harness)
    recs = svc.discover()
    kinds = {r.kind for r in recs}
    assert kinds == set(_CONTAINER_SPECS.keys())
    hrn = next(r for r in recs if r.kind == "harness")
    assert hrn.is_running is False


def test_port_open_swallows_socket_errors(monkeypatch):
    """Real _port_open with a closed port must return False, not raise."""
    svc = AgentContainerDiscoveryService(port_timeout=0.05)
    assert svc._port_open(1) is False


def test_run_pgrep_returns_empty_when_pgrep_absent(monkeypatch):
    svc = AgentContainerDiscoveryService()

    def _raise(*a, **kw):
        raise FileNotFoundError("no pgrep")

    monkeypatch.setattr("subprocess.check_output", _raise)
    assert svc._run_pgrep("anything") == []


# ==========================================================================
# B/C/D. register-local integration
# ==========================================================================

def _install_fake_looper_service(record: dict | None = None,
                                 discover_return=None,
                                 upsert_raises=None):
    mod = types.ModuleType("app.services.agent_looper_discovery_service")

    class _FakeService:
        def discover(self):
            if record is not None:
                record["looper_discover"] = record.get("looper_discover", 0) + 1
            return discover_return if discover_return is not None else []

        def upsert_discovered(self, db, configs, user_id):
            if record is not None:
                record["looper_upsert"] = True
            if upsert_raises is not None:
                raise upsert_raises
            return configs or []

    mod.AgentLooperDiscoveryService = _FakeService
    sys.modules["app.services.agent_looper_discovery_service"] = mod
    return mod


def _uninstall_fake_looper_service():
    sys.modules.pop("app.services.agent_looper_discovery_service", None)


def _install_fake_opencode_config_service(mcp_created=0, mcp_updated=0,
                                          skill_created=0, skill_updated=0,
                                          raises=None,
                                          record: dict | None = None):
    mod = types.ModuleType("app.services.opencode_config_discovery_service")

    class _FakeSvc:
        def __init__(self, *args, **kwargs):
            if record is not None:
                record["oc_init"] = record.get("oc_init", 0) + 1
                record["oc_kwargs"] = kwargs

        def discover_all(self, dry_run: bool = False):
            if record is not None:
                record["oc_discover_dry_run"] = dry_run
            if raises is not None:
                raise raises
            return {
                "mcps_found": mcp_created + mcp_updated,
                "skills_found": skill_created + skill_updated,
                "mcp_created": mcp_created,
                "mcp_updated": mcp_updated,
                "skill_created": skill_created,
                "skill_updated": skill_updated,
                "created": mcp_created + skill_created,
                "updated": mcp_updated + skill_updated,
                "errors": [],
                "dry_run": dry_run,
            }

    mod.OpencodeConfigDiscoveryService = _FakeSvc
    sys.modules["app.services.opencode_config_discovery_service"] = mod
    return mod


def _uninstall_fake_opencode_config_service():
    sys.modules.pop("app.services.opencode_config_discovery_service", None)


def _install_fake_container_service(running_kinds: list[str] | None = None,
                                    raises=None,
                                    record: dict | None = None):
    mod = types.ModuleType("app.services.agent_container_discovery_service")

    class _FakeSvc:
        def __init__(self, *args, **kwargs):
            if record is not None:
                record["container_init"] = record.get("container_init", 0) + 1

        def discover_running(self):
            if raises is not None:
                raise raises
            kinds = running_kinds if running_kinds is not None else ["opencode"]
            return [_FakeRec(k) for k in kinds]

    class _FakeRec:
        def __init__(self, kind: str):
            self.kind = kind

        def to_dict(self):
            return {"kind": self.kind, "is_running": True}

    mod.AgentContainerDiscoveryService = _FakeSvc
    sys.modules["app.services.agent_container_discovery_service"] = mod
    return mod


def _uninstall_fake_container_service():
    sys.modules.pop("app.services.agent_container_discovery_service", None)


def _patch_agent_discovery(monkeypatch):
    from app.services import agent_discovery as ad_mod

    class _FakeResult:
        agents: list = []
        total_ports_scanned = 0
        errors: list = []

    def _fake_discover(host, instance_id=None, scan_processes=True):
        return _FakeResult()

    monkeypatch.setattr(ad_mod, "discover_agents", _fake_discover)


def test_register_local_payload_has_new_counts(client, monkeypatch, isolated_engine):
    _install_fake_looper_service()
    _install_fake_opencode_config_service(mcp_created=2, mcp_updated=1,
                                          skill_created=3, skill_updated=0)
    _install_fake_container_service(running_kinds=["opencode", "harness"])
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/instances/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert body["mcp_count"] == 3
        assert body["skill_count"] == 3
        assert body["container_count"] == 2
        assert isinstance(body["discovered_containers"], list)
        assert {c["kind"] for c in body["discovered_containers"]} == {"opencode", "harness"}
    finally:
        _uninstall_fake_looper_service()
        _uninstall_fake_opencode_config_service()
        _uninstall_fake_container_service()


def test_register_local_graceful_when_opencode_service_missing(client, monkeypatch, isolated_engine):
    _install_fake_looper_service()
    _uninstall_fake_opencode_config_service()
    _install_fake_container_service(running_kinds=[])
    _patch_agent_discovery(monkeypatch)
    try:
        import app.services.opencode_config_discovery_service as _real
        real_backup = _real
        sys.modules["app.services.opencode_config_discovery_service"] = types.ModuleType(
            "app.services.opencode_config_discovery_service"
        )
        try:
            resp = client.post("/api/v1/resources/instances/register-local")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["code"] == "SUCCESS"
            assert body["mcp_count"] == 0
            assert body["skill_count"] == 0
            assert "opencode_config_error" in body
        finally:
            sys.modules["app.services.opencode_config_discovery_service"] = real_backup
    finally:
        _uninstall_fake_looper_service()
        _uninstall_fake_container_service()


def test_register_local_graceful_when_opencode_service_raises(client, monkeypatch):
    _install_fake_looper_service()
    _install_fake_opencode_config_service(raises=RuntimeError("kapow"))
    _install_fake_container_service(running_kinds=[])
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/instances/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert body["mcp_count"] == 0
        assert body["skill_count"] == 0
        assert "opencode_config_error" in body
        assert "kapow" in body["opencode_config_error"]
    finally:
        _uninstall_fake_looper_service()
        _uninstall_fake_opencode_config_service()
        _uninstall_fake_container_service()


def test_register_local_graceful_when_container_service_raises(client, monkeypatch):
    _install_fake_looper_service()
    _install_fake_opencode_config_service()
    _install_fake_container_service(raises=RuntimeError("boom-c"))
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/instances/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert body["container_count"] == 0
        assert body["discovered_containers"] == []
        assert "agent_container_error" in body
        assert "boom-c" in body["agent_container_error"]
    finally:
        _uninstall_fake_looper_service()
        _uninstall_fake_opencode_config_service()
        _uninstall_fake_container_service()


def test_register_local_idempotent_with_new_hooks(client, monkeypatch, db_session):
    record: dict = {}
    _install_fake_looper_service(record=record)
    _install_fake_opencode_config_service(mcp_created=1, skill_created=1, record=record)
    _install_fake_container_service(running_kinds=["opencode"], record=record)
    _patch_agent_discovery(monkeypatch)
    try:
        r1 = client.post("/api/v1/resources/instances/register-local")
        assert r1.status_code == 200
        r2 = client.post("/api/v1/resources/instances/register-local")
        assert r2.status_code == 200

        import platform
        from app.db.models.instance_model import Instance
        rows = db_session.query(Instance).filter(Instance.name == platform.node()).all()
        assert len(rows) == 1

        b1 = r1.json()
        b2 = r2.json()
        for body in (b1, b2):
            assert "mcp_count" in body
            assert "skill_count" in body
            assert "container_count" in body
            assert body["container_count"] == 1
        assert record.get("oc_init", 0) >= 2, "OpencodeConfigDiscoveryService 应在两次调用中都被实例化"
        assert record.get("container_init", 0) >= 2, "AgentContainerDiscoveryService 应在两次调用中都被实例化"
    finally:
        _uninstall_fake_looper_service()
        _uninstall_fake_opencode_config_service()
        _uninstall_fake_container_service()
