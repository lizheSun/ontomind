"""知识库服务层：4 个子库 CRUD + 文档上传/下载 + 标签池 + 跨库聚合搜索。

统一入口 KbService 对外只暴露 Pydantic Read schema，不泄漏 ORM row。
所有写操作都在 `_tx()` 上下文里完成：外层无事务 → `session.begin()`（顶层）；
外层已有事务（如上一次 SELECT 触发的 autobegin）→ `session.begin_nested()`
（SAVEPOINT），语义等价、无需要求调用方额外 commit。
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.kb_code_repo_model import KbCodeRepo
from app.db.models.kb_data_asset_model import KbDataAsset
from app.db.models.kb_document_model import KbDocument
from app.db.models.kb_experience_model import KbExperience
from app.db.models.kb_library_model import KbLibrary
from app.db.repositories.kb_code_repo_repo import KbCodeRepoRepository
from app.db.repositories.kb_data_asset_repo import KbDataAssetRepository
from app.db.repositories.kb_document_repo import KbDocumentRepository
from app.db.repositories.kb_experience_repo import KbExperienceRepository
from app.db.repositories.kb_library_repo import KbLibraryRepository
from app.db.repositories.kb_tag_repo import KbTagRepository
from app.schemas.kb_code_repo_schema import (
    KbCodeRepoCreate,
    KbCodeRepoRead,
    KbCodeRepoUpdate,
)
from app.schemas.kb_data_asset_schema import (
    KbDataAssetCreate,
    KbDataAssetRead,
    KbDataAssetUpdate,
)
from app.schemas.kb_document_schema import (
    KbDocumentMetaCreate,
    KbDocumentRead,
    KbDocumentUpdate,
)
from app.schemas.kb_experience_schema import (
    KbExperienceCreate,
    KbExperienceRead,
    KbExperienceUpdate,
)
from app.schemas.kb_library_schema import KbLibraryRead
from app.schemas.kb_search_schema import (
    KbSearchGrouped,
    KbSearchResult,
)
from app.schemas.kb_tag_schema import KbTagRead

_SUB_LIB_CODES = ("data_asset", "code_repo", "document", "experience")


class KbService:
    """知识库统一服务：4 子库 CRUD + 上传下载 + 标签池 + 聚合搜索。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.lib_repo = KbLibraryRepository(db)
        self.asset_repo = KbDataAssetRepository(db)
        self.repo_repo = KbCodeRepoRepository(db)
        self.doc_repo = KbDocumentRepository(db)
        self.exp_repo = KbExperienceRepository(db)
        self.tag_repo = KbTagRepository(db)

    @contextmanager
    def _tx(self) -> Iterator[None]:
        """事务上下文：顶层 begin 或 SAVEPOINT 嵌套，两种场景语义等价。"""
        if self.db.in_transaction():
            with self.db.begin_nested():
                yield
        else:
            with self.db.begin():
                yield

    # ------------------------------------------------------------------
    # Libraries (read-only)
    # ------------------------------------------------------------------
    def list_libraries(self) -> List[KbLibraryRead]:
        rows = self.lib_repo.list_ordered()
        return [KbLibraryRead.model_validate(r) for r in rows]

    def get_library_by_code(self, code: str) -> KbLibraryRead:
        row = self.lib_repo.get_by_code(code)
        if row is None:
            raise NotFoundException(
                message=f"library code={code} 不存在",
                code="KB_LIB_NOT_FOUND",
            )
        return KbLibraryRead.model_validate(row)

    # ------------------------------------------------------------------
    # Data assets
    # ------------------------------------------------------------------
    def list_data_assets(
        self,
        user_id: int,
        owner_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KbDataAssetRead]:
        if owner_only:
            rows = self.asset_repo.list_by_owner(user_id, skip=skip, limit=limit)
        else:
            rows = self.asset_repo.get_all(skip=skip, limit=limit)
        return [KbDataAssetRead.model_validate(r) for r in rows]

    def create_data_asset(
        self, payload: KbDataAssetCreate, user_id: int
    ) -> KbDataAssetRead:
        data = payload.model_dump()
        data["owner_user_id"] = user_id
        data["created_by_user_id"] = user_id
        with self._tx():
            self._ensure_library_id_matches(payload.library_id, "data_asset")
            self._register_tags(payload.tags)
            row = self.asset_repo.create(data)
        return KbDataAssetRead.model_validate(row)

    def update_data_asset(
        self, id: int, payload: KbDataAssetUpdate, user_id: int
    ) -> KbDataAssetRead:
        with self._tx():
            self._require_owned_asset(id, user_id)
            self._register_tags(payload.tags)
            row = self.asset_repo.update(id, payload.model_dump(exclude_unset=True))
        assert row is not None  # _require_owned_asset guarantees existence
        return KbDataAssetRead.model_validate(row)

    def delete_data_asset(self, id: int, user_id: int) -> None:
        with self._tx():
            self._require_owned_asset(id, user_id)
            self.asset_repo.delete(id)

    # ------------------------------------------------------------------
    # Code repos
    # ------------------------------------------------------------------
    def list_code_repos(
        self,
        user_id: int,
        owner_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KbCodeRepoRead]:
        if owner_only:
            rows = self.repo_repo.list_by_owner(user_id, skip=skip, limit=limit)
        else:
            rows = self.repo_repo.get_all(skip=skip, limit=limit)
        return [KbCodeRepoRead.model_validate(r) for r in rows]

    def create_code_repo(
        self, payload: KbCodeRepoCreate, user_id: int
    ) -> KbCodeRepoRead:
        data = payload.model_dump()
        data["owner_user_id"] = user_id
        data["created_by_user_id"] = user_id
        with self._tx():
            self._ensure_library_id_matches(payload.library_id, "code_repo")
            self._register_tags(payload.tags)
            row = self.repo_repo.create(data)
        return KbCodeRepoRead.model_validate(row)

    def update_code_repo(
        self, id: int, payload: KbCodeRepoUpdate, user_id: int
    ) -> KbCodeRepoRead:
        with self._tx():
            self._require_owned_repo(id, user_id)
            self._register_tags(payload.tags)
            row = self.repo_repo.update(id, payload.model_dump(exclude_unset=True))
        assert row is not None
        return KbCodeRepoRead.model_validate(row)

    def delete_code_repo(self, id: int, user_id: int) -> None:
        with self._tx():
            self._require_owned_repo(id, user_id)
            self.repo_repo.delete(id)

    # ------------------------------------------------------------------
    # Documents (metadata CRUD; upload/download below)
    # ------------------------------------------------------------------
    def list_documents(
        self,
        user_id: int,
        owner_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KbDocumentRead]:
        if owner_only:
            rows = self.doc_repo.list_by_owner(user_id, skip=skip, limit=limit)
        else:
            rows = self.doc_repo.get_all(skip=skip, limit=limit)
        return [KbDocumentRead.model_validate(r) for r in rows]

    def update_document(
        self, id: int, payload: KbDocumentUpdate, user_id: int
    ) -> KbDocumentRead:
        with self._tx():
            self._require_owned_doc(id, user_id)
            self._register_tags(payload.tags)
            row = self.doc_repo.update(id, payload.model_dump(exclude_unset=True))
        assert row is not None
        return KbDocumentRead.model_validate(row)

    def delete_document(self, id: int, user_id: int) -> None:
        with self._tx():
            self._require_owned_doc(id, user_id)
            self.doc_repo.delete(id)

    async def upload_document(
        self,
        *,
        file: UploadFile,
        meta: KbDocumentMetaCreate,
        user_id: int,
    ) -> KbDocumentRead:
        """上传文档：校验子库、读取字节、注册标签、落库+落盘。"""
        contents = await file.read()
        if not contents:
            raise BusinessException(
                code="KB_DOC_EMPTY",
                message="上传文件为空",
                status_code=400,
            )
        with self._tx():
            self._ensure_library_id_matches(meta.library_id, "document")
            self._register_tags(meta.tags)
            row = self.doc_repo.create_with_file(
                filename=file.filename or "unnamed",
                mime_type=file.content_type or "application/octet-stream",
                contents=contents,
                title_zh=meta.title_zh,
                library_id=meta.library_id,
                owner_user_id=user_id,
                created_by_user_id=user_id,
                description_md=meta.description_md,
                tags=meta.tags,
            )
        return KbDocumentRead.model_validate(row)

    def get_document_bytes(self, id: int) -> Tuple[KbDocument, bytes]:
        """返回 (row, bytes)；路由包装为 FileResponse。"""
        row = self.doc_repo.get_by_id(id)
        if row is None:
            raise NotFoundException(
                message=f"document id={id} 不存在",
                code="KB_DOC_NOT_FOUND",
            )
        abs_path = self.doc_repo.absolute_path(row)
        if not abs_path.is_file():
            raise NotFoundException(
                message=f"物理文件不存在：{row.storage_path}",
                code="KB_DOC_FILE_MISSING",
            )
        return row, abs_path.read_bytes()

    # ------------------------------------------------------------------
    # Experiences
    # ------------------------------------------------------------------
    def list_experiences(
        self,
        user_id: int,
        owner_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KbExperienceRead]:
        if owner_only:
            rows = self.exp_repo.list_by_owner(user_id, skip=skip, limit=limit)
        else:
            rows = self.exp_repo.get_all(skip=skip, limit=limit)
        return [KbExperienceRead.model_validate(r) for r in rows]

    def create_experience(
        self, payload: KbExperienceCreate, user_id: int
    ) -> KbExperienceRead:
        data = payload.model_dump()
        data["owner_user_id"] = user_id
        data["created_by_user_id"] = user_id
        with self._tx():
            self._ensure_library_id_matches(payload.library_id, "experience")
            self._register_tags(payload.tags)
            row = self.exp_repo.create(data)
        return KbExperienceRead.model_validate(row)

    def update_experience(
        self, id: int, payload: KbExperienceUpdate, user_id: int
    ) -> KbExperienceRead:
        with self._tx():
            self._require_owned_exp(id, user_id)
            self._register_tags(payload.tags)
            row = self.exp_repo.update(id, payload.model_dump(exclude_unset=True))
        assert row is not None
        return KbExperienceRead.model_validate(row)

    def delete_experience(self, id: int, user_id: int) -> None:
        with self._tx():
            self._require_owned_exp(id, user_id)
            self.exp_repo.delete(id)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def list_tags(self) -> List[KbTagRead]:
        return [KbTagRead.model_validate(r) for r in self.tag_repo.list_all()]

    # ------------------------------------------------------------------
    # Cross-lib search
    # ------------------------------------------------------------------
    def search_all(
        self,
        *,
        q: str,
        library_code: Optional[str] = None,
        limit: int = 20,
    ) -> KbSearchGrouped:
        grouped = KbSearchGrouped()
        if q is None or not q.strip():
            return grouped
        q_stripped = q.strip()
        target_codes = (
            {library_code} if library_code is not None else set(_SUB_LIB_CODES)
        )
        target_codes = target_codes.intersection(_SUB_LIB_CODES)

        if "data_asset" in target_codes:
            grouped.data_asset = [
                KbSearchResult(
                    library_code="data_asset",
                    id=r.id,
                    title=r.title_zh,
                    snippet=(r.description_md[:120] if r.description_md else None),
                )
                for r in self.asset_repo.search_like(q_stripped, limit=limit)
            ]
        if "code_repo" in target_codes:
            grouped.code_repo = [
                KbSearchResult(
                    library_code="code_repo",
                    id=r.id,
                    title=r.title_zh,
                    snippet=r.repo_url,
                )
                for r in self.repo_repo.search_like(q_stripped, limit=limit)
            ]
        if "document" in target_codes:
            grouped.document = [
                KbSearchResult(
                    library_code="document",
                    id=r.id,
                    title=r.title_zh,
                    snippet=r.filename,
                )
                for r in self.doc_repo.search_like(q_stripped, limit=limit)
            ]
        if "experience" in target_codes:
            grouped.experience = [
                KbSearchResult(
                    library_code="experience",
                    id=r.id,
                    title=r.title_zh,
                    snippet=(
                        r.scenario
                        if r.scenario
                        else (r.content_md[:120] if r.content_md else None)
                    ),
                )
                for r in self.exp_repo.search_like(q_stripped, limit=limit)
            ]
        return grouped

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_library_id_matches(
        self, library_id: int, expected_code: str
    ) -> None:
        row: Optional[KbLibrary] = (
            self.db.query(KbLibrary).filter(KbLibrary.id == library_id).first()
        )
        if row is None:
            raise BusinessException(
                code="KB_LIB_INVALID",
                message=f"library_id={library_id} 不存在",
                status_code=400,
            )
        if row.code != expected_code:
            raise BusinessException(
                code="KB_LIB_MISMATCH",
                message=(
                    f"library_id={library_id} 属于 {row.code}，"
                    f"不匹配 {expected_code}"
                ),
                status_code=400,
            )

    def _register_tags(self, tags: Optional[List[str]]) -> None:
        """幂等 upsert 标签池；调用方已在外层 `with self.db.begin():` 中。"""
        if not tags:
            return
        names = [t for t in tags if isinstance(t, str) and t.strip()]
        if not names:
            return
        self.tag_repo.upsert_names(names)

    def _require_owned_asset(self, id: int, user_id: int) -> KbDataAsset:
        row = self.asset_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                message=f"data_asset id={id} 不存在或无权限",
                code="KB_ASSET_NOT_FOUND",
            )
        return row

    def _require_owned_repo(self, id: int, user_id: int) -> KbCodeRepo:
        row = self.repo_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                message=f"code_repo id={id} 不存在或无权限",
                code="KB_REPO_NOT_FOUND",
            )
        return row

    def _require_owned_doc(self, id: int, user_id: int) -> KbDocument:
        row = self.doc_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                message=f"document id={id} 不存在或无权限",
                code="KB_DOC_NOT_FOUND",
            )
        return row

    def _require_owned_exp(self, id: int, user_id: int) -> KbExperience:
        row = self.exp_repo.get_by_id(id)
        if row is None or row.owner_user_id != user_id:
            raise NotFoundException(
                message=f"experience id={id} 不存在或无权限",
                code="KB_EXP_NOT_FOUND",
            )
        return row


__all__ = ["KbService"]
