"""统一会话 API：CRUD + SSE（假插件，不启 CLI）。"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.harness.protocol import PluginInfo, RunRequest, StreamEvent
from app.harness.registry import PluginRegistry, set_registry


class FakePlugin:
    def __init__(self, plugin_id: str, label: str) -> None:
        self.id = plugin_id
        self.label = label

    def probe(self) -> PluginInfo:
        return PluginInfo(id=self.id, label=self.label, available=True, detail="fake")

    async def stream(self, req: RunRequest) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(kind="thinking", text="ok", delta=False)
        yield StreamEvent(kind="text", text=f"echo:{req.prompt}", delta=False)
        yield StreamEvent(kind="meta", delta=False, meta={"plugin_session_id": f"sid-{req.session_key}"})


@pytest.fixture
def fake_plugins():
    reg = PluginRegistry()
    reg.register(FakePlugin("opencode", "OpenCode"))
    reg.register(FakePlugin("dsh", "DeepSeek Harness"))
    set_registry(reg)
    yield
    set_registry(None)


def test_plugin_list_and_session_crud(client, fake_plugins):
    r = client.get("/api/v1/harness/plugins")
    assert r.status_code == 200, r.text
    ids = {p["id"] for p in r.json()}
    assert ids == {"opencode", "dsh"}
    assert all(p["available"] for p in r.json())

    r = client.post("/api/v1/harness/sessions", json={"plugin_id": "dsh"})
    assert r.status_code == 200, r.text
    sess = r.json()
    assert sess["plugin_id"] == "dsh"
    assert sess["title"] == "新会话"
    sid = sess["id"]

    r = client.patch(f"/api/v1/harness/sessions/{sid}", json={"title": "排查登录"})
    assert r.status_code == 200
    assert r.json()["title"] == "排查登录"

    r = client.get("/api/v1/harness/sessions")
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = client.delete(f"/api/v1/harness/sessions/{sid}")
    assert r.status_code == 200
    r = client.get(f"/api/v1/harness/sessions/{sid}")
    assert r.status_code == 404


def test_send_message_sse(client, fake_plugins):
    r = client.post("/api/v1/harness/sessions", json={"plugin_id": "opencode"})
    sid = r.json()["id"]
    r = client.post(f"/api/v1/harness/sessions/{sid}/messages", json={"content": "你好"})
    assert r.status_code == 200, r.text
    body = r.text
    assert "event: chunk" in body
    assert "echo:你好" in body
    assert "event: done" in body

    r = client.get(f"/api/v1/harness/sessions/{sid}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    kinds = [p["kind"] for p in msgs[1]["parts"]]
    assert "thinking" in kinds and "text" in kinds

    r = client.get(f"/api/v1/harness/sessions/{sid}")
    assert r.json()["title"] == "你好"
    assert r.json()["plugin_session_id"] == f"sid-om-{sid}"


def test_unknown_session_404(client, fake_plugins):
    r = client.get("/api/v1/harness/sessions/99999")
    assert r.status_code == 404


def test_workspace_upload_and_attachments(client, fake_plugins, tmp_path):
    r = client.post("/api/v1/harness/sessions", json={"plugin_id": "opencode"})
    sid = r.json()["id"]

    r = client.get("/api/v1/harness/workspaces")
    assert r.status_code == 200
    assert r.json()["home"]

    ws = tmp_path / "proj"
    ws.mkdir()
    r = client.patch(f"/api/v1/harness/sessions/{sid}", json={"workspace_path": str(ws)})
    assert r.status_code == 200
    assert r.json()["workspace_path"] == str(ws.resolve())

    r = client.post(
        f"/api/v1/harness/sessions/{sid}/files",
        files=[("files", ("笔记.txt", b"hello", "text/plain"))],
    )
    assert r.status_code == 200, r.text
    uploaded = r.json()
    assert uploaded[0]["rel"] == "inbox/笔记.txt"
    assert (ws / "inbox" / "笔记.txt").read_bytes() == b"hello"

    r = client.post(
        f"/api/v1/harness/sessions/{sid}/messages",
        json={"content": "看看这个文件", "attachments": ["inbox/笔记.txt"]},
    )
    assert r.status_code == 200
    assert "inbox/笔记.txt" in r.text
    msgs = client.get(f"/api/v1/harness/sessions/{sid}/messages").json()
    kinds = [p["kind"] for p in msgs[0]["parts"]]
    assert "text" in kinds and "file" in kinds


def test_optimize_prompt(client, fake_plugins, monkeypatch):
    class FakeLLM:
        def chat(self, messages, **kwargs):
            return "请用三步排查登录失败，并给出验证方法。"

    monkeypatch.setattr(
        "app.services.harness_service.resolve_llm_client",
        lambda db=None: FakeLLM(),
    )
    r = client.post("/api/v1/harness/prompt/optimize", json={"text": "登录挂了", "plugin_id": "dsh"})
    assert r.status_code == 200, r.text
    assert "三步" in r.json()["text"]
