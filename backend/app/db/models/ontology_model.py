"""本体建模 ORM."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum

from app.db.models.base import BaseModel


class OntologyJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OntologyBuildPhase(str, enum.Enum):
    EXTRACT = "extract"
    ALIGN = "align"
    JUDGE = "judge"
    MERGE = "merge"
    DONE = "done"


class OntologyElementSource(str, enum.Enum):
    RULE = "rule"
    LLM = "llm"
    HUMAN = "human"


class OntologyElementStatus(str, enum.Enum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class OntologyMappingElementType(str, enum.Enum):
    OBJECT_TYPE = "object_type"
    PROPERTY = "property"
    LINK_TYPE = "link_type"


class OntologyCQVerifyStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


class Ontology(BaseModel):
    __tablename__ = "ontologies"
    __table_args__ = {"comment": "本体"}

    name = Column(String(128), nullable=False)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(String(512), nullable=True)
    domain = Column(String(128), nullable=True)
    current_version = Column(Integer, nullable=False, default=0)


class OntologyBuildJob(BaseModel):
    __tablename__ = "ontology_build_jobs"
    __table_args__ = {"comment": "本体构建任务"}

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(
        SAEnum(OntologyJobStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyJobStatus.PENDING,
    )
    phase = Column(
        SAEnum(OntologyBuildPhase, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyBuildPhase.EXTRACT,
    )
    mode = Column(String(16), nullable=False, default="rules")
    scope_json = Column(JSON, nullable=True)
    batch_size = Column(Integer, nullable=False, default=8)
    progress = Column(Float, nullable=False, default=0.0)
    delta_json = Column(JSON, nullable=True)
    error_detail = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)


class OntologyObjectType(BaseModel):
    __tablename__ = "ontology_object_types"
    __table_args__ = (
        UniqueConstraint("ontology_id", "key", name="uq_ontology_object_type_key"),
        {"comment": "本体对象类型"},
    )

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    definition = Column(Text, nullable=True)
    parent_key = Column(String(128), nullable=True)
    aliases_json = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(OntologyElementSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementSource.RULE,
    )
    status = Column(
        SAEnum(OntologyElementStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementStatus.DRAFT,
    )


class OntologyProperty(BaseModel):
    __tablename__ = "ontology_properties"
    __table_args__ = (
        UniqueConstraint("object_type_id", "key", name="uq_ontology_property_key"),
        {"comment": "本体属性"},
    )

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_type_id = Column(
        Integer,
        ForeignKey("ontology_object_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    data_type = Column(String(64), nullable=True)
    definition = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(OntologyElementSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementSource.RULE,
    )
    status = Column(
        SAEnum(OntologyElementStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementStatus.DRAFT,
    )


class OntologyLinkType(BaseModel):
    __tablename__ = "ontology_link_types"
    __table_args__ = (
        UniqueConstraint("ontology_id", "key", name="uq_ontology_link_type_key"),
        {"comment": "本体关系类型"},
    )

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    from_key = Column(String(128), nullable=False)
    to_key = Column(String(128), nullable=False)
    cardinality = Column(String(16), nullable=True)
    definition = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(OntologyElementSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementSource.RULE,
    )
    status = Column(
        SAEnum(OntologyElementStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementStatus.DRAFT,
    )
    evidence_json = Column(JSON, nullable=True)


class OntologyMapping(BaseModel):
    __tablename__ = "ontology_mappings"
    __table_args__ = {"comment": "本体到物理表映射"}

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    element_type = Column(
        SAEnum(OntologyMappingElementType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    element_key = Column(String(128), nullable=False)
    source_id = Column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    database = Column(String(128), nullable=False)
    table_name = Column(String(128), nullable=False)
    column_name = Column(String(128), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(OntologyElementSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementSource.RULE,
    )
    status = Column(
        SAEnum(OntologyElementStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementStatus.DRAFT,
    )


class OntologyMetric(BaseModel):
    __tablename__ = "ontology_metrics"
    __table_args__ = (
        UniqueConstraint("ontology_id", "key", name="uq_ontology_metric_key"),
        {"comment": "本体指标（语义层）"},
    )

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    definition = Column(Text, nullable=True)
    sql_expr = Column(Text, nullable=True)
    unit = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(
        SAEnum(OntologyElementSource, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementSource.RULE,
    )
    status = Column(
        SAEnum(OntologyElementStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyElementStatus.DRAFT,
    )


class OntologyCQ(BaseModel):
    __tablename__ = "ontology_cqs"
    __table_args__ = {"comment": "Competency Questions"}

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question = Column(Text, nullable=False)
    category = Column(String(64), nullable=True)
    verify_status = Column(
        SAEnum(OntologyCQVerifyStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OntologyCQVerifyStatus.PENDING,
    )
    verify_note = Column(Text, nullable=True)
    related_keys_json = Column(JSON, nullable=True)


class OntologyVersion(BaseModel):
    __tablename__ = "ontology_versions"
    __table_args__ = (
        UniqueConstraint("ontology_id", "version", name="uq_ontology_version"),
        {"comment": "本体版本快照"},
    )

    ontology_id = Column(
        Integer, ForeignKey("ontologies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    diff_json = Column(JSON, nullable=True)
    change_note = Column(String(512), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
