"""标准项与字段绑定测试。"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sync_bg(isolated_engine, monkeypatch):
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )

    def _open():
        return SessionLocal()

    monkeypatch.setattr("app.services.job_runner.open_job_session", _open)
    monkeypatch.setattr("app.services.meta_brief_service.open_job_session", _open)

    def immediate(fn, *args, **kwargs):
        fn(*args, **kwargs)

    monkeypatch.setattr("app.services.meta_brief_service.run_in_background", immediate)
    return SessionLocal


def _seed_source(db_session):
    from app.db.models.data_source_model import DataSource, DataSourceStatus, DataSourceType

    src = DataSource(
        name="std-src",
        source_type=DataSourceType.DORIS,
        host="127.0.0.1",
        port=9030,
        username="root",
        password="",
        database="tmp",
        status=DataSourceStatus.ONLINE,
        is_default=True,
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)
    return src


def _seed_column(db_session, source_id: int):
    from app.db.models.meta_model import MetaColumn, MetaTable

    t = MetaTable(
        source_id=source_id,
        database="tmp",
        table_name="dwd_cust",
        table_comment="客户",
        row_count=100,
        column_count=2,
    )
    db_session.add(t)
    db_session.flush()
    c1 = MetaColumn(table_id=t.id, column_name="mobile", ordinal=1, data_type="varchar", column_type="varchar(20)")
    c2 = MetaColumn(table_id=t.id, column_name="phone2", ordinal=2, data_type="varchar", column_type="varchar(20)")
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)
    return t, c1, c2


def test_standard_one_to_many_bind(client, db_session, auth_headers):
    src = _seed_source(db_session)
    _, c1, c2 = _seed_column(db_session, src.id)

    r = client.post(
        "/api/v1/metadata/standards",
        headers=auth_headers,
        json={
            "code": "STD_PHONE_T",
            "name": "手机号",
            "security_level": "L3",
            "length_rule": {"min": 11, "max": 11},
            "quality_rule": {"regex": r"^1\\d{10}$"},
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    b1 = client.post(
        f"/api/v1/metadata/columns/{c1.id}/bind-standard",
        headers=auth_headers,
        json={"standard_id": sid, "status": "accepted", "source": "human"},
    )
    assert b1.status_code == 200, b1.text
    b2 = client.post(
        f"/api/v1/metadata/columns/{c2.id}/bind-standard",
        headers=auth_headers,
        json={"standard_id": sid, "status": "accepted", "source": "human"},
    )
    assert b2.status_code == 200

    detail = client.get(f"/api/v1/metadata/standards/{sid}", headers=auth_headers)
    assert detail.json()["bound_column_count"] == 2

    ws = client.get(
        "/api/v1/metadata/workspace/columns",
        headers=auth_headers,
        params={"source_id": src.id, "database": "tmp", "standard_id": sid},
    )
    assert ws.status_code == 200
    assert len(ws.json()) == 2

    # 字段 1:1 — 换绑另一标准
    r2 = client.post(
        "/api/v1/metadata/standards",
        headers=auth_headers,
        json={"code": "STD_OTHER", "name": "其它", "security_level": "L1"},
    )
    other = r2.json()["id"]
    client.post(
        f"/api/v1/metadata/columns/{c1.id}/bind-standard",
        headers=auth_headers,
        json={"standard_id": other, "status": "accepted", "source": "human"},
    )
    ws2 = client.get(
        "/api/v1/metadata/workspace/columns",
        headers=auth_headers,
        params={"source_id": src.id, "database": "tmp", "column_name": "mobile"},
    )
    assert len(ws2.json()) == 1
    assert ws2.json()[0]["standard_id"] == other


def test_jobs_and_brief(client, db_session, auth_headers, sync_bg):
    src = _seed_source(db_session)
    _seed_column(db_session, src.id)

    j = client.post(
        "/api/v1/metadata/briefs",
        headers=auth_headers,
        json={"source_id": src.id, "database": "tmp", "mode": "rules"},
    )
    assert j.status_code == 200, j.text
    assert j.json()["job_kind"] == "brief"
    job_id = j.json()["id"]
    job = client.get(f"/api/v1/metadata/jobs/{job_id}", headers=auth_headers).json()
    assert job["status"] == "succeeded", job

    brief = client.get(
        "/api/v1/metadata/briefs",
        headers=auth_headers,
        params={"source_id": src.id, "database": "tmp"},
    )
    assert brief.status_code == 200
    assert brief.json()["content_md"]

    jobs = client.get(
        "/api/v1/metadata/jobs",
        headers=auth_headers,
        params={"source_id": src.id, "database": "tmp"},
    )
    assert jobs.status_code == 200
    assert any(x["job_kind"] == "brief" for x in jobs.json())


def test_llm_settings_roundtrip(client, auth_headers):
    g = client.get("/api/v1/metadata/llm-settings", headers=auth_headers)
    assert g.status_code == 200
    assert isinstance(g.json(), list)

    # 创建第一套配置 → 自动成为默认（当前生效）
    u = client.post(
        "/api/v1/metadata/llm-settings",
        headers=auth_headers,
        json={
            "name": "Primary",
            "base_url": "https://example.com/v1",
            "model": "demo-model",
            "api_key": "sk-test-key-123456",
            "enabled": True,
        },
    )
    assert u.status_code == 200, u.text
    body = u.json()
    assert body["configured"] is True
    assert body["source"] == "db"
    assert body["has_api_key"] is True
    assert body["is_default"] is True
    assert "sk-test" not in (body.get("api_key_masked") or "")
    first_id = body["id"]

    # 创建第二套配置 → 不应抢占默认
    u2 = client.post(
        "/api/v1/metadata/llm-settings",
        headers=auth_headers,
        json={
            "name": "Secondary",
            "base_url": "https://example.com/v1",
            "model": "demo-model-2",
            "api_key": "sk-test-key-654321",
            "enabled": True,
        },
    )
    assert u2.status_code == 200, u2.text
    assert u2.json()["is_default"] is False
    second_id = u2.json()["id"]

    # 应用第二套 → 默认切换
    a = client.post(f"/api/v1/metadata/llm-settings/{second_id}/apply", headers=auth_headers)
    assert a.status_code == 200, a.text
    assert a.json()["is_default"] is True

    # 列表里只有一条默认
    lst = client.get("/api/v1/metadata/llm-settings", headers=auth_headers).json()
    db_rows = [r for r in lst if r["source"] == "db"]
    assert sum(1 for r in db_rows if r["is_default"]) == 1

    # 更新（不含 api_key 时密钥保留）
    p = client.put(
        f"/api/v1/metadata/llm-settings/{first_id}",
        headers=auth_headers,
        json={"name": "Primary-renamed", "enabled": False},
    )
    assert p.status_code == 200, p.text
    assert p.json()["name"] == "Primary-renamed"
    assert p.json()["has_api_key"] is True

    # 删除
    d = client.delete(f"/api/v1/metadata/llm-settings/{first_id}", headers=auth_headers)
    assert d.status_code == 200, d.text

