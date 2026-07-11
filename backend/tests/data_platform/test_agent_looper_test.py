"""T36 tests: agent-looper SSE test endpoint + test_run persistence + TTL purge script.

- SSE stream yields multiple `text` events + one `done` event on success.
- error path: LLM 抛异常 → `error` event + test_run.status=='error'.
- Every test call persists one AgentLooperTestRun row with correct status.
- purge script deletes rows older than TTL cutoff.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun
from app.db.models.agent_looper_version_model import AgentLooperVersion
from app.db.models.user_model import User


_LLM_PATCH = "app.services.llm_config_service.LLMConfigService.chat_completion"


# ---------- helpers ----------

def _seed_user(session, username: str = "t36") -> User:
    u = User(
        username=username,
        email=f"{username}@e.f",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def _seed_agent(session, *, owner_id: int, system_prompt: str = "你是 SQL 专家", temperature: float = 0.5):
    """Create a config + version and wire current_version_id."""
    config_json = {
        "system_prompt": system_prompt,
        "model": "gpt-4o-mini",
        "temperature": temperature,
        "guardrails": {"max_tokens": 512},
    }
    cfg = AgentLooperConfig(
        name="test-agent",
        type="custom_looper",
        description="d",
        owner_user_id=owner_id,
        is_active=True,
        is_published=False,
        active_config_json=json.dumps(config_json, ensure_ascii=False),
    )
    session.add(cfg)
    session.flush()
    ver = AgentLooperVersion(
        config_id=cfg.id,
        version_number=1,
        config_json=json.dumps(config_json, ensure_ascii=False),
        prompt_snapshot=system_prompt,
        created_by_user_id=owner_id,
    )
    session.add(ver)
    session.flush()
    cfg.current_version_id = ver.id
    session.commit()
    session.refresh(cfg)
    return cfg, ver


def _parse_sse(body: str):
    """Parse SSE frames (support both \r\n and \n line endings)."""
    body = body.replace("\r\n", "\n")
    events: list[tuple[str, str]] = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        evt = None
        data_lines = []
        for line in chunk.split("\n"):
            if line.startswith("event:"):
                evt = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())
        if evt is not None:
            events.append((evt, "\n".join(data_lines)))
    return events



@pytest.fixture(autouse=True)
def _reset_sse_app_status():
    """sse_starlette 会把 should_exit_event 绑到 asyncio loop；测试间需要重置，
    避免第二次 TestClient 复用到已废弃的 loop 上抛 RuntimeError。"""
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    yield
    AppStatus.should_exit_event = None

# ---------- SSE happy path ----------

def test_sse_happy_yields_text_and_done(isolated_engine, db_session, override_db):
    """成功路径：SSE 至少产出一次 text 事件 + 一次 done 事件，test_run 状态=success。"""
    from app.main import app

    override_db(app)

    user = _seed_user(db_session, "sse_ok")
    cfg, ver = _seed_agent(db_session, owner_id=user.id)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_chat(self, messages, **kw):  # noqa: ANN001
        return {"content": "Hello agent world", "model": "gpt-4o-mini"}

    with patch(_LLM_PATCH, new=fake_chat):
        with TestClient(app) as client:
            with client.stream(
                "POST",
                f"/api/v1/agent-looper/configs/{cfg.id}/test",
                json={"prompt": "你好"},
                headers=headers,
            ) as resp:
                assert resp.status_code == 200
                body = resp.read().decode()
    events = _parse_sse(body)
    kinds = [e for e, _ in events]
    assert "text" in kinds
    assert "done" in kinds
    # Reconstruct text
    text_content = "".join(d for e, d in events if e == "text")
    assert "Hello" in text_content and "agent" in text_content and "world" in text_content
    # done payload has latency_ms + model + run_id
    done_data = next(d for e, d in events if e == "done")
    payload = json.loads(done_data)
    assert "latency_ms" in payload and "model" in payload and "run_id" in payload

    # DB assertion: exactly one row, status=success
    SessionLocal = sessionmaker(bind=isolated_engine, autoflush=False, future=True)
    with SessionLocal() as s:
        rows = s.query(AgentLooperTestRun).all()
        assert len(rows) == 1
        r = rows[0]
        assert r.status == "success"
        assert r.config_id == cfg.id
        assert r.version_id == ver.id
        assert r.prompt == "你好"
        assert r.response == "Hello agent world"
        assert r.latency_ms is not None
        assert r.user_id == user.id

    app.dependency_overrides.clear()


# ---------- SSE error path ----------

def test_sse_error_yields_error_event_and_marks_run(isolated_engine, db_session, override_db):
    """错误路径：LLM 抛异常 → SSE 一条 error 事件；test_run.status='error'。"""
    from app.main import app

    override_db(app)

    user = _seed_user(db_session, "sse_err")
    cfg, ver = _seed_agent(db_session, owner_id=user.id)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async def boom(self, messages, **kw):  # noqa: ANN001
        raise RuntimeError("upstream 503")

    with patch(_LLM_PATCH, new=boom):
        with TestClient(app) as client:
            with client.stream(
                "POST",
                f"/api/v1/agent-looper/configs/{cfg.id}/test",
                json={"prompt": "trigger boom"},
                headers=headers,
            ) as resp:
                assert resp.status_code == 200
                body = resp.read().decode()
    events = _parse_sse(body)
    kinds = [e for e, _ in events]
    assert "error" in kinds
    assert "done" not in kinds
    err_msg = next(d for e, d in events if e == "error")
    assert "upstream 503" in err_msg

    SessionLocal = sessionmaker(bind=isolated_engine, autoflush=False, future=True)
    with SessionLocal() as s:
        rows = s.query(AgentLooperTestRun).all()
        assert len(rows) == 1
        r = rows[0]
        assert r.status == "error"
        assert r.error and "upstream 503" in r.error

    app.dependency_overrides.clear()


# ---------- list history endpoint ----------

def test_list_test_runs_returns_history(isolated_engine, db_session, override_db):
    """POST /test-runs/{config_id} 返回该 Agent 的历史记录。"""
    from app.main import app

    override_db(app)

    user = _seed_user(db_session, "hist_user")
    cfg, ver = _seed_agent(db_session, owner_id=user.id)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_chat(self, messages, **kw):  # noqa: ANN001
        return {"content": "Ok", "model": "m"}

    with patch(_LLM_PATCH, new=fake_chat):
        with TestClient(app) as client:
            # 触发两次测试
            for i in range(2):
                with client.stream(
                    "POST",
                    f"/api/v1/agent-looper/configs/{cfg.id}/test",
                    json={"prompt": f"prompt {i}"},
                    headers=headers,
                ) as r:
                    assert r.status_code == 200
                    _ = r.read()
            # 列表
            resp = client.post(
                f"/api/v1/agent-looper/test-runs/{cfg.id}",
                headers=headers,
            )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    for row in data:
        assert row["config_id"] == cfg.id
        assert row["status"] == "success"

    app.dependency_overrides.clear()


# ---------- purge script ----------

def test_purge_test_runs_removes_old_rows(db_session):
    """TTL purge 删除 created_at < cutoff 的记录。"""
    from app.scripts.purge_test_runs import purge_old_test_runs

    user = _seed_user(db_session, "purge_user")
    cfg, ver = _seed_agent(db_session, owner_id=user.id)

    old = AgentLooperTestRun(
        config_id=cfg.id, version_id=ver.id, prompt="p_old",
        status="success", user_id=user.id,
    )
    fresh = AgentLooperTestRun(
        config_id=cfg.id, version_id=ver.id, prompt="p_new",
        status="success", user_id=user.id,
    )
    db_session.add_all([old, fresh])
    db_session.commit()
    # Force `old.created_at` to 60 days ago
    db_session.query(AgentLooperTestRun).filter(
        AgentLooperTestRun.id == old.id,
    ).update({"created_at": datetime.utcnow() - timedelta(days=60)})
    db_session.commit()

    deleted = purge_old_test_runs(db_session, days=30, dry_run=False)
    assert deleted == 1

    remaining = db_session.query(AgentLooperTestRun).all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh.id


def test_purge_test_runs_dry_run_counts_but_does_not_delete(db_session):
    from app.scripts.purge_test_runs import purge_old_test_runs

    user = _seed_user(db_session, "purge_dry_user")
    cfg, ver = _seed_agent(db_session, owner_id=user.id)

    old = AgentLooperTestRun(
        config_id=cfg.id, version_id=ver.id, prompt="p_old",
        status="success", user_id=user.id,
    )
    db_session.add(old)
    db_session.commit()
    db_session.query(AgentLooperTestRun).filter(
        AgentLooperTestRun.id == old.id,
    ).update({"created_at": datetime.utcnow() - timedelta(days=90)})
    db_session.commit()

    n = purge_old_test_runs(db_session, days=30, dry_run=True)
    assert n == 1
    # not deleted
    assert db_session.query(AgentLooperTestRun).count() == 1


# ---------- parse_config integration (agent's system_prompt wins) ----------

@pytest.mark.asyncio
async def test_parse_config_uses_agent_system_prompt_when_id_given(db_session):
    """当传 agent_looper_config_id 时，parse_config 使用 Agent 的 system_prompt。"""
    from app.services.dp_data_source_service import DpDataSourceService

    user = _seed_user(db_session, "parse_agent_user")
    custom_prompt = "SPECIAL AGENT PROMPT - return {\"name\":\"agent-driven\",\"dialect\":\"mysql\",\"host\":\"h\",\"database\":\"d\",\"port\":3306}"
    cfg, _ver = _seed_agent(db_session, owner_id=user.id, system_prompt=custom_prompt)

    captured: dict = {}

    async def spy(self, messages, **kw):
        captured["messages"] = messages
        return {
            "content": '{"name":"agent-driven","dialect":"mysql","host":"h","database":"d","port":3306}',
            "model": "m",
        }

    svc = DpDataSourceService(db_session)
    with patch(_LLM_PATCH, new=spy):
        result = await svc.parse_config(
            "raw", agent_looper_config_id=cfg.id, user_id=user.id,
        )
    assert result.parsed["name"] == "agent-driven"
    # System prompt should be the agent's
    assert any(m["role"] == "system" and custom_prompt in m["content"] for m in captured["messages"])


@pytest.mark.asyncio
async def test_parse_config_default_prompt_when_no_agent_id(db_session):
    """不传 agent_looper_config_id 时保持原行为（使用默认 _PARSE_CONFIG_PROMPT）。"""
    from app.services.dp_data_source_service import _PARSE_CONFIG_PROMPT, DpDataSourceService

    captured: dict = {}

    async def spy(self, messages, **kw):
        captured["messages"] = messages
        return {
            "content": '{"name":"default","dialect":"mysql","host":"h","database":"d","port":3306}',
            "model": "m",
        }

    svc = DpDataSourceService(db_session)
    with patch(_LLM_PATCH, new=spy):
        result = await svc.parse_config("raw")
    assert result.parsed["name"] == "default"
    assert any(m["role"] == "system" and m["content"] == _PARSE_CONFIG_PROMPT for m in captured["messages"])


# ---------- chat send_message integration (agent wins over model_config_id) ----------

@pytest.mark.asyncio
async def test_send_message_uses_agent_system_prompt(db_session):
    """当 session.agent_looper_config_id 设置时，send_message 使用 Agent 的 system_prompt。"""
    from app.db.models.dp_data_source_model import DpDataSource
    from app.db.models.dp_chat_session_model import DpChatSession
    from app.services.dp_chat_service import DpChatService

    user = _seed_user(db_session, "chat_agent_user")
    ds = DpDataSource(
        name="ds1", source_type="sqlite", dialect="sqlite",
        database=":memory:", charset="utf8mb4",
        owner_user_id=user.id, created_by_user_id=user.id,
        status="active", read_only_flag=True,
    )
    db_session.add(ds)
    db_session.commit()

    agent_prompt = "AGENT-CUSTOM-PROMPT: Only return SELECT 1"
    cfg, _ver = _seed_agent(db_session, owner_id=user.id, system_prompt=agent_prompt)

    sess = DpChatSession(
        name="s1", source_id=ds.id, user_id=user.id,
        agent_looper_config_id=cfg.id,
    )
    db_session.add(sess)
    db_session.commit()

    captured: dict = {}

    async def spy_chat(self, messages, **kw):
        captured["messages"] = messages
        return {"content": "```sql\nSELECT 1\n```", "model": "m"}

    svc = DpChatService(db_session)
    with patch(_LLM_PATCH, new=spy_chat):
        msg = await svc.send_message(
            session_id=sess.id, content="give me one row", user_id=user.id,
        )
    assert msg.role == "assistant"
    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert system_msg["content"] == agent_prompt


@pytest.mark.asyncio
async def test_send_message_default_prompt_when_no_agent(db_session):
    """没有 agent_looper_config_id 时保持默认 SQL 系统 prompt。"""
    from app.db.models.dp_data_source_model import DpDataSource
    from app.db.models.dp_chat_session_model import DpChatSession
    from app.services.dp_chat_service import DpChatService

    user = _seed_user(db_session, "chat_default_user")
    ds = DpDataSource(
        name="ds2", source_type="sqlite", dialect="sqlite",
        database=":memory:", charset="utf8mb4",
        owner_user_id=user.id, created_by_user_id=user.id,
        status="active", read_only_flag=True,
    )
    db_session.add(ds)
    db_session.commit()

    sess = DpChatSession(name="s2", source_id=ds.id, user_id=user.id)
    db_session.add(sess)
    db_session.commit()

    captured: dict = {}

    async def spy_chat(self, messages, **kw):
        captured["messages"] = messages
        return {"content": "```sql\nSELECT 1\n```", "model": "m"}

    svc = DpChatService(db_session)
    with patch(_LLM_PATCH, new=spy_chat):
        await svc.send_message(session_id=sess.id, content="q", user_id=user.id)
    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "SELECT" in system_msg["content"] and "SQLite" in system_msg["content"]
