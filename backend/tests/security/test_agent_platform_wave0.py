"""Agent platform Wave 0 security baseline tests."""
from __future__ import annotations

import re
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from starlette.websockets import WebSocketDisconnect


def _concrete_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def test_all_resource_http_endpoints_require_jwt(anon_client):
    from app.main import app

    checked = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if not path.startswith("/api/v1/resources") or not methods:
            continue
        for method in methods - {"HEAD", "OPTIONS"}:
            kwargs = {"json": {}} if method in {"POST", "PUT", "PATCH"} else {}
            response = anon_client.request(
                method, _concrete_path(path), follow_redirects=False, **kwargs
            )
            assert response.status_code == 401, (
                f"{method} {path} should reject anonymous access, "
                f"got {response.status_code}: {response.text[:200]}"
            )
            checked += 1
    assert checked >= 30


def test_credential_response_is_masked_and_audited(
    client, auth_headers, db_session
):
    secret = "wave0-super-secret-value"
    response = client.post(
        "/api/v1/resources/credentials",
        headers=auth_headers,
        json={
            "name": "wave0-openai",
            "credential_type": "api_key",
            "payload": {"api_key": secret, "tenant": "acme"},
            "description": "security baseline test",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["payload"] == {"api_key": "********", "tenant": "********"}
    assert secret not in response.text
    assert "encrypted_payload" not in response.text

    from app.core.crypto import decrypt
    from app.db.models.audit_log_model import AuditLog
    from app.db.models.credential_model import Credential

    row = db_session.query(Credential).filter_by(id=body["id"]).one()
    assert secret not in row.encrypted_payload
    assert secret in decrypt(row.encrypted_payload)

    audit = (
        db_session.query(AuditLog)
        .filter_by(action="credential.create", resource_id=str(row.id))
        .one()
    )
    assert audit.actor_user_id == body["owner_user_id"]
    assert secret not in str(audit.details)

    listed = client.get("/api/v1/resources/credentials", headers=auth_headers)
    assert listed.status_code == 200
    assert secret not in listed.text
    assert "encrypted_payload" not in listed.text


def test_non_admin_cannot_manage_credentials(client, auth_headers2):
    response = client.get(
        "/api/v1/resources/credentials", headers=auth_headers2
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_resource_websocket_requires_valid_query_token(client, test_user):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/resources/agents/999/chat/stream"):
            pass
    assert exc_info.value.code == 1008

    with client.websocket_connect(
        f"/api/v1/resources/agents/999/chat/stream?token={test_user['token']}"
    ):
        pass


def test_production_rejects_default_or_missing_keys():
    from app.core.config import DEFAULT_SECRET_KEY, validate_production_security

    config = SimpleNamespace(
        ENVIRONMENT="production",
        SECRET_KEY=DEFAULT_SECRET_KEY,
        FERNET_KEY=None,
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY.*FERNET_KEY"):
        validate_production_security(config)

    valid = SimpleNamespace(
        ENVIRONMENT="production",
        SECRET_KEY="a-production-secret-that-is-not-the-default",
        FERNET_KEY=Fernet.generate_key().decode("ascii"),
    )
    validate_production_security(valid)
