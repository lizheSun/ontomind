"""Router-level integration tests for /api/v1/knowledge-base/*.

Covers libraries listing, CRUD each of the 4 sub-libs, doc upload+download,
grouped search, owner scoping.
"""
from __future__ import annotations

import io


API = "/api/v1/knowledge-base"


def test_list_libraries_returns_4_after_seed(client, auth_headers, kb_libraries):
    r = client.get(f"{API}/libraries", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    codes = [row["code"] for row in body["data"]]
    assert set(codes) == {"data_asset", "code_repo", "document", "experience"}


# ------------------------ data_assets CRUD ---------------------------
def test_data_assets_crud(client, auth_headers, kb_libraries):
    lib = kb_libraries["data_asset"]
    created = client.post(
        f"{API}/data-assets",
        json={"title_zh": "订单主表", "library_id": lib, "tags": ["trade"]},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    aid = created.json()["data"]["id"]

    listed = client.get(f"{API}/data-assets", headers=auth_headers).json()
    assert listed["total"] == 1

    got = client.get(f"{API}/data-assets/{aid}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["title_zh"] == "订单主表"

    upd = client.put(
        f"{API}/data-assets/{aid}", json={"title_zh": "订单主表 v2"}, headers=auth_headers
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["title_zh"] == "订单主表 v2"

    dele = client.delete(f"{API}/data-assets/{aid}", headers=auth_headers)
    assert dele.status_code == 200
    assert client.get(f"{API}/data-assets", headers=auth_headers).json()["total"] == 0


# ------------------------ code_repos CRUD ----------------------------
def test_code_repos_crud(client, auth_headers, kb_libraries):
    lib = kb_libraries["code_repo"]
    created = client.post(
        f"{API}/code-repos",
        json={
            "title_zh": "OntoMind",
            "repo_url": "git@example.com:me/o.git",
            "branch": "main",
            "language": "Python",
            "library_id": lib,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    cid = created.json()["data"]["id"]

    upd = client.put(
        f"{API}/code-repos/{cid}", json={"branch": "dev"}, headers=auth_headers
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["branch"] == "dev"

    assert client.delete(f"{API}/code-repos/{cid}", headers=auth_headers).status_code == 200


# ------------------------ experiences CRUD ---------------------------
def test_experiences_crud(client, auth_headers, kb_libraries):
    lib = kb_libraries["experience"]
    created = client.post(
        f"{API}/experiences",
        json={
            "title_zh": "定价异常处理",
            "scenario": "线上大促",
            "content_md": "# 步骤",
            "library_id": lib,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    eid = created.json()["data"]["id"]
    assert client.get(f"{API}/experiences", headers=auth_headers).json()["total"] == 1
    assert client.delete(f"{API}/experiences/{eid}", headers=auth_headers).status_code == 200


# ------------------------ documents upload + download ----------------
def test_documents_upload_download_roundtrip(
    client, auth_headers, kb_libraries, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    lib = kb_libraries["document"]
    contents = b"# Hello\nworld\n"
    files = {"file": ("hello.md", io.BytesIO(contents), "text/markdown")}
    data = {"title_zh": "测试文档", "library_id": str(lib), "description_md": "smoke"}
    up = client.post(
        f"{API}/documents/upload", files=files, data=data, headers=auth_headers
    )
    assert up.status_code == 201, up.text
    doc = up.json()["data"]
    assert doc["size_bytes"] == len(contents)

    r = client.get(f"{API}/documents/{doc['id']}/download", headers=auth_headers)
    assert r.status_code == 200
    assert r.content == contents


# ------------------------ search grouped -----------------------------
def test_search_grouped_returns_4_buckets(
    client, auth_headers, kb_libraries
):
    lib = kb_libraries["data_asset"]
    client.post(
        f"{API}/data-assets",
        json={"title_zh": "订单主表", "library_id": lib},
        headers=auth_headers,
    )
    r = client.get(f"{API}/search", params={"q": "订单"}, headers=auth_headers)
    assert r.status_code == 200
    grouped = r.json()["data"]
    assert set(grouped.keys()) >= {"data_asset", "code_repo", "document", "experience"}
    assert len(grouped["data_asset"]) == 1
    assert grouped["data_asset"][0]["title"] == "订单主表"


def test_search_rejects_empty_q_with_422(client, auth_headers, kb_libraries):
    r = client.get(f"{API}/search", params={"q": ""}, headers=auth_headers)
    assert r.status_code == 422


# ------------------------ owner scoping ------------------------------
def test_data_assets_owner_only_scopes_to_user(
    client, auth_headers, auth_headers2, kb_libraries
):
    lib = kb_libraries["data_asset"]
    client.post(
        f"{API}/data-assets",
        json={"title_zh": "user1's asset", "library_id": lib},
        headers=auth_headers,
    )

    r1 = client.get(
        f"{API}/data-assets", params={"owner_only": True}, headers=auth_headers
    ).json()
    assert r1["total"] == 1

    r2 = client.get(
        f"{API}/data-assets", params={"owner_only": True}, headers=auth_headers2
    ).json()
    assert r2["total"] == 0


# ------------------------ tags list ----------------------------------
def test_tags_endpoint_reflects_created_tags(
    client, auth_headers, kb_libraries
):
    lib = kb_libraries["data_asset"]
    client.post(
        f"{API}/data-assets",
        json={"title_zh": "t", "library_id": lib, "tags": ["alpha", "beta"]},
        headers=auth_headers,
    )
    r = client.get(f"{API}/tags", headers=auth_headers)
    assert r.status_code == 200
    names = {row["name"] for row in r.json()["data"]}
    assert {"alpha", "beta"}.issubset(names)


# ------------------------ get-by-id + 404 for each sub-lib -----------
def test_get_by_id_and_404_for_all_sublibs(client, auth_headers, kb_libraries):
    da_id = client.post(
        f"{API}/data-assets",
        json={"title_zh": "a", "library_id": kb_libraries["data_asset"]},
        headers=auth_headers,
    ).json()["data"]["id"]
    cr_id = client.post(
        f"{API}/code-repos",
        json={
            "title_zh": "r",
            "repo_url": "git@x:y.git",
            "library_id": kb_libraries["code_repo"],
        },
        headers=auth_headers,
    ).json()["data"]["id"]
    ex_id = client.post(
        f"{API}/experiences",
        json={
            "title_zh": "e",
            "content_md": "x",
            "library_id": kb_libraries["experience"],
        },
        headers=auth_headers,
    ).json()["data"]["id"]

    assert client.get(f"{API}/data-assets/{da_id}", headers=auth_headers).status_code == 200
    assert client.get(f"{API}/code-repos/{cr_id}", headers=auth_headers).status_code == 200
    assert client.get(f"{API}/experiences/{ex_id}", headers=auth_headers).status_code == 200

    for path, code in [
        ("data-assets", "KB_ASSET_NOT_FOUND"),
        ("code-repos", "KB_REPO_NOT_FOUND"),
        ("experiences", "KB_EXP_NOT_FOUND"),
    ]:
        r = client.get(f"{API}/{path}/99999", headers=auth_headers)
        assert r.status_code == 404
        assert r.json()["code"] == code


# ------------------------ delete doc DB-only -------------------------
def test_delete_document_removes_db_row(
    client, auth_headers, kb_libraries, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    lib = kb_libraries["document"]
    files = {"file": ("d.txt", io.BytesIO(b"data"), "text/plain")}
    data = {"title_zh": "d", "library_id": str(lib)}
    doc_id = client.post(
        f"{API}/documents/upload", files=files, data=data, headers=auth_headers
    ).json()["data"]["id"]

    r = client.delete(f"{API}/documents/{doc_id}", headers=auth_headers)
    assert r.status_code == 200
    got = client.get(f"{API}/documents/{doc_id}", headers=auth_headers)
    assert got.status_code == 404
    assert got.json()["code"] == "KB_DOC_NOT_FOUND"
