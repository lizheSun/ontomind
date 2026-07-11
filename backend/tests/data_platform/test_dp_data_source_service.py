"""dp_data_source_service TDD：覆盖创建/更新/加密/engine cache/连接测试/introspect/删除/ACL。"""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessException
from app.schemas.dp_data_source_schema import (
    DpDataSourceCreate,
    DpDataSourceUpdate,
)
from app.services.dp_data_source_service import (
    _ENGINE_STORE,
    DpDataSourceService,
)


def _mk_sqlite_payload(name: str, path: str) -> DpDataSourceCreate:
    return DpDataSourceCreate(
        name=name,
        source_type="sqlite",
        dialect="sqlite",
        database=path,  # :memory: 或文件路径
        charset="utf8mb4",
        read_only_flag=True,
    )


def _mk_mysql_payload(name: str, password: str = "s3cret") -> DpDataSourceCreate:
    return DpDataSourceCreate(
        name=name,
        source_type="mysql",
        dialect="mysql",
        host="localhost",
        port=3306,
        username="u",
        password=password,
        database="testdb",
        charset="utf8mb4",
        read_only_flag=True,
    )


def test_create_encrypts_password(db, user_id):
    svc = DpDataSourceService(db)
    read = svc.create(_mk_mysql_payload("ds1"), user_id=user_id)
    assert read.has_password is True
    row = svc.repo.get_by_id(read.id)
    assert row.password_enc and row.password_enc != "s3cret"


def test_create_refuses_when_encryption_disabled(db, user_id, monkeypatch):
    from app.core import crypto

    monkeypatch.setattr(crypto, "ENCRYPTION_DISABLED", True)
    svc = DpDataSourceService(db)
    with pytest.raises(BusinessException) as exc:
        svc.create(_mk_mysql_payload("ds-nokey"), user_id=user_id)
    assert exc.value.code == "ENCRYPTION_DISABLED"


def test_update_blank_password_preserves(db, user_id):
    svc = DpDataSourceService(db)
    ds = svc.create(_mk_mysql_payload("ds-upd", password="orig"), user_id=user_id)
    original_enc = svc.repo.get_by_id(ds.id).password_enc

    # password=None (unset) → 保留
    svc.update(ds.id, DpDataSourceUpdate(description="new desc"), user_id=user_id)
    assert svc.repo.get_by_id(ds.id).password_enc == original_enc

    # password="" (空串) → 保留
    svc.update(ds.id, DpDataSourceUpdate(password=""), user_id=user_id)
    assert svc.repo.get_by_id(ds.id).password_enc == original_enc


def test_update_new_password_rotates(db, user_id):
    svc = DpDataSourceService(db)
    ds = svc.create(_mk_mysql_payload("ds-rot", password="orig"), user_id=user_id)
    original_enc = svc.repo.get_by_id(ds.id).password_enc
    svc.update(ds.id, DpDataSourceUpdate(password="newpw"), user_id=user_id)
    new_enc = svc.repo.get_by_id(ds.id).password_enc
    assert new_enc and new_enc != original_enc


def test_name_conflict_on_create(db, user_id):
    svc = DpDataSourceService(db)
    svc.create(_mk_mysql_payload("dup"), user_id=user_id)
    with pytest.raises(BusinessException) as exc:
        svc.create(_mk_mysql_payload("dup"), user_id=user_id)
    assert exc.value.code == "DP_DS_NAME_EXISTS"


def test_engine_cache_hit_and_invalidate(db, user_id, tmp_path):
    svc = DpDataSourceService(db)
    sqlite_path = str(tmp_path / "cache.sqlite")
    ds = svc.create(_mk_sqlite_payload("ds-sqlite", sqlite_path), user_id=user_id)
    eng1 = svc.get_engine(ds.id)
    eng2 = svc.get_engine(ds.id)
    assert eng1 is eng2  # cache hit
    # update → invalidate
    svc.update(ds.id, DpDataSourceUpdate(description="tick"), user_id=user_id)
    eng3 = svc.get_engine(ds.id)
    assert eng3 is not eng1  # new engine after invalidation


def test_test_connection_happy_sqlite(db, user_id, tmp_path):
    svc = DpDataSourceService(db)
    sqlite_path = str(tmp_path / "probe.sqlite")
    ds = svc.create(_mk_sqlite_payload("ds-probe", sqlite_path), user_id=user_id)
    result = svc.test_connection(ds.id)
    assert result.ok is True
    assert result.server_version
    assert result.elapsed_ms >= 0


def test_test_connection_bad_host_returns_ok_false(db, user_id):
    svc = DpDataSourceService(db)
    ds = svc.create(
        DpDataSourceCreate(
            name="ds-bad",
            source_type="postgresql",
            dialect="postgresql",
            host="10.255.255.1",  # blackhole
            port=5432,
            username="u",
            password="p",
            database="none",
            charset="utf8mb4",
            read_only_flag=True,
        ),
        user_id=user_id,
    )
    result = svc.test_connection(ds.id)
    assert result.ok is False
    assert result.error


def test_describe_schema_sqlite(db, user_id, tmp_path):
    """建一个真的 SQLite 库并写一个表进去，再 introspect 拿结构。"""
    from sqlalchemy import create_engine, text

    sqlite_path = str(tmp_path / "schema.sqlite")
    eng = create_engine(f"sqlite:///{sqlite_path}", future=True)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY, name TEXT)"))
    eng.dispose()

    svc = DpDataSourceService(db)
    ds = svc.create(_mk_sqlite_payload("ds-schema", sqlite_path), user_id=user_id)
    schema = svc.describe_schema(ds.id)
    dbs = schema["databases"]
    assert len(dbs) == 1
    names = {t["name"] for t in dbs[0]["tables"]}
    assert "probe" in names
    probe_cols = next(t for t in dbs[0]["tables"] if t["name"] == "probe")["columns"]
    assert {c["name"] for c in probe_cols} == {"id", "name"}


def test_delete_removes_engine_cache(db, user_id, tmp_path):
    svc = DpDataSourceService(db)
    sqlite_path = str(tmp_path / "del.sqlite")
    ds = svc.create(_mk_sqlite_payload("ds-del", sqlite_path), user_id=user_id)
    svc.get_engine(ds.id)
    assert any(k[0] == ds.id for k in _ENGINE_STORE)
    svc.delete(ds.id, user_id=user_id)
    assert not any(k[0] == ds.id for k in _ENGINE_STORE)


def test_non_owner_cannot_update(db, user_id):
    svc = DpDataSourceService(db)
    ds = svc.create(_mk_mysql_payload("ds-acl"), user_id=user_id)
    other_user = user_id + 999
    with pytest.raises(BusinessException) as exc:
        svc.update(ds.id, DpDataSourceUpdate(description="hack"), user_id=other_user)
    assert exc.value.code == "DP_DS_FORBIDDEN"
