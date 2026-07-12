"""Backend-wide shared test fixtures.

Provides FastAPI TestClient with `get_db` dependency-overridden to a per-test
in-memory SQLite engine (with MySQL type-compat shims), an autouse
session-scoped FERNET_KEY setup, and a `test_user` fixture minting real JWTs.

Note: existing sub-directory conftests (`tests/data_platform/conftest.py`,
`tests/knowledge_base/conftest.py`) already provide their own `db` fixture for
service-level tests. This root conftest ADDS non-conflicting fixtures
(`isolated_engine`, `db_session`, `override_db`, `client`, `test_user`,
`auth_headers`) used by the new router-integration and auth-gate tests.
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker


# MEDIUMTEXT (MySQL-only) → TEXT so SQLite create_all works.
@compiles(MEDIUMTEXT, "sqlite")
def _mediumtext_sqlite(element, compiler, **kw):  # type: ignore[no-untyped-def]
    return "TEXT"


@pytest.fixture(autouse=True, scope="session")
def _fernet_key_for_tests() -> None:
    """Guarantee FERNET_KEY is set BEFORE app.core.crypto is imported."""
    os.environ["FERNET_KEY"] = Fernet.generate_key().decode("ascii")
    from app.core import crypto as _crypto

    _crypto._load()  # type: ignore[attr-defined]


def _strip_mysql_fulltext_indexes(metadata) -> None:
    """MySQL FULLTEXT indexes crash SQLite create_all → strip on test rigs."""
    for tbl in list(metadata.tables.values()):
        keep = set()
        for idx in tbl.indexes:
            prefix = idx.dialect_options.get("mysql", {}).get("prefix")
            if prefix != "FULLTEXT":
                keep.add(idx)
        tbl.indexes = keep


@pytest.fixture
def isolated_engine():
    """Fresh in-memory sqlite engine per test (single shared connection)."""
    import app.db.models  # noqa: F401 populate metadata
    from app.db.session import Base

    _strip_mysql_fulltext_indexes(Base.metadata)

    # StaticPool + shared connection so :memory: is visible across sessions.
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(isolated_engine) -> Iterator[Session]:
    """Direct SQLAlchemy Session bound to `isolated_engine` for test setup."""
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def override_db(isolated_engine):
    """Return a factory that installs a `get_db` override into a FastAPI app."""
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )

    def _factory(app):
        from app.db.session import get_db as real_get_db
        from app.db.session import get_session_factory as real_session_factory

        def _override():
            s = SessionLocal()
            try:
                yield s
            finally:
                s.close()

        def _override_factory():
            return SessionLocal

        app.dependency_overrides[real_get_db] = _override
        app.dependency_overrides[real_session_factory] = _override_factory
        return app

    return _factory


@pytest.fixture
def client(override_db, test_user) -> Iterator[TestClient]:
    """FastAPI TestClient with in-memory sqlite backing all requests.

    Uses raw TestClient() without `with:` so the lifespan seeder does NOT run
    against real MySQL; tests seed kb_libraries manually via db_session where
    needed.
    """
    from app.main import app

    override_db(app)
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {test_user['token']}"})
    try:
        yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anon_client() -> Iterator[TestClient]:
    """TestClient with NO db override — used by auth-gate tests that never
    reach a `Depends(get_db)` because the auth dependency 401s first."""
    from app.main import app

    c = TestClient(app)
    try:
        yield c
    finally:
        pass


@pytest.fixture
def test_user(db_session) -> dict:
    """Seed a test user and mint a real JWT."""
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.user_model import User

    u = User(
        username="tester",
        email="tester@example.com",
        password_hash=get_password_hash("test-pw"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(u)
    db_session.commit()
    token = create_access_token({"sub": u.username, "user_id": u.id})
    return {"id": u.id, "username": u.username, "token": token}


@pytest.fixture
def test_user2(db_session) -> dict:
    """Seed a second user for owner-scope tests."""
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.user_model import User

    u = User(
        username="tester2",
        email="tester2@example.com",
        password_hash=get_password_hash("test-pw"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(u)
    db_session.commit()
    token = create_access_token({"sub": u.username, "user_id": u.id})
    return {"id": u.id, "username": u.username, "token": token}


@pytest.fixture
def auth_headers(test_user) -> dict:
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest.fixture
def auth_headers2(test_user2) -> dict:
    return {"Authorization": f"Bearer {test_user2['token']}"}


@pytest.fixture
def kb_libraries(db_session) -> dict:
    """Seed the 4 kb_libraries rows (which the lifespan seeder would normally
    write). Returns code → id mapping."""
    from app.db.models.kb_library_model import KbLibrary

    seeds = [
        ("data_asset", "数据资产", "DatabaseOutlined", 1),
        ("code_repo", "代码库", "GithubOutlined", 2),
        ("document", "文档库", "FileTextOutlined", 3),
        ("experience", "业务经验库", "BulbOutlined", 4),
    ]
    ids: dict[str, int] = {}
    for code, name_zh, icon, sort in seeds:
        row = KbLibrary(
            code=code,
            name_zh=name_zh,
            icon=icon,
            description=f"seed {code}",
            sort_order=sort,
        )
        db_session.add(row)
        db_session.flush()
        ids[code] = row.id
    db_session.commit()
    return ids
