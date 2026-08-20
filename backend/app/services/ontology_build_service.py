"""本体构建服务 — delta 迭代管道 + 版本/导出/图查询。"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.db.models.data_source_model import DataSource
from app.db.models.ontology_model import (
    Ontology,
    OntologyBuildJob,
    OntologyBuildPhase,
    OntologyElementSource,
    OntologyJobStatus,
    OntologyLinkType,
    OntologyMapping,
    OntologyMetric,
    OntologyObjectType,
    OntologyProperty,
    OntologyVersion,
)
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.repositories.meta_repo import MetaColumnRepository, MetaTableRepository
from app.db.repositories.ontology_repo import (
    OntologyBuildJobRepository,
    OntologyCQRepository,
    OntologyLinkTypeRepository,
    OntologyMappingRepository,
    OntologyMetricRepository,
    OntologyObjectTypeRepository,
    OntologyPropertyRepository,
    OntologyRepository,
    OntologyVersionRepository,
)
from app.schemas.ontology_schema import (
    InferRelationsRequest,
    LinkTypeCreate,
    LinkTypeUpdate,
    MappingCreate,
    MappingUpdate,
    ObjectTypeCreate,
    ObjectTypeUpdate,
    OntologyBuildJobCreate,
    OntologyCreate,
    OntologyUpdate,
    PropertyCreate,
    PropertyUpdate,
    ReviewRequest,
    ReviewItem,
)
from app.services.dataops_connector import DataSourceConnector
from app.services.job_runner import open_job_session, run_in_background
from app.services.llm_settings_service import resolve_llm_client
from app.services.ontology_fragments import get_domain_fragment

logger = logging.getLogger(__name__)

CONF_AUTO_ACCEPT = 0.85
CONF_SUGGEST_MIN = 0.65

_SLUG_RE = re.compile(r"[^a-z0-9\-]+")
_KEY_RE = re.compile(r"[^a-z0-9_]+")
_ID_SUFFIX_RE = re.compile(r"^(?P<root>.+?)_id$", re.I)


def _slugify(text: str) -> str:
    s = (text or "").strip().lower().replace(" ", "-")
    s = _SLUG_RE.sub("-", s).strip("-")
    return (s or "ontology")[:60]


def _normalize_key(text: str) -> str:
    s = (text or "").strip()
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = s.lower().replace("-", "_").replace(" ", "_")
    s = _KEY_RE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unnamed"


def _normalize_ot_key(text: str) -> str:
    """对象类型 key：保留 PascalCase，只清洗非法字符。"""
    s = (text or "").strip().replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "Unnamed"


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def confidence_tier(confidence: float, judge_verdict: str = "pass") -> str:
    """返回 accepted / draft / rejected。"""
    conf = float(confidence or 0.0)
    verdict = (judge_verdict or "pass").lower()
    if verdict == "fail" or conf < CONF_SUGGEST_MIN:
        return "rejected"
    if verdict == "warn" or conf < CONF_AUTO_ACCEPT:
        return "draft"
    return "accepted"


class OntologyBuildService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ontologies = OntologyRepository(db)
        self.jobs = OntologyBuildJobRepository(db)
        self.object_types = OntologyObjectTypeRepository(db)
        self.properties = OntologyPropertyRepository(db)
        self.link_types = OntologyLinkTypeRepository(db)
        self.mappings = OntologyMappingRepository(db)
        self.metrics = OntologyMetricRepository(db)
        self.cqs = OntologyCQRepository(db)
        self.versions = OntologyVersionRepository(db)
        self.sources = DataSourceRepository(db)
        self.meta_tables = MetaTableRepository(db)
        self.meta_columns = MetaColumnRepository(db)

    # ------------------------------------------------------------------
    # Ontology CRUD
    # ------------------------------------------------------------------

    def list_ontologies(self, *, limit: int = 50, offset: int = 0) -> list[Ontology]:
        return self.ontologies.list(limit=limit, offset=offset)

    def create_ontology(self, data: OntologyCreate) -> Ontology:
        slug = _slugify(data.slug)
        if self.ontologies.get_by_slug(slug):
            raise ConflictException(f"本体 slug 已存在: {slug}")
        row = Ontology(
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            domain=data.domain,
            current_version=0,
        )
        self.ontologies.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_ontology(self, oid: int) -> Ontology:
        row = self.ontologies.get(oid)
        if not row:
            raise NotFoundException(f"本体不存在: {oid}")
        return row

    def update_ontology(self, oid: int, data: OntologyUpdate) -> Ontology:
        row = self.get_ontology(oid)
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_ontology(self, oid: int) -> None:
        row = self.get_ontology(oid)
        self.ontologies.delete(row)
        self.db.commit()

    # ------------------------------------------------------------------
    # Object types / properties / links / mappings
    # ------------------------------------------------------------------

    def _ot_resp(self, row: OntologyObjectType) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "key": row.key,
            "display_name": row.display_name,
            "definition": row.definition,
            "parent_key": row.parent_key,
            "aliases": row.aliases_json or [],
            "confidence": float(row.confidence or 0),
            "source": _enum_val(row.source),
            "status": _enum_val(row.status),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _prop_resp(self, row: OntologyProperty) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "object_type_id": row.object_type_id,
            "key": row.key,
            "display_name": row.display_name,
            "data_type": row.data_type,
            "definition": row.definition,
            "confidence": float(row.confidence or 0),
            "source": _enum_val(row.source),
            "status": _enum_val(row.status),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _link_resp(self, row: OntologyLinkType) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "key": row.key,
            "display_name": row.display_name,
            "from_key": row.from_key,
            "to_key": row.to_key,
            "cardinality": row.cardinality,
            "definition": row.definition,
            "confidence": float(row.confidence or 0),
            "source": _enum_val(row.source),
            "status": _enum_val(row.status),
            "evidence": row.evidence_json,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _mapping_resp(self, row: OntologyMapping) -> dict[str, Any]:
        return {
            "id": row.id,
            "ontology_id": row.ontology_id,
            "element_type": _enum_val(row.element_type),
            "element_key": row.element_key,
            "source_id": row.source_id,
            "database": row.database,
            "table_name": row.table_name,
            "column_name": row.column_name,
            "confidence": float(row.confidence or 0),
            "source": _enum_val(row.source),
            "status": _enum_val(row.status),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def list_object_types(self, oid: int, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        self.get_ontology(oid)
        return [self._ot_resp(r) for r in self.object_types.list(oid, status=status)]

    def create_object_type(self, oid: int, data: ObjectTypeCreate) -> dict[str, Any]:
        self.get_ontology(oid)
        key = _normalize_ot_key(data.key)
        if self.object_types.get_by_key(oid, key):
            raise ConflictException(f"对象类型 key 已存在: {key}")
        row = OntologyObjectType(
            ontology_id=oid,
            key=key,
            display_name=data.display_name.strip(),
            definition=data.definition,
            parent_key=_normalize_ot_key(data.parent_key) if data.parent_key else None,
            aliases_json=list(data.aliases) if data.aliases else [],
            confidence=float(data.confidence),
            source=data.source,
            status=data.status,
        )
        self.object_types.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._ot_resp(row)

    def update_object_type(self, ot_id: int, data: ObjectTypeUpdate) -> dict[str, Any]:
        row = self.object_types.get(ot_id)
        if not row:
            raise NotFoundException(f"对象类型不存在: {ot_id}")
        payload = data.model_dump(exclude_unset=True)
        if "aliases" in payload:
            row.aliases_json = payload.pop("aliases") or []
        if "parent_key" in payload and payload["parent_key"]:
            payload["parent_key"] = _normalize_ot_key(payload["parent_key"])
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) and k != "status" else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._ot_resp(row)

    def delete_object_type(self, ot_id: int) -> None:
        row = self.object_types.get(ot_id)
        if not row:
            raise NotFoundException(f"对象类型不存在: {ot_id}")
        self.object_types.delete(row)
        self.db.commit()

    def list_properties(self, ot_id: int) -> list[dict[str, Any]]:
        ot = self.object_types.get(ot_id)
        if not ot:
            raise NotFoundException(f"对象类型不存在: {ot_id}")
        return [self._prop_resp(r) for r in self.properties.list_by_object_type(ot_id)]

    def create_property(self, ot_id: int, data: PropertyCreate) -> dict[str, Any]:
        ot = self.object_types.get(ot_id)
        if not ot:
            raise NotFoundException(f"对象类型不存在: {ot_id}")
        key = _normalize_key(data.key)
        row = OntologyProperty(
            ontology_id=ot.ontology_id,
            object_type_id=ot_id,
            key=key,
            display_name=data.display_name.strip(),
            data_type=data.data_type,
            definition=data.definition,
            confidence=float(data.confidence),
            source=data.source,
            status=data.status,
        )
        self.properties.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._prop_resp(row)

    def update_property(self, prop_id: int, data: PropertyUpdate) -> dict[str, Any]:
        row = self.properties.get(prop_id)
        if not row:
            raise NotFoundException(f"属性不存在: {prop_id}")
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) and k not in ("status", "data_type") else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._prop_resp(row)

    def delete_property(self, prop_id: int) -> None:
        row = self.properties.get(prop_id)
        if not row:
            raise NotFoundException(f"属性不存在: {prop_id}")
        self.properties.delete(row)
        self.db.commit()

    def list_link_types(self, oid: int, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        self.get_ontology(oid)
        return [self._link_resp(r) for r in self.link_types.list(oid, status=status)]

    def create_link_type(self, oid: int, data: LinkTypeCreate) -> dict[str, Any]:
        self.get_ontology(oid)
        key = _normalize_key(data.key)
        if self.link_types.get_by_key(oid, key):
            raise ConflictException(f"关系类型 key 已存在: {key}")
        row = OntologyLinkType(
            ontology_id=oid,
            key=key,
            display_name=data.display_name.strip(),
            from_key=_normalize_ot_key(data.from_key),
            to_key=_normalize_ot_key(data.to_key),
            cardinality=data.cardinality,
            definition=data.definition,
            confidence=float(data.confidence),
            source=data.source,
            status=data.status,
            evidence_json=data.evidence,
        )
        self.link_types.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._link_resp(row)

    def update_link_type(self, link_id: int, data: LinkTypeUpdate) -> dict[str, Any]:
        row = self.link_types.get(link_id)
        if not row:
            raise NotFoundException(f"关系类型不存在: {link_id}")
        payload = data.model_dump(exclude_unset=True)
        if "evidence" in payload:
            row.evidence_json = payload.pop("evidence")
        for k in ("from_key", "to_key"):
            if k in payload and payload[k]:
                payload[k] = _normalize_ot_key(payload[k])
        for k, v in payload.items():
            setattr(row, k, v.strip() if isinstance(v, str) and k != "status" else v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._link_resp(row)

    def delete_link_type(self, link_id: int) -> None:
        row = self.link_types.get(link_id)
        if not row:
            raise NotFoundException(f"关系类型不存在: {link_id}")
        self.link_types.delete(row)
        self.db.commit()

    def list_mappings(self, oid: int, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        self.get_ontology(oid)
        return [self._mapping_resp(r) for r in self.mappings.list(oid, status=status)]

    def create_mapping(self, oid: int, data: MappingCreate) -> dict[str, Any]:
        self.get_ontology(oid)
        row = OntologyMapping(
            ontology_id=oid,
            element_type=data.element_type,
            element_key=_normalize_ot_key(data.element_key)
            if data.element_type == "object_type"
            else (
                data.element_key
                if data.element_type == "property" and "." in data.element_key
                else _normalize_key(data.element_key)
            ),
            source_id=data.source_id,
            database=data.database.strip(),
            table_name=data.table_name.strip(),
            column_name=data.column_name.strip() if data.column_name else None,
            confidence=float(data.confidence),
            source=data.source,
            status=data.status,
        )
        self.mappings.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._mapping_resp(row)

    def update_mapping(self, mapping_id: int, data: MappingUpdate) -> dict[str, Any]:
        row = self.mappings.get(mapping_id)
        if not row:
            raise NotFoundException(f"映射不存在: {mapping_id}")
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(row, k, v)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._mapping_resp(row)

    def delete_mapping(self, mapping_id: int) -> None:
        row = self.mappings.get(mapping_id)
        if not row:
            raise NotFoundException(f"映射不存在: {mapping_id}")
        self.mappings.delete(row)
        self.db.commit()

    def review(self, oid: int, data: ReviewRequest) -> dict[str, Any]:
        self.get_ontology(oid)
        items = list(data.items or [])
        if data.accept_all_drafts or data.reject_all_drafts:
            action = "accept" if data.accept_all_drafts else "reject"
            for row in self.object_types.list(oid, status="draft"):
                items.append(
                    ReviewItem(element_type="object_type", element_id=row.id, action=action)
                )
            for row in self.properties.list_by_ontology(oid, status="draft"):
                items.append(
                    ReviewItem(element_type="property", element_id=row.id, action=action)
                )
            for row in self.link_types.list(oid, status="draft"):
                items.append(
                    ReviewItem(element_type="link_type", element_id=row.id, action=action)
                )
            for row in self.mappings.list(oid, status="draft"):
                items.append(
                    ReviewItem(element_type="mapping", element_id=row.id, action=action)
                )
            for row in self.metrics.list(oid, status="draft"):
                items.append(
                    ReviewItem(element_type="metric", element_id=row.id, action=action)
                )
        if not items:
            return {"updated": 0}
        updated = 0
        for item in items:
            status = "accepted" if item.action == "accept" else "rejected"
            row = None
            if item.element_type == "object_type":
                row = self.object_types.get(item.element_id)
            elif item.element_type == "property":
                row = self.properties.get(item.element_id)
            elif item.element_type == "link_type":
                row = self.link_types.get(item.element_id)
            elif item.element_type == "mapping":
                row = self.mappings.get(item.element_id)
            elif item.element_type == "metric":
                row = self.metrics.get(item.element_id)
            if not row or getattr(row, "ontology_id", None) != oid:
                continue
            row.status = status
            if hasattr(row, "source"):
                row.source = OntologyElementSource.HUMAN
            self.db.add(row)
            updated += 1
        self.db.commit()
        return {"updated": updated}

    # ------------------------------------------------------------------
    # Build job
    # ------------------------------------------------------------------

    def create_build_job(self, oid: int, req: OntologyBuildJobCreate) -> OntologyBuildJob:
        self.get_ontology(oid)
        if req.mode in ("llm", "hybrid"):
            client = resolve_llm_client(self.db)
            if not client.is_configured():
                raise BusinessException(
                    "未配置 LLM，请在 GovOps → LLM 配置 或 .env 设置 LLM_API_KEY",
                    code="LLM_NOT_CONFIGURED",
                )
        scope = dict(req.scope or {})
        if req.reuse_domain_fragment:
            scope["reuse_domain_fragment"] = req.reuse_domain_fragment
        job = OntologyBuildJob(
            ontology_id=oid,
            status=OntologyJobStatus.PENDING,
            phase=OntologyBuildPhase.EXTRACT,
            mode=req.mode,
            scope_json=scope,
            batch_size=req.batch_size,
            progress=0.0,
            delta_json={"batches": []},
        )
        self.jobs.add(job)
        self.db.commit()
        self.db.refresh(job)
        run_in_background(OntologyBuildService._run_build_entrypoint, job.id)
        return job

    @staticmethod
    def _run_build_entrypoint(job_id: int) -> None:
        db = open_job_session()
        try:
            OntologyBuildService(db)._run_build(job_id)
        finally:
            db.close()

    def get_build_job(self, job_id: int) -> OntologyBuildJob:
        job = self.jobs.get(job_id)
        if not job:
            raise NotFoundException(f"构建任务不存在: {job_id}")
        return job

    def _set_phase(self, job: OntologyBuildJob, phase: str, progress: float) -> None:
        job.phase = phase
        job.progress = progress
        self.db.add(job)
        self.db.commit()

    def _run_build(self, job_id: int) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        started = time.perf_counter()
        job.status = OntologyJobStatus.RUNNING
        job.phase = OntologyBuildPhase.EXTRACT
        job.progress = 0.0
        job.error_detail = None
        self.db.add(job)
        self.db.commit()

        try:
            scope = job.scope_json if isinstance(job.scope_json, dict) else {}
            source_id = scope.get("source_id")
            database = scope.get("database")
            tables_filter = scope.get("tables")
            fragment_name = scope.get("reuse_domain_fragment")
            fragment = get_domain_fragment(fragment_name)

            table_rows: list[Any] = []
            if source_id and database:
                table_rows = self.meta_tables.list_by_source_db(int(source_id), str(database))
                if tables_filter:
                    wanted = set(tables_filter)
                    table_rows = [t for t in table_rows if t.table_name in wanted]
            table_rows = self._sort_tables_for_extract(table_rows)

            batch_size = max(1, int(job.batch_size or 8))
            batches = [
                table_rows[i : i + batch_size] for i in range(0, max(len(table_rows), 1), batch_size)
            ]
            if not table_rows:
                batches = [[]]

            all_batch_results: list[dict[str, Any]] = []
            total = max(len(batches), 1)

            for bidx, batch in enumerate(batches):
                # phase=extract
                self._set_phase(job, "extract", bidx / total * 0.9)
                delta = self._extract_delta(job, batch, fragment)

                # phase=align
                self._set_phase(job, "align", (bidx + 0.3) / total * 0.9)
                delta = self._align_delta(job.ontology_id, delta, fragment)

                # phase=judge
                self._set_phase(job, "judge", (bidx + 0.6) / total * 0.9)
                verdicts = self.rule_judge(job.ontology_id, delta, scope)
                for v in self._llm_judge_optional(job.mode, delta):
                    verdicts.append(v)

                # phase=merge
                self._set_phase(job, "merge", (bidx + 0.8) / total * 0.9)
                merge_stats = self._merge_delta(job.ontology_id, delta, verdicts, job.mode)

                batch_result = {
                    "batch_index": bidx,
                    "tables": [getattr(t, "table_name", None) for t in batch],
                    "delta": delta,
                    "verdicts": verdicts,
                    "merge": merge_stats,
                }
                all_batch_results.append(batch_result)
                job.delta_json = {"batches": all_batch_results}
                self.db.add(job)
                self.db.commit()

            self._set_phase(job, "done", 1.0)
            job.status = OntologyJobStatus.SUCCEEDED
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            self.db.add(job)
            self.db.commit()
        except Exception as exc:
            logger.exception("ontology build failed")
            job.status = OntologyJobStatus.FAILED
            job.error_detail = str(exc)[:2000]
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            self.db.add(job)
            self.db.commit()

    def _sort_tables_for_extract(self, tables: list[Any]) -> list[Any]:
        def score(t: Any) -> tuple:
            name = (t.table_name or "").lower()
            entity = 0
            # entity_candidate annotations bump priority
            try:
                from app.db.models.meta_model import Annotation, AnnotationLabelKind

                anns = (
                    self.db.query(Annotation)
                    .filter(
                        Annotation.target_type == "table",
                        Annotation.target_id == t.id,
                        Annotation.label_kind == AnnotationLabelKind.ENTITY_CANDIDATE,
                        Annotation.status == "accepted",
                    )
                    .all()
                )
                if anns:
                    entity = 2
            except Exception:
                pass
            if any(x in name for x in ("dim_", "dwd_", "cust", "user", "party", "product", "contract")):
                entity = max(entity, 1)
            fact = 1 if any(x in name for x in ("fact_", "dws_", "txn", "log", "detail")) else 0
            row_count = int(t.row_count or 0)
            return (-entity, fact, -row_count, name)

        return sorted(tables, key=score)

    def _core_summary(self, ontology_id: int) -> list[dict[str, Any]]:
        ots = self.object_types.list(ontology_id)
        links = self.link_types.list(ontology_id)
        return [
            {
                "key": ot.key,
                "display_name": ot.display_name,
                "definition": (ot.definition or "")[:120],
                "status": _enum_val(ot.status),
            }
            for ot in ots
            if _enum_val(ot.status) != "rejected"
        ] + [
            {"link_key": lk.key, "from": lk.from_key, "to": lk.to_key}
            for lk in links
            if _enum_val(lk.status) != "rejected"
        ]

    def _extract_delta(
        self,
        job: OntologyBuildJob,
        batch: list[Any],
        fragment: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        mode = job.mode or "rules"
        if mode in ("llm", "hybrid"):
            try:
                return self._extract_via_llm(job, batch, fragment)
            except Exception as exc:
                logger.warning("LLM extract fallback to rules: %s", exc)
        return self._extract_via_rules(job, batch, fragment)

    def _extract_via_rules(
        self,
        job: OntologyBuildJob,
        batch: list[Any],
        fragment: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        delta: dict[str, Any] = {
            "new_object_types": [],
            "new_properties": [],
            "new_link_types": [],
            "mappings": [],
            "aligned_to_existing": [],
            "conflicts": [],
        }
        frag_keys = {
            ot["key"].lower(): ot for ot in (fragment or {}).get("object_types", [])
        }
        scope = job.scope_json if isinstance(job.scope_json, dict) else {}
        source_id = scope.get("source_id")
        database = scope.get("database") or ""

        for table in batch:
            tname = table.table_name
            key = _normalize_key(tname)
            # strip common prefixes
            for prefix in ("dwd_", "dim_", "ods_", "dws_", "tmp_", "fact_"):
                if key.startswith(prefix):
                    key = key[len(prefix) :]
                    break
            display = table.biz_name or table.table_comment or tname
            conf = 0.8
            aligned = None
            for fk, fot in frag_keys.items():
                if fk in key or key in fk or fk.replace("_", "") in key.replace("_", ""):
                    aligned = fot
                    key = fot["key"]
                    display = fot.get("display_name") or display
                    conf = 0.9
                    break
            ot = {
                "key": _normalize_key(key) if not aligned else aligned["key"],
                "display_name": display,
                "definition": table.biz_description or table.table_comment or (aligned or {}).get("definition"),
                "parent_key": (aligned or {}).get("parent_key"),
                "aliases": (aligned or {}).get("aliases") or [],
                "confidence": conf,
                "source": "rule",
            }
            # PascalCase keys from fragment stay as-is via normalize that lowercases —
            # keep fragment key casing by re-applying fragment key
            if aligned:
                ot["key"] = aligned["key"]
            else:
            # title-case for readability while keeping snake for uniqueness
                ot["key"] = _normalize_ot_key(key)

            delta["new_object_types"].append(ot)
            if source_id:
                delta["mappings"].append(
                    {
                        "element_type": "object_type",
                        "element_key": ot["key"],
                        "source_id": int(source_id),
                        "database": database,
                        "table_name": tname,
                        "column_name": None,
                        "confidence": conf,
                        "source": "rule",
                    }
                )

            cols = self.meta_columns.list_by_table(table.id) if hasattr(table, "id") else []
            for col in cols:
                pkey = _normalize_key(col.column_name)
                delta["new_properties"].append(
                    {
                        "object_type_key": ot["key"],
                        "key": pkey,
                        "display_name": col.biz_name or col.column_comment or col.column_name,
                        "data_type": col.data_type,
                        "definition": col.biz_description or col.column_comment,
                        "confidence": 0.75,
                        "source": "rule",
                    }
                )
                if source_id:
                    delta["mappings"].append(
                        {
                            "element_type": "property",
                            "element_key": f"{ot['key']}.{pkey}",
                            "source_id": int(source_id),
                            "database": database,
                            "table_name": tname,
                            "column_name": col.column_name,
                            "confidence": 0.75,
                            "source": "rule",
                        }
                    )

        # seed fragment classes when no tables
        if not batch and fragment:
            for fot in fragment.get("object_types", []):
                delta["new_object_types"].append(
                    {
                        "key": fot["key"],
                        "display_name": fot["display_name"],
                        "definition": fot.get("definition"),
                        "parent_key": fot.get("parent_key"),
                        "aliases": fot.get("aliases") or [],
                        "confidence": 0.9,
                        "source": "rule",
                    }
                )
            for fl in fragment.get("link_types", []):
                delta["new_link_types"].append(
                    {
                        "key": fl["key"],
                        "display_name": fl["display_name"],
                        "from_key": fl["from_key"],
                        "to_key": fl["to_key"],
                        "cardinality": fl.get("cardinality"),
                        "definition": fl.get("definition"),
                        "confidence": 0.9,
                        "source": "rule",
                    }
                )
        return delta

    def _extract_via_llm(
        self,
        job: OntologyBuildJob,
        batch: list[Any],
        fragment: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        client = resolve_llm_client(self.db)
        summary = self._core_summary(job.ontology_id)
        tables_ctx = []
        for t in batch:
            cols = self.meta_columns.list_by_table(t.id)
            tables_ctx.append(
                {
                    "table": t.table_name,
                    "comment": t.table_comment,
                    "biz_name": t.biz_name,
                    "columns": [
                        {
                            "name": c.column_name,
                            "type": c.data_type,
                            "comment": c.column_comment,
                        }
                        for c in cols[:40]
                    ],
                }
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是本体工程师。根据表结构生成本体 delta JSON。"
                    "只输出 JSON，字段: new_object_types, new_properties, new_link_types, "
                    "mappings, aligned_to_existing, conflicts。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "core_summary": summary[:50],
                        "domain_fragment": fragment,
                        "tables": tables_ctx,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        data = client.chat_json(messages)
        if not isinstance(data, dict):
            raise BusinessException("LLM 返回非对象", code="LLM_BAD_DELTA")
        for k in (
            "new_object_types",
            "new_properties",
            "new_link_types",
            "mappings",
            "aligned_to_existing",
            "conflicts",
        ):
            data.setdefault(k, [])
        return data

    def _align_delta(
        self,
        ontology_id: int,
        delta: dict[str, Any],
        fragment: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        existing = {ot.key.lower(): ot for ot in self.object_types.list(ontology_id)}
        frag_by_alias: dict[str, dict[str, Any]] = {}
        for fot in (fragment or {}).get("object_types", []):
            frag_by_alias[fot["key"].lower()] = fot
            for a in fot.get("aliases") or []:
                frag_by_alias[str(a).lower()] = fot

        existing_keys = {ot.key for ot in self.object_types.list(ontology_id)}

        aligned_ots = []
        for ot in delta.get("new_object_types") or []:
            raw_key = ot.get("key") or ot.get("display_name") or "unnamed"
            # keep PascalCase fragment keys; otherwise snake
            if raw_key in {f["key"] for f in (fragment or {}).get("object_types", [])}:
                key = raw_key
            else:
                key = _normalize_ot_key(raw_key)
            display = (ot.get("display_name") or key).strip()
            aliases = list(ot.get("aliases") or [])
            # synonym merge via fragment aliases / display
            match = frag_by_alias.get(key.lower()) or frag_by_alias.get(display.lower())
            for a in aliases:
                match = match or frag_by_alias.get(str(a).lower())
            if match:
                key = match["key"]
                display = match.get("display_name") or display
                ot["parent_key"] = ot.get("parent_key") or match.get("parent_key")
                aliases = list({*(aliases), *(match.get("aliases") or [])})
                delta.setdefault("aligned_to_existing", []).append(
                    {"proposed": raw_key, "existing": key, "reason": "domain_fragment"}
                )
            elif key.lower() in existing:
                ex = existing[key.lower()]
                key = ex.key
                delta.setdefault("aligned_to_existing", []).append(
                    {"proposed": raw_key, "existing": key, "reason": "core_key_match"}
                )

            parent = ot.get("parent_key")
            if parent:
                parent_norm = parent if parent in existing_keys or parent == key else _normalize_key(parent)
                # also accept fragment parent keys
                frag_keys = {f["key"] for f in (fragment or {}).get("object_types", [])}
                if parent not in existing_keys and parent not in frag_keys and parent_norm not in existing_keys:
                    # degrade to top-level
                    conf = float(ot.get("confidence") or 0.8) * 0.85
                    ot["confidence"] = conf
                    parent = None
                else:
                    parent = parent if parent in frag_keys or parent in existing_keys else parent_norm

            aligned_ots.append(
                {
                    **ot,
                    "key": key,
                    "display_name": display,
                    "parent_key": parent,
                    "aliases": aliases,
                    "confidence": float(ot.get("confidence") or 0.7),
                }
            )
        delta["new_object_types"] = aligned_ots

        for prop in delta.get("new_properties") or []:
            prop["key"] = _normalize_key(prop.get("key") or "prop")
            otk = prop.get("object_type_key")
            if otk and otk not in {o["key"] for o in aligned_ots} and otk.lower() not in existing:
                # try normalize
                prop["object_type_key"] = _normalize_key(otk)

        for link in delta.get("new_link_types") or []:
            link["key"] = link.get("key") or _normalize_key(
                f"{link.get('from_key')}_{link.get('to_key')}"
            )
            if not re.match(r"^[A-Za-z]", str(link["key"])):
                link["key"] = _normalize_key(link["key"])
            else:
                # keep snake for link keys from fragment
                if "_" in str(link["key"]) or str(link["key"]).islower():
                    link["key"] = _normalize_key(link["key"]) if link["key"].islower() else link["key"]
                    if link["key"] != link.get("key"):
                        pass
                # prefer fragment-style snake keys
                link["key"] = str(link["key"]) if link["key"] in {
                    fl["key"] for fl in (fragment or {}).get("link_types", [])
                } else _normalize_key(link["key"])

        return delta

    def rule_judge(
        self,
        ontology_id: int,
        delta: dict[str, Any],
        scope: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """机械规则 Judge：返回 verdicts 列表。"""
        verdicts: list[dict[str, Any]] = []
        existing_ot = {ot.key for ot in self.object_types.list(ontology_id)}
        proposed_ot = {ot["key"] for ot in delta.get("new_object_types") or []}
        all_ot = existing_ot | proposed_ot

        # key uniqueness within delta
        seen_ot: set[str] = set()
        for ot in delta.get("new_object_types") or []:
            key = ot["key"]
            target = f"object_type:{key}"
            if key in seen_ot:
                verdicts.append(
                    {"target": target, "verdict": "fail", "reason": "duplicate_key_in_delta", "confidence_adjust": -1.0}
                )
            elif key in existing_ot:
                verdicts.append(
                    {"target": target, "verdict": "warn", "reason": "key_already_exists", "confidence_adjust": -0.05}
                )
            else:
                verdicts.append(
                    {"target": target, "verdict": "pass", "reason": "ok", "confidence_adjust": 0.0}
                )
            seen_ot.add(key)

        for prop in delta.get("new_properties") or []:
            otk = prop.get("object_type_key")
            target = f"property:{otk}.{prop.get('key')}"
            if not otk or otk not in all_ot:
                verdicts.append(
                    {
                        "target": target,
                        "verdict": "fail",
                        "reason": "property_orphan_object_type",
                        "confidence_adjust": -1.0,
                    }
                )
            else:
                verdicts.append(
                    {"target": target, "verdict": "pass", "reason": "ok", "confidence_adjust": 0.0}
                )

        for link in delta.get("new_link_types") or []:
            target = f"link_type:{link.get('key')}"
            fk, tk = link.get("from_key"), link.get("to_key")
            if not fk or not tk or fk not in all_ot or tk not in all_ot:
                verdicts.append(
                    {
                        "target": target,
                        "verdict": "fail",
                        "reason": "link_from_to_missing",
                        "confidence_adjust": -1.0,
                    }
                )
            else:
                verdicts.append(
                    {"target": target, "verdict": "pass", "reason": "ok", "confidence_adjust": 0.0}
                )

        # mapping physical existence
        scope = scope or {}
        for mp in delta.get("mappings") or []:
            target = f"mapping:{mp.get('element_key')}"
            sid = mp.get("source_id") or scope.get("source_id")
            database = mp.get("database") or scope.get("database")
            table_name = mp.get("table_name")
            if not sid or not database or not table_name:
                verdicts.append(
                    {
                        "target": target,
                        "verdict": "fail",
                        "reason": "mapping_incomplete",
                        "confidence_adjust": -1.0,
                    }
                )
                continue
            meta_t = self.meta_tables.get_by_uq(int(sid), str(database), str(table_name))
            if not meta_t:
                verdicts.append(
                    {
                        "target": target,
                        "verdict": "fail",
                        "reason": "mapping_table_not_in_meta",
                        "confidence_adjust": -1.0,
                    }
                )
                continue
            col = mp.get("column_name")
            if col:
                cols = self.meta_columns.list_by_table(meta_t.id)
                if not any(c.column_name == col for c in cols):
                    verdicts.append(
                        {
                            "target": target,
                            "verdict": "fail",
                            "reason": "mapping_column_not_in_meta",
                            "confidence_adjust": -1.0,
                        }
                    )
                    continue
            verdicts.append(
                {"target": target, "verdict": "pass", "reason": "ok", "confidence_adjust": 0.0}
            )
        return verdicts

    def _llm_judge_optional(self, mode: str, delta: dict[str, Any]) -> list[dict[str, Any]]:
        if mode not in ("llm", "hybrid"):
            return []
        client = resolve_llm_client(self.db)
        if not client.is_configured():
            return []
        try:
            data = client.chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是本体审稿人。检查 delta 是否合理，输出 "
                            '{"verdicts":[{"target","verdict":"pass|warn|fail","reason","confidence_adjust"}]}'
                        ),
                    },
                    {"role": "user", "content": json.dumps(delta, ensure_ascii=False)[:12000]},
                ]
            )
            return list((data or {}).get("verdicts") or [])
        except Exception as exc:
            logger.warning("LLM judge skipped: %s", exc)
            return []

    def _verdict_for(self, verdicts: list[dict[str, Any]], target: str) -> dict[str, Any]:
        hits = [v for v in verdicts if v.get("target") == target]
        if not hits:
            return {"verdict": "pass", "confidence_adjust": 0.0, "reason": "no_verdict"}
        # worst wins
        order = {"fail": 0, "warn": 1, "pass": 2}
        hits.sort(key=lambda v: order.get(str(v.get("verdict")), 9))
        return hits[0]

    def _merge_delta(
        self,
        ontology_id: int,
        delta: dict[str, Any],
        verdicts: list[dict[str, Any]],
        mode: str,
    ) -> dict[str, Any]:
        stats = {"accepted": 0, "draft": 0, "rejected": 0}
        source = "llm" if mode in ("llm", "hybrid") else "rule"
        ot_id_by_key: dict[str, int] = {
            ot.key: ot.id for ot in self.object_types.list(ontology_id)
        }

        for ot in delta.get("new_object_types") or []:
            target = f"object_type:{ot['key']}"
            v = self._verdict_for(verdicts, target)
            conf = float(ot.get("confidence") or 0.7) + float(v.get("confidence_adjust") or 0)
            conf = max(0.0, min(1.0, conf))
            status = confidence_tier(conf, str(v.get("verdict") or "pass"))
            stats[status] = stats.get(status, 0) + 1
            if status == "rejected":
                continue
            existing = self.object_types.get_by_key(ontology_id, ot["key"])
            if existing:
                if float(existing.confidence or 0) < conf:
                    existing.confidence = conf
                    existing.status = status
                    existing.definition = ot.get("definition") or existing.definition
                    existing.display_name = ot.get("display_name") or existing.display_name
                    self.db.add(existing)
                ot_id_by_key[existing.key] = existing.id
                continue
            row = OntologyObjectType(
                ontology_id=ontology_id,
                key=ot["key"],
                display_name=ot.get("display_name") or ot["key"],
                definition=ot.get("definition"),
                parent_key=ot.get("parent_key"),
                aliases_json=ot.get("aliases") or [],
                confidence=conf,
                source=source,
                status=status,
            )
            self.object_types.add(row)
            self.db.flush()
            ot_id_by_key[row.key] = row.id

        for prop in delta.get("new_properties") or []:
            otk = prop.get("object_type_key")
            target = f"property:{otk}.{prop.get('key')}"
            v = self._verdict_for(verdicts, target)
            conf = float(prop.get("confidence") or 0.7) + float(v.get("confidence_adjust") or 0)
            conf = max(0.0, min(1.0, conf))
            status = confidence_tier(conf, str(v.get("verdict") or "pass"))
            stats[status] = stats.get(status, 0) + 1
            if status == "rejected":
                continue
            ot_id = ot_id_by_key.get(otk or "")
            if not ot_id:
                continue
            row = OntologyProperty(
                ontology_id=ontology_id,
                object_type_id=ot_id,
                key=prop["key"],
                display_name=prop.get("display_name") or prop["key"],
                data_type=prop.get("data_type"),
                definition=prop.get("definition"),
                confidence=conf,
                source=source,
                status=status,
            )
            self.properties.add(row)

        for link in delta.get("new_link_types") or []:
            target = f"link_type:{link.get('key')}"
            v = self._verdict_for(verdicts, target)
            conf = float(link.get("confidence") or 0.7) + float(v.get("confidence_adjust") or 0)
            conf = max(0.0, min(1.0, conf))
            status = confidence_tier(conf, str(v.get("verdict") or "pass"))
            stats[status] = stats.get(status, 0) + 1
            if status == "rejected":
                continue
            if self.link_types.get_by_key(ontology_id, link["key"]):
                continue
            row = OntologyLinkType(
                ontology_id=ontology_id,
                key=link["key"],
                display_name=link.get("display_name") or link["key"],
                from_key=link["from_key"],
                to_key=link["to_key"],
                cardinality=link.get("cardinality"),
                definition=link.get("definition"),
                confidence=conf,
                source=source,
                status=status,
                evidence_json=link.get("evidence"),
            )
            self.link_types.add(row)

        for mp in delta.get("mappings") or []:
            target = f"mapping:{mp.get('element_key')}"
            v = self._verdict_for(verdicts, target)
            conf = float(mp.get("confidence") or 0.7) + float(v.get("confidence_adjust") or 0)
            conf = max(0.0, min(1.0, conf))
            status = confidence_tier(conf, str(v.get("verdict") or "pass"))
            stats[status] = stats.get(status, 0) + 1
            if status == "rejected":
                continue
            row = OntologyMapping(
                ontology_id=ontology_id,
                element_type=mp.get("element_type") or "object_type",
                element_key=str(mp.get("element_key")),
                source_id=int(mp["source_id"]),
                database=str(mp["database"]),
                table_name=str(mp["table_name"]),
                column_name=mp.get("column_name"),
                confidence=conf,
                source=source,
                status=status,
            )
            self.mappings.add(row)

        self.db.commit()
        return stats

    # ------------------------------------------------------------------
    # Relation inference (3-way voting)
    # ------------------------------------------------------------------

    def _connector_for(self, row: DataSource) -> DataSourceConnector:
        st = row.source_type.value if hasattr(row.source_type, "value") else str(row.source_type)
        return DataSourceConnector(
            source_type=st,
            host=row.host,
            port=row.port,
            username=row.username,
            password=row.password,
            database=row.database,
            charset=row.charset or "utf8mb4",
        )

    def infer_relations(self, oid: int, req: InferRelationsRequest) -> list[dict[str, Any]]:
        self.get_ontology(oid)
        scope = req.scope or {}
        source_id = scope.get("source_id")
        database = scope.get("database")
        if not source_id or not database:
            raise BusinessException("scope 需要 source_id 与 database", code="INVALID_SCOPE")
        src = self.sources.get(int(source_id))
        if not src:
            raise NotFoundException(f"数据源不存在: {source_id}")

        tables = self.meta_tables.list_by_source_db(int(source_id), str(database))
        wanted = set(scope.get("tables") or [])
        if wanted:
            tables = [t for t in tables if t.table_name in wanted]

        # index primary-ish columns
        table_cols: dict[str, list[Any]] = {}
        pk_map: dict[str, str] = {}  # table -> pk col
        for t in tables:
            cols = self.meta_columns.list_by_table(t.id)
            table_cols[t.table_name] = cols
            pk = None
            for c in cols:
                if (c.column_key or "").upper() == "PRI" or c.column_name.lower() in ("id", f"{t.table_name}_id"):
                    pk = c.column_name
                    break
            if pk:
                pk_map[t.table_name] = pk

        connector = self._connector_for(src)
        candidates: list[dict[str, Any]] = []

        for t in tables:
            for col in table_cols.get(t.table_name, []):
                m = _ID_SUFFIX_RE.match(col.column_name or "")
                if not m:
                    continue
                root = m.group("root").lower()
                # find target table
                target_table = None
                for tn in pk_map:
                    tn_l = tn.lower()
                    if tn_l == root or tn_l.endswith(f"_{root}") or tn_l.replace("_", "") == root.replace("_", ""):
                        target_table = tn
                        break
                    # cust -> dwd_cust_info
                    if root in tn_l and pk_map.get(tn):
                        target_table = tn
                        break
                if not target_table or target_table == t.table_name:
                    continue
                target_pk = pk_map[target_table]

                naming_w = 0.4
                overlap_w = 0.0
                overlap = 0.0
                veto = False
                try:
                    overlap = float(
                        connector.overlap_ratio(
                            str(database),
                            t.table_name,
                            col.column_name,
                            target_table,
                            target_pk,
                        )
                    )
                except Exception as exc:
                    logger.warning("overlap_ratio failed: %s", exc)
                    overlap = 0.0
                if overlap < 0.5:
                    veto = True
                elif overlap > 0.95:
                    overlap_w = 0.4
                elif overlap >= 0.8:
                    overlap_w = 0.25
                else:
                    overlap_w = 0.1

                llm_w = 0.0
                llm_card = None
                llm_rel = f"{_normalize_key(t.table_name)}_to_{_normalize_key(target_table)}"
                client = resolve_llm_client(self.db)
                if client.is_configured():
                    try:
                        j = client.chat_json(
                            [
                                {
                                    "role": "system",
                                    "content": '输出 JSON: {"relation":str,"cardinality":"1-1|n-1|1-n|n-n","confidence":float}',
                                },
                                {
                                    "role": "user",
                                    "content": json.dumps(
                                        {
                                            "from_table": t.table_name,
                                            "from_col": col.column_name,
                                            "to_table": target_table,
                                            "to_col": target_pk,
                                        },
                                        ensure_ascii=False,
                                    ),
                                },
                            ]
                        )
                        llm_w = 0.2 * float(j.get("confidence") or 0.5)
                        llm_card = j.get("cardinality")
                        if j.get("relation"):
                            llm_rel = _normalize_key(str(j["relation"]))
                    except Exception:
                        llm_w = 0.0

                if veto:
                    continue

                # cardinality from distinct_ratio if available
                distinct_ratio = getattr(col, "distinct_ratio", None)
                if distinct_ratio is None:
                    distinct_ratio = 0.5
                card = llm_card or ("1-1" if float(distinct_ratio) >= 0.95 else "n-1")

                conf = naming_w + overlap_w + llm_w
                from_key = _normalize_key(t.table_name)
                to_key = _normalize_key(target_table)
                for prefix in ("dwd_", "dim_", "ods_", "dws_", "tmp_", "fact_"):
                    if from_key.startswith(prefix):
                        from_key = from_key[len(prefix) :]
                    if to_key.startswith(prefix):
                        to_key = to_key[len(prefix) :]

                cand = {
                    "key": llm_rel,
                    "display_name": f"{t.table_name} → {target_table}",
                    "from_key": from_key,
                    "to_key": to_key,
                    "cardinality": card,
                    "confidence": round(min(1.0, conf), 4),
                    "source": "rule",
                    "status": confidence_tier(conf),
                    "evidence": {
                        "naming_match": True,
                        "naming_weight": naming_w,
                        "overlap_ratio": overlap,
                        "overlap_weight": overlap_w,
                        "llm_weight": llm_w,
                        "from_table": t.table_name,
                        "from_column": col.column_name,
                        "to_table": target_table,
                        "to_column": target_pk,
                    },
                }
                candidates.append(cand)

                # persist as draft/accepted link if endpoints exist
                ot_keys = {ot.key for ot in self.object_types.list(oid)}
                # fuzzy: also match normalized
                if from_key in ot_keys and to_key in ot_keys:
                    if not self.link_types.get_by_key(oid, cand["key"]):
                        self.link_types.add(
                            OntologyLinkType(
                                ontology_id=oid,
                                key=cand["key"],
                                display_name=cand["display_name"],
                                from_key=from_key,
                                to_key=to_key,
                                cardinality=card,
                                definition="inferred relation",
                                confidence=cand["confidence"],
                                source=OntologyElementSource.RULE,
                                status=cand["status"],
                                evidence_json=cand["evidence"],
                            )
                        )
        self.db.commit()
        return candidates

    # ------------------------------------------------------------------
    # Publish / rollback / export / graph
    # ------------------------------------------------------------------

    def _build_snapshot(self, oid: int, *, accepted_only: bool = True) -> dict[str, Any]:
        status = "accepted" if accepted_only else None
        ots = self.object_types.list(oid, status=status)
        props = self.properties.list_by_ontology(oid, status=status)
        links = self.link_types.list(oid, status=status)
        maps = self.mappings.list(oid, status=status)
        metrics = self.metrics.list(oid, status=status)
        cqs = self.cqs.list(oid)
        return {
            "object_types": [_json_safe(self._ot_resp(r)) for r in ots],
            "properties": [_json_safe(self._prop_resp(r)) for r in props],
            "link_types": [_json_safe(self._link_resp(r)) for r in links],
            "mappings": [_json_safe(self._mapping_resp(r)) for r in maps],
            "metrics": [
                _json_safe(
                    {
                        "id": m.id,
                        "key": m.key,
                        "display_name": m.display_name,
                        "definition": m.definition,
                        "sql_expr": m.sql_expr,
                        "unit": m.unit,
                        "confidence": float(m.confidence or 0),
                        "source": _enum_val(m.source),
                        "status": _enum_val(m.status),
                    }
                )
                for m in metrics
            ],
            "cqs": [
                _json_safe(
                    {
                        "id": c.id,
                        "question": c.question,
                        "category": c.category,
                        "verify_status": _enum_val(c.verify_status),
                        "related_keys": c.related_keys_json or [],
                    }
                )
                for c in cqs
            ],
        }

    def _diff_snapshots(self, prev: Optional[dict], curr: dict) -> dict[str, Any]:
        def keys(items: list, field: str = "key") -> set[str]:
            return {str(i.get(field)) for i in (items or []) if i.get(field) is not None}

        prev = prev or {}
        diff: dict[str, Any] = {}
        for section in ("object_types", "properties", "link_types", "mappings", "metrics"):
            pk = keys(prev.get(section) or [])
            ck = keys(curr.get(section) or [])
            # properties use object_type_id+key; still ok for coarse diff
            if section == "mappings":
                pk = {f"{i.get('element_type')}:{i.get('element_key')}" for i in (prev.get(section) or [])}
                ck = {f"{i.get('element_type')}:{i.get('element_key')}" for i in (curr.get(section) or [])}
            diff[section] = {
                "added": sorted(ck - pk),
                "removed": sorted(pk - ck),
            }
        return diff

    def publish_version(self, oid: int, change_note: Optional[str], user_id: int) -> OntologyVersion:
        ont = self.get_ontology(oid)
        snapshot = self._build_snapshot(oid, accepted_only=True)
        new_ver = int(ont.current_version or 0) + 1
        prev = None
        if ont.current_version:
            prev_row = self.versions.get(oid, ont.current_version)
            if prev_row:
                prev = prev_row.snapshot_json
        diff = self._diff_snapshots(prev if isinstance(prev, dict) else None, snapshot)
        row = OntologyVersion(
            ontology_id=oid,
            version=new_ver,
            snapshot_json=snapshot,
            diff_json=diff,
            change_note=change_note,
            author_user_id=user_id,
        )
        self.versions.add(row)
        ont.current_version = new_ver
        self.db.add(ont)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_versions(self, oid: int) -> list[OntologyVersion]:
        self.get_ontology(oid)
        return self.versions.list(oid)

    def get_version(self, oid: int, version: int) -> OntologyVersion:
        self.get_ontology(oid)
        row = self.versions.get(oid, version)
        if not row:
            raise NotFoundException(f"版本不存在: v{version}")
        return row

    def rollback_version(self, oid: int, version: int, user_id: int) -> OntologyVersion:
        ont = self.get_ontology(oid)
        snap_row = self.versions.get(oid, version)
        if not snap_row:
            raise NotFoundException(f"版本不存在: v{version}")
        snap = snap_row.snapshot_json if isinstance(snap_row.snapshot_json, dict) else {}

        # clear current elements
        for prop in self.properties.list_by_ontology(oid):
            self.properties.delete(prop)
        for link in self.link_types.list(oid):
            self.link_types.delete(link)
        for mp in self.mappings.list(oid):
            self.mappings.delete(mp)
        for m in self.metrics.list(oid):
            self.metrics.delete(m)
        for ot in self.object_types.list(oid):
            self.object_types.delete(ot)
        self.db.flush()

        key_to_id: dict[str, int] = {}
        for ot in snap.get("object_types") or []:
            row = OntologyObjectType(
                ontology_id=oid,
                key=ot["key"],
                display_name=ot.get("display_name") or ot["key"],
                definition=ot.get("definition"),
                parent_key=ot.get("parent_key"),
                aliases_json=ot.get("aliases") or [],
                confidence=float(ot.get("confidence") or 1.0),
                source=ot.get("source") or "human",
                status=ot.get("status") or "accepted",
            )
            self.object_types.add(row)
            self.db.flush()
            key_to_id[row.key] = row.id

        snap_ot_id_to_key = {
            ot.get("id"): ot["key"] for ot in (snap.get("object_types") or []) if ot.get("id")
        }
        for prop in snap.get("properties") or []:
            ot_key = snap_ot_id_to_key.get(prop.get("object_type_id"))
            ot_id = key_to_id.get(ot_key) if ot_key else None
            if not ot_id:
                ot_id = next(iter(key_to_id.values()), None)
            if not ot_id:
                continue
            self.properties.add(
                OntologyProperty(
                    ontology_id=oid,
                    object_type_id=ot_id,
                    key=prop["key"],
                    display_name=prop.get("display_name") or prop["key"],
                    data_type=prop.get("data_type"),
                    definition=prop.get("definition"),
                    confidence=float(prop.get("confidence") or 1.0),
                    source=prop.get("source") or "human",
                    status=prop.get("status") or "accepted",
                )
            )

        for link in snap.get("link_types") or []:
            self.link_types.add(
                OntologyLinkType(
                    ontology_id=oid,
                    key=link["key"],
                    display_name=link.get("display_name") or link["key"],
                    from_key=link["from_key"],
                    to_key=link["to_key"],
                    cardinality=link.get("cardinality"),
                    definition=link.get("definition"),
                    confidence=float(link.get("confidence") or 1.0),
                    source=link.get("source") or "human",
                    status=link.get("status") or "accepted",
                    evidence_json=link.get("evidence"),
                )
            )

        for mp in snap.get("mappings") or []:
            self.mappings.add(
                OntologyMapping(
                    ontology_id=oid,
                    element_type=mp.get("element_type") or "object_type",
                    element_key=mp["element_key"],
                    source_id=int(mp["source_id"]),
                    database=mp["database"],
                    table_name=mp["table_name"],
                    column_name=mp.get("column_name"),
                    confidence=float(mp.get("confidence") or 1.0),
                    source=mp.get("source") or "human",
                    status=mp.get("status") or "accepted",
                )
            )

        for m in snap.get("metrics") or []:
            self.metrics.add(
                OntologyMetric(
                    ontology_id=oid,
                    key=m["key"],
                    display_name=m.get("display_name") or m["key"],
                    definition=m.get("definition"),
                    sql_expr=m.get("sql_expr"),
                    unit=m.get("unit"),
                    confidence=float(m.get("confidence") or 1.0),
                    source=m.get("source") or "human",
                    status=m.get("status") or "accepted",
                )
            )

        self.db.flush()
        # publish as new version from restored snapshot
        return self.publish_version(oid, f"rollback to v{version}", user_id)

    def export_ontology(self, oid: int, fmt: str = "json") -> str:
        self.get_ontology(oid)
        snap = self._build_snapshot(oid, accepted_only=False)
        # prefer latest published if exists
        ont = self.get_ontology(oid)
        if ont.current_version:
            ver = self.versions.get(oid, ont.current_version)
            if ver and isinstance(ver.snapshot_json, dict):
                snap = ver.snapshot_json

        fmt = (fmt or "json").lower()
        if fmt == "json":
            return json.dumps(snap, ensure_ascii=False, indent=2)
        if fmt == "jsonld":
            return self._to_jsonld(snap)
        if fmt == "turtle":
            return self._to_turtle(snap)
        raise BusinessException(f"不支持的导出格式: {fmt}", code="INVALID_FORMAT")

    def _to_jsonld(self, snap: dict[str, Any]) -> str:
        ctx = {
            "@vocab": "https://ontomind.local/ontology#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "label": "rdfs:label",
            "comment": "rdfs:comment",
            "subClassOf": {"@id": "rdfs:subClassOf", "@type": "@id"},
            "domain": {"@id": "rdfs:domain", "@type": "@id"},
            "range": {"@id": "rdfs:range", "@type": "@id"},
        }
        graph: list[dict[str, Any]] = []
        for ot in snap.get("object_types") or []:
            node: dict[str, Any] = {
                "@id": ot["key"],
                "@type": "rdfs:Class",
                "label": ot.get("display_name"),
                "comment": ot.get("definition"),
            }
            if ot.get("parent_key"):
                node["subClassOf"] = ot["parent_key"]
            graph.append(node)
        for prop in snap.get("properties") or []:
            graph.append(
                {
                    "@id": prop["key"],
                    "@type": "owl:DatatypeProperty",
                    "label": prop.get("display_name"),
                    "comment": prop.get("definition"),
                }
            )
        for link in snap.get("link_types") or []:
            graph.append(
                {
                    "@id": link["key"],
                    "@type": "owl:ObjectProperty",
                    "label": link.get("display_name"),
                    "comment": link.get("definition"),
                    "domain": link.get("from_key"),
                    "range": link.get("to_key"),
                }
            )
        return json.dumps({"@context": ctx, "@graph": graph}, ensure_ascii=False, indent=2)

    def _turtle_escape(self, s: str) -> str:
        return (s or "").replace("\\", "\\\\").replace('"', '\\"')

    def _to_turtle(self, snap: dict[str, Any]) -> str:
        lines = [
            "@prefix : <https://ontomind.local/ontology#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "",
        ]
        for ot in snap.get("object_types") or []:
            key = ot["key"]
            lines.append(f":{key} a rdfs:Class ;")
            lines.append(f'  rdfs:label "{self._turtle_escape(ot.get("display_name") or key)}"')
            if ot.get("definition"):
                lines[-1] += " ;"
                lines.append(f'  rdfs:comment "{self._turtle_escape(ot["definition"])}"')
            if ot.get("parent_key"):
                lines[-1] += " ;"
                lines.append(f"  rdfs:subClassOf :{ot['parent_key']}")
            lines[-1] += " ."
            lines.append("")
        for prop in snap.get("properties") or []:
            key = prop["key"]
            lines.append(f":{key} a owl:DatatypeProperty ;")
            lines.append(f'  rdfs:label "{self._turtle_escape(prop.get("display_name") or key)}" .')
            lines.append("")
        for link in snap.get("link_types") or []:
            key = link["key"]
            lines.append(f":{key} a owl:ObjectProperty ;")
            lines.append(f'  rdfs:label "{self._turtle_escape(link.get("display_name") or key)}" ;')
            lines.append(f"  rdfs:domain :{link['from_key']} ;")
            lines.append(f"  rdfs:range :{link['to_key']} .")
            lines.append("")
        return "\n".join(lines)

    def graph_data(
        self, oid: int, *, focus_key: Optional[str] = None, depth: int = 2
    ) -> dict[str, Any]:
        self.get_ontology(oid)
        ots = [ot for ot in self.object_types.list(oid) if _enum_val(ot.status) != "rejected"]
        links = [lk for lk in self.link_types.list(oid) if _enum_val(lk.status) != "rejected"]
        maps = self.mappings.list(oid, status="accepted")
        table_count: dict[str, int] = {}
        for mp in maps:
            if _enum_val(mp.element_type) == "object_type":
                table_count[mp.element_key] = table_count.get(mp.element_key, 0) + 1

        all_keys = {ot.key for ot in ots}
        keep = set(all_keys)
        if focus_key and focus_key in all_keys:
            keep = {focus_key}
            # undirected BFS on link graph
            adj: dict[str, set[str]] = {k: set() for k in all_keys}
            for lk in links:
                if lk.from_key in adj and lk.to_key in adj:
                    adj[lk.from_key].add(lk.to_key)
                    adj[lk.to_key].add(lk.from_key)
            q: deque[tuple[str, int]] = deque([(focus_key, 0)])
            seen = {focus_key}
            while q:
                node, d = q.popleft()
                if d >= depth:
                    continue
                for nb in adj.get(node, ()):
                    if nb not in seen:
                        seen.add(nb)
                        keep.add(nb)
                        q.append((nb, d + 1))
            keep = seen

        nodes = [
            {
                "id": str(ot.id),
                "key": ot.key,
                "label": ot.display_name,
                "parent": ot.parent_key,
                "confidence": float(ot.confidence or 0),
                "status": _enum_val(ot.status),
                "table_count": table_count.get(ot.key, 0),
            }
            for ot in ots
            if ot.key in keep
        ]
        edges = [
            {
                "id": str(lk.id),
                "source": lk.from_key,
                "target": lk.to_key,
                "label": lk.display_name or lk.key,
                "cardinality": lk.cardinality,
                "confidence": float(lk.confidence or 0),
                "status": _enum_val(lk.status),
            }
            for lk in links
            if lk.from_key in keep and lk.to_key in keep
        ]
        return {"nodes": nodes, "edges": edges}
