"""Backend-wide shared test fixtures.

提供 FastAPI TestClient（`get_db` 被 override 到内存 SQLite）+ 真实 JWT 的 test_user。

2026-08-03 深度精简：项目只剩 4 张表（users / roles / user_roles / audit_logs）
与 3 个路由域（auth / users / opencode），原来针对 data_platform / knowledge_base
的 fixture（kb_libraries / MEDIUMTEXT shim / FULLTEXT strip / FERNET_KEY）已全部删除。
"""
from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def isolated_engine():
    """每个测试一个全新的内存 sqlite engine（StaticPool 让 :memory: 跨 session 可见）."""
    import app.db.models  # noqa: F401 — populate metadata
    from app.db.session import Base

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
    """直连 isolated_engine 的 Session，用于测试数据准备."""
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
    """返回一个工厂：把 `get_db` override 装进 FastAPI app."""
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )

    def _factory(app):
        from app.db.session import get_db as real_get_db

        def _override():
            s = SessionLocal()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[real_get_db] = _override
        return app

    return _factory


@pytest.fixture
def test_user(db_session) -> dict:
    """建一个测试用户 + 签发真实 JWT."""
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
def client(override_db, test_user) -> Iterator[TestClient]:
    """带认证头的 TestClient（内存 sqlite 支撑所有请求）."""
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
    """无认证头的 TestClient（测 401 闸门用）."""
    from app.main import app

    return_client = TestClient(app)
    try:
        yield return_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user) -> dict:
    return {"Authorization": f"Bearer {test_user['token']}"}
