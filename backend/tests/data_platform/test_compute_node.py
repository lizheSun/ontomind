"""T37 · Compute node auto-discovery — register-local + AgentLooperDiscoveryService hook.

Coverage:
  1. register-local payload includes agent_looper_count field (additive)
  2. AgentLooperDiscoveryService is called with correct db + user_id
  3. Graceful degradation when service is missing / raises (does not break register-local)
  4. Idempotency — calling register-local twice does not duplicate the local node row
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


# --- helpers -----------------------------------------------------------------


def _install_fake_service(discover_return=None, upsert_return=None, upsert_raises=None,
                          record: dict | None = None):
    """Install a fake `app.services.agent_looper_discovery_service` module.

    The fake exposes `AgentLooperDiscoveryService` with `discover()` +
    `upsert_discovered(db, configs, user_id)`. Every call is recorded in
    `record` (if provided) for assertion.
    """
    mod = types.ModuleType("app.services.agent_looper_discovery_service")

    class _FakeService:
        def __init__(self):
            if record is not None:
                record["init_called"] = record.get("init_called", 0) + 1

        def discover(self):
            if record is not None:
                record["discover_called"] = record.get("discover_called", 0) + 1
            return discover_return if discover_return is not None else [{"name": "fake-cfg"}]

        def upsert_discovered(self, db, configs, user_id):
            if record is not None:
                record["upsert_call"] = {
                    "db_is_none": db is None,
                    "configs": configs,
                    "user_id": user_id,
                }
            if upsert_raises is not None:
                raise upsert_raises
            return upsert_return if upsert_return is not None else configs or []

    mod.AgentLooperDiscoveryService = _FakeService
    sys.modules["app.services.agent_looper_discovery_service"] = mod
    return mod


def _uninstall_fake_service():
    sys.modules.pop("app.services.agent_looper_discovery_service", None)


def _patch_agent_discovery(monkeypatch):
    """Stub discover_agents to return empty result — real one does port scans."""
    from app.services import agent_discovery as ad_mod

    class _FakeResult:
        agents: list = []
        total_ports_scanned = 0
        errors: list = []

        def __init__(self, host, instance_id=None):
            pass

    def _fake_discover(host, instance_id=None, scan_processes=True):
        return _FakeResult(host, instance_id)

    monkeypatch.setattr(ad_mod, "discover_agents", _fake_discover)
    # resources.py does `from app.services.agent_discovery import discover_agents`
    # inline — that resolves at call time, so patching the module attr is enough.


# --- tests -------------------------------------------------------------------


def test_register_local_payload_has_agent_looper_count(client, monkeypatch, isolated_engine):
    """新字段 agent_looper_count 必须出现在 payload 中。"""
    record: dict = {}
    _install_fake_service(discover_return=[{"a": 1}, {"a": 2}, {"a": 3}],
                          upsert_return=[1, 2, 3], record=record)
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/instances/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert "agent_looper_count" in body
        assert body["agent_looper_count"] == 3
        assert "hostname" in body
        assert "platform" in body
        assert "agent_count" in body
        # 主键 data 仍然存在（保持向后兼容）
        assert "data" in body and body["data"].get("name")
    finally:
        _uninstall_fake_service()


def test_agent_looper_service_called_with_db_and_user_id(client, monkeypatch, test_user):
    """AgentLooperDiscoveryService.upsert_discovered 收到正确的 db + user_id。"""
    record: dict = {}
    _install_fake_service(record=record)
    _patch_agent_discovery(monkeypatch)
    try:
        # 带 auth header — 传递 user_id
        resp = client.post(
            "/api/v1/resources/instances/register-local",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        assert resp.status_code == 200, resp.text
        assert record.get("init_called", 0) >= 1, "service ctor 未被调用"
        assert record.get("discover_called", 0) >= 1, "discover() 未被调用"
        call = record.get("upsert_call")
        assert call is not None, "upsert_discovered 未被调用"
        assert call["db_is_none"] is False, "db 不能为空"
        # 提供了 valid token 时 user_id 应等于 test_user['id']
        assert call["user_id"] == test_user["id"]
    finally:
        _uninstall_fake_service()


def test_graceful_degradation_when_service_missing(client, monkeypatch):
    """service 模块 import 失败时 register-local 依旧返回 SUCCESS，agent_looper_count=0。"""
    # 确保没有 fake 模块
    _uninstall_fake_service()
    # 让 import 抛 ImportError — 通过在 sys.modules 里塞一个会 raise 的 finder 太复杂，
    # 直接确保模块名不存在即可（真实环境下 T35 未上线就是这种）
    assert "app.services.agent_looper_discovery_service" not in sys.modules

    _patch_agent_discovery(monkeypatch)

    resp = client.post("/api/v1/resources/instances/register-local")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "SUCCESS"
    assert body["agent_looper_count"] == 0
    # graceful degradation 会带上 error 字段（不 fail 主流程）
    assert "agent_looper_error" in body


def test_graceful_degradation_when_service_raises(client, monkeypatch):
    """service.upsert_discovered() 抛异常时 register-local 依旧成功。"""
    _install_fake_service(upsert_raises=RuntimeError("boom"))
    _patch_agent_discovery(monkeypatch)
    try:
        resp = client.post("/api/v1/resources/instances/register-local")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == "SUCCESS"
        assert body["agent_looper_count"] == 0
        assert "agent_looper_error" in body
        assert "boom" in body["agent_looper_error"]
    finally:
        _uninstall_fake_service()


def test_register_local_is_idempotent(client, monkeypatch, db_session):
    """连续调用 2 次不会重复创建 instance 行。"""
    _install_fake_service()
    _patch_agent_discovery(monkeypatch)
    try:
        r1 = client.post("/api/v1/resources/instances/register-local")
        assert r1.status_code == 200, r1.text
        r2 = client.post("/api/v1/resources/instances/register-local")
        assert r2.status_code == 200, r2.text

        # 直接查 db 校验只有 1 条本地 instance
        import platform
        from app.db.models.instance_model import Instance
        hostname = platform.node()
        rows = db_session.query(Instance).filter(Instance.name == hostname).all()
        assert len(rows) == 1, f"期望 1 条 instance，实际 {len(rows)}"

        # 第二次响应的 message 应该指示 "已存在"
        b2 = r2.json()
        assert "已存在" in b2.get("message", "") or b2["agent_count"] == 0
        # 两次 payload 都应有 agent_looper_count 字段
        assert "agent_looper_count" in r1.json()
        assert "agent_looper_count" in r2.json()
    finally:
        _uninstall_fake_service()
