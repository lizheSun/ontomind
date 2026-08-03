-- ============================================================
-- OntoMind Database Schema
-- 数据库: ontomind (utf8mb4 / InnoDB)
--
-- ⚠️ 本文件由 ORM 自动导出（再生成命令见文件末尾），仅作参考文档。
--    **建表权威是 app/db/models/ 下的 SQLAlchemy Model**：
--    后端启动时 `Base.metadata.create_all()` 自动建缺失的表。
--
-- 当前只有 4 张表（2026-08-03 深度精简后）：
--   users / roles / user_roles / audit_logs
--
-- 项目当前形态：
--   前端 = AIDE（iframe 嵌 opencode Web UI）+ 用户管理
--   后端 = /api/v1/{auth, users, opencode}  共 11 个端点
--
-- ============================================================
-- 🗑️ 2026-08-03 分两批共 DROP 88 张表
-- ============================================================
--
-- 【第一批 39 张】五层业务域 + resources + agent-looper/platform：
--   对话工作台   : opencode_sessions
--   感知层       : data_sources / meta_tables / meta_columns / meta_profiles
--   认知层       : onto_versions / onto_classes / onto_properties
--                  / onto_relationships / onto_constraints
--   资源管理     : instances / agents / credentials / mcp_configs
--   T44 平台     : compute_nodes / agent_containers / node_containers
--                  / container_agents / container_skills / container_mcps
--                  / agent_skills / agent_mcps / node_connections
--                  / discovery_runs / discovery_items
--   AgentLooper  : agent_looper_configs / agent_looper_versions / agent_looper_test_runs
--   AgentPlatform: agent_versions / agent_deployments
--   旧知识库     : knowledge_bases / knowledge_chunks / knowledge_documents
--                  / source_code_repos / source_code_files
--   旧算力表名   : docker_services / schedule_tasks / task_runs / task_log_entries
--   Alembic      : alembic_version
--
-- 【第二批 49 张】专家团 + 算力调度 + 数据平台 + 知识库 + LLM：
--   专家团       : experts / agent_relations / skills / mcps
--   算力调度     : docker_nodes / compute_tasks / compute_runs / container_templates
--   数据平台     : dp_data_sources / dp_sql_queries / dp_query_history
--                  / dp_chat_sessions / dp_chat_messages
--   知识库       : kb_libraries / kb_data_assets / kb_code_repos
--                  / kb_documents / kb_experiences / kb_tags
--   LLM 配置     : llm_configs
--   （另含 25 张第一批已删但被 create_all 重建的空表壳）
-- ============================================================

CREATE DATABASE IF NOT EXISTS `ontomind`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `ontomind`;


-- ------------------------------------------------------------
-- roles  — Agent 平台角色
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `roles`;
CREATE TABLE roles (
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(256), 
	is_system BOOL NOT NULL, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='Agent 平台角色' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- users  — 用户表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE users (
	username VARCHAR(50) NOT NULL COMMENT '用户名', 
	email VARCHAR(100) NOT NULL COMMENT '邮箱', 
	password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希', 
	full_name VARCHAR(100) COMMENT '全名', 
	is_active BOOL NOT NULL COMMENT '是否激活', 
	is_superuser BOOL NOT NULL COMMENT '是否超级管理员', 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id)
)COMMENT='用户表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- audit_logs  — Agent 平台安全审计日志
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE audit_logs (
	actor_user_id INTEGER, 
	action VARCHAR(128) NOT NULL, 
	resource_type VARCHAR(64) NOT NULL, 
	resource_id VARCHAR(128), 
	outcome VARCHAR(32) NOT NULL, 
	details JSON, 
	request_id VARCHAR(128), 
	source_ip VARCHAR(64), 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)COMMENT='Agent 平台安全审计日志' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- user_roles  — 用户角色关联
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `user_roles`;
CREATE TABLE user_roles (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	assigned_by_user_id INTEGER, 
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	created_at DATETIME COMMENT '创建时间' DEFAULT now(), 
	updated_at DATETIME COMMENT '更新时间', 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)COMMENT='用户角色关联' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 再生成本文件：
--   cd backend && python3 -c "
--   from sqlalchemy.schema import CreateTable
--   from sqlalchemy.dialects import mysql
--   from app.db.session import Base
--   import app.db.models
--   for t in Base.metadata.sorted_tables:
--       print(CreateTable(t).compile(dialect=mysql.dialect()))
--   "
-- ============================================================
