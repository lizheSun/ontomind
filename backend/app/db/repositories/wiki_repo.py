"""Wiki Repository — 仅 flush。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, or_
from sqlalchemy.orm import Session

from app.db.models.wiki_model import WikiDocument, WikiDocumentVersion, WikiSpace


class WikiSpaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_spaces(self) -> list[WikiSpace]:
        return self.db.query(WikiSpace).order_by(WikiSpace.sort_order.asc(), WikiSpace.id.asc()).all()

    def get_space(self, space_id: int) -> Optional[WikiSpace]:
        return self.db.get(WikiSpace, space_id)

    def get_space_by_slug(self, slug: str) -> Optional[WikiSpace]:
        return self.db.query(WikiSpace).filter(WikiSpace.slug == slug).first()

    def add_space(self, row: WikiSpace) -> WikiSpace:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_space(self, row: WikiSpace) -> None:
        self.db.delete(row)
        self.db.flush()


class WikiDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_documents(
        self,
        *,
        space_id: Optional[int] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WikiDocument]:
        q = self.db.query(WikiDocument)
        if space_id is not None:
            q = q.filter(WikiDocument.space_id == space_id)
        if status:
            q = q.filter(WikiDocument.status == status)
        if keyword:
            kw = f"%{keyword.strip()}%"
            q = q.filter(or_(WikiDocument.title.like(kw), WikiDocument.content_md.like(kw)))
        if tag:
            q = q.filter(WikiDocument.tags_json.cast(String).like(f'%"{tag}"%'))
        return (
            q.order_by(WikiDocument.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
            .all()
        )

    def get_document(self, doc_id: int) -> Optional[WikiDocument]:
        return self.db.get(WikiDocument, doc_id)

    def add_document(self, row: WikiDocument) -> WikiDocument:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_document(self, row: WikiDocument) -> None:
        self.db.delete(row)
        self.db.flush()

    def list_versions(self, doc_id: int) -> list[WikiDocumentVersion]:
        return (
            self.db.query(WikiDocumentVersion)
            .filter(WikiDocumentVersion.document_id == doc_id)
            .order_by(WikiDocumentVersion.version.desc())
            .all()
        )

    def add_version(self, row: WikiDocumentVersion) -> WikiDocumentVersion:
        self.db.add(row)
        self.db.flush()
        return row

    def get_version(self, doc_id: int, version: int) -> Optional[WikiDocumentVersion]:
        return (
            self.db.query(WikiDocumentVersion)
            .filter(WikiDocumentVersion.document_id == doc_id, WikiDocumentVersion.version == version)
            .first()
        )
