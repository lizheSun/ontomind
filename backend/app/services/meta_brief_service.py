"""库级概况分析（rules 优先；llm 可选）。"""
from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.meta_model import JobKind, MetaDatabaseBrief, MetaScanJob, ScanStatus
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.repositories.meta_repo import (
    MetaColumnRepository,
    MetaDatabaseBriefRepository,
    MetaScanJobRepository,
    MetaTableRepository,
)
from app.schemas.metadata_schema import DatabaseBriefCreate, DatabaseBriefResponse
from app.services.job_runner import open_job_session, run_in_background
from app.services.llm_settings_service import resolve_llm_client

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MetaBriefService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = MetaScanJobRepository(db)
        self.briefs = MetaDatabaseBriefRepository(db)
        self.tables = MetaTableRepository(db)
        self.columns = MetaColumnRepository(db)
        self.sources = DataSourceRepository(db)

    def get_brief(self, source_id: int, database: str) -> Optional[DatabaseBriefResponse]:
        row = self.briefs.get_by_uq(source_id, database)
        return DatabaseBriefResponse.model_validate(row) if row else None

    def create_brief_job(self, req: DatabaseBriefCreate) -> MetaScanJob:
        src = self.sources.get(req.source_id)
        if not src:
            raise NotFoundException(f"数据源不存在: {req.source_id}")
        job = MetaScanJob(
            source_id=req.source_id,
            database=req.database.strip(),
            job_kind=JobKind.BRIEF,
            status=ScanStatus.PENDING,
            progress=0.0,
            mode=req.mode,
        )
        self.jobs.add(job)
        self.db.commit()
        self.db.refresh(job)
        run_in_background(MetaBriefService._run_entrypoint, job.id)
        return job

    @staticmethod
    def _run_entrypoint(job_id: int) -> None:
        db = open_job_session()
        try:
            MetaBriefService(db)._run(job_id)
        finally:
            db.close()

    def _run(self, job_id: int) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        t0 = time.time()
        job.status = ScanStatus.RUNNING
        job.started_at = _utcnow()
        job.progress = 0.1
        self.db.commit()
        try:
            tables = self.tables.list_by_source_db(job.source_id, job.database)
            cols = self.columns.list_by_table_ids([t.id for t in tables])
            stats, content = self._rules_brief(tables, cols)
            mode = (job.mode or "rules").lower()
            if mode == "llm":
                content = self._maybe_llm_brief(job, tables, cols, content, stats)
            row = self.briefs.get_by_uq(job.source_id, job.database)
            if row:
                row.mode = mode
                row.content_md = content
                row.stats_json = stats
                row.job_id = job.id
            else:
                self.briefs.add(
                    MetaDatabaseBrief(
                        source_id=job.source_id,
                        database=job.database,
                        mode=mode,
                        content_md=content,
                        stats_json=stats,
                        job_id=job.id,
                    )
                )
            job.progress = 1.0
            job.status = ScanStatus.SUCCEEDED
            job.stats_json = stats
            job.finished_at = _utcnow()
            job.duration_ms = int((time.time() - t0) * 1000)
            self.db.commit()
        except Exception as exc:
            logger.exception("brief job %s failed", job_id)
            job.status = ScanStatus.FAILED
            job.error_detail = str(exc)[:2000]
            job.finished_at = _utcnow()
            job.duration_ms = int((time.time() - t0) * 1000)
            self.db.commit()

    def _rules_brief(self, tables, cols) -> tuple[dict, str]:
        layer = Counter()
        for t in tables:
            name = (t.table_name or "").lower()
            hit = "other"
            for p in ("ods_", "dwd_", "dws_", "dim_", "fact_", "ads_", "tmp_"):
                if name.startswith(p):
                    hit = p.rstrip("_")
                    break
            layer[hit] += 1
        commented_t = sum(1 for t in tables if t.table_comment)
        commented_c = sum(1 for c in cols if c.column_comment)
        pii = sum(1 for c in cols if (c.pii_level or "") in ("L2", "L3"))
        biz = sum(1 for c in cols if c.biz_name)
        top_tables = sorted(tables, key=lambda x: -(x.row_count or 0))[:8]
        suggest_cols = [
            c
            for c in cols
            if not c.biz_name
            and any(k in (c.column_name or "").lower() for k in ("id", "phone", "mobile", "name", "amt", "amt", "no"))
        ][:10]
        stats = {
            "table_count": len(tables),
            "column_count": len(cols),
            "layer_dist": dict(layer),
            "table_comment_rate": round(commented_t / len(tables), 3) if tables else 0,
            "column_comment_rate": round(commented_c / len(cols), 3) if cols else 0,
            "pii_hot_columns": pii,
            "biz_named_columns": biz,
        }
        lines = [
            f"## 库概况（规则摘要）",
            f"- 表 **{len(tables)}** · 字段 **{len(cols)}**",
            f"- 分层分布：{', '.join(f'{k}={v}' for k, v in sorted(layer.items())) or '无'}",
            f"- 表注释覆盖率 {stats['table_comment_rate']*100:.0f}% · 列注释 {stats['column_comment_rate']*100:.0f}%",
            f"- 已有业务名字段 {biz} · 疑似 PII(L2/L3) {pii}",
            "",
            "### 大表（按行数）",
        ]
        for t in top_tables:
            lines.append(f"- `{t.table_name}` rows≈{t.row_count or '?'} · {t.table_comment or '无注释'}")
        if suggest_cols:
            lines.append("")
            lines.append("### 建议优先标注")
            # need table names
            tmap = {t.id: t.table_name for t in tables}
            for c in suggest_cols:
                lines.append(f"- `{tmap.get(c.table_id, '?')}.{c.column_name}`")
        return stats, "\n".join(lines)

    def _maybe_llm_brief(self, job, tables, cols, rules_md: str, stats: dict) -> str:
        client = resolve_llm_client(self.db)
        if not client.is_configured():
            return rules_md + "\n\n> LLM 未配置，已回退规则摘要。可前往 GovOps → LLM 配置。"
        sample = []
        for t in tables[:20]:
            sample.append(
                {
                    "table": t.table_name,
                    "comment": t.table_comment,
                    "rows": t.row_count,
                    "domain": t.domain,
                }
            )
        messages = [
            {
                "role": "system",
                "content": "你是数仓治理专家。根据表清单写简洁中文库概况 Markdown（分层、主题、风险、标注优先级）。只输出 Markdown。",
            },
            {
                "role": "user",
                "content": f"数据库={job.database}\n统计={stats}\n表样例={sample}\n规则摘要:\n{rules_md}",
            },
        ]
        try:
            return client.chat(messages, temperature=0.2, max_tokens=2048)
        except Exception as exc:
            logger.warning("llm brief failed: %s", exc)
            return rules_md + f"\n\n> LLM 调用失败：{exc}"
