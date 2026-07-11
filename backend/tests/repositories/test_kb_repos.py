"""kb_* 仓储层烟雾测试：CRUD + search_like + create_with_file。"""
from __future__ import annotations

import pytest

from app.db.models.kb_library_model import KbLibrary
from app.db.models.user_model import User
from app.db.repositories.kb_code_repo_repo import KbCodeRepoRepository
from app.db.repositories.kb_data_asset_repo import KbDataAssetRepository
from app.db.repositories.kb_document_repo import KbDocumentRepository
from app.db.repositories.kb_experience_repo import KbExperienceRepository
from app.db.repositories.kb_library_repo import KbLibraryRepository
from app.db.repositories.kb_tag_repo import KbTagRepository


@pytest.fixture
def user_id(db):
    u = User(
        username="bob",
        email="b@c.d",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )
    db.add(u)
    db.flush()
    return u.id


@pytest.fixture
def library_id(db):
    lib = KbLibrary(
        code="data_asset",
        name_zh="数据资产",
        icon="DatabaseOutlined",
        description="按业务域整理",
        sort_order=1,
    )
    db.add(lib)
    db.flush()
    return lib.id


def test_kb_library_ordered_and_by_code(db, library_id):
    repo = KbLibraryRepository(db)
    db.add_all(
        [
            KbLibrary(
                code="code_repo",
                name_zh="代码库",
                icon="GithubOutlined",
                description="",
                sort_order=2,
            ),
            KbLibrary(
                code="document",
                name_zh="文档库",
                icon="FileTextOutlined",
                description="",
                sort_order=3,
            ),
        ]
    )
    db.flush()
    ordered = repo.list_ordered()
    assert [r.code for r in ordered] == ["data_asset", "code_repo", "document"]
    hit = repo.get_by_code("code_repo")
    assert hit is not None and hit.name_zh == "代码库"
    assert repo.get_by_code("nope") is None


def test_kb_data_asset_crud_search(db, user_id, library_id):
    repo = KbDataAssetRepository(db)
    row = repo.create(
        {
            "library_id": library_id,
            "title_zh": "订单主表",
            "title_en": "orders_main",
            "domain": "trade",
            "owner_user_id": user_id,
            "description_md": "核心订单表",
            "created_by_user_id": user_id,
            "tags": ["hot"],
        }
    )
    assert row.id
    hits = repo.search_like("订单")
    assert hits and hits[0].id == row.id
    hits2 = repo.search_like("orders_main")
    assert hits2 and hits2[0].id == row.id
    assert len(repo.list_by_owner(user_id=user_id)) == 1


def test_kb_code_repo_crud_search(db, user_id, library_id):
    repo = KbCodeRepoRepository(db)
    row = repo.create(
        {
            "library_id": library_id,
            "title_zh": "本项目",
            "repo_url": "git@example.com:me/ontomind.git",
            "branch": "main",
            "language": "Python",
            "description_md": "OntoMind backend",
            "owner_user_id": user_id,
            "created_by_user_id": user_id,
        }
    )
    hits = repo.search_like("OntoMind")
    assert hits and hits[0].id == row.id
    assert len(repo.list_by_owner(user_id=user_id)) == 1


def test_kb_document_create_with_file(db, user_id, library_id, monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    repo = KbDocumentRepository(db)
    contents = b"# Hello\nworld\n"
    row = repo.create_with_file(
        filename="hello.md",
        mime_type="text/markdown",
        contents=contents,
        title_zh="测试文档",
        library_id=library_id,
        owner_user_id=user_id,
        created_by_user_id=user_id,
        description_md="smoke doc",
    )
    assert row.size_bytes == len(contents)
    assert row.filename == "hello.md"
    abs_path = repo.absolute_path(row)
    assert abs_path.is_file()
    assert abs_path.read_bytes() == contents
    # storage_path is relative to UPLOAD_DIR
    assert not row.storage_path.startswith(str(tmp_path))
    # search across cols
    assert repo.search_like("hello")[0].id == row.id


def test_kb_experience_crud_search(db, user_id, library_id):
    repo = KbExperienceRepository(db)
    row = repo.create(
        {
            "library_id": library_id,
            "title_zh": "定价异常处理",
            "scenario": "线上大促限流",
            "content_md": "细则……",
            "outcome": "P0 恢复",
            "tags": ["prod"],
            "owner_user_id": user_id,
            "created_by_user_id": user_id,
        }
    )
    hits = repo.search_like("限流")
    assert hits and hits[0].id == row.id


def test_kb_tag_upsert(db):
    repo = KbTagRepository(db)
    first = repo.upsert_names(["prod", "trade"])
    assert {t.name for t in first} == {"prod", "trade"}
    repo.upsert_names(["prod", "growth"])  # prod stays, growth new
    all_tags = {t.name for t in repo.list_all()}
    assert all_tags == {"prod", "trade", "growth"}
    assert repo.get_by_name("prod") is not None
    assert repo.get_by_name("nope") is None
