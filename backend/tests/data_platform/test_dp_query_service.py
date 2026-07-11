"""dp_query_service TDD: guard, LIMIT, stream batches, saved-query CRUD, history lifecycle."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from app.core.exceptions import BusinessException
from app.schemas.dp_data_source_schema import DpDataSourceCreate
from app.schemas.dp_query_schema import SavedQueryCreate, SavedQueryUpdate
from app.services.dp_data_source_service import DpDataSourceService
from app.services.dp_query_service import DpQueryService


@pytest.fixture
def source_id(db, user_id, tmp_path):
    sqlite_path = str(tmp_path / "queries.sqlite")
    eng = create_engine(f"sqlite:///{sqlite_path}", future=True)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        for i in range(1500):
            c.execute(text(f"INSERT INTO users VALUES ({i}, 'u{i}')"))
    eng.dispose()

    svc = DpDataSourceService(db)
    ds = svc.create(
        DpDataSourceCreate(
            name="qsvc-src",
            source_type="sqlite",
            dialect="sqlite",
            database=sqlite_path,
            charset="utf8mb4",
            read_only_flag=True,
        ),
        user_id=user_id,
    )
    return ds.id


@pytest.mark.asyncio
async def test_execute_sync_limit_injection(db, user_id, source_id):
    q = DpQueryService(db)
    resp = await q.execute_sync(
        source_id=source_id,
        sql="SELECT id, name FROM users",
        max_rows=100,
        user_id=user_id,
    )
    assert resp.row_count == 100
    assert [c.name for c in resp.columns] == ["id", "name"]
    assert resp.truncated is True


@pytest.mark.asyncio
async def test_execute_sync_ddl_rejected_and_history_error(db, user_id, source_id):
    q = DpQueryService(db)
    with pytest.raises(BusinessException) as exc:
        await q.execute_sync(
            source_id=source_id,
            sql="DROP TABLE users",
            max_rows=100,
            user_id=user_id,
        )
    assert exc.value.code.startswith("SQL_GUARD_")
    histories = q.list_history(user_id=user_id)
    assert any(h.status == "error" for h in histories)


@pytest.mark.asyncio
async def test_execute_sync_preserves_limit_below_cap(db, user_id, source_id):
    q = DpQueryService(db)
    resp = await q.execute_sync(
        source_id=source_id,
        sql="SELECT id FROM users LIMIT 5",
        max_rows=1000,
        user_id=user_id,
    )
    assert resp.row_count == 5
    assert resp.truncated is False


@pytest.mark.asyncio
async def test_execute_stream_multiple_batches(db, user_id, source_id):
    q = DpQueryService(db)
    events = []
    async for evt in q.execute_stream(
        source_id=source_id,
        sql="SELECT id FROM users LIMIT 1200",
        user_id=user_id,
        max_rows=10_000,
    ):
        events.append(evt)
    kinds = [e["event"] for e in events]
    assert kinds[0] == "columns"
    assert kinds.count("rows") >= 2  # 1200 / 500 = 3 batches
    assert kinds[-1] == "done"
    total = sum(len(e["data"]) for e in events if e["event"] == "rows")
    assert total == 1200
    assert events[-1]["data"]["row_count"] == 1200


@pytest.mark.asyncio
async def test_execute_stream_guard_error_emits_event(db, user_id, source_id):
    q = DpQueryService(db)
    events = []
    async for evt in q.execute_stream(
        source_id=source_id,
        sql="DROP TABLE users",
        user_id=user_id,
        max_rows=100,
    ):
        events.append(evt)
    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert events[0]["data"]["code"].startswith("SQL_GUARD_")


def test_saved_query_crud_owner_only(db, user_id, source_id):
    q = DpQueryService(db)
    saved = q.create_saved(
        SavedQueryCreate(
            name="top10",
            source_id=source_id,
            sql_text="SELECT * FROM users LIMIT 10",
            is_favorite=False,
        ),
        user_id=user_id,
    )
    listed = q.list_saved(user_id=user_id)
    assert len(listed) == 1
    updated = q.update_saved(
        saved.id, SavedQueryUpdate(is_favorite=True), user_id=user_id,
    )
    assert updated.is_favorite is True
    # non-owner cannot update
    with pytest.raises(Exception):
        q.update_saved(
            saved.id, SavedQueryUpdate(is_favorite=False), user_id=user_id + 99,
        )
    q.delete_saved(saved.id, user_id=user_id)
    assert q.list_saved(user_id=user_id) == []
