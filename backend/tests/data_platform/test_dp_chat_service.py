"""dp_chat_service TDD: mocked LLM + guard integration + owner ACL."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine, text

from app.core.exceptions import BusinessException
from app.schemas.dp_chat_schema import SessionCreate
from app.schemas.dp_data_source_schema import DpDataSourceCreate
from app.services.dp_chat_service import (
    DpChatService,
    _extract_assistant_text,
    _extract_sql_fence,
)
from app.services.dp_data_source_service import DpDataSourceService


@pytest.fixture
def source_id(db, user_id, tmp_path):
    sqlite_path = str(tmp_path / "chat.sqlite")
    eng = create_engine(f"sqlite:///{sqlite_path}", future=True)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        c.execute(text("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')"))
    eng.dispose()

    svc = DpDataSourceService(db)
    ds = svc.create(
        DpDataSourceCreate(
            name="chat-src", source_type="sqlite", dialect="sqlite",
            database=sqlite_path, charset="utf8mb4", read_only_flag=True,
        ),
        user_id=user_id,
    )
    return ds.id


def _make_service(db, llm_reply: str) -> DpChatService:
    llm = MagicMock()
    llm.chat_completion = AsyncMock(return_value={"content": llm_reply})
    return DpChatService(db, llm_service=llm)


# ---- helper tests --------------------------------------------------

def test_extract_sql_fence_variants():
    assert _extract_sql_fence("```sql\nSELECT 1\n```") == "SELECT 1"
    assert _extract_sql_fence("```\nSELECT 2\n```") == "SELECT 2"
    assert _extract_sql_fence("SELECT 3") == "SELECT 3"
    assert _extract_sql_fence("blah blah") is None
    assert _extract_sql_fence("") is None


def test_extract_assistant_text_openai_and_normalized():
    assert _extract_assistant_text({"choices": [{"message": {"content": "hi"}}]}) == "hi"
    assert _extract_assistant_text({"content": "normalized"}) == "normalized"
    assert _extract_assistant_text("plain") == "plain"


# ---- service tests -------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_parses_fenced_sql(db, user_id, source_id):
    llm_reply = "```sql\nSELECT id, name FROM users LIMIT 10\n```"
    svc = _make_service(db, llm_reply)
    session = svc.create_session(
        SessionCreate(name="s1", source_id=source_id, model_config_id=None),
        user_id=user_id,
    )
    msg = await svc.send_message(session_id=session.id, content="show users", user_id=user_id)
    assert msg.role == "assistant"
    assert msg.generated_sql
    assert "SELECT id, name FROM users LIMIT 10" in msg.generated_sql
    assert msg.executed is False


@pytest.mark.asyncio
async def test_apply_message_runs_guarded_sql(db, user_id, source_id):
    llm_reply = "```sql\nSELECT id, name FROM users\n```"
    svc = _make_service(db, llm_reply)
    session = svc.create_session(
        SessionCreate(name="s2", source_id=source_id, model_config_id=None),
        user_id=user_id,
    )
    msg = await svc.send_message(session_id=session.id, content="users", user_id=user_id)
    resp = await svc.apply_message(
        session_id=session.id, message_id=msg.id, user_id=user_id, max_rows=10,
    )
    assert resp.row_count == 2  # 2 rows in fixture
    # Message marked executed after apply
    msgs = svc.list_messages(session.id, user_id=user_id)
    reloaded = next(m for m in msgs if m.id == msg.id)
    assert reloaded.executed is True


@pytest.mark.asyncio
async def test_apply_rejects_malicious_llm_sql(db, user_id, source_id):
    llm_reply = "```sql\nDROP TABLE users\n```"
    svc = _make_service(db, llm_reply)
    session = svc.create_session(
        SessionCreate(name="s3", source_id=source_id, model_config_id=None),
        user_id=user_id,
    )
    msg = await svc.send_message(session_id=session.id, content="rm users", user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        await svc.apply_message(session_id=session.id, message_id=msg.id, user_id=user_id)
    assert exc.value.code.startswith("SQL_GUARD_")


@pytest.mark.asyncio
async def test_non_owner_cannot_access_session(db, user_id, source_id):
    llm_reply = "```sql\nSELECT 1\n```"
    svc = _make_service(db, llm_reply)
    session = svc.create_session(
        SessionCreate(name="s4", source_id=source_id, model_config_id=None),
        user_id=user_id,
    )
    msg = await svc.send_message(session_id=session.id, content="x", user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        await svc.apply_message(
            session_id=session.id, message_id=msg.id, user_id=user_id + 99,
        )
    assert exc.value.code == "DP_CHAT_FORBIDDEN"


@pytest.mark.asyncio
async def test_apply_missing_sql_returns_400(db, user_id, source_id):
    llm_reply = "抱歉我无法回答。"  # no SQL fence
    svc = _make_service(db, llm_reply)
    session = svc.create_session(
        SessionCreate(name="s5", source_id=source_id, model_config_id=None),
        user_id=user_id,
    )
    msg = await svc.send_message(session_id=session.id, content="?", user_id=user_id)
    assert msg.generated_sql is None
    with pytest.raises(BusinessException) as exc:
        await svc.apply_message(session_id=session.id, message_id=msg.id, user_id=user_id)
    assert exc.value.code == "DP_CHAT_NO_SQL"
