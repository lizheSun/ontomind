"""KbService 服务层测试：库列表、CRUD + owner ACL、上传下载、跨库搜索。"""
from __future__ import annotations

from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile

from app.core.exceptions import BusinessException, NotFoundException
from app.schemas.kb_code_repo_schema import KbCodeRepoCreate, KbCodeRepoUpdate
from app.schemas.kb_data_asset_schema import (
    KbDataAssetCreate,
    KbDataAssetUpdate,
)
from app.schemas.kb_document_schema import KbDocumentMetaCreate
from app.schemas.kb_experience_schema import KbExperienceCreate
from app.services.kb_service import KbService


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _make_upload(name: str, mime: str, contents: bytes) -> UploadFile:
    return UploadFile(
        filename=name,
        file=BytesIO(contents),
        headers=Headers({"content-type": mime}),
    )


# ----------------------------------------------------------------------
# 1. Libraries list
# ----------------------------------------------------------------------
def test_list_libraries(db, library_ids):
    svc = KbService(db)
    libs = svc.list_libraries()
    codes = [row.code for row in libs]
    assert codes == ["data_asset", "code_repo", "document", "experience"]


# ----------------------------------------------------------------------
# 2. create_data_asset registers tags
# ----------------------------------------------------------------------
def test_create_data_asset_registers_tags(db, library_ids, user_id):
    svc = KbService(db)
    payload = KbDataAssetCreate(
        title_zh="订单主表",
        title_en="orders_main",
        domain="trade",
        description_md="核心订单表",
        library_id=library_ids["data_asset"],
        tags=["trade", "hot"],
    )
    row = svc.create_data_asset(payload, user_id=user_id)
    assert row.id and row.owner_user_id == user_id
    tag_names = {t.name for t in svc.list_tags()}
    assert {"trade", "hot"}.issubset(tag_names)


# ----------------------------------------------------------------------
# 3. create_data_asset rejects wrong library code
# ----------------------------------------------------------------------
def test_create_data_asset_rejects_wrong_library_code(db, library_ids, user_id):
    svc = KbService(db)
    payload = KbDataAssetCreate(
        title_zh="标题",
        library_id=library_ids["code_repo"],  # 错的库
    )
    with pytest.raises(BusinessException) as exc:
        svc.create_data_asset(payload, user_id=user_id)
    assert exc.value.code == "KB_LIB_MISMATCH"
    assert exc.value.status_code == 400


# ----------------------------------------------------------------------
# 4. update_data_asset owner ACL
# ----------------------------------------------------------------------
def test_update_data_asset_owner_only(db, library_ids, user_id, other_user_id):
    svc = KbService(db)
    row = svc.create_data_asset(
        KbDataAssetCreate(
            title_zh="订单主表",
            library_id=library_ids["data_asset"],
        ),
        user_id=user_id,
    )
    with pytest.raises(NotFoundException) as exc:
        svc.update_data_asset(
            row.id,
            KbDataAssetUpdate(title_zh="改名"),
            user_id=other_user_id,
        )
    assert exc.value.code == "KB_ASSET_NOT_FOUND"


# ----------------------------------------------------------------------
# 5. delete_data_asset owner ACL
# ----------------------------------------------------------------------
def test_delete_data_asset_owner_only(db, library_ids, user_id, other_user_id):
    svc = KbService(db)
    row = svc.create_data_asset(
        KbDataAssetCreate(
            title_zh="订单主表",
            library_id=library_ids["data_asset"],
        ),
        user_id=user_id,
    )
    with pytest.raises(NotFoundException) as exc:
        svc.delete_data_asset(row.id, user_id=other_user_id)
    assert exc.value.code == "KB_ASSET_NOT_FOUND"


# ----------------------------------------------------------------------
# 6. code_repo CRUD smoke
# ----------------------------------------------------------------------
def test_code_repo_crud_smoke(db, library_ids, user_id):
    svc = KbService(db)
    row = svc.create_code_repo(
        KbCodeRepoCreate(
            title_zh="OntoMind",
            repo_url="git@example.com:me/ontomind.git",
            branch="main",
            language="Python",
            library_id=library_ids["code_repo"],
        ),
        user_id=user_id,
    )
    listed = svc.list_code_repos(user_id=user_id, owner_only=True)
    assert len(listed) == 1 and listed[0].id == row.id

    updated = svc.update_code_repo(
        row.id,
        KbCodeRepoUpdate(branch="dev"),
        user_id=user_id,
    )
    assert updated.branch == "dev"

    svc.delete_code_repo(row.id, user_id=user_id)
    assert svc.list_code_repos(user_id=user_id, owner_only=True) == []


# ----------------------------------------------------------------------
# 7. Document upload persists row + bytes (async)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_upload_persists_row_and_bytes(
    db, library_ids, user_id, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    svc = KbService(db)
    contents = b"# Hello\nworld\n"
    upload = _make_upload("hello.md", "text/markdown", contents)
    meta = KbDocumentMetaCreate(
        title_zh="测试文档",
        library_id=library_ids["document"],
        description_md="smoke",
        tags=["md"],
    )
    row = await svc.upload_document(file=upload, meta=meta, user_id=user_id)
    assert row.size_bytes == len(contents)
    assert row.filename == "hello.md"
    # Readback
    _doc_row, blob = svc.get_document_bytes(row.id)
    assert blob == contents


# ----------------------------------------------------------------------
# 8. Document upload rejects empty payload
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_upload_rejects_empty(
    db, library_ids, user_id, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    svc = KbService(db)
    upload = _make_upload("empty.txt", "text/plain", b"")
    meta = KbDocumentMetaCreate(
        title_zh="空",
        library_id=library_ids["document"],
    )
    with pytest.raises(BusinessException) as exc:
        await svc.upload_document(file=upload, meta=meta, user_id=user_id)
    assert exc.value.code == "KB_DOC_EMPTY"
    assert exc.value.status_code == 400


# ----------------------------------------------------------------------
# 9. Experience CRUD smoke
# ----------------------------------------------------------------------
def test_experience_crud_smoke(db, library_ids, user_id):
    svc = KbService(db)
    row = svc.create_experience(
        KbExperienceCreate(
            title_zh="定价异常处理",
            scenario="线上大促",
            content_md="# 步骤",
            outcome="P0 恢复",
            tags=["prod"],
            library_id=library_ids["experience"],
        ),
        user_id=user_id,
    )
    listed = svc.list_experiences(user_id=user_id, owner_only=True)
    assert len(listed) == 1 and listed[0].id == row.id


# ----------------------------------------------------------------------
# 10. Cross-lib search grouped + library_code filter
# ----------------------------------------------------------------------
def test_search_all_grouped(db, library_ids, user_id):
    svc = KbService(db)
    svc.create_data_asset(
        KbDataAssetCreate(
            title_zh="订单主表",
            description_md="核心订单",
            library_id=library_ids["data_asset"],
        ),
        user_id=user_id,
    )
    svc.create_code_repo(
        KbCodeRepoCreate(
            title_zh="订单服务",
            repo_url="git@example.com:me/order.git",
            branch="main",
            library_id=library_ids["code_repo"],
        ),
        user_id=user_id,
    )
    # Document via upload (uses tmp_path to avoid touching real UPLOAD_DIR)
    import asyncio
    import tempfile
    from app.core.config import settings as _settings

    original = _settings.UPLOAD_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            _settings.UPLOAD_DIR = td
            asyncio.run(
                svc.upload_document(
                    file=_make_upload("订单流程.md", "text/markdown", b"content"),
                    meta=KbDocumentMetaCreate(
                        title_zh="订单流程手册",
                        library_id=library_ids["document"],
                    ),
                    user_id=user_id,
                )
            )
    finally:
        _settings.UPLOAD_DIR = original

    svc.create_experience(
        KbExperienceCreate(
            title_zh="订单降级预案",
            scenario="订单峰值",
            content_md="按用户等级降级",
            library_id=library_ids["experience"],
        ),
        user_id=user_id,
    )

    grouped = svc.search_all(q="订单")
    assert len(grouped.data_asset) == 1
    assert grouped.data_asset[0].library_code == "data_asset"
    assert grouped.data_asset[0].title == "订单主表"
    assert len(grouped.code_repo) == 1
    assert grouped.code_repo[0].library_code == "code_repo"
    assert grouped.code_repo[0].snippet == "git@example.com:me/order.git"
    assert len(grouped.document) == 1
    assert grouped.document[0].library_code == "document"
    assert grouped.document[0].snippet == "订单流程.md"
    assert len(grouped.experience) == 1
    assert grouped.experience[0].library_code == "experience"
    assert grouped.experience[0].snippet == "订单峰值"

    narrow = svc.search_all(q="订单", library_code="data_asset")
    assert len(narrow.data_asset) == 1
    assert narrow.code_repo == []
    assert narrow.document == []
    assert narrow.experience == []


# ----------------------------------------------------------------------
# 11. search_all empty / whitespace query
# ----------------------------------------------------------------------
def test_search_all_empty_query_returns_empty(db, library_ids, user_id):
    svc = KbService(db)
    svc.create_data_asset(
        KbDataAssetCreate(
            title_zh="订单主表",
            library_id=library_ids["data_asset"],
        ),
        user_id=user_id,
    )
    grouped = svc.search_all(q="   ")
    assert grouped.data_asset == []
    assert grouped.code_repo == []
    assert grouped.document == []
    assert grouped.experience == []
