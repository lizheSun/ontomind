"""Wiki 知识库 ORM."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum

from app.db.models.base import BaseModel


class WikiSourceType(str, enum.Enum):
    PASTE = "paste"
    MARKDOWN = "markdown"
    URL = "url"
    MANUAL = "manual"


class WikiDocStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class WikiSpace(BaseModel):
    __tablename__ = "wiki_spaces"
    __table_args__ = {"comment": "Wiki 空间"}

    name = Column(String(128), nullable=False)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(String(512), nullable=True)
    icon = Column(String(32), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)


class WikiDocument(BaseModel):
    __tablename__ = "wiki_documents"
    __table_args__ = {"comment": "Wiki 文档"}

    space_id = Column(Integer, ForeignKey("wiki_spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("wiki_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(256), nullable=False)
    slug = Column(String(128), nullable=False, index=True)
    content_md = Column(Text, nullable=False, default="")
    source_type = Column(
        SAEnum(WikiSourceType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=WikiSourceType.MANUAL,
    )
    source_url = Column(String(1024), nullable=True)
    source_meta_json = Column(JSON, nullable=True)
    tags_json = Column(JSON, nullable=True)
    status = Column(
        SAEnum(WikiDocStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=WikiDocStatus.DRAFT,
    )
    current_version = Column(Integer, nullable=False, default=1)
    word_count = Column(Integer, nullable=False, default=0)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class WikiDocumentVersion(BaseModel):
    __tablename__ = "wiki_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_wiki_doc_version"),
        {"comment": "Wiki 文档版本快照"},
    )

    document_id = Column(
        Integer, ForeignKey("wiki_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    content_md = Column(Text, nullable=False, default="")
    title = Column(String(256), nullable=False)
    change_note = Column(String(512), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
