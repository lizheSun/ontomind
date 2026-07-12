from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.connectors.base import (
    CommandResult,
    CommandSpec,
    ConnectionReport,
    ConnectorSecurityError,
    HostKeyVerificationError,
    ManagedPath,
)
from app.connectors.local import LocalConnector
from app.connectors.ssh import SSHConnector, _FingerprintClient


@pytest.mark.asyncio
async def test_local_connector_runs_argv_and_limits_paths(tmp_path):
    connector = LocalConnector([str(tmp_path)], allowed_programs=frozenset({"uname"}))
    result = await connector.run(CommandSpec("uname", ("-s",), output_limit=64))
    assert result.exit_code == 0
    assert result.stdout.strip()

    managed = tmp_path / "sample.txt"
    managed.write_text("ok")
    assert await connector.read_file(ManagedPath(str(managed))) == b"ok"
    with pytest.raises(ConnectorSecurityError):
        await connector.read_file(ManagedPath("/etc/passwd"))


@pytest.mark.asyncio
async def test_command_spec_rejects_program_and_shell_syntax(tmp_path):
    connector = LocalConnector([str(tmp_path)], allowed_programs=frozenset({"uname"}))
    with pytest.raises(ConnectorSecurityError):
        await connector.run(CommandSpec("sh", ("-c", "id")))
    with pytest.raises(ConnectorSecurityError):
        await connector.run(CommandSpec("uname", ("-s; id",)))


def test_ssh_host_key_rejects_mismatch():
    class FakeKey:
        def get_algorithm(self):
            return "ssh-ed25519"

        def get_fingerprint(self, hash_alg):
            assert hash_alg == "sha256"
            return "SHA256:different"

    client = _FingerprintClient("ssh-ed25519", "SHA256:confirmed")
    assert client.validate_host_public_key("host", "127.0.0.1", 22, FakeKey()) is False
    with pytest.raises(HostKeyVerificationError):
        SSHConnector(
            host="host",
            port=22,
            username="user",
            host_key_algorithm="",
            host_key_fingerprint="",
            managed_roots=["/srv/opencode"],
        )


@pytest.mark.asyncio
async def test_ssh_connector_mock_uses_verified_connection(monkeypatch):
    events = {}

    @dataclass
    class FakeResult:
        exit_status: int = 0
        stdout: str = "Darwin\n"
        stderr: str = ""

    class FakeConn:
        async def run(self, command, **kwargs):
            events["command"] = command
            return FakeResult()

        def close(self):
            events["closed"] = True

        async def wait_closed(self):
            pass

    connector = SSHConnector(
        host="host",
        port=22,
        username="user",
        host_key_algorithm="ssh-ed25519",
        host_key_fingerprint="SHA256:confirmed",
        managed_roots=["/srv/opencode"],
        allowed_programs=frozenset({"uname"}),
    )

    async def fake_connect():
        return FakeConn()

    monkeypatch.setattr(connector, "_connect", fake_connect)
    result = await connector.run(CommandSpec("uname", ("-s",)))
    assert result.stdout == "Darwin\n"
    assert events["command"] == "uname -s"
    assert events["closed"] is True


class FakeDiscoveryConnector:
    async def test_connection(self):
        return ConnectionReport(True, "ok")

    async def run(self, command):
        if command.program == "which":
            return CommandResult(0, "/usr/local/bin/opencode\n", "")
        return CommandResult(0, "1.0.0\n", "")

    async def read_file(self, path):
        if path.value.endswith("opencode.json"):
            return b'{"mcp":{"demo":{"type":"stdio","command":["demo"]}}}'
        if path.value.endswith("SKILL.md"):
            return b"---\nname: demo-skill\ndescription: demo\n---\nBody"
        raise FileNotFoundError(path.value)

    async def list_files(self, root, pattern):
        return [f"{root.value}/skills/demo/SKILL.md"]


@pytest.mark.asyncio
async def test_discovery_preview_status_and_explicit_apply(db_session):
    from app.db.models.audit_log_model import AuditLog
    from app.db.models.compute_node_model import ComputeNode
    from app.db.models.mcp_model import MCP
    from app.db.models.node_connection_model import NodeConnection
    from app.services.agent_platform.discovery_service import DiscoveryService

    node = ComputeNode(name="test-node", status="online")
    db_session.add(node)
    db_session.flush()
    db_session.add(NodeConnection(
        node_id=node.id,
        connector_type="local",
        managed_roots=["/tmp/opencode"],
        enabled=True,
    ))
    db_session.commit()

    service = DiscoveryService(db_session)
    run = await service.start(node.id, user_id=None, connector=FakeDiscoveryConnector())
    assert run["status"] == "completed"
    assert run["summary"]["preview_only"] is True
    assert db_session.query(MCP).filter(MCP.name == "demo").first() is None

    mcp_item = next(item for item in service.items(run["id"]) if item["resource_type"] == "mcp")
    service.decide(run["id"], mcp_item["id"], "import", user_id=None)
    result = service.apply(run["id"], user_id=None)
    assert result["configuration_writes"] == 0
    assert result["preview_only"] is True
    assert db_session.query(MCP).filter(MCP.name == "demo").first() is None
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "discovery.apply.preview"
    ).one()
    assert audit.details["configuration_writes"] == 0


@pytest.mark.asyncio
async def test_discovery_failed_status(db_session):
    from app.db.models.compute_node_model import ComputeNode
    from app.db.models.node_connection_model import NodeConnection
    from app.services.agent_platform.discovery_service import DiscoveryService

    class RejectingConnector(FakeDiscoveryConnector):
        async def test_connection(self):
            return ConnectionReport(False, "host key rejected")

    node = ComputeNode(name="bad-node", status="offline")
    db_session.add(node)
    db_session.flush()
    db_session.add(NodeConnection(
        node_id=node.id,
        connector_type="local",
        managed_roots=["/tmp/opencode"],
        enabled=True,
    ))
    db_session.commit()

    run = await DiscoveryService(db_session).start(
        node.id, user_id=None, connector=RejectingConnector()
    )
    assert run["status"] == "failed"
    assert "host key rejected" in run["error_message"]


def test_node_api_create_list_and_connection_test(client, auth_headers, tmp_path):
    payload = {
        "name": "api-local-node",
        "platform": "darwin",
        "connection": {
            "connector_type": "local",
            "managed_roots": [str(tmp_path)],
        },
    }
    created = client.post(
        "/api/v1/agent-platform/nodes", json=payload, headers=auth_headers
    )
    assert created.status_code == 201, created.text
    node = created.json()["data"]
    assert node["connection"]["has_credential"] is False
    assert "encrypted_credential" not in created.text

    listed = client.get("/api/v1/agent-platform/nodes", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == node["id"] for item in listed.json()["data"])

    tested = client.post(
        f"/api/v1/agent-platform/nodes/{node['id']}/connection-tests",
        headers=auth_headers,
    )
    assert tested.status_code == 200
    assert tested.json()["data"]["ok"] is True


def test_ssh_credentials_are_referenced_and_host_key_confirmation_is_audited(
    client, auth_headers, test_user, db_session
):
    from app.db.models.audit_log_model import AuditLog
    from app.db.models.compute_node_model import ComputeNode
    from app.db.models.credential_model import Credential
    from app.db.models.node_connection_model import NodeConnection

    secret = "never-store-this-password"
    created = client.post(
        "/api/v1/agent-platform/nodes",
        headers=auth_headers,
        json={
            "name": "pending-ssh-node",
            "connection": {
                "connector_type": "ssh",
                "address": "node.example.test",
                "username": "operator",
                "password": secret,
                "managed_roots": ["/srv/opencode"],
            },
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()["data"]
    assert secret not in created.text
    assert "password" not in created.text
    assert "private_key" not in created.text
    assert "encrypted_credential" not in created.text
    assert body["created_by_user_id"] == test_user["id"]
    assert body["connection"]["host_key_status"] == "pending"
    assert body["connection"]["credential_id"] is not None

    connection = db_session.query(NodeConnection).filter(
        NodeConnection.node_id == body["id"]
    ).one()
    assert not hasattr(connection, "encrypted_credential")
    credential = db_session.query(Credential).filter(
        Credential.id == connection.credential_id
    ).one()
    assert secret not in credential.encrypted_payload
    assert db_session.get(ComputeNode, body["id"]).created_by_user_id == test_user["id"]

    pending_test = client.post(
        f"/api/v1/agent-platform/nodes/{body['id']}/connection-tests",
        headers=auth_headers,
    )
    assert pending_test.status_code == 422

    confirmed = client.post(
        f"/api/v1/agent-platform/nodes/{body['id']}/host-key-confirmations",
        headers=auth_headers,
        json={
            "host_key_algorithm": "ssh-ed25519",
            "host_key_fingerprint": "SHA256:confirmed-key",
            "reason": "verified out of band",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    connection_data = confirmed.json()["data"]["connection"]
    assert connection_data["host_key_status"] == "confirmed"
    assert connection_data["host_key_confirmed_at"]
    actions = {
        row.action
        for row in db_session.query(AuditLog)
        .filter(AuditLog.resource_id == str(body["id"]))
        .all()
    }
    assert {"node.create", "node.host_key.confirm"} <= actions


def test_node_migration_is_single_linear_head():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend_root = Path(__file__).resolve().parents[2]
    config = Config()
    config.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["2026071204"]
    revision = script.get_revision("2026071204")
    assert revision.down_revision == "2026071203"
