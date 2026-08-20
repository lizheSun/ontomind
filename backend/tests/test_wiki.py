"""Wiki 知识库测试."""
from __future__ import annotations


def test_wiki_space_and_document_lifecycle(client):
    r = client.get("/api/v1/wiki/spaces")
    assert r.status_code == 200, r.text
    spaces = r.json()
    assert any(s["slug"] == "default" for s in spaces)
    space_id = next(s["id"] for s in spaces if s["slug"] == "default")

    r = client.post(
        "/api/v1/wiki/documents",
        json={
            "space_id": space_id,
            "title": "客户术语",
            "content_md": "# 客户\n\n- **客户**：申请贷款的个人或机构\n",
            "source_type": "manual",
            "tags": ["消金"],
            "status": "published",
        },
    )
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["current_version"] == 1
    doc_id = doc["id"]

    r = client.put(
        f"/api/v1/wiki/documents/{doc_id}",
        json={"content_md": "# 客户\n\n更新后的定义\n", "change_note": "修订"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["current_version"] == 2

    r = client.get(f"/api/v1/wiki/documents/{doc_id}/versions")
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) >= 2

    r = client.post(f"/api/v1/wiki/documents/{doc_id}/rollback", json={"version": 1})
    assert r.status_code == 200, r.text
    assert r.json()["current_version"] == 3
    assert "客户" in r.json()["content_md"]

    r = client.post(
        "/api/v1/wiki/import",
        json={"source_type": "paste", "title": "导入样例", "content_md": "## Hello\n\nworld"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "导入样例"


def test_wiki_fetch_url_rejects_private(client):
    for url in (
        "http://127.0.0.1/x",
        "http://localhost/x",
        "http://192.168.1.1/x",
        "http://10.0.0.1/x",
        "ftp://example.com/x",
    ):
        r = client.post("/api/v1/wiki/fetch-url", json={"url": url})
        assert r.status_code in (400, 403), f"{url} → {r.status_code} {r.text}"


def test_wiki_space_crud(client):
    r = client.post(
        "/api/v1/wiki/spaces",
        json={"name": "风控", "slug": "risk", "description": "风险域"},
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    r = client.put(f"/api/v1/wiki/spaces/{sid}", json={"description": "更新"})
    assert r.status_code == 200
    assert r.json()["description"] == "更新"
    r = client.delete(f"/api/v1/wiki/spaces/{sid}")
    assert r.status_code == 200
