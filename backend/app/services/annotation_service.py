"""元数据自动标注服务。"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.meta_model import (
    Annotation,
    AnnotationLabelKind,
    AnnotationSource,
    AnnotationStatus,
    AnnotationTargetType,
    JobKind,
    MetaColumn,
    MetaScanJob,
    MetaTable,
    ScanStatus,
)
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.repositories.meta_repo import (
    AnnotationRepository,
    GlossaryTermRepository,
    MetaColumnRepository,
    MetaScanJobRepository,
    MetaTableRepository,
)
from app.schemas.metadata_schema import AnnotateJobCreate
from app.services.annotation_prompts import (
    TABLE_ANNOTATE_SCHEMA_HINT,
    TABLE_ANNOTATE_SYSTEM,
    TABLE_ANNOTATE_USER_TMPL,
)
from app.services.annotation_rules import (
    detect_layer_domain,
    detect_pii_level,
    expand_name_to_biz,
    is_entity_table_candidate,
    is_join_key_candidate,
)
from app.services.job_runner import open_job_session, run_in_background
from app.services.llm_settings_service import resolve_llm_client

logger = logging.getLogger(__name__)

CONF_AUTO_ACCEPT = 0.85
CONF_SUGGEST_MIN = 0.65

_WRITEBACK_FIELDS = {
    "biz_name",
    "biz_description",
    "domain",
    "pii_level",
    "semantic_type",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


class AnnotationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = MetaScanJobRepository(db)
        self.tables = MetaTableRepository(db)
        self.columns = MetaColumnRepository(db)
        self.anns = AnnotationRepository(db)
        self.glossary = GlossaryTermRepository(db)
        self.sources = DataSourceRepository(db)

    def create_annotate_job(self, req: AnnotateJobCreate) -> MetaScanJob:
        src = self.sources.get(req.source_id)
        if not src:
            raise NotFoundException(f"数据源不存在: {req.source_id}")
        if req.mode in ("llm", "hybrid"):
            client = resolve_llm_client(self.db)
            if not client.is_configured():
                raise BusinessException(
                    "未配置 LLM，请在 GovOps → LLM 配置 或 .env 设置 LLM_API_KEY",
                    code="LLM_NOT_CONFIGURED",
                )
        job = MetaScanJob(
            source_id=req.source_id,
            database=req.database.strip(),
            job_kind=JobKind.ANNOTATE,
            status=ScanStatus.PENDING,
            progress=0.0,
            with_profile=False,
            mode=req.mode,
            tables_json={
                "tables": list(req.tables) if req.tables else None,
                "label_kinds": list(req.label_kinds) if req.label_kinds else None,
            },
        )
        self.jobs.add(job)
        self.db.commit()
        self.db.refresh(job)
        run_in_background(AnnotationService._run_annotate_entrypoint, job.id)
        return job

    @staticmethod
    def _run_annotate_entrypoint(job_id: int) -> None:
        db = open_job_session()
        try:
            AnnotationService(db)._run_annotate(job_id)
        finally:
            db.close()

    def get_annotate_job(self, job_id: int) -> MetaScanJob:
        job = self.jobs.get(job_id)
        if not job or _enum_val(job.job_kind) != "annotate":
            raise NotFoundException(f"标注任务不存在: {job_id}")
        return job

    def _run_annotate(self, job_id: int) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        started = time.perf_counter()
        job.status = ScanStatus.RUNNING
        job.started_at = _utcnow()
        job.progress = 0.0
        self.db.add(job)
        self.db.commit()

        dropped = 0
        written = 0
        accepted = 0
        try:
            scope = job.tables_json if isinstance(job.tables_json, dict) else {}
            table_filter = scope.get("tables") if isinstance(scope, dict) else None
            label_kinds = scope.get("label_kinds") if isinstance(scope, dict) else None
            kind_set = set(label_kinds) if label_kinds else None

            tables = self.tables.list_by_source_db(job.source_id, job.database)
            if table_filter:
                wanted = set(table_filter)
                tables = [t for t in tables if t.table_name in wanted]
            if not tables:
                raise BusinessException("无可用元数据表，请先执行扫描", code="NO_META_TABLES")

            glossary_terms = self.glossary.all_terms()
            total = max(len(tables), 1)
            sibling_names = [t.table_name for t in self.tables.list_by_source_db(job.source_id, job.database)]

            for idx, table in enumerate(tables):
                cols = self.columns.list_by_table(table.id)
                candidates = self._rules_round(table, cols, glossary_terms, kind_set)
                for cand in candidates:
                    result = self._persist_candidate(cand)
                    if result == "dropped":
                        dropped += 1
                    elif result == "accepted":
                        accepted += 1
                        written += 1
                    elif result == "written":
                        written += 1

                mode = (job.mode or "rules").lower()
                if mode in ("llm", "hybrid"):
                    llm_cands = self._llm_round(table, cols, glossary_terms, sibling_names, kind_set)
                    for cand in llm_cands:
                        result = self._persist_candidate(cand)
                        if result == "dropped":
                            dropped += 1
                        elif result == "accepted":
                            accepted += 1
                            written += 1
                        elif result == "written":
                            written += 1

                job.progress = round((idx + 1) / total, 4)
                self.db.add(job)
                self.db.commit()

            job.status = ScanStatus.SUCCEEDED
            job.progress = 1.0
            job.finished_at = _utcnow()
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            job.stats_json = {
                "table_count": len(tables),
                "written": written,
                "accepted": accepted,
                "dropped_low_confidence": dropped,
            }
            self.db.add(job)
            self.db.commit()
        except Exception as exc:
            logger.exception("annotate failed job_id=%s", job_id)
            job.status = ScanStatus.FAILED
            job.error_detail = str(exc)[:2000]
            job.finished_at = _utcnow()
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            self.db.add(job)
            self.db.commit()

    def _rules_round(
        self,
        table: MetaTable,
        cols: list[MetaColumn],
        glossary_terms: list[Any],
        kind_set: Optional[set[str]],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        def allow(kind: str) -> bool:
            return kind_set is None or kind in kind_set

        domain = detect_layer_domain(table.table_name)
        if domain and allow("domain"):
            out.append(
                {
                    "target_type": "table",
                    "target_id": table.id,
                    "label_kind": "domain",
                    "label_value": domain,
                    "confidence": 0.9,
                    "source": "rule",
                    "evidence": {"reason": "layer_prefix"},
                }
            )

        biz, conf = expand_name_to_biz(table.table_name)
        if biz and allow("biz_name"):
            out.append(
                {
                    "target_type": "table",
                    "target_id": table.id,
                    "label_kind": "biz_name",
                    "label_value": biz,
                    "confidence": conf,
                    "source": "rule",
                    "evidence": {"reason": "abbrev_dict", "from": table.table_name},
                }
            )

        pk_cols = [c for c in cols if (c.column_key or "").upper() == "PRI"]
        is_entity, econf, eev = is_entity_table_candidate(
            table.table_name, has_single_pk=len(pk_cols) == 1, row_count=table.row_count
        )
        if is_entity and allow("entity_candidate"):
            out.append(
                {
                    "target_type": "table",
                    "target_id": table.id,
                    "label_kind": "entity_candidate",
                    "label_value": "true",
                    "confidence": econf,
                    "source": "rule",
                    "evidence": eev,
                }
            )

        for col in cols:
            if allow("biz_name"):
                cbiz, cconf = expand_name_to_biz(col.column_name)
                if cbiz:
                    out.append(
                        {
                            "target_type": "column",
                            "target_id": col.id,
                            "label_kind": "biz_name",
                            "label_value": cbiz,
                            "confidence": cconf,
                            "source": "rule",
                            "evidence": {"reason": "abbrev_dict", "from": col.column_name},
                        }
                    )

            if allow("pii_level"):
                level, pconf, pev = detect_pii_level(col.column_name, col.profile_json)
                if level:
                    out.append(
                        {
                            "target_type": "column",
                            "target_id": col.id,
                            "label_kind": "pii_level",
                            "label_value": level,
                            "confidence": pconf,
                            "source": "rule",
                            "evidence": pev,
                        }
                    )

            if allow("join_key"):
                ok, jconf, jev = is_join_key_candidate(
                    col.column_name, col.column_key, col.profile_json
                )
                if ok:
                    out.append(
                        {
                            "target_type": "column",
                            "target_id": col.id,
                            "label_kind": "join_key",
                            "label_value": "true",
                            "confidence": jconf,
                            "source": "rule",
                            "evidence": jev,
                        }
                    )

            if allow("glossary"):
                for hit in self._match_glossary(col, table, glossary_terms):
                    out.append(hit)

        return out

    def _match_glossary(
        self, col: MetaColumn, table: MetaTable, terms: list[Any]
    ) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        comment = (col.column_comment or "").lower()
        cname = (col.column_name or "").lower()
        tcomment = (table.table_comment or "").lower()
        for term in terms:
            name = (term.name or "").strip()
            if not name:
                continue
            name_l = name.lower()
            aliases = [str(a) for a in (term.aliases_json or []) if a]
            conf = None
            evidence = None
            if name_l and (name_l in comment or name in (col.column_comment or "")):
                conf = 0.9
                evidence = {"matched": "column_comment", "term": name}
            elif name_l and name_l in cname:
                conf = 0.75
                evidence = {"matched": "column_name", "term": name}
            else:
                for alias in aliases:
                    al = alias.lower()
                    if al and (al in comment or alias in (col.column_comment or "")):
                        conf = 0.7
                        evidence = {"matched": "alias_comment", "term": name, "alias": alias}
                        break
                    if al and al in cname:
                        conf = 0.7
                        evidence = {"matched": "alias_name", "term": name, "alias": alias}
                        break
                if conf is None and name_l and (name_l in tcomment or name in (table.table_comment or "")):
                    conf = 0.7
                    evidence = {"matched": "table_comment", "term": name}
            if conf is not None:
                hits.append(
                    {
                        "target_type": "column",
                        "target_id": col.id,
                        "label_kind": "glossary",
                        "label_value": name,
                        "confidence": conf,
                        "source": "rule",
                        "evidence": evidence,
                    }
                )
        return hits

    def _llm_round(
        self,
        table: MetaTable,
        cols: list[MetaColumn],
        glossary_terms: list[Any],
        sibling_names: list[str],
        kind_set: Optional[set[str]],
    ) -> list[dict[str, Any]]:
        client = resolve_llm_client(self.db)
        columns_block = []
        for c in cols:
            profile = c.profile_json or {}
            top_k = profile.get("top_k") or []
            samples = []
            for item in top_k[:5]:
                val = item.get("value") if isinstance(item, dict) else item
                samples.append(self._mask_sample(str(val), c.column_name, c.pii_level))
            columns_block.append(
                {
                    "column_name": c.column_name,
                    "data_type": c.data_type,
                    "comment": c.column_comment,
                    "nullable": c.nullable,
                    "key": c.column_key,
                    "null_rate": profile.get("null_rate"),
                    "distinct_ratio": profile.get("distinct_ratio"),
                    "top_samples": samples,
                }
            )
        glossary_block = [
            {
                "name": t.name,
                "aliases": t.aliases_json or [],
                "definition": (t.definition or "")[:200],
            }
            for t in glossary_terms[:20]
        ]
        user = TABLE_ANNOTATE_USER_TMPL.format(
            table_name=table.table_name,
            table_comment=table.table_comment or "",
            row_count=table.row_count,
            domain=table.domain or "",
            columns_block=str(columns_block),
            glossary_block=str(glossary_block),
            sibling_tables=", ".join(sibling_names[:80]),
        )
        try:
            result = client.chat_json(
                [
                    {"role": "system", "content": TABLE_ANNOTATE_SYSTEM},
                    {"role": "user", "content": user},
                ],
                schema_hint=TABLE_ANNOTATE_SCHEMA_HINT,
            )
        except Exception as exc:
            logger.warning("llm annotate failed for %s: %s", table.table_name, exc)
            return []

        out: list[dict[str, Any]] = []

        def allow(kind: str) -> bool:
            return kind_set is None or kind in kind_set

        tinfo = result.get("table") or {}
        tconf = float(tinfo.get("confidence") or 0.0)
        if allow("biz_name") and tinfo.get("biz_name"):
            out.append(self._llm_cand("table", table.id, "biz_name", str(tinfo["biz_name"]), tconf, tinfo))
        if allow("biz_description") and tinfo.get("biz_description"):
            out.append(
                self._llm_cand(
                    "table", table.id, "biz_description", str(tinfo["biz_description"]), tconf, tinfo
                )
            )
        if allow("domain") and tinfo.get("domain"):
            out.append(self._llm_cand("table", table.id, "domain", str(tinfo["domain"]), tconf, tinfo))
        if allow("entity_candidate") and tinfo.get("is_entity_table"):
            out.append(
                self._llm_cand("table", table.id, "entity_candidate", "true", tconf, tinfo)
            )

        col_by_name = {c.column_name: c for c in cols}
        for cinfo in result.get("columns") or []:
            if not isinstance(cinfo, dict):
                continue
            cname = cinfo.get("column_name")
            col = col_by_name.get(cname)
            if not col:
                continue
            cconf = float(cinfo.get("confidence") or 0.0)
            if allow("biz_name") and cinfo.get("biz_name"):
                out.append(
                    self._llm_cand("column", col.id, "biz_name", str(cinfo["biz_name"]), cconf, cinfo)
                )
            if allow("biz_description") and cinfo.get("biz_description"):
                out.append(
                    self._llm_cand(
                        "column", col.id, "biz_description", str(cinfo["biz_description"]), cconf, cinfo
                    )
                )
            if allow("semantic_type") and cinfo.get("semantic_type"):
                out.append(
                    self._llm_cand(
                        "column", col.id, "semantic_type", str(cinfo["semantic_type"]), cconf, cinfo
                    )
                )
            if allow("pii_level") and cinfo.get("pii_level"):
                out.append(
                    self._llm_cand("column", col.id, "pii_level", str(cinfo["pii_level"]), cconf, cinfo)
                )
            if allow("glossary") and cinfo.get("glossary_term"):
                out.append(
                    self._llm_cand(
                        "column", col.id, "glossary", str(cinfo["glossary_term"]), cconf, cinfo
                    )
                )
            if allow("join_key") and cinfo.get("is_join_key"):
                out.append(self._llm_cand("column", col.id, "join_key", "true", cconf, cinfo))
        return out

    @staticmethod
    def _llm_cand(
        target_type: str,
        target_id: int,
        label_kind: str,
        label_value: str,
        confidence: float,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "target_type": target_type,
            "target_id": target_id,
            "label_kind": label_kind,
            "label_value": label_value,
            "confidence": confidence,
            "source": "llm",
            "evidence": {
                "evidence": evidence.get("evidence"),
                "raw_confidence": confidence,
            },
        }

    @staticmethod
    def _mask_sample(value: str, column_name: str, pii_level: Optional[str]) -> str:
        if not value:
            return value
        lower = (column_name or "").lower()
        if pii_level in ("L2", "L3") or any(
            x in lower for x in ("phone", "mobile", "idcard", "id_no", "email", "name", "addr")
        ):
            if len(value) <= 4:
                return "***"
            return value[:2] + "***" + value[-2:]
        return value

    def _persist_candidate(self, cand: dict[str, Any]) -> str:
        conf = float(cand.get("confidence") or 0.0)
        if conf < CONF_SUGGEST_MIN:
            return "dropped"

        target_type = cand["target_type"]
        target_id = int(cand["target_id"])
        label_kind = cand["label_kind"]
        label_value = str(cand["label_value"])
        source = cand.get("source") or "rule"
        evidence = cand.get("evidence")

        accepted = self.anns.get_accepted(target_type, target_id, label_kind)
        if accepted:
            row = Annotation(
                target_type=AnnotationTargetType(target_type),
                target_id=target_id,
                label_kind=AnnotationLabelKind(label_kind),
                label_value=label_value,
                confidence=conf,
                source=AnnotationSource(source),
                status=AnnotationStatus.SUGGESTED,
                evidence_json={
                    **(evidence or {}),
                    "conflict_with_accepted": accepted.id,
                },
            )
            self.anns.add(row)
            self.db.commit()
            return "written"

        actives = self.anns.list_active_for_key(target_type, target_id, label_kind)
        same_value_llm_or_rule = [
            a
            for a in actives
            if a.label_value == label_value and _enum_val(a.status) == "suggested"
        ]
        conflicting = [
            a
            for a in actives
            if a.label_value != label_value and _enum_val(a.status) == "suggested"
        ]

        for other in same_value_llm_or_rule:
            if _enum_val(other.source) != source:
                conf = min(1.0, max(conf, float(other.confidence)) + 0.1)
                other.status = AnnotationStatus.SUPERSEDED
                self.db.add(other)

        for other in conflicting:
            ev = dict(other.evidence_json or {})
            ev["conflict_with"] = {"value": label_value, "source": source, "confidence": conf}
            other.evidence_json = ev
            self.db.add(other)

        for other in actives:
            if (
                _enum_val(other.status) == "suggested"
                and other.label_value == label_value
                and _enum_val(other.source) == source
            ):
                other.status = AnnotationStatus.SUPERSEDED
                self.db.add(other)

        if conf >= CONF_AUTO_ACCEPT and not accepted:
            status = AnnotationStatus.ACCEPTED
            row = Annotation(
                target_type=AnnotationTargetType(target_type),
                target_id=target_id,
                label_kind=AnnotationLabelKind(label_kind),
                label_value=label_value,
                confidence=conf,
                source=AnnotationSource(source),
                status=status,
                evidence_json=evidence,
            )
            self.anns.add(row)
            self._writeback(target_type, target_id, label_kind, label_value)
            self.db.commit()
            return "accepted"

        row = Annotation(
            target_type=AnnotationTargetType(target_type),
            target_id=target_id,
            label_kind=AnnotationLabelKind(label_kind),
            label_value=label_value,
            confidence=conf,
            source=AnnotationSource(source),
            status=AnnotationStatus.SUGGESTED,
            evidence_json=evidence,
        )
        self.anns.add(row)
        self.db.commit()
        return "written"

    def _writeback(
        self, target_type: str, target_id: int, label_kind: str, label_value: str
    ) -> None:
        if label_kind not in _WRITEBACK_FIELDS and label_kind not in (
            "biz_name",
            "biz_description",
            "domain",
            "pii_level",
            "semantic_type",
        ):
            return
        if target_type == "table":
            row = self.tables.get(target_id)
            if not row:
                return
            if label_kind == "biz_name":
                row.biz_name = label_value
            elif label_kind == "biz_description":
                row.biz_description = label_value
            elif label_kind == "domain":
                row.domain = label_value
            self.db.add(row)
        elif target_type == "column":
            row = self.columns.get(target_id)
            if not row:
                return
            if label_kind == "biz_name":
                row.biz_name = label_value
            elif label_kind == "biz_description":
                row.biz_description = label_value
            elif label_kind == "pii_level":
                row.pii_level = label_value
            elif label_kind == "semantic_type":
                row.semantic_type = label_value
            self.db.add(row)

    def list_annotations(
        self,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        label_kind: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Annotation]:
        return self.anns.list(
            target_type=target_type,
            target_id=target_id,
            label_kind=label_kind,
            status=status,
            source=source,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            limit=limit,
            offset=offset,
        )

    def review_annotation(
        self,
        ann_id: int,
        action: str,
        *,
        user_id: int,
        value_override: Optional[str] = None,
    ) -> Annotation:
        row = self.anns.get(ann_id)
        if not row:
            raise NotFoundException(f"标注不存在: {ann_id}")
        if action == "reject":
            row.status = AnnotationStatus.REJECTED
            row.reviewed_by = user_id
            row.reviewed_at = _utcnow()
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return row
        if action != "accept":
            raise BusinessException(f"未知审核动作: {action}")
        if value_override is not None:
            row.label_value = value_override
        row.status = AnnotationStatus.ACCEPTED
        row.source = AnnotationSource.HUMAN
        row.reviewed_by = user_id
        row.reviewed_at = _utcnow()
        self.db.add(row)
        self._writeback(
            _enum_val(row.target_type),
            row.target_id,
            _enum_val(row.label_kind),
            row.label_value,
        )
        siblings = self.anns.list_active_for_key(
            _enum_val(row.target_type), row.target_id, _enum_val(row.label_kind)
        )
        for other in siblings:
            if other.id != row.id and _enum_val(other.status) == "suggested":
                other.status = AnnotationStatus.SUPERSEDED
                self.db.add(other)
        self.db.commit()
        self.db.refresh(row)
        return row

    def batch_review(self, ann_ids: list[int], action: str, *, user_id: int) -> list[Annotation]:
        out = []
        for aid in ann_ids:
            out.append(self.review_annotation(aid, action, user_id=user_id))
        return out

    def annotate_stats(self, source_id: int, database: str) -> dict[str, Any]:
        tables = self.tables.list_by_source_db(source_id, database)
        table_ids = [t.id for t in tables]
        cols = self.columns.list_by_table_ids(table_ids)
        column_ids = [c.id for c in cols]
        anns = self.anns.list_for_targets(table_ids=table_ids, column_ids=column_ids)

        table_count = len(tables)
        column_count = len(cols)
        t_biz = sum(1 for t in tables if t.biz_name)
        c_biz = sum(1 for c in cols if c.biz_name)
        t_cmt = sum(1 for t in tables if t.table_comment)
        c_cmt = sum(1 for c in cols if c.column_comment)

        status_counts = {"accepted": 0, "suggested": 0, "rejected": 0, "superseded": 0}
        confs: list[float] = []
        pii_dist: dict[str, int] = {}
        for a in anns:
            st = _enum_val(a.status)
            status_counts[st] = status_counts.get(st, 0) + 1
            confs.append(float(a.confidence or 0))
            if _enum_val(a.label_kind) == "pii_level":
                pii_dist[a.label_value] = pii_dist.get(a.label_value, 0) + 1
        for c in cols:
            if c.pii_level:
                pii_dist[c.pii_level] = pii_dist.get(c.pii_level, 0)

        return {
            "table_count": table_count,
            "column_count": column_count,
            "table_biz_name_coverage": round(t_biz / table_count, 4) if table_count else 0.0,
            "column_biz_name_coverage": round(c_biz / column_count, 4) if column_count else 0.0,
            "table_comment_coverage": round(t_cmt / table_count, 4) if table_count else 0.0,
            "column_comment_coverage": round(c_cmt / column_count, 4) if column_count else 0.0,
            "accepted_count": status_counts.get("accepted", 0),
            "suggested_count": status_counts.get("suggested", 0),
            "rejected_count": status_counts.get("rejected", 0),
            "pii_distribution": pii_dist,
            "avg_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
        }
