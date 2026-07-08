"""本体模型 — 认知层自动构建产物的存储（MySQL 关系表表达 T-Box）.

本体以「版本」组织：每个 OntologyVersion 对应一次构建，包含类/属性/关系/约束。
图谱与 OWL 导出在查询时按需派生，不单独建表。
"""
import json
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, Float, ForeignKey, Index,
)
from app.db.models.base import BaseModel


class OntologyVersion(BaseModel):
    """本体版本 — 每次构建生成一个版本，状态机: building -> ready / failed."""

    __tablename__ = "onto_versions"
    __table_args__ = (
        Index("ix_onto_versions_ds", "datasource_id"),
    )

    datasource_id = Column(Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, comment="关联数据源 ID")
    name = Column(String(256), nullable=False, comment="版本名称")
    description = Column(Text, nullable=True, comment="版本说明")
    status = Column(String(20), default="building", comment="构建状态: building/ready/failed")
    method = Column(String(20), default="rules", comment="构建方式: rules/llm/agent")
    llm_config_id = Column(Integer, ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True, comment="使用的平台 LLM 配置")
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, comment="使用的 Agent（method=agent 时）")
    stats = Column(Text, nullable=True, comment="JSON: {entity, relationship, property, constraint, table} 计数")
    error = Column(Text, nullable=True, comment="失败原因")

    def to_response_dict(self) -> dict:
        stats = None
        if self.stats:
            try:
                stats = json.loads(self.stats)
            except (json.JSONDecodeError, ValueError):
                stats = None
        return {
            "id": self.id,
            "datasource_id": self.datasource_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "method": self.method,
            "llm_config_id": self.llm_config_id,
            "agent_id": self.agent_id,
            "stats": stats,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OntologyClass(BaseModel):
    """本体类 — 对应数据源中的一个实体（表）."""

    __tablename__ = "onto_classes"
    __table_args__ = (
        Index("ix_onto_classes_version", "version_id"),
        Index("ix_onto_classes_src_table", "source_table_id"),
    )

    version_id = Column(Integer, ForeignKey("onto_versions.id", ondelete="CASCADE"), nullable=False, comment="所属本体版本")
    source_table_id = Column(Integer, ForeignKey("meta_tables.id", ondelete="SET NULL"), nullable=True, comment="来源表元数据 ID")
    local_name = Column(String(256), nullable=False, comment="IRI 局部名（类名）")
    label = Column(String(256), nullable=True, comment="中文标签/显示名")
    definition = Column(Text, nullable=True, comment="类定义/业务描述")
    domain = Column(String(128), nullable=True, comment="业务域")
    entity_type = Column(String(64), nullable=True, comment="实体类型: class/enumeration")
    is_entity = Column(Boolean, default=True, comment="是否作为本体实体（类）")
    confidence = Column(Float, nullable=True, comment="抽取置信度 0~1")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "version_id": self.version_id,
            "source_table_id": self.source_table_id,
            "local_name": self.local_name,
            "label": self.label,
            "definition": self.definition,
            "domain": self.domain,
            "entity_type": self.entity_type,
            "is_entity": bool(self.is_entity),
            "confidence": self.confidence,
        }


class OntologyProperty(BaseModel):
    """本体属性 — 数据属性（datatype）或对象属性（object，指向另一个类）."""

    __tablename__ = "onto_properties"
    __table_args__ = (
        Index("ix_onto_properties_version", "version_id"),
        Index("ix_onto_properties_class", "class_id"),
    )

    version_id = Column(Integer, ForeignKey("onto_versions.id", ondelete="CASCADE"), nullable=False, comment="所属本体版本")
    class_id = Column(Integer, ForeignKey("onto_classes.id", ondelete="CASCADE"), nullable=True, comment="定义域类（domain）")
    name = Column(String(256), nullable=False, comment="属性名")
    property_type = Column(String(16), default="data", comment="属性类型: data/object")
    range_type = Column(String(128), nullable=True, comment="值域：xsd 类型或目标类的 local_name")
    source_column_id = Column(Integer, ForeignKey("meta_columns.id", ondelete="SET NULL"), nullable=True, comment="来源字段元数据 ID")
    related_class_id = Column(Integer, ForeignKey("onto_classes.id", ondelete="SET NULL"), nullable=True, comment="对象属性指向的类（range class）")
    semantic_type = Column(String(64), nullable=True, comment="语义类型（来自字段画像/标注）")
    confidence = Column(Float, nullable=True, comment="抽取置信度 0~1")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "version_id": self.version_id,
            "class_id": self.class_id,
            "name": self.name,
            "property_type": self.property_type,
            "range_type": self.range_type,
            "source_column_id": self.source_column_id,
            "related_class_id": self.related_class_id,
            "semantic_type": self.semantic_type,
            "confidence": self.confidence,
        }


class OntologyRelationship(BaseModel):
    """本体关系 — 实体间的关联（由外键或语义关系推导）."""

    __tablename__ = "onto_relationships"
    __table_args__ = (
        Index("ix_onto_relationships_version", "version_id"),
        Index("ix_onto_relationships_from", "from_class_id"),
        Index("ix_onto_relationships_to", "to_class_id"),
    )

    version_id = Column(Integer, ForeignKey("onto_versions.id", ondelete="CASCADE"), nullable=False, comment="所属本体版本")
    from_class_id = Column(Integer, ForeignKey("onto_classes.id", ondelete="CASCADE"), nullable=False, comment="起点类")
    to_class_id = Column(Integer, ForeignKey("onto_classes.id", ondelete="CASCADE"), nullable=False, comment="终点类")
    name = Column(String(256), nullable=False, comment="关系名（如 hasX / 属于）")
    source_column_id = Column(Integer, ForeignKey("meta_columns.id", ondelete="SET NULL"), nullable=True, comment="对应的外键字段")
    cardinality = Column(String(32), default="0..*", comment="基数: 0..1/1/0..*/1..* 等")
    confidence = Column(Float, nullable=True, comment="抽取置信度 0~1")

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "version_id": self.version_id,
            "from_class_id": self.from_class_id,
            "to_class_id": self.to_class_id,
            "name": self.name,
            "source_column_id": self.source_column_id,
            "cardinality": self.cardinality,
            "confidence": self.confidence,
        }


class OntologyConstraint(BaseModel):
    """本体约束 — 挂在类/属性/关系上的约束规则，记录来源与置信度以便溯源."""

    __tablename__ = "onto_constraints"
    __table_args__ = (
        Index("ix_onto_constraints_version", "version_id"),
        Index("ix_onto_constraints_target", "target_type", "target_id"),
    )

    version_id = Column(Integer, ForeignKey("onto_versions.id", ondelete="CASCADE"), nullable=False, comment="所属本体版本")
    target_type = Column(String(16), nullable=False, comment="约束目标类型: class/property/relationship")
    target_id = Column(Integer, nullable=False, comment="约束目标 ID")
    constraint_type = Column(String(32), nullable=False, comment="约束类型: cardinality/enum/range/pattern/functional/inverse/transitive/symmetric")
    expression = Column(Text, nullable=True, comment="约束表达式（JSON 或文本）")
    severity = Column(String(16), default="info", comment="严重级别: info/warn/error")
    source = Column(String(16), default="schema", comment="来源: schema/profile/llm/agent")
    confidence = Column(Float, nullable=True, comment="置信度 0~1")

    def to_response_dict(self) -> dict:
        expression = None
        if self.expression:
            try:
                expression = json.loads(self.expression)
            except (json.JSONDecodeError, ValueError):
                expression = self.expression
        return {
            "id": self.id,
            "version_id": self.version_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "constraint_type": self.constraint_type,
            "expression": expression,
            "severity": self.severity,
            "source": self.source,
            "confidence": self.confidence,
        }
