"""本体 Repository — 仅 flush。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.ontology_model import (
    Ontology,
    OntologyBuildJob,
    OntologyCQ,
    OntologyLinkType,
    OntologyMapping,
    OntologyMetric,
    OntologyObjectType,
    OntologyProperty,
    OntologyVersion,
)


class OntologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: Ontology) -> Ontology:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, oid: int) -> Optional[Ontology]:
        return self.db.get(Ontology, oid)

    def get_by_slug(self, slug: str) -> Optional[Ontology]:
        return self.db.query(Ontology).filter(Ontology.slug == slug).first()

    def list(self, *, limit: int = 50, offset: int = 0) -> list[Ontology]:
        return (
            self.db.query(Ontology)
            .order_by(Ontology.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
            .all()
        )

    def delete(self, row: Ontology) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyBuildJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyBuildJob) -> OntologyBuildJob:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, job_id: int) -> Optional[OntologyBuildJob]:
        return self.db.get(OntologyBuildJob, job_id)

    def list_by_ontology(self, ontology_id: int, *, limit: int = 50) -> list[OntologyBuildJob]:
        return (
            self.db.query(OntologyBuildJob)
            .filter(OntologyBuildJob.ontology_id == ontology_id)
            .order_by(OntologyBuildJob.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )


class OntologyObjectTypeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyObjectType) -> OntologyObjectType:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, ot_id: int) -> Optional[OntologyObjectType]:
        return self.db.get(OntologyObjectType, ot_id)

    def get_by_key(self, ontology_id: int, key: str) -> Optional[OntologyObjectType]:
        return (
            self.db.query(OntologyObjectType)
            .filter(OntologyObjectType.ontology_id == ontology_id, OntologyObjectType.key == key)
            .first()
        )

    def list(
        self, ontology_id: int, *, status: Optional[str] = None
    ) -> list[OntologyObjectType]:
        q = self.db.query(OntologyObjectType).filter(OntologyObjectType.ontology_id == ontology_id)
        if status:
            q = q.filter(OntologyObjectType.status == status)
        return q.order_by(OntologyObjectType.id.asc()).all()

    def delete(self, row: OntologyObjectType) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyPropertyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyProperty) -> OntologyProperty:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, prop_id: int) -> Optional[OntologyProperty]:
        return self.db.get(OntologyProperty, prop_id)

    def list_by_object_type(self, object_type_id: int) -> list[OntologyProperty]:
        return (
            self.db.query(OntologyProperty)
            .filter(OntologyProperty.object_type_id == object_type_id)
            .order_by(OntologyProperty.id.asc())
            .all()
        )

    def list_by_ontology(
        self, ontology_id: int, *, status: Optional[str] = None
    ) -> list[OntologyProperty]:
        q = self.db.query(OntologyProperty).filter(OntologyProperty.ontology_id == ontology_id)
        if status:
            q = q.filter(OntologyProperty.status == status)
        return q.order_by(OntologyProperty.id.asc()).all()

    def delete(self, row: OntologyProperty) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyLinkTypeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyLinkType) -> OntologyLinkType:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, link_id: int) -> Optional[OntologyLinkType]:
        return self.db.get(OntologyLinkType, link_id)

    def get_by_key(self, ontology_id: int, key: str) -> Optional[OntologyLinkType]:
        return (
            self.db.query(OntologyLinkType)
            .filter(OntologyLinkType.ontology_id == ontology_id, OntologyLinkType.key == key)
            .first()
        )

    def list(
        self, ontology_id: int, *, status: Optional[str] = None
    ) -> list[OntologyLinkType]:
        q = self.db.query(OntologyLinkType).filter(OntologyLinkType.ontology_id == ontology_id)
        if status:
            q = q.filter(OntologyLinkType.status == status)
        return q.order_by(OntologyLinkType.id.asc()).all()

    def delete(self, row: OntologyLinkType) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyMappingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyMapping) -> OntologyMapping:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, mapping_id: int) -> Optional[OntologyMapping]:
        return self.db.get(OntologyMapping, mapping_id)

    def list(
        self, ontology_id: int, *, status: Optional[str] = None
    ) -> list[OntologyMapping]:
        q = self.db.query(OntologyMapping).filter(OntologyMapping.ontology_id == ontology_id)
        if status:
            q = q.filter(OntologyMapping.status == status)
        return q.order_by(OntologyMapping.id.asc()).all()

    def delete(self, row: OntologyMapping) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyMetricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyMetric) -> OntologyMetric:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, metric_id: int) -> Optional[OntologyMetric]:
        return self.db.get(OntologyMetric, metric_id)

    def get_by_key(self, ontology_id: int, key: str) -> Optional[OntologyMetric]:
        return (
            self.db.query(OntologyMetric)
            .filter(OntologyMetric.ontology_id == ontology_id, OntologyMetric.key == key)
            .first()
        )

    def list(
        self, ontology_id: int, *, status: Optional[str] = None
    ) -> list[OntologyMetric]:
        q = self.db.query(OntologyMetric).filter(OntologyMetric.ontology_id == ontology_id)
        if status:
            q = q.filter(OntologyMetric.status == status)
        return q.order_by(OntologyMetric.id.asc()).all()

    def delete(self, row: OntologyMetric) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyCQRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyCQ) -> OntologyCQ:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, cq_id: int) -> Optional[OntologyCQ]:
        return self.db.get(OntologyCQ, cq_id)

    def list(self, ontology_id: int) -> list[OntologyCQ]:
        return (
            self.db.query(OntologyCQ)
            .filter(OntologyCQ.ontology_id == ontology_id)
            .order_by(OntologyCQ.id.asc())
            .all()
        )

    def delete(self, row: OntologyCQ) -> None:
        self.db.delete(row)
        self.db.flush()


class OntologyVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: OntologyVersion) -> OntologyVersion:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, ontology_id: int, version: int) -> Optional[OntologyVersion]:
        return (
            self.db.query(OntologyVersion)
            .filter(OntologyVersion.ontology_id == ontology_id, OntologyVersion.version == version)
            .first()
        )

    def list(self, ontology_id: int) -> list[OntologyVersion]:
        return (
            self.db.query(OntologyVersion)
            .filter(OntologyVersion.ontology_id == ontology_id)
            .order_by(OntologyVersion.version.desc())
            .all()
        )
