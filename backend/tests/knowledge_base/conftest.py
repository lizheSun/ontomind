"""KbService 测试 fixture：内存 sqlite + SAVEPOINT 事务回滚 + 4 库种子。"""
from __future__ import annotations

from typing import Dict, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401 - populate metadata
from app.db.models.kb_library_model import KbLibrary
from app.db.models.user_model import User
from app.db.session import Base


# MEDIUMTEXT is MySQL-only; map to TEXT on SQLite so create_all works in-memory.
@compiles(MEDIUMTEXT, "sqlite")
def _mediumtext_sqlite(element, compiler, **kw):  # type: ignore[no-untyped-def]
    return "TEXT"


def _strip_mysql_fulltext_indexes() -> None:
    """MySQL FULLTEXT 索引在 SQLite 上 create_all 会失败：测试期剥离。"""
    for tbl in list(Base.metadata.tables.values()):
        keep = set()
        for idx in tbl.indexes:
            prefix = idx.dialect_options.get("mysql", {}).get("prefix")
            if prefix != "FULLTEXT":
                keep.add(idx)
        tbl.indexes = keep


@pytest.fixture(scope="function")
def db() -> Iterator[Session]:
    """每个测试独享一个 in-memory sqlite；服务层 session.begin() 需要独立事务，
    所以这里不再套 connection.begin()，靠 engine.dispose() 完成回收。

    `expire_on_commit=False`：commit 后不过期属性，避免 fixture 返回的 id
    在测试中被重新访问时触发隐式 autobegin，与 service 的 `db.begin()` 冲突。
    """
    _strip_mysql_fulltext_indexes()
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(bind=engine, future=True, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def user_id(db) -> int:
    u = User(
        username="alice",
        email="alice@example.com",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.commit()
    return u.id


@pytest.fixture
def other_user_id(db) -> int:
    u = User(
        username="bob",
        email="bob@example.com",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.commit()
    return u.id


@pytest.fixture
def library_ids(db) -> Dict[str, int]:
    """种子 4 个 kb_libraries 行，返回 code -> id。"""
    seeds = [
        ("data_asset", "数据资产", "DatabaseOutlined", 1),
        ("code_repo", "代码库", "GithubOutlined", 2),
        ("document", "文档库", "FileTextOutlined", 3),
        ("experience", "业务经验库", "BulbOutlined", 4),
    ]
    ids: Dict[str, int] = {}
    for code, name_zh, icon, sort in seeds:
        row = KbLibrary(
            code=code,
            name_zh=name_zh,
            icon=icon,
            description=f"seed {code}",
            sort_order=sort,
        )
        db.add(row)
        db.flush()
        ids[code] = row.id
    db.commit()
    return ids
