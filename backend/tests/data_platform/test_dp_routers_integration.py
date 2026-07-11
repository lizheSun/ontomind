"""Router-level integration tests for /api/v1/data-platform/*.

Uses `client` (TestClient with in-memory sqlite via `get_db` override) +
`test_user` from the root conftest. Covers CRUD, ACL, SQL-guard integration,
saved-queries / history lifecycle, chat with mocked LLM, and SSE streaming.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import create_engine, text


API = "/api/v1/data-platform"


# ----------------------------- helpers --------------------------------
def _sqlite_payload(name: str, path: str) -> dict[str, Any]:
    return {
        "name": name,
        "source_type": "sqlite",
        "dialect": "sqlite",
        "database": path,
        "charset": "utf8mb4",
        "read_only_flag": True,
    }


def _mysql_payload(name: str, password: str = "s3cret") -> dict[str, Any]:
    return {
        "name": name,
        "source_type": "mysql",
        "dialect": "mysql",
        "host": "localhost",
        "port": 3306,
        "username": "u",
        "password": password,
        "database": "testdb",
        "charset": "utf8mb4",
        "read_only_flag": True,
    }


def _seed_sqlite_users(path: str, count: int = 3) -> None:
    eng = create_engine(f"sqlite:///{path}", future=True)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        for i in range(count):
            c.execute(text(f"INSERT INTO users VALUES ({i}, 'u{i}')"))
    eng.dispose()


# ----------------------------- sources CRUD ---------------------------
def test_create_source_returns_201_and_has_password_flag(client, auth_headers):
    r = client.post(f"{API}/sources", json=_mysql_payload("ds-a"), headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "SUCCESS"
    data = body["data"]
    assert data["has_password"] is True
    assert "password" not in data
    assert "password_enc" not in data


def test_list_sources_scoped_to_owner(client, auth_headers, auth_headers2):
    r = client.post(f"{API}/sources", json=_mysql_payload("only-mine"), headers=auth_headers)
    assert r.status_code == 201

    r1 = client.get(f"{API}/sources", headers=auth_headers)
    assert r1.status_code == 200
    assert r1.json()["total"] == 1

    r2 = client.get(f"{API}/sources", headers=auth_headers2)
    assert r2.status_code == 200
    assert r2.json()["total"] == 0


def test_get_source_by_id_returns_404_when_missing(client, auth_headers):
    r = client.get(f"{API}/sources/9999", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["code"] == "DP_DS_NOT_FOUND"


def test_update_source_preserves_password_when_empty(client, auth_headers):
    created = client.post(
        f"{API}/sources", json=_mysql_payload("ds-upd", password="orig"), headers=auth_headers
    ).json()["data"]
    sid = created["id"]
    # empty password → keep original
    r = client.put(
        f"{API}/sources/{sid}",
        json={"description": "changed", "password": ""},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["has_password"] is True
    assert r.json()["data"]["description"] == "changed"


def test_delete_source_cascades_removes_from_list(client, auth_headers):
    sid = client.post(
        f"{API}/sources", json=_mysql_payload("ds-del"), headers=auth_headers
    ).json()["data"]["id"]
    r = client.delete(f"{API}/sources/{sid}", headers=auth_headers)
    assert r.status_code == 200
    listing = client.get(f"{API}/sources", headers=auth_headers).json()
    assert all(s["id"] != sid for s in listing["data"])


def test_test_connection_returns_ok_true_for_sqlite(client, auth_headers, tmp_path):
    path = str(tmp_path / "probe.sqlite")
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-probe", path), headers=auth_headers
    ).json()["data"]["id"]
    r = client.post(f"{API}/sources/{sid}/test", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["ok"] is True
    assert data["elapsed_ms"] >= 0


def test_describe_schema_returns_databases_tables_columns(
    client, auth_headers, tmp_path
):
    path = str(tmp_path / "schema.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-schema", path), headers=auth_headers
    ).json()["data"]["id"]
    r = client.get(f"{API}/sources/{sid}/schema", headers=auth_headers)
    assert r.status_code == 200
    schema = r.json()["data"]
    assert "databases" in schema and schema["databases"]
    tables = schema["databases"][0]["tables"]
    assert any(t["name"] == "users" for t in tables)


# ----------------------------- execute --------------------------------
def test_execute_sync_rejects_drop_table_with_sql_guard_code(
    client, auth_headers, tmp_path
):
    path = str(tmp_path / "guard.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-guard", path), headers=auth_headers
    ).json()["data"]["id"]
    r = client.post(
        f"{API}/sources/{sid}/execute",
        json={"sql": "DROP TABLE users", "max_rows": 100},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert r.json()["code"].startswith("SQL_GUARD_")


def test_execute_sync_happy_path_returns_rows(client, auth_headers, tmp_path):
    path = str(tmp_path / "exec.sqlite")
    _seed_sqlite_users(path, count=3)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-exec", path), headers=auth_headers
    ).json()["data"]["id"]
    r = client.post(
        f"{API}/sources/{sid}/execute",
        json={"sql": "SELECT id, name FROM users", "max_rows": 100},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["row_count"] == 3
    assert [c["name"] for c in data["columns"]] == ["id", "name"]


def test_stream_execute_emits_columns_and_rows(client, auth_headers, tmp_path):
    path = str(tmp_path / "stream.sqlite")
    _seed_sqlite_users(path, count=3)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-stream", path), headers=auth_headers
    ).json()["data"]["id"]

    with client.stream(
        "GET",
        f"{API}/sources/{sid}/execute/stream",
        params={"sql": "SELECT id, name FROM users", "max_rows": 1000},
        headers=auth_headers,
    ) as r:
        body = r.read().decode()
    assert "event: columns" in body
    assert "event: rows" in body
    assert "event: done" in body


# --------------------------- saved queries ----------------------------
def test_saved_query_crud_cycle(client, auth_headers, tmp_path):
    path = str(tmp_path / "saved.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-saved", path), headers=auth_headers
    ).json()["data"]["id"]

    created = client.post(
        f"{API}/saved-queries",
        json={
            "name": "top",
            "source_id": sid,
            "sql_text": "SELECT * FROM users LIMIT 10",
            "is_favorite": False,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    qid = created.json()["data"]["id"]

    listed = client.get(f"{API}/saved-queries", headers=auth_headers).json()
    assert listed["total"] == 1

    upd = client.put(
        f"{API}/saved-queries/{qid}", json={"is_favorite": True}, headers=auth_headers
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["is_favorite"] is True

    dele = client.delete(f"{API}/saved-queries/{qid}", headers=auth_headers)
    assert dele.status_code == 200

    listed2 = client.get(f"{API}/saved-queries", headers=auth_headers).json()
    assert listed2["total"] == 0


# ------------------------------ history -------------------------------
def test_history_lists_after_execute(client, auth_headers, tmp_path):
    path = str(tmp_path / "hist.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-hist", path), headers=auth_headers
    ).json()["data"]["id"]
    client.post(
        f"{API}/sources/{sid}/execute",
        json={"sql": "SELECT id FROM users", "max_rows": 10},
        headers=auth_headers,
    )
    r = client.get(f"{API}/history", headers=auth_headers)
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) >= 1
    assert any(h["status"] == "success" for h in rows)


# -------------------------------- chat --------------------------------
def _install_llm_mock(monkeypatch, reply_text: str) -> None:
    """Patch LLMConfigService.chat_completion — used as the default llm_service
    when DpChatService is constructed without an explicit llm_service."""
    from app.services import llm_config_service as _m

    async def _fake(self, *args, **kwargs):  # noqa: ANN001
        return {"content": reply_text}

    monkeypatch.setattr(_m.LLMConfigService, "chat_completion", _fake)


def test_chat_session_create_and_send_message_with_mocked_llm(
    client, auth_headers, tmp_path, monkeypatch
):
    path = str(tmp_path / "chat.sqlite")
    _seed_sqlite_users(path, count=2)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-chat", path), headers=auth_headers
    ).json()["data"]["id"]

    _install_llm_mock(monkeypatch, "```sql\nSELECT id, name FROM users LIMIT 10\n```")

    sess = client.post(
        f"{API}/chat/sessions",
        json={"name": "s1", "source_id": sid, "model_config_id": None},
        headers=auth_headers,
    )
    assert sess.status_code == 201, sess.text
    session_id = sess.json()["data"]["id"]

    msg = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "show users"},
        headers=auth_headers,
    )
    assert msg.status_code == 201, msg.text
    data = msg.json()["data"]
    assert data["role"] == "assistant"
    assert data["generated_sql"] and "SELECT id, name FROM users" in data["generated_sql"]
    assert data["executed"] is False


def test_chat_apply_message_runs_guarded_sql(
    client, auth_headers, tmp_path, monkeypatch
):
    path = str(tmp_path / "apply.sqlite")
    _seed_sqlite_users(path, count=2)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-apply", path), headers=auth_headers
    ).json()["data"]["id"]
    _install_llm_mock(monkeypatch, "```sql\nSELECT id, name FROM users\n```")

    session_id = client.post(
        f"{API}/chat/sessions",
        json={"name": "s2", "source_id": sid, "model_config_id": None},
        headers=auth_headers,
    ).json()["data"]["id"]
    msg_id = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "list users"},
        headers=auth_headers,
    ).json()["data"]["id"]

    r = client.post(
        f"{API}/chat/sessions/{session_id}/apply/{msg_id}",
        params={"max_rows": 10},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    payload = r.json()["data"]
    assert payload["row_count"] == 2


def test_chat_session_list_get_delete(
    client, auth_headers, tmp_path, monkeypatch
):
    """Exercise list/get/delete/list_messages branches in chat router."""
    path = str(tmp_path / "chatx.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-chatx", path), headers=auth_headers
    ).json()["data"]["id"]
    _install_llm_mock(monkeypatch, "```sql\nSELECT 1\n```")

    session_id = client.post(
        f"{API}/chat/sessions",
        json={"name": "sx", "source_id": sid, "model_config_id": None},
        headers=auth_headers,
    ).json()["data"]["id"]

    listed = client.get(f"{API}/chat/sessions", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    got = client.get(f"{API}/chat/sessions/{session_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == session_id

    # send a message so list_messages has something
    client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "hello"},
        headers=auth_headers,
    )
    msgs = client.get(
        f"{API}/chat/sessions/{session_id}/messages", headers=auth_headers
    )
    assert msgs.status_code == 200
    assert msgs.json()["total"] >= 2  # user + assistant

    dele = client.delete(f"{API}/chat/sessions/{session_id}", headers=auth_headers)
    assert dele.status_code == 200


def test_chat_apply_rejects_llm_generated_drop(
    client, auth_headers, tmp_path, monkeypatch
):
    path = str(tmp_path / "drop.sqlite")
    _seed_sqlite_users(path)
    sid = client.post(
        f"{API}/sources", json=_sqlite_payload("ds-drop", path), headers=auth_headers
    ).json()["data"]["id"]
    _install_llm_mock(monkeypatch, "```sql\nDROP TABLE users\n```")

    session_id = client.post(
        f"{API}/chat/sessions",
        json={"name": "s-drop", "source_id": sid, "model_config_id": None},
        headers=auth_headers,
    ).json()["data"]["id"]
    msg_id = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "nuke it"},
        headers=auth_headers,
    ).json()["data"]["id"]

    r = client.post(
        f"{API}/chat/sessions/{session_id}/apply/{msg_id}", headers=auth_headers
    )
    assert r.status_code == 400
    assert r.json()["code"].startswith("SQL_GUARD_")
