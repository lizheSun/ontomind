"""Wiki 知识库服务."""
from __future__ import annotations

import ipaddress
import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, ConflictException, NotFoundException, PermissionException
from app.db.models.wiki_model import (
    WikiDocStatus,
    WikiDocument,
    WikiDocumentVersion,
    WikiSourceType,
    WikiSpace,
)
from app.db.repositories.wiki_repo import WikiDocumentRepository, WikiSpaceRepository
from app.schemas.wiki_schema import (
    WikiDocumentCreate,
    WikiDocumentUpdate,
    WikiImportRequest,
    WikiSpaceCreate,
    WikiSpaceUpdate,
)

_SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def _slugify(text: str) -> str:
    s = (text or "").strip().lower().replace(" ", "-")
    s = _SLUG_RE.sub("-", s).strip("-")
    return (s or "doc")[:120]


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


class WikiService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.spaces = WikiSpaceRepository(db)
        self.docs = WikiDocumentRepository(db)

    def ensure_seed_space(self) -> None:
        if self.spaces.get_space_by_slug("default"):
            return
        self.spaces.add_space(
            WikiSpace(name="默认空间", slug="default", description="系统默认 Wiki 空间", icon="book", sort_order=0)
        )
        self.db.commit()

    def _space_resp(self, row: WikiSpace) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "icon": row.icon,
            "sort_order": row.sort_order or 0,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _doc_list_item(self, row: WikiDocument) -> dict[str, Any]:
        return {
            "id": row.id,
            "space_id": row.space_id,
            "parent_id": row.parent_id,
            "title": row.title,
            "slug": row.slug,
            "source_type": _enum_val(row.source_type),
            "source_url": row.source_url,
            "tags": row.tags_json or [],
            "status": _enum_val(row.status),
            "current_version": row.current_version or 1,
            "word_count": row.word_count or 0,
            "author_user_id": row.author_user_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _doc_resp(self, row: WikiDocument) -> dict[str, Any]:
        data = self._doc_list_item(row)
        data["content_md"] = row.content_md or ""
        data["source_meta"] = row.source_meta_json
        return data

    def list_spaces(self) -> list[dict[str, Any]]:
        self.ensure_seed_space()
        return [self._space_resp(r) for r in self.spaces.list_spaces()]

    def create_space(self, data: WikiSpaceCreate) -> dict[str, Any]:
        slug = _slugify(data.slug)
        if self.spaces.get_space_by_slug(slug):
            raise ConflictException(f"空间 slug 已存在: {slug}")
        row = WikiSpace(
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            icon=data.icon,
            sort_order=data.sort_order or 0,
        )
        self.spaces.add_space(row)
        self.db.commit()
        self.db.refresh(row)
        return self._space_resp(row)

    def get_space(self, space_id: int) -> dict[str, Any]:
        row = self.spaces.get_space(space_id)
        if not row:
            raise NotFoundException(f"空间不存在: {space_id}")
        return self._space_resp(row)

    def update_space(self, space_id: int, data: WikiSpaceUpdate) -> dict[str, Any]:
        row = self.spaces.get_space(space_id)
        if not row:
            raise NotFoundException(f"空间不存在: {space_id}")
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._space_resp(row)

    def delete_space(self, space_id: int) -> None:
        row = self.spaces.get_space(space_id)
        if not row:
            raise NotFoundException(f"空间不存在: {space_id}")
        if row.slug == "default":
            raise BusinessException("默认空间不可删除", code="WIKI_DEFAULT_SPACE")
        self.spaces.delete_space(row)
        self.db.commit()

    def list_documents(
        self,
        *,
        space_id: Optional[int] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = self.docs.list_documents(
            space_id=space_id, keyword=keyword, tag=tag, status=status, limit=limit, offset=offset
        )
        return [self._doc_list_item(r) for r in rows]

    def get_document(self, doc_id: int) -> dict[str, Any]:
        row = self.docs.get_document(doc_id)
        if not row:
            raise NotFoundException(f"文档不存在: {doc_id}")
        return self._doc_resp(row)

    def create_document(self, data: WikiDocumentCreate, user_id: Optional[int]) -> dict[str, Any]:
        if not self.spaces.get_space(data.space_id):
            raise NotFoundException(f"空间不存在: {data.space_id}")
        content = data.content_md or ""
        title = data.title.strip()
        slug = _slugify(data.slug or title)
        row = WikiDocument(
            space_id=data.space_id,
            parent_id=data.parent_id,
            title=title,
            slug=slug,
            content_md=content,
            source_type=WikiSourceType(data.source_type),
            source_url=data.source_url,
            source_meta_json=data.source_meta,
            tags_json=data.tags or [],
            status=WikiDocStatus(data.status),
            current_version=1,
            word_count=len(content),
            author_user_id=user_id,
        )
        self.docs.add_document(row)
        self.docs.add_version(
            WikiDocumentVersion(
                document_id=row.id,
                version=1,
                content_md=content,
                title=title,
                change_note="初始版本",
                author_user_id=user_id,
            )
        )
        self.db.commit()
        self.db.refresh(row)
        return self._doc_resp(row)

    def update_document(self, doc_id: int, data: WikiDocumentUpdate, user_id: Optional[int]) -> dict[str, Any]:
        row = self.docs.get_document(doc_id)
        if not row:
            raise NotFoundException(f"文档不存在: {doc_id}")
        payload = data.model_dump(exclude_unset=True)
        change_note = payload.pop("change_note", None)
        content_changed = "content_md" in payload and payload["content_md"] != (row.content_md or "")
        title_changed = "title" in payload and payload["title"] and payload["title"] != row.title

        if "title" in payload and payload["title"]:
            row.title = payload["title"].strip()
        if "content_md" in payload and payload["content_md"] is not None:
            row.content_md = payload["content_md"]
            row.word_count = len(row.content_md or "")
        if "parent_id" in payload:
            row.parent_id = payload["parent_id"]
        if "source_url" in payload:
            row.source_url = payload["source_url"]
        if "source_meta" in payload:
            row.source_meta_json = payload["source_meta"]
        if "tags" in payload:
            row.tags_json = payload["tags"] or []
        if "status" in payload and payload["status"]:
            row.status = WikiDocStatus(payload["status"])

        if content_changed or title_changed:
            row.current_version = int(row.current_version or 1) + 1
            self.docs.add_version(
                WikiDocumentVersion(
                    document_id=row.id,
                    version=row.current_version,
                    content_md=row.content_md or "",
                    title=row.title,
                    change_note=change_note or "更新",
                    author_user_id=user_id,
                )
            )

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._doc_resp(row)

    def delete_document(self, doc_id: int) -> None:
        row = self.docs.get_document(doc_id)
        if not row:
            raise NotFoundException(f"文档不存在: {doc_id}")
        self.docs.delete_document(row)
        self.db.commit()

    def list_versions(self, doc_id: int) -> list[dict[str, Any]]:
        if not self.docs.get_document(doc_id):
            raise NotFoundException(f"文档不存在: {doc_id}")
        rows = self.docs.list_versions(doc_id)
        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "version": r.version,
                "title": r.title,
                "content_md": r.content_md,
                "change_note": r.change_note,
                "author_user_id": r.author_user_id,
                "created_at": r.created_at,
            }
            for r in rows
        ]

    def rollback_document(self, doc_id: int, version: int, user_id: Optional[int]) -> dict[str, Any]:
        row = self.docs.get_document(doc_id)
        if not row:
            raise NotFoundException(f"文档不存在: {doc_id}")
        snap = self.docs.get_version(doc_id, version)
        if not snap:
            raise NotFoundException(f"版本不存在: v{version}")
        row.title = snap.title
        row.content_md = snap.content_md
        row.word_count = len(snap.content_md or "")
        row.current_version = int(row.current_version or 1) + 1
        self.docs.add_version(
            WikiDocumentVersion(
                document_id=row.id,
                version=row.current_version,
                content_md=row.content_md or "",
                title=row.title,
                change_note=f"回滚自 v{version}",
                author_user_id=user_id,
            )
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._doc_resp(row)

    def import_document(self, data: WikiImportRequest, user_id: Optional[int]) -> dict[str, Any]:
        self.ensure_seed_space()
        space_id = data.space_id
        if space_id is None:
            default = self.spaces.get_space_by_slug("default")
            space_id = default.id if default else None
        if space_id is None:
            raise BusinessException("无可用 Wiki 空间", code="WIKI_NO_SPACE")
        title = (data.title or "").strip()
        if not title:
            for line in (data.content_md or "").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            title = title or "未命名文档"
        return self.create_document(
            WikiDocumentCreate(
                space_id=space_id,
                parent_id=data.parent_id,
                title=title,
                content_md=data.content_md,
                source_type=data.source_type,
                source_url=data.source_url,
                source_meta=data.source_meta,
                tags=data.tags,
                status=data.status,
            ),
            user_id,
        )

    def fetch_url(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise BusinessException("仅允许 http/https URL", code="WIKI_URL_SCHEME")
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
            raise PermissionException("禁止访问内网地址", code="WIKI_URL_PRIVATE")
        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise PermissionException("禁止访问内网地址", code="WIKI_URL_PRIVATE")
        except ValueError:
            pass
        if host.startswith("10.") or host.startswith("192.168.") or host.startswith("127.") or host.startswith("169.254."):
            raise PermissionException("禁止访问内网地址", code="WIKI_URL_PRIVATE")
        if re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.", host):
            raise PermissionException("禁止访问内网地址", code="WIKI_URL_PRIVATE")

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "OntoMindWikiBot/1.0"})
                if resp.status_code >= 400:
                    raise BusinessException(f"抓取失败 HTTP {resp.status_code}", code="WIKI_FETCH_FAILED")
                raw = resp.content
                if len(raw) > 5 * 1024 * 1024:
                    raise BusinessException("响应超过 5MB", code="WIKI_FETCH_TOO_LARGE")
                html = raw.decode(resp.encoding or "utf-8", errors="replace")
                return {"url": str(resp.url), "html": html, "status_code": resp.status_code}
        except BusinessException:
            raise
        except Exception as exc:
            raise BusinessException(f"抓取失败: {exc}", code="WIKI_FETCH_FAILED") from exc
