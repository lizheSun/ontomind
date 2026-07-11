"""知识库-文档库仓储：管理数据库行 + 文件系统落盘。"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.kb_document_model import KbDocument
from app.db.repositories.base_repo import BaseRepository


class KbDocumentRepository(BaseRepository[KbDocument]):
    """KbDocument 仓储：owner scope + LIKE 搜索 + 落盘写入。"""

    def __init__(self, db: Session) -> None:
        super().__init__(KbDocument, db)

    def _docs_dir(self) -> Path:
        return Path(settings.UPLOAD_DIR) / "kb" / "documents"

    def list_by_owner(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[KbDocument]:
        return (
            self.db.query(KbDocument)
            .filter(KbDocument.owner_user_id == user_id)
            .order_by(KbDocument.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    def search_like(self, q: str, limit: int = 20) -> List[KbDocument]:
        like = f"%{q}%"
        return (
            self.db.query(KbDocument)
            .filter(
                or_(
                    KbDocument.title_zh.ilike(like),
                    KbDocument.filename.ilike(like),
                    KbDocument.description_md.ilike(like),
                )
            )
            .limit(limit).all()
        )

    def create_with_file(
        self,
        *,
        filename: str,
        mime_type: str,
        contents: bytes,
        title_zh: str,
        library_id: int,
        owner_user_id: int,
        created_by_user_id: int,
        description_md: Optional[str] = None,
        tags: Any = None,
    ) -> KbDocument:
        """将上传字节写入 UPLOAD_DIR/kb/documents/<uuid>.<ext>，再落库。"""
        docs = self._docs_dir()
        docs.mkdir(parents=True, exist_ok=True)
        ext = "".join(Path(filename).suffixes)  # 支持 .tar.gz
        storage_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = docs / storage_name
        storage_path.write_bytes(contents)
        rel_path = str(storage_path.relative_to(Path(settings.UPLOAD_DIR)))
        row = KbDocument(
            library_id=library_id,
            title_zh=title_zh,
            filename=filename,
            storage_path=rel_path,
            mime_type=mime_type,
            size_bytes=len(contents),
            description_md=description_md,
            tags=tags,
            owner_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def absolute_path(self, doc: KbDocument) -> Path:
        return Path(settings.UPLOAD_DIR) / doc.storage_path
