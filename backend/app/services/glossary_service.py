"""业务术语抽取与管理。"""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.db.models.meta_model import GlossarySource, GlossaryTerm
from app.db.models.wiki_model import WikiDocument
from app.db.repositories.meta_repo import GlossaryTermRepository
from app.db.repositories.wiki_repo import WikiDocumentRepository
from app.schemas.metadata_schema import GlossaryTermCreate, GlossaryTermUpdate
from app.services.llm_settings_service import resolve_llm_client

_DEF_LIST_RE = re.compile(
    r"^[\-\*]\s+\*\*(.+?)\*\*[：:]\s*(.+)$",
    re.MULTILINE,
)
_HEADING_RE = re.compile(r"^#{2,4}\s+(.+)$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|", re.MULTILINE)

_GLOSSARY_LLM_SCHEMA = """{
  "terms": [
    {"name": str, "aliases": [str], "definition": str, "domain": str|null, "confidence": float}
  ]
}"""


class GlossaryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = GlossaryTermRepository(db)
        self.docs = WikiDocumentRepository(db)

    def list_terms(
        self,
        *,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[GlossaryTerm]:
        return self.repo.list(keyword=keyword, domain=domain, limit=limit, offset=offset)

    def get_term(self, term_id: int) -> GlossaryTerm:
        row = self.repo.get(term_id)
        if not row:
            raise NotFoundException(f"术语不存在: {term_id}")
        return row

    def create_term(self, data: GlossaryTermCreate) -> GlossaryTerm:
        if self.repo.get_by_name(data.name.strip()):
            raise ConflictException(f"术语已存在: {data.name}")
        row = GlossaryTerm(
            name=data.name.strip(),
            aliases_json=list(data.aliases) if data.aliases else [],
            definition=data.definition,
            domain=data.domain,
            source_type=GlossarySource(data.source_type),
            source_doc_id=data.source_doc_id,
            confidence=data.confidence if data.confidence is not None else 1.0,
        )
        self.repo.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_term(self, term_id: int, data: GlossaryTermUpdate) -> GlossaryTerm:
        row = self.get_term(term_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"]:
            other = self.repo.get_by_name(payload["name"].strip())
            if other and other.id != term_id:
                raise ConflictException(f"术语已存在: {payload['name']}")
            row.name = payload["name"].strip()
        if "aliases" in payload:
            row.aliases_json = list(payload["aliases"] or [])
        for key in ("definition", "domain", "confidence"):
            if key in payload:
                setattr(row, key, payload[key])
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_term(self, term_id: int) -> None:
        row = self.get_term(term_id)
        self.repo.delete(row)
        self.db.commit()

    def extract_from_wiki(
        self,
        doc_ids: Optional[list[int]],
        mode: Literal["rules", "llm"] = "rules",
    ) -> list[GlossaryTerm]:
        docs = self._load_docs(doc_ids)
        if not docs:
            return []
        extracted: list[dict[str, Any]] = []
        if mode == "rules":
            for doc in docs:
                for item in self._extract_rules(doc.content_md or ""):
                    item["source_doc_id"] = doc.id
                    extracted.append(item)
        else:
            client = resolve_llm_client(self.db)
            if not client.is_configured():
                raise BusinessException(
                    "未配置 LLM，请在 GovOps → LLM 配置 或 .env 设置 LLM_API_KEY",
                    code="LLM_NOT_CONFIGURED",
                )
            for doc in docs:
                for chunk in self._chunk_text(doc.content_md or "", 4000):
                    result = client.chat_json(
                        [
                            {
                                "role": "system",
                                "content": "你从业务文档中抽取术语表，只输出 JSON。",
                            },
                            {
                                "role": "user",
                                "content": f"文档标题: {doc.title}\n\n正文:\n{chunk}",
                            },
                        ],
                        schema_hint=_GLOSSARY_LLM_SCHEMA,
                    )
                    for term in result.get("terms") or []:
                        if not isinstance(term, dict) or not term.get("name"):
                            continue
                        extracted.append(
                            {
                                "name": str(term["name"]).strip(),
                                "aliases": list(term.get("aliases") or []),
                                "definition": term.get("definition"),
                                "domain": term.get("domain"),
                                "confidence": float(term.get("confidence") or 0.7),
                                "source_doc_id": doc.id,
                            }
                        )

        source_type = GlossarySource.RULES if mode == "rules" else GlossarySource.LLM
        out: list[GlossaryTerm] = []
        for item in extracted:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            row = self._upsert_term(
                name=name,
                aliases=list(item.get("aliases") or []),
                definition=item.get("definition"),
                domain=item.get("domain"),
                source_type=source_type,
                source_doc_id=item.get("source_doc_id"),
                confidence=float(item.get("confidence") or 0.8),
            )
            out.append(row)
        self.db.commit()
        for row in out:
            self.db.refresh(row)
        return out

    def _load_docs(self, doc_ids: Optional[list[int]]) -> list[WikiDocument]:
        if doc_ids:
            docs = []
            for did in doc_ids:
                d = self.docs.get_document(did)
                if d:
                    docs.append(d)
            return docs
        return self.docs.list_documents(status="published", limit=50, offset=0)

    def _upsert_term(
        self,
        *,
        name: str,
        aliases: list[str],
        definition: Optional[str],
        domain: Optional[str],
        source_type: GlossarySource,
        source_doc_id: Optional[int],
        confidence: float,
    ) -> GlossaryTerm:
        existing = self.repo.get_by_name(name)
        if existing:
            old_aliases = list(existing.aliases_json or [])
            merged = list(dict.fromkeys([*old_aliases, *[a for a in aliases if a]]))
            existing.aliases_json = merged
            if definition and not existing.definition:
                existing.definition = definition
            if domain and not existing.domain:
                existing.domain = domain
            if source_doc_id and not existing.source_doc_id:
                existing.source_doc_id = source_doc_id
            if confidence and (existing.confidence is None or confidence > existing.confidence):
                existing.confidence = confidence
            self.db.add(existing)
            self.db.flush()
            return existing
        row = GlossaryTerm(
            name=name,
            aliases_json=list(dict.fromkeys([a for a in aliases if a])),
            definition=definition,
            domain=domain,
            source_type=source_type,
            source_doc_id=source_doc_id,
            confidence=confidence,
        )
        return self.repo.add(row)

    @staticmethod
    def _chunk_text(text: str, size: int) -> list[str]:
        raw = text or ""
        if not raw:
            return []
        return [raw[i : i + size] for i in range(0, len(raw), size)]

    @staticmethod
    def _extract_rules(md: str) -> list[dict[str, Any]]:
        terms: list[dict[str, Any]] = []
        seen: set[str] = set()

        def _add(name: str, definition: str, conf: float = 0.85) -> None:
            n = name.strip().strip("*").strip()
            d = definition.strip()
            if not n or n in seen or len(n) > 64:
                return
            if n.lower() in {"术语", "名称", "name", "定义", "definition"}:
                return
            seen.add(n)
            terms.append(
                {
                    "name": n,
                    "aliases": [],
                    "definition": d,
                    "domain": None,
                    "confidence": conf,
                }
            )

        for m in _DEF_LIST_RE.finditer(md or ""):
            _add(m.group(1), m.group(2), 0.9)

        lines = (md or "").splitlines()
        i = 0
        while i < len(lines):
            hm = re.match(r"^#{2,4}\s+(.+)$", lines[i].strip())
            if hm:
                title = hm.group(1).strip()
                body: list[str] = []
                j = i + 1
                while j < len(lines) and not re.match(r"^#{1,4}\s+", lines[j].strip()):
                    if lines[j].strip():
                        body.append(lines[j].strip())
                    j += 1
                    if len(body) >= 3:
                        break
                if body and len(title) <= 32:
                    _add(title, " ".join(body)[:500], 0.75)
                i = j
                continue
            i += 1

        for m in _TABLE_ROW_RE.finditer(md or ""):
            left, right = m.group(1).strip(), m.group(2).strip()
            if set(left) <= {"-", ":"} or set(right) <= {"-", ":"}:
                continue
            _add(left, right, 0.8)

        return terms
