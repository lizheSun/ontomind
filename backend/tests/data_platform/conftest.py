"""Data-platform 服务测试的共享 fixture：in-memory sqlite + FERNET key。

service 层用 `with self.db.begin():` 提交，因此 fixture 不使用外层 transaction wrapper，
每个测试给一份全新的 in-memory DB。
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker


# SQLite compat for MySQL-only types (T07/T09 conftest 同款)
@compiles(MEDIUMTEXT, "sqlite")
def _mediumtext_sqlite(element, compiler, **kw):  # type: ignore[no-untyped-def]
    return "TEXT"


@pytest.fixture(autouse=True, scope="session")
def _fernet_key_for_tests() -> None:
    """在导入 app.core.crypto 之前保证 FERNET_KEY 存在。"""
    from cryptography.fernet import Fernet

    os.environ["FERNET_KEY"] = Fernet.generate_key().decode("ascii")
    # 强制 reload crypto 模块状态，令 ENCRYPTION_DISABLED=False
    from app.core import crypto as _crypto

    _crypto._load()  # type: ignore[attr-defined]


def _strip_mysql_fulltext_indexes(metadata) -> None:
    """MySQL FULLTEXT 索引在 SQLite create_all 时会失败。"""
    for tbl in list(metadata.tables.values()):
        keep = set()
        for idx in tbl.indexes:
            prefix = idx.dialect_options.get("mysql", {}).get("prefix")
            if prefix != "FULLTEXT":
                keep.add(idx)
        tbl.indexes = keep


@pytest.fixture(scope="function")
def db() -> Iterator[Session]:
    """每 test 一份全新的 in-memory sqlite；service 层自己 commit。"""
    import app.db.models  # noqa: F401  populate metadata
    from app.db.session import Base

    _strip_mysql_fulltext_indexes(Base.metadata)

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def user_id(db: Session) -> int:
    from app.db.models.user_model import User

    u = User(
        username="carol",
        email="c@e.f",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.flush()
    uid = int(u.id)
    db.commit()
    return uid
