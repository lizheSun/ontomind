"""In-memory SQLite fixture with transactional rollback for repo tests."""
from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401 - populate metadata
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
    _strip_mysql_fulltext_indexes()
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, future=True)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
