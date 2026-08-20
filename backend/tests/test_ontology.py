"""本体建模 Phase 3 测试。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from app.services.ontology_build_service import OntologyBuildService, confidence_tier
from app.services.ontology_cq_service import OntologyCQService
from app.services.ontology_fragments import CONSUMER_FINANCE_FRAGMENT


@pytest.fixture
def sync_bg(isolated_engine, monkeypatch):
    SessionLocal = sessionmaker(
        bind=isolated_engine, autoflush=False, expire_on_commit=False, future=True
    )

    def _open():
        return SessionLocal()

    monkeypatch.setattr("app.services.job_runner.open_job_session", _open)
    monkeypatch.setattr("app.services.ontology_build_service.open_job_session", _open)

    def immediate(fn, *args, **kwargs):
        fn(*args, **kwargs)

    monkeypatch.setattr("app.services.ontology_build_service.run_in_background", immediate)
    return SessionLocal


def _create_ontology(client, slug="cf"):
    r = client.post(
        "/api/v1/ontology/ontologies",
        json={"name": "消金本体", "slug": slug, "domain": "consumer_finance", "description": "test"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_ontology_crud(client):
    ont = _create_ontology(client, "crud-ont")
    oid = ont["id"]
    assert ont["current_version"] == 0

    r = client.get(f"/api/v1/ontology/ontologies/{oid}")
    assert r.status_code == 200
    assert r.json()["slug"] == "crud-ont"

    r = client.put(f"/api/v1/ontology/ontologies/{oid}", json={"description": "更新"})
    assert r.status_code == 200
    assert r.json()["description"] == "更新"

    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "Party", "display_name": "主体", "status": "accepted"},
    )
    assert r.status_code == 200, r.text
    ot_id = r.json()["id"]

    r = client.post(
        f"/api/v1/ontology/object-types/{ot_id}/properties",
        json={"key": "party_id", "display_name": "主体ID", "data_type": "bigint"},
    )
    assert r.status_code == 200

    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/link-types",
        json={
            "key": "applies_for",
            "display_name": "申请",
            "from_key": "Party",
            "to_key": "LoanApplication",
            "cardinality": "1-n",
        },
    )
    assert r.status_code == 200

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/object-types")
    assert r.status_code == 200
    assert any(x["key"] == "Party" for x in r.json())

    r = client.delete(f"/api/v1/ontology/ontologies/{oid}")
    assert r.status_code == 200


def test_confidence_tiers():
    assert confidence_tier(0.9, "pass") == "accepted"
    assert confidence_tier(0.7, "pass") == "draft"
    assert confidence_tier(0.7, "warn") == "draft"
    assert confidence_tier(0.9, "warn") == "draft"
    assert confidence_tier(0.5, "pass") == "rejected"
    assert confidence_tier(0.99, "fail") == "rejected"


def test_rule_judge_checks(client, db_session):
    ont = _create_ontology(client, "judge-ont")
    oid = ont["id"]
    svc = OntologyBuildService(db_session)

    # seed one accepted OT so "exists" checks work for some cases
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "Party", "display_name": "主体", "status": "accepted"},
    )

    delta = {
        "new_object_types": [
            {"key": "LoanAccount", "display_name": "账户", "confidence": 0.9},
            {"key": "LoanAccount", "display_name": "重复", "confidence": 0.9},
        ],
        "new_properties": [
            {"object_type_key": "Missing", "key": "x", "confidence": 0.9},
            {"object_type_key": "Party", "key": "id", "confidence": 0.9},
        ],
        "new_link_types": [
            {"key": "bad_link", "from_key": "A", "to_key": "B", "confidence": 0.9},
            {"key": "good_link", "from_key": "Party", "to_key": "LoanAccount", "confidence": 0.9},
        ],
        "mappings": [
            {
                "element_key": "Party",
                "element_type": "object_type",
                "source_id": 999,
                "database": "tmp",
                "table_name": "nope",
            }
        ],
    }
    verdicts = svc.rule_judge(oid, delta, scope={})
    by_target = {v["target"]: v for v in verdicts}
    assert by_target["object_type:LoanAccount"]["verdict"] in ("pass", "fail")
    # duplicate in delta → fail for second occurrence; first pass
    fails = [v for v in verdicts if v["target"] == "object_type:LoanAccount" and v["verdict"] == "fail"]
    assert fails, "duplicate key should fail"
    assert by_target["property:Missing.x"]["verdict"] == "fail"
    assert by_target["property:Party.id"]["verdict"] == "pass"
    assert by_target["link_type:bad_link"]["verdict"] == "fail"
    assert by_target["link_type:good_link"]["verdict"] == "pass"
    assert by_target["mapping:Party"]["verdict"] == "fail"


def test_infer_relations_three_way(client, db_session, monkeypatch):
    from app.db.models.data_source_model import DataSource, DataSourceStatus, DataSourceType
    from app.db.models.meta_model import MetaColumn, MetaTable

    src = DataSource(
        name="infer-ds",
        source_type=DataSourceType.DORIS,
        host="127.0.0.1",
        port=9030,
        username="root",
        password="",
        database="tmp",
        status=DataSourceStatus.ONLINE,
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    t_loan = MetaTable(source_id=src.id, database="tmp", table_name="loan_account", row_count=100)
    t_cust = MetaTable(source_id=src.id, database="tmp", table_name="customer", row_count=50)
    db_session.add_all([t_loan, t_cust])
    db_session.commit()
    db_session.refresh(t_loan)
    db_session.refresh(t_cust)

    db_session.add_all(
        [
            MetaColumn(
                table_id=t_loan.id, column_name="cust_id", ordinal=1, data_type="bigint", column_key=""
            ),
            MetaColumn(
                table_id=t_cust.id, column_name="id", ordinal=1, data_type="bigint", column_key="PRI"
            ),
        ]
    )
    db_session.commit()

    ont = _create_ontology(client, "infer-ont")
    oid = ont["id"]
    for key, name in (("loan_account", "贷款账户"), ("customer", "客户")):
        client.post(
            f"/api/v1/ontology/ontologies/{oid}/object-types",
            json={"key": key, "display_name": name, "status": "accepted"},
        )

    mock_conn = MagicMock()
    mock_conn.overlap_ratio.return_value = 0.97
    monkeypatch.setattr(
        "app.services.ontology_build_service.DataSourceConnector",
        lambda **kwargs: mock_conn,
    )
    # ensure LLM path skipped
    mock_llm = MagicMock()
    mock_llm.is_configured.return_value = False
    monkeypatch.setattr(
        "app.services.ontology_build_service.resolve_llm_client",
        lambda db=None: mock_llm,
    )

    svc = OntologyBuildService(db_session)
    from app.schemas.ontology_schema import InferRelationsRequest

    cands = svc.infer_relations(
        oid, InferRelationsRequest(scope={"source_id": src.id, "database": "tmp"})
    )
    assert cands, "should produce candidates"
    cand = cands[0]
    assert cand["evidence"]["naming_match"] is True
    assert cand["evidence"]["overlap_ratio"] == 0.97
    assert cand["evidence"]["naming_weight"] == 0.4
    assert cand["evidence"]["overlap_weight"] == 0.4
    assert cand["confidence"] >= 0.8
    mock_conn.overlap_ratio.assert_called()


def test_publish_snapshot_accepted_only_and_rollback(client):
    ont = _create_ontology(client, "pub-ont")
    oid = ont["id"]

    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "Party", "display_name": "主体", "status": "accepted", "confidence": 1.0},
    )
    assert r.status_code == 200
    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "DraftThing", "display_name": "草稿", "status": "draft", "confidence": 0.7},
    )
    assert r.status_code == 200

    r = client.post(f"/api/v1/ontology/ontologies/{oid}/publish", json={"change_note": "v1"})
    assert r.status_code == 200, r.text
    ver = r.json()
    assert ver["version"] == 1
    keys = {ot["key"] for ot in ver["snapshot_json"]["object_types"]}
    assert "Party" in keys
    assert "DraftThing" not in keys

    # add another accepted then publish v2
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "LoanAccount", "display_name": "账户", "status": "accepted"},
    )
    r = client.post(f"/api/v1/ontology/ontologies/{oid}/publish", json={"change_note": "v2"})
    assert r.status_code == 200
    assert r.json()["version"] == 2

    r = client.post(f"/api/v1/ontology/ontologies/{oid}/rollback", json={"version": 1})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 3
    # after rollback, current elements should match v1 (Party only among accepted from snap)
    r = client.get(f"/api/v1/ontology/ontologies/{oid}/object-types")
    keys = {x["key"] for x in r.json()}
    assert "Party" in keys
    assert "LoanAccount" not in keys


def test_export_formats(client):
    ont = _create_ontology(client, "export-ont")
    oid = ont["id"]
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "Party", "display_name": "主体", "status": "accepted", "parent_key": None},
    )
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "Person", "display_name": "个人", "status": "accepted", "parent_key": "Party"},
    )
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/link-types",
        json={
            "key": "applies_for",
            "display_name": "申请",
            "from_key": "Party",
            "to_key": "Person",
            "status": "accepted",
        },
    )
    client.post(f"/api/v1/ontology/ontologies/{oid}/publish", json={"change_note": "export"})

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/export", params={"fmt": "json"})
    assert r.status_code == 200
    assert "object_types" in r.text

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/export", params={"fmt": "jsonld"})
    assert r.status_code == 200
    assert "@context" in r.text
    assert "rdfs:Class" in r.text

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/export", params={"fmt": "turtle"})
    assert r.status_code == 200
    ttl = r.text
    assert "@prefix" in ttl
    assert ttl.count("(") == ttl.count(")")
    assert "rdfs:Class" in ttl


def test_graph_data_focus_depth(client):
    ont = _create_ontology(client, "graph-ont")
    oid = ont["id"]
    for key in ("A", "B", "C", "D"):
        client.post(
            f"/api/v1/ontology/ontologies/{oid}/object-types",
            json={"key": key, "display_name": key, "status": "accepted"},
        )
    # A-B, B-C, C-D
    for fk, tk, k in (("A", "B", "ab"), ("B", "C", "bc"), ("C", "D", "cd")):
        client.post(
            f"/api/v1/ontology/ontologies/{oid}/link-types",
            json={
                "key": k,
                "display_name": k,
                "from_key": fk,
                "to_key": tk,
                "status": "accepted",
            },
        )

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/graph", params={"focus_key": "A", "depth": 1})
    assert r.status_code == 200
    keys = {n["key"] for n in r.json()["nodes"]}
    assert keys == {"A", "B"}

    r = client.get(f"/api/v1/ontology/ontologies/{oid}/graph", params={"focus_key": "A", "depth": 2})
    keys = {n["key"] for n in r.json()["nodes"]}
    assert keys == {"A", "B", "C"}


def test_cq_bfs_reachability(client, db_session):
    ont = _create_ontology(client, "cq-ont")
    oid = ont["id"]
    for key in ("Party", "LoanApplication", "LoanContract", "RiskEvent"):
        client.post(
            f"/api/v1/ontology/ontologies/{oid}/object-types",
            json={"key": key, "display_name": key, "status": "accepted"},
        )
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/link-types",
        json={
            "key": "applies_for",
            "display_name": "申请",
            "from_key": "Party",
            "to_key": "LoanApplication",
            "status": "accepted",
        },
    )
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/link-types",
        json={
            "key": "results_in",
            "display_name": "生成",
            "from_key": "LoanApplication",
            "to_key": "LoanContract",
            "status": "accepted",
        },
    )
    # mappings for Party / LoanApplication / LoanContract (not RiskEvent)
    from app.db.models.data_source_model import DataSource, DataSourceStatus, DataSourceType

    src = DataSource(
        name="cq-ds",
        source_type=DataSourceType.DORIS,
        host="127.0.0.1",
        port=9030,
        username="root",
        password="",
        database="tmp",
        status=DataSourceStatus.ONLINE,
    )
    db_session.add(src)
    db_session.commit()
    db_session.refresh(src)

    for key in ("Party", "LoanApplication", "LoanContract"):
        client.post(
            f"/api/v1/ontology/ontologies/{oid}/mappings",
            json={
                "element_type": "object_type",
                "element_key": key,
                "source_id": src.id,
                "database": "tmp",
                "table_name": key.lower(),
                "status": "accepted",
            },
        )

    # reachable CQ
    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/cqs",
        json={
            "question": "某客户申请对应的合约有哪些？",
            "category": "关系遍历",
            "related_keys": ["Party", "LoanContract"],
        },
    )
    assert r.status_code == 200
    cq_ok = r.json()["id"]

    # unreachable: Party → RiskEvent with no path
    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/cqs",
        json={
            "question": "客户的风险事件？",
            "related_keys": ["Party", "RiskEvent"],
        },
    )
    cq_fail = r.json()["id"]

    r = client.post(f"/api/v1/ontology/cqs/{cq_ok}/verify")
    assert r.status_code == 200
    assert r.json()["verify_status"] == "pass"

    r = client.post(f"/api/v1/ontology/cqs/{cq_fail}/verify")
    assert r.status_code == 200
    assert r.json()["verify_status"] == "fail"
    assert "可达" in (r.json()["verify_note"] or "") or "路径" in (r.json()["verify_note"] or "")

    # unit: BFS helper
    svc = OntologyCQService(db_session)
    ok, note = svc._bfs_reachable(oid, ["Party", "LoanContract"], depth=3)
    assert ok is True
    ok, note = svc._bfs_reachable(oid, ["Party", "RiskEvent"], depth=3)
    assert ok is False


def test_consumer_finance_fragment_shape():
    assert "object_types" in CONSUMER_FINANCE_FRAGMENT
    keys = {ot["key"] for ot in CONSUMER_FINANCE_FRAGMENT["object_types"]}
    for required in (
        "Party",
        "Person",
        "Organization",
        "LoanApplication",
        "LoanContract",
        "CreditProduct",
        "LoanAccount",
        "Transaction",
        "RepaymentBehavior",
        "RiskEvent",
        "Collateral",
        "AcquisitionChannel",
        "ScorecardModel",
        "RiskFeature",
    ):
        assert required in keys
    assert CONSUMER_FINANCE_FRAGMENT["link_types"]


def test_build_job_rules_mode(client, sync_bg, db_session):
    ont = _create_ontology(client, "build-ont")
    oid = ont["id"]
    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/build-jobs",
        json={
            "mode": "rules",
            "scope": {},
            "batch_size": 8,
            "reuse_domain_fragment": "consumer_finance",
        },
    )
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["status"] in ("succeeded", "running", "pending")
    # sync_bg runs immediately
    r = client.get(f"/api/v1/ontology/build-jobs/{job['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "succeeded"
    assert body["phase"] == "done"
    # fragment should have seeded classes
    r = client.get(f"/api/v1/ontology/ontologies/{oid}/object-types")
    keys = {x["key"] for x in r.json()}
    assert "Party" in keys or "LoanAccount" in keys


def test_review_accept_all_drafts(client):
    ont = _create_ontology(client, "review-all")
    oid = ont["id"]
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "A", "display_name": "A", "status": "draft", "confidence": 0.7},
    )
    client.post(
        f"/api/v1/ontology/ontologies/{oid}/object-types",
        json={"key": "B", "display_name": "B", "status": "draft", "confidence": 0.7},
    )
    r = client.post(
        f"/api/v1/ontology/ontologies/{oid}/review",
        json={"accept_all_drafts": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["updated"] >= 2
    rows = client.get(f"/api/v1/ontology/ontologies/{oid}/object-types").json()
    assert all(x["status"] == "accepted" for x in rows)
