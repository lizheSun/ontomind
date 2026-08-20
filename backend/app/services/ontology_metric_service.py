"""本体指标（语义层）服务。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.ontology_model import OntologyMetric
from app.db.repositories.meta_repo import GlossaryTermRepository, MetaColumnRepository, MetaTableRepository
from app.db.repositories.ontology_repo import OntologyMetricRepository, OntologyRepository
from app.schemas.ontology_schema import MetricCreate, MetricUpdate
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_METRIC_HINT_RE = re.compile(r"(率|额|数|占比|逾期|不良|余额|金额|次数)")


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _normalize_key(text: str) -> str:
    s = (text or "").strip()
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = s.lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "metric"


class OntologyMetricService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ontologies = OntologyRepository(db)
        self.metrics = OntologyMetricRepository(db)
        try:
            self.glossary = GlossaryTermRepository(db)
        except Exception:
            self.glossary = None  # type: ignore
        self.meta_tables = MetaTableRepository(db)
        self.meta_columns = MetaColumnRepository(db)

    def _resp(self, row: OntologyMetric) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "key": row.key,
            "display_name": row.display_name,
            "definition": row.definition,
            "sql_expr": row.sql_expr,
            "unit": row.unit,
            "confidence": float(row.confidence or 0),
            "source": _enum_val(row.source),
            "status": _enum_val(row.status),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _ensure(self, oid: int) -> None:
        if not self.ontologies.get(oid):
            raise NotFoundException(f"本体不存在: {oid}")

    def list_metrics(self, oid: int, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        self._ensure(oid)
        return [self._resp(r) for r in self.metrics.list(oid, status=status)]

    def create_metric(self, oid: int, data: MetricCreate) -> dict[str, Any]:
        self._ensure(oid)
        key = _normalize_key(data.key)
        if self.metrics.get_by_key(oid, key):
            raise ConflictException(f"指标 key 已存在: {key}")
        row = OntologyMetric(
            ontology_id=oid,
            key=key,
            display_name=data.display_name.strip(),
            definition=data.definition,
            sql_expr=data.sql_expr,
            unit=data.unit,
            confidence=float(data.confidence),
            source=data.source,
            status=data.status,
        )
        self.metrics.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._resp(row)

    def update_metric(self, metric_id: int, data: MetricUpdate) -> dict[str, Any]:
        row = self.metrics.get(metric_id)
        if not row:
            raise NotFoundException(f"指标不存在: {metric_id}")
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) and k not in ("status", "sql_expr") else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._resp(row)

    def delete_metric(self, metric_id: int) -> None:
        row = self.metrics.get(metric_id)
        if not row:
            raise NotFoundException(f"指标不存在: {metric_id}")
        self.metrics.delete(row)
        self.db.commit()

    def suggest_metrics(self, oid: int) -> list[dict[str, Any]]:
        self._ensure(oid)
        hints: list[dict[str, Any]] = []

        # glossary terms with metric-ish names
        try:
            terms = self.glossary.all_terms() if self.glossary else []
        except Exception:
            terms = []
        for term in terms:
            name = getattr(term, "name", "") or ""
            if _METRIC_HINT_RE.search(name):
                hints.append(
                    {
                        "key": _normalize_key(name),
                        "display_name": name,
                        "definition": getattr(term, "definition", None),
                        "sql_expr": None,
                        "unit": None,
                        "confidence": 0.7,
                        "source": "rule",
                        "status": "draft",
                    }
                )

        # numeric columns
        try:
            tables = self.meta_tables.list(limit=200)
        except TypeError:
            tables = []
        for table in tables[:50]:
            try:
                cols = self.meta_columns.list_by_table(table.id)
            except Exception:
                continue
            for col in cols:
                dt = (col.data_type or "").lower()
                cname = col.column_name or ""
                if not any(x in dt for x in ("int", "decimal", "float", "double", "numeric")):
                    if not _METRIC_HINT_RE.search(cname):
                        continue
                if not _METRIC_HINT_RE.search(cname) and not _METRIC_HINT_RE.search(col.column_comment or ""):
                    continue
                hints.append(
                    {
                        "key": _normalize_key(f"{table.table_name}_{cname}"),
                        "display_name": col.biz_name or col.column_comment or cname,
                        "definition": col.biz_description or col.column_comment,
                        "sql_expr": f"SUM({table.table_name}.{cname})",
                        "unit": None,
                        "confidence": 0.65,
                        "source": "rule",
                        "status": "draft",
                    }
                )

        client = LLMClient()
        if client.is_configured() and hints:
            try:
                data = client.chat_json(
                    [
                        {
                            "role": "system",
                            "content": (
                                "根据候选术语与数值列，提出业务指标及 sql_expr 草稿。"
                                '输出 JSON: {"metrics":[{"key","display_name","definition","sql_expr","unit","confidence"}]}'
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps({"candidates": hints[:30]}, ensure_ascii=False),
                        },
                    ]
                )
                llm_items = list((data or {}).get("metrics") or [])
                if llm_items:
                    hints = [
                        {
                            "key": _normalize_key(m.get("key") or m.get("display_name") or "metric"),
                            "display_name": m.get("display_name") or m.get("key"),
                            "definition": m.get("definition"),
                            "sql_expr": m.get("sql_expr"),
                            "unit": m.get("unit"),
                            "confidence": float(m.get("confidence") or 0.7),
                            "source": "llm",
                            "status": "draft",
                        }
                        for m in llm_items
                    ]
            except Exception as exc:
                logger.warning("suggest_metrics LLM skipped: %s", exc)

        # persist as draft if not exists
        created: list[dict[str, Any]] = []
        for h in hints[:20]:
            if self.metrics.get_by_key(oid, h["key"]):
                continue
            row = OntologyMetric(
                ontology_id=oid,
                key=h["key"],
                display_name=h["display_name"],
                definition=h.get("definition"),
                sql_expr=h.get("sql_expr"),
                unit=h.get("unit"),
                confidence=float(h.get("confidence") or 0.7),
                source=h.get("source") or "rule",
                status="draft",
            )
            self.metrics.add(row)
            self.db.flush()
            created.append(self._resp(row))
        self.db.commit()
        return created
