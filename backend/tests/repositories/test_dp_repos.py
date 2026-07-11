"""dp_* 仓储层烟雾测试：验证 CRUD + owner scope + 特化方法。"""
from __future__ import annotations

import pytest

from app.db.models.user_model import User
from app.db.repositories.dp_chat_repo import (
    DpChatMessageRepository,
    DpChatSessionRepository,
)
from app.db.repositories.dp_data_source_repo import DpDataSourceRepository
from app.db.repositories.dp_query_history_repo import DpQueryHistoryRepository
from app.db.repositories.dp_sql_query_repo import DpSqlQueryRepository


@pytest.fixture
def user_id(db):
    u = User(
        username="alice",
        email="a@b.c",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.flush()
    return u.id


def _mk_ds(db, user_id: int, name: str = "test-mysql"):
    return DpDataSourceRepository(db).create(
        {
            "name": name,
            "source_type": "mysql",
            "dialect": "mysql",
            "database": "testdb",
            "charset": "utf8mb4",
            "status": "active",
            "read_only_flag": True,
            "owner_user_id": user_id,
            "created_by_user_id": user_id,
        }
    )


def test_dp_datasource_crud_and_owner_scope(db, user_id):
    repo = DpDataSourceRepository(db)
    row = _mk_ds(db, user_id, name="test-mysql")
    assert row.id and row.name == "test-mysql"
    assert repo.name_exists("test-mysql")
    assert not repo.name_exists("test-mysql", exclude_id=row.id)
    assert repo.get_by_name("test-mysql").id == row.id
    assert len(repo.list_by_owner(user_id=user_id)) == 1
    assert len(repo.list_by_owner(user_id=user_id + 99)) == 0


def test_dp_sql_query_toggle_favorite(db, user_id):
    ds = _mk_ds(db, user_id, name="src")
    q_repo = DpSqlQueryRepository(db)
    q = q_repo.create(
        {
            "name": "top10",
            "source_id": ds.id,
            "sql_text": "SELECT 1",
            "is_favorite": False,
            "owner_user_id": user_id,
        }
    )
    assert q.is_favorite is False
    toggled = q_repo.toggle_favorite(q.id)
    assert toggled is not None and toggled.is_favorite is True
    # Scoped list_by_owner works with optional source filter
    listed = q_repo.list_by_owner(user_id=user_id, source_id=ds.id)
    assert len(listed) == 1 and listed[0].id == q.id
    assert q_repo.toggle_favorite(9999) is None


def test_dp_query_history_lifecycle(db, user_id):
    ds = _mk_ds(db, user_id, name="src2")
    h_repo = DpQueryHistoryRepository(db)
    running = h_repo.create_running(
        user_id=user_id, source_id=ds.id, sql_text="SELECT 1"
    )
    assert running.status == "running"
    ok = h_repo.mark_success(
        running.id,
        row_count=1,
        elapsed_ms=5,
        columns_json=[{"name": "c", "type": "int"}],
    )
    assert ok is not None and ok.status == "success"
    assert ok.finished_at is not None

    # error path on a fresh row
    another = h_repo.create_running(
        user_id=user_id, source_id=ds.id, sql_text="BAD SQL"
    )
    err = h_repo.mark_error(another.id, error_message="boom")
    assert err is not None and err.status == "error" and err.error_message == "boom"

    recents = h_repo.list_recent(user_id=user_id)
    assert len(recents) == 2
    assert h_repo.mark_error(9999, error_message="x") is None
    assert h_repo.mark_success(9999, row_count=0, elapsed_ms=0, columns_json=None) is None


def test_dp_chat_session_and_messages(db, user_id):
    ds = _mk_ds(db, user_id, name="chat-src")
    s_repo = DpChatSessionRepository(db)
    session = s_repo.create(
        {
            "name": "chat 1",
            "source_id": ds.id,
            "user_id": user_id,
            "model_config_id": None,
        }
    )
    m_repo = DpChatMessageRepository(db)
    m_repo.append(session_id=session.id, role="user", content="last 10 users?")
    a_msg = m_repo.append(
        session_id=session.id,
        role="assistant",
        content="SELECT ...",
        generated_sql="SELECT * FROM users LIMIT 10",
    )
    msgs = m_repo.list_by_session(session.id)
    assert len(msgs) == 2 and msgs[0].role == "user" and msgs[1].role == "assistant"
    updated = m_repo.mark_executed(a_msg.id)
    assert updated is not None and updated.executed is True
    assert m_repo.mark_executed(9999) is None

    sessions = s_repo.list_by_owner(user_id=user_id)
    assert len(sessions) == 1 and sessions[0].id == session.id
