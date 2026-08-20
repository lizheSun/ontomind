"""元数据 Repository — 仅 flush。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models.meta_model import (
    Annotation,
    GlossaryTerm,
    MetaColumn,
    MetaColumnStandard,
    MetaColumnStandardHistory,
    MetaDatabaseBrief,
    MetaScanJob,
    MetaStandard,
    MetaStandardVersion,
    MetaTable,
    PlatformLlmSetting,
)


class MetaScanJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaScanJob) -> MetaScanJob:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, job_id: int) -> Optional[MetaScanJob]:
        return self.db.get(MetaScanJob, job_id)

    def list(
        self,
        *,
        source_id: Optional[int] = None,
        database: Optional[str] = None,
        job_kind: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MetaScanJob]:
        q = self.db.query(MetaScanJob)
        if source_id is not None:
            q = q.filter(MetaScanJob.source_id == source_id)
        if database:
            q = q.filter(MetaScanJob.database == database)
        if job_kind:
            q = q.filter(MetaScanJob.job_kind == job_kind)
        if status:
            q = q.filter(MetaScanJob.status == status)
        return (
            q.order_by(MetaScanJob.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
            .all()
        )


class MetaTableRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaTable) -> MetaTable:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, table_id: int) -> Optional[MetaTable]:
        return self.db.get(MetaTable, table_id)

    def get_by_uq(self, source_id: int, database: str, table_name: str) -> Optional[MetaTable]:
        return (
            self.db.query(MetaTable)
            .filter(
                MetaTable.source_id == source_id,
                MetaTable.database == database,
                MetaTable.table_name == table_name,
            )
            .first()
        )

    def list(
        self,
        *,
        source_id: Optional[int] = None,
        database: Optional[str] = None,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        annotated: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetaTable]:
        q = self.db.query(MetaTable)
        if source_id is not None:
            q = q.filter(MetaTable.source_id == source_id)
        if database:
            q = q.filter(MetaTable.database == database)
        if domain:
            q = q.filter(MetaTable.domain == domain)
        if keyword:
            kw = f"%{keyword.strip()}%"
            q = q.filter(
                or_(
                    MetaTable.table_name.like(kw),
                    MetaTable.biz_name.like(kw),
                    MetaTable.table_comment.like(kw),
                )
            )
        if annotated is True:
            q = q.filter(
                or_(
                    MetaTable.biz_name.isnot(None),
                    MetaTable.biz_description.isnot(None),
                    MetaTable.domain.isnot(None),
                )
            )
        elif annotated is False:
            q = q.filter(
                and_(
                    MetaTable.biz_name.is_(None),
                    MetaTable.biz_description.is_(None),
                    MetaTable.domain.is_(None),
                )
            )
        return (
            q.order_by(MetaTable.table_name.asc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def list_by_source_db(self, source_id: int, database: str) -> list[MetaTable]:
        return (
            self.db.query(MetaTable)
            .filter(MetaTable.source_id == source_id, MetaTable.database == database)
            .order_by(MetaTable.table_name.asc())
            .all()
        )


class MetaColumnRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaColumn) -> MetaColumn:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, column_id: int) -> Optional[MetaColumn]:
        return self.db.get(MetaColumn, column_id)

    def get_by_uq(self, table_id: int, column_name: str) -> Optional[MetaColumn]:
        return (
            self.db.query(MetaColumn)
            .filter(MetaColumn.table_id == table_id, MetaColumn.column_name == column_name)
            .first()
        )

    def list_by_table(self, table_id: int) -> list[MetaColumn]:
        return (
            self.db.query(MetaColumn)
            .filter(MetaColumn.table_id == table_id)
            .order_by(MetaColumn.ordinal.asc(), MetaColumn.id.asc())
            .all()
        )

    def list_by_table_ids(self, table_ids: list[int]) -> list[MetaColumn]:
        if not table_ids:
            return []
        return (
            self.db.query(MetaColumn)
            .filter(MetaColumn.table_id.in_(table_ids))
            .order_by(MetaColumn.table_id.asc(), MetaColumn.ordinal.asc())
            .all()
        )


class GlossaryTermRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: GlossaryTerm) -> GlossaryTerm:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, term_id: int) -> Optional[GlossaryTerm]:
        return self.db.get(GlossaryTerm, term_id)

    def get_by_name(self, name: str) -> Optional[GlossaryTerm]:
        return self.db.query(GlossaryTerm).filter(GlossaryTerm.name == name).first()

    def list(
        self,
        *,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[GlossaryTerm]:
        q = self.db.query(GlossaryTerm)
        if domain:
            q = q.filter(GlossaryTerm.domain == domain)
        if keyword:
            kw = f"%{keyword.strip()}%"
            q = q.filter(
                or_(GlossaryTerm.name.like(kw), GlossaryTerm.definition.like(kw))
            )
        return (
            q.order_by(GlossaryTerm.name.asc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def delete(self, row: GlossaryTerm) -> None:
        self.db.delete(row)
        self.db.flush()

    def all_terms(self) -> list[GlossaryTerm]:
        return self.db.query(GlossaryTerm).order_by(GlossaryTerm.name.asc()).all()


class AnnotationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: Annotation) -> Annotation:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, ann_id: int) -> Optional[Annotation]:
        return self.db.get(Annotation, ann_id)

    def list(
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
        q = self.db.query(Annotation)
        if target_type:
            q = q.filter(Annotation.target_type == target_type)
        if target_id is not None:
            q = q.filter(Annotation.target_id == target_id)
        if label_kind:
            q = q.filter(Annotation.label_kind == label_kind)
        if status:
            q = q.filter(Annotation.status == status)
        if source:
            q = q.filter(Annotation.source == source)
        if confidence_min is not None:
            q = q.filter(Annotation.confidence >= confidence_min)
        if confidence_max is not None:
            q = q.filter(Annotation.confidence <= confidence_max)
        return (
            q.order_by(Annotation.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def list_active_for_key(
        self, target_type: str, target_id: int, label_kind: str
    ) -> list[Annotation]:
        return (
            self.db.query(Annotation)
            .filter(
                Annotation.target_type == target_type,
                Annotation.target_id == target_id,
                Annotation.label_kind == label_kind,
                Annotation.status.in_(["suggested", "accepted"]),
            )
            .all()
        )

    def get_accepted(
        self, target_type: str, target_id: int, label_kind: str
    ) -> Optional[Annotation]:
        return (
            self.db.query(Annotation)
            .filter(
                Annotation.target_type == target_type,
                Annotation.target_id == target_id,
                Annotation.label_kind == label_kind,
                Annotation.status == "accepted",
            )
            .first()
        )

    def count_by_status(
        self, *, table_ids: list[int], column_ids: list[int]
    ) -> dict[str, int]:
        counts = {"suggested": 0, "accepted": 0, "rejected": 0, "superseded": 0}
        if not table_ids and not column_ids:
            return counts
        q = self.db.query(Annotation)
        clauses = []
        if table_ids:
            clauses.append(
                and_(Annotation.target_type == "table", Annotation.target_id.in_(table_ids))
            )
        if column_ids:
            clauses.append(
                and_(Annotation.target_type == "column", Annotation.target_id.in_(column_ids))
            )
        rows = q.filter(or_(*clauses)).all() if clauses else []
        for row in rows:
            st = row.status.value if hasattr(row.status, "value") else str(row.status)
            counts[st] = counts.get(st, 0) + 1
        return counts

    def list_for_targets(
        self, *, table_ids: list[int], column_ids: list[int]
    ) -> list[Annotation]:
        clauses = []
        if table_ids:
            clauses.append(
                and_(Annotation.target_type == "table", Annotation.target_id.in_(table_ids))
            )
        if column_ids:
            clauses.append(
                and_(Annotation.target_type == "column", Annotation.target_id.in_(column_ids))
            )
        if not clauses:
            return []
        return self.db.query(Annotation).filter(or_(*clauses)).all()


class MetaStandardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaStandard) -> MetaStandard:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, sid: int) -> Optional[MetaStandard]:
        return self.db.get(MetaStandard, sid)

    def get_by_code(self, code: str) -> Optional[MetaStandard]:
        return self.db.query(MetaStandard).filter(MetaStandard.code == code).first()

    def list(
        self,
        *,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[MetaStandard]:
        q = self.db.query(MetaStandard)
        if status:
            q = q.filter(MetaStandard.status == status)
        if keyword:
            kw = f"%{keyword.strip()}%"
            q = q.filter(
                or_(MetaStandard.code.like(kw), MetaStandard.name.like(kw), MetaStandard.description.like(kw))
            )
        return (
            q.order_by(MetaStandard.code.asc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def delete(self, row: MetaStandard) -> None:
        self.db.delete(row)
        self.db.flush()

    def count_bindings(self, standard_id: int) -> int:
        return (
            self.db.query(MetaColumnStandard)
            .filter(MetaColumnStandard.standard_id == standard_id)
            .count()
        )


class MetaStandardVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaStandardVersion) -> MetaStandardVersion:
        self.db.add(row)
        self.db.flush()
        return row


class MetaColumnStandardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaColumnStandard) -> MetaColumnStandard:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, bind_id: int) -> Optional[MetaColumnStandard]:
        return self.db.get(MetaColumnStandard, bind_id)

    def get_by_column(self, column_id: int) -> Optional[MetaColumnStandard]:
        return (
            self.db.query(MetaColumnStandard)
            .filter(MetaColumnStandard.column_id == column_id)
            .first()
        )

    def delete(self, row: MetaColumnStandard) -> None:
        self.db.delete(row)
        self.db.flush()

    def list_by_standard(self, standard_id: int) -> list[MetaColumnStandard]:
        return (
            self.db.query(MetaColumnStandard)
            .filter(MetaColumnStandard.standard_id == standard_id)
            .all()
        )


class MetaColumnStandardHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaColumnStandardHistory) -> MetaColumnStandardHistory:
        self.db.add(row)
        self.db.flush()
        return row


class MetaDatabaseBriefRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: MetaDatabaseBrief) -> MetaDatabaseBrief:
        self.db.add(row)
        self.db.flush()
        return row

    def get_by_uq(self, source_id: int, database: str) -> Optional[MetaDatabaseBrief]:
        return (
            self.db.query(MetaDatabaseBrief)
            .filter(
                MetaDatabaseBrief.source_id == source_id,
                MetaDatabaseBrief.database == database,
            )
            .first()
        )


class PlatformLlmSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[PlatformLlmSetting]:
        return self.db.query(PlatformLlmSetting).order_by(PlatformLlmSetting.id.asc()).all()

    def get(self, setting_id: int) -> Optional[PlatformLlmSetting]:
        return self.db.query(PlatformLlmSetting).filter(PlatformLlmSetting.id == setting_id).first()

    def get_singleton(self) -> Optional[PlatformLlmSetting]:
        """历史兼容：返回最早一条（无 is_default 时的兜底）。"""
        return self.db.query(PlatformLlmSetting).order_by(PlatformLlmSetting.id.asc()).first()

    def get_default(self) -> Optional[PlatformLlmSetting]:
        """返回当前生效（is_default=True 且 enabled=True）的配置。"""
        return (
            self.db.query(PlatformLlmSetting)
            .filter(PlatformLlmSetting.is_default.is_(True), PlatformLlmSetting.enabled.is_(True))
            .order_by(PlatformLlmSetting.id.asc())
            .first()
        )

    def add(self, row: PlatformLlmSetting) -> PlatformLlmSetting:
        self.db.add(row)
        self.db.flush()
        return row

    def delete(self, row: PlatformLlmSetting) -> None:
        self.db.delete(row)
        self.db.flush()

    def clear_default(self, exclude_id: Optional[int] = None) -> None:
        q = self.db.query(PlatformLlmSetting).filter(PlatformLlmSetting.is_default.is_(True))
        if exclude_id is not None:
            q = q.filter(PlatformLlmSetting.id != exclude_id)
        for row in q.all():
            row.is_default = False
            self.db.add(row)
        self.db.flush()
