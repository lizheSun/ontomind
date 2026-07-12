"""ORM models."""
from app.db.models.user_model import User
from app.db.models.llm_config_model import LLMConfig
from app.db.models.data_source_model import DataSource
from app.db.models.metadata_model import MetaTable, MetaColumn, MetaProfile
from app.db.models.ontology_model import (
    OntologyVersion, OntologyClass, OntologyProperty,
    OntologyRelationship, OntologyConstraint,
)
from app.db.models.instance_model import Instance
from app.db.models.agent_model import Agent
from app.db.models.skill_model import Skill
from app.db.models.mcp_model import MCP
from app.db.models.agent_run_model import AgentRun
from app.db.models.project_model import Project
from app.db.models.requirement_model import Requirement
from app.db.models.plan_model import Plan
from app.db.models.task_model import Task

# --- Data Platform (T06) ---
from app.db.models.dp_data_source_model import DpDataSource
from app.db.models.dp_sql_query_model import DpSqlQuery
from app.db.models.dp_query_history_model import DpQueryHistory
from app.db.models.dp_chat_session_model import DpChatSession
from app.db.models.dp_chat_message_model import DpChatMessage

# --- Knowledge Base (T07) ---
from app.db.models.kb_library_model import KbLibrary
from app.db.models.kb_data_asset_model import KbDataAsset
from app.db.models.kb_code_repo_model import KbCodeRepo
from app.db.models.kb_document_model import KbDocument
from app.db.models.kb_experience_model import KbExperience
from app.db.models.kb_tag_model import KbTag

# --- Agent Looper (T34) ---
from app.db.models.agent_looper_config_model import AgentLooperConfig
from app.db.models.agent_looper_version_model import AgentLooperVersion
from app.db.models.agent_looper_test_run_model import AgentLooperTestRun

# --- Agent Resource Platform (T44) — 5 核心 + 7 关联 ---
from app.db.models.compute_node_model import ComputeNode
from app.db.models.agent_container_model import AgentContainer
from app.db.models.node_container_model import NodeContainer
from app.db.models.container_agent_model import ContainerAgent
from app.db.models.container_skill_model import ContainerSkill
from app.db.models.container_mcp_model import ContainerMCP
from app.db.models.agent_skill_model import AgentSkill
from app.db.models.agent_mcp_model import AgentMCP
from app.db.models.agent_run_job_model import AgentRunJob
from app.db.models.credential_model import Credential
from app.db.models.audit_log_model import AuditLog
from app.db.models.role_model import Role, UserRole
from app.db.models.agent_platform_model import (
    AgentVersion, AgentDeployment, AgentSession, AgentMessage,
    AgentRunStep, AgentRunEvent, AgentToolApproval, EvalSuite, EvalCase,
)
from app.db.models.node_connection_model import NodeConnection
from app.db.models.discovery_run_model import DiscoveryRun
from app.db.models.discovery_item_model import DiscoveryItem

# Backwards-compat alias: 旧代码继续 import MCPConfig（已重命名为 MCP）
MCPConfig = MCP

__all__ = ["User", "LLMConfig", "DataSource", "MetaTable", "MetaColumn", "MetaProfile",
           "OntologyVersion", "OntologyClass", "OntologyProperty",
           "OntologyRelationship", "OntologyConstraint",
           "Instance", "Agent", "Skill", "MCP", "MCPConfig", "AgentRun",
           "Project", "Requirement", "Plan", "Task",
           "DpDataSource", "DpSqlQuery", "DpQueryHistory",
           "DpChatSession", "DpChatMessage",
           "KbLibrary", "KbDataAsset", "KbCodeRepo",
           "KbDocument", "KbExperience", "KbTag",
           "AgentLooperConfig", "AgentLooperVersion", "AgentLooperTestRun",
           # T44
           "ComputeNode", "AgentContainer",
           "NodeContainer", "ContainerAgent", "ContainerSkill", "ContainerMCP",
           "AgentSkill", "AgentMCP", "AgentRunJob",
           "AgentVersion", "AgentDeployment", "AgentSession", "AgentMessage",
           "AgentRunStep", "AgentRunEvent", "AgentToolApproval",
           "EvalSuite", "EvalCase",
           "Credential", "AuditLog", "Role", "UserRole",
           "NodeConnection", "DiscoveryRun", "DiscoveryItem"]
