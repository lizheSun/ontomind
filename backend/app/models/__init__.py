"""Core database models for OntoMind platform."""

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """Platform user."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class DataSource(Base):
    """感知层 - 数据源连接配置."""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    source_type = Column(String(32), nullable=False)  # mysql, postgresql, kafka, api, file
    connection_config = Column(JSON, nullable=False)  # encrypted connection details
    status = Column(String(16), default="inactive")  # active, inactive, error
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Document(Base):
    """感知层 - 上传的文档."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(256), nullable=False)
    file_type = Column(String(16), nullable=False)  # pdf, docx, xlsx, md, txt
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String(16), default="uploaded")  # uploaded, chunking, embedded, ready
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class OntologyEntity(Base):
    """认知层 - 本体实体."""
    __tablename__ = "ontology_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    entity_type = Column(String(64), nullable=False)  # concept, instance, attribute, relation
    properties = Column(JSON, default=dict)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    confidence = Column(Integer, default=100)  # 0-100 confidence score
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class OntologyRelation(Base):
    """认知层 - 本体关系."""
    __tablename__ = "ontology_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("ontology_entities.id"), nullable=False)
    predicate = Column(String(128), nullable=False)
    object_id = Column(Integer, ForeignKey("ontology_entities.id"), nullable=False)
    properties = Column(JSON, default=dict)
    confidence = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("OntologyEntity", foreign_keys=[subject_id])
    object = relationship("OntologyEntity", foreign_keys=[object_id])


class MLModel(Base):
    """决策层 - 机器学习模型."""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    model_type = Column(String(32), nullable=False)  # classification, regression, clustering
    framework = Column(String(32), nullable=False)  # sklearn, xgboost, pytorch
    parameters = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)  # accuracy, precision, recall, f1, etc.
    model_path = Column(String(512), nullable=True)  # path to serialized model
    version = Column(String(32), nullable=False)
    status = Column(String(16), default="training")  # training, ready, deployed, archived
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Strategy(Base):
    """决策层 - 决策策略/规则."""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    strategy_type = Column(String(32), nullable=False)  # risk_control, marketing, recommendation
    rule_definition = Column(JSON, nullable=False)  # structured rule definition
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=True)
    priority = Column(Integer, default=0)
    status = Column(String(16), default="draft")  # draft, testing, active, archived
    version = Column(String(32), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class StrategyExecution(Base):
    """执行层 - 策略下发记录."""
    __tablename__ = "strategy_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    target_system = Column(String(64), nullable=False)  # risk_engine, marketing_platform
    execution_params = Column(JSON, default=dict)
    status = Column(String(16), default="pending")  # pending, running, success, failed, rolled_back
    result = Column(JSON, default=dict)
    executed_by = Column(Integer, ForeignKey("users.id"))
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
