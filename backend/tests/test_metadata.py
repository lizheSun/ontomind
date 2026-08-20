"""元数据扫描与自动标注测试。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
    monkeypatch.setattr("app.services.meta_scan_service.open_job_session", _open)
    monkeypatch.setattr("app.services.annotation_service.open_job_session", _open)

    def immediate(fn, *args, **kwargs):
        fn(*args, **kwargs)

    monkeypatch.setattr("app.services.meta_scan_service.run_in_background", immediate)
    monkeypatch.setattr("app.services.annotation_service.run_in_background", immediate)
    return SessionLocal


def _seed_source(db_session):
    from app.db.models.data_source_model import DataSource, DataSourceStatus, DataSourceType

    src = DataSource(
        name="test-doris",
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


def _mock_connector():
    conn = MagicMock()
    conn.list_tables_meta.return_value = [
        {
            "name": "dwd_cust_info",
            "type": "BASE TABLE",
            "comment": "客户信息",
            "row_count": 5000,
            "engine": "olap",
        },
        {
            "name": "tmp_log_detail",
            "type": "BASE TABLE",
            "comment": None,
            "row_count": 10,
            "engine": "olap",
        },
    ]
    conn.batch_columns.return_value = {
        "dwd_cust_info": [
            {
                "name": "cust_id",
                "ordinal": 1,
                "data_type": "bigint",
                "type": "bigint",
                "nullable": False,
                "key": "PRI",
                "default": None,
                "extra": "",
                "comment": "客户标识",
            },
            {
                "name": "phone_no",
                "ordinal": 2,
                "data_type": "varchar",
                "type": "varchar(20)",
                "nullable": True,
                "key": "",
                "default": None,
                "extra": "",
                "comment": "手机号",
            },
            {
                "name": "loan_amt",
                "ordinal": 3,
                "data_type": "decimal",
                "type": "decimal(18,2)",
                "nullable": True,
                "key": "",
                "default": None,
                "extra": "",
                "comment": "贷款金额",
            },
        ],
        "tmp_log_detail": [
            {
                "name": "id",
                "ordinal": 1,
                "data_type": "bigint",
                "type": "bigint",
                "nullable": False,
                "key": "PRI",
                "default": None,
                "extra": "",
                "comment": None,
            },
        ],
    }
    conn.profile_column.return_value = {
        "total": 100,
        "null_rate": 0.0,
        "distinct_count": 100,
        "distinct_ratio": 1.0,
        "min": None,
        "max": None,
        "sampled": True,
        "top_k": [{"value": "13800138000", "cnt": 1}],
    }
    return conn


def test_scan_upsert_preserves_biz_fields(client, db_session, sync_bg):
    src = _seed_source(db_session)
    mock = _mock_connector()

    with patch("app.services.meta_scan_service.DataSourceConnector", return_value=mock):
        r = client.post(
            "/api/v1/metadata/scans",
            json={"source_id": src.id, "database": "tmp", "with_profile": False},
        )
        assert r.status_code == 200, r.text
        job_id = r.json()["id"]
        job = client.get(f"/api/v1/metadata/scans/{job_id}").json()
        assert job["status"] == "succeeded", job
        assert job["stats_json"]["table_count"] == 2

    tables = client.get("/api/v1/metadata/tables", params={"source_id": src.id, "database": "tmp"})
    assert tables.status_code == 200
    rows = tables.json()
    assert len(rows) == 2
    cust = next(t for t in rows if t["table_name"] == "dwd_cust_info")
    tid = cust["id"]

    r = client.put(
        f"/api/v1/metadata/tables/{tid}",
        json={"biz_name": "客户主档", "biz_description": "人工维护", "domain": "客户"},
    )
    assert r.status_code == 200
    assert r.json()["biz_name"] == "客户主档"

    detail = client.get(f"/api/v1/metadata/tables/{tid}")
    col = next(c for c in detail.json()["columns"] if c["column_name"] == "cust_id")
    client.put(
        f"/api/v1/metadata/columns/{col['id']}",
        json={"biz_name": "客户主键", "biz_description": "人工列注释"},
    )

    mock.list_tables_meta.return_value[0]["comment"] = "客户信息更新"
    with patch("app.services.meta_scan_service.DataSourceConnector", return_value=mock):
        r = client.post(
            "/api/v1/metadata/scans",
            json={"source_id": src.id, "database": "tmp"},
        )
        assert r.status_code == 200
        job2 = client.get(f"/api/v1/metadata/scans/{r.json()['id']}").json()
        assert job2["status"] == "succeeded", job2

    tables2 = client.get("/api/v1/metadata/tables", params={"source_id": src.id, "database": "tmp"})
    cust2 = next(t for t in tables2.json() if t["table_name"] == "dwd_cust_info")
    assert cust2["id"] == tid
    assert cust2["biz_name"] == "客户主档"
    assert cust2["biz_description"] == "人工维护"
    assert cust2["domain"] == "客户"
    assert cust2["table_comment"] == "客户信息更新"

    detail2 = client.get(f"/api/v1/metadata/tables/{tid}")
    col2 = next(c for c in detail2.json()["columns"] if c["column_name"] == "cust_id")
    assert col2["biz_name"] == "客户主键"
    assert col2["biz_description"] == "人工列注释"


def test_rules_annotation_abbrev_pii_join_key(client, db_session, sync_bg):
    src = _seed_source(db_session)
    mock = _mock_connector()
    with patch("app.services.meta_scan_service.DataSourceConnector", return_value=mock):
        r = client.post(
            "/api/v1/metadata/scans",
            json={"source_id": src.id, "database": "tmp"},
        )
        assert r.status_code == 200
        assert client.get(f"/api/v1/metadata/scans/{r.json()['id']}").json()["status"] == "succeeded"

    r = client.post(
        "/api/v1/metadata/annotate-jobs",
        json={"source_id": src.id, "database": "tmp", "mode": "rules"},
    )
    assert r.status_code == 200, r.text
    job = client.get(f"/api/v1/metadata/annotate-jobs/{r.json()['id']}").json()
    assert job["status"] == "succeeded", job
    assert job["job_kind"] == "annotate"

    anns = client.get("/api/v1/metadata/annotations").json()
    kinds = {(a["target_type"], a["label_kind"], a["label_value"]) for a in anns}

    assert any(k[1] == "domain" and k[2] == "DWD" for k in kinds)
    assert any(k[1] == "biz_name" and "客户" in k[2] for k in kinds)
    assert any(k[1] == "pii_level" and k[2] == "L3" for k in kinds)
    assert any(k[1] == "join_key" and k[2] == "true" for k in kinds)
    assert any(k[1] == "entity_candidate" for k in kinds)


def test_confidence_tiers_and_review_writeback(client, db_session, sync_bg):
    from app.db.models.meta_model import (
        Annotation,
        AnnotationLabelKind,
        AnnotationStatus,
        MetaColumn,
        MetaTable,
    )
    from app.services.annotation_service import AnnotationService, CONF_AUTO_ACCEPT, CONF_SUGGEST_MIN

    src = _seed_source(db_session)
    table = MetaTable(
        source_id=src.id,
        database="tmp",
        table_name="dim_prod",
        row_count=100,
    )
    db_session.add(table)
    db_session.flush()
    col = MetaColumn(table_id=table.id, column_name="prod_id", ordinal=1, data_type="bigint")
    db_session.add(col)
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(col)

    svc = AnnotationService(db_session)

    dropped = svc._persist_candidate(
        {
            "target_type": "column",
            "target_id": col.id,
            "label_kind": "biz_name",
            "label_value": "低置信",
            "confidence": CONF_SUGGEST_MIN - 0.1,
            "source": "rule",
            "evidence": {},
        }
    )
    assert dropped == "dropped"

    suggested = svc._persist_candidate(
        {
            "target_type": "column",
            "target_id": col.id,
            "label_kind": "biz_name",
            "label_value": "产品标识",
            "confidence": 0.7,
            "source": "rule",
            "evidence": {},
        }
    )
    assert suggested == "written"
    anns = (
        db_session.query(Annotation)
        .filter(Annotation.target_id == col.id, Annotation.label_kind == AnnotationLabelKind.BIZ_NAME)
        .all()
    )
    assert any(a.status == AnnotationStatus.SUGGESTED for a in anns)

    accepted = svc._persist_candidate(
        {
            "target_type": "column",
            "target_id": col.id,
            "label_kind": "semantic_type",
            "label_value": "identifier",
            "confidence": CONF_AUTO_ACCEPT,
            "source": "rule",
            "evidence": {},
        }
    )
    assert accepted == "accepted"
    db_session.refresh(col)
    assert col.semantic_type == "identifier"

    sug = next(a for a in anns if a.status == AnnotationStatus.SUGGESTED)
    reviewed = svc.review_annotation(sug.id, "accept", user_id=1, value_override="产品编号")
    assert reviewed.status == AnnotationStatus.ACCEPTED
    db_session.refresh(col)
    assert col.biz_name == "产品编号"


def test_glossary_rules_extract_from_markdown(client, db_session, sync_bg):
    spaces = client.get("/api/v1/wiki/spaces").json()
    space_id = next(s["id"] for s in spaces if s["slug"] == "default")
    md = """# 术语

- **客户**：申请贷款的个人或机构
- **逾期**：超过约定还款日仍未结清

### 授信额度

客户可支用的最大金额上限。

| 术语 | 定义 |
| --- | --- |
| 还款 | 按期偿还本金与利息 |
"""
    r = client.post(
        "/api/v1/wiki/documents",
        json={
            "space_id": space_id,
            "title": "消金术语",
            "content_md": md,
            "source_type": "manual",
            "status": "published",
        },
    )
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    r = client.post(
        "/api/v1/metadata/glossary/extract",
        json={"doc_ids": [doc_id], "mode": "rules"},
    )
    assert r.status_code == 200, r.text
    terms = r.json()
    names = {t["name"] for t in terms}
    assert "客户" in names
    assert "逾期" in names
    assert "授信额度" in names
    assert "还款" in names
    cust = next(t for t in terms if t["name"] == "客户")
    assert "申请贷款" in (cust.get("definition") or "")
    assert cust["source_type"] == "rules"
    assert cust["source_doc_id"] == doc_id
