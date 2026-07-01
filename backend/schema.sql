-- ============================================================
-- OntoMind Database Schema
-- 数据库: ontomind (utf8mb4)
-- 引擎: InnoDB
-- 生成时间: 2025-06-30
-- ============================================================

CREATE DATABASE IF NOT EXISTS `ontomind`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `ontomind`;

-- ============================================================
-- 1. 用户表
-- ============================================================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username`      VARCHAR(50)   NOT NULL COMMENT '用户名',
  `email`         VARCHAR(100)  NOT NULL COMMENT '邮箱',
  `password_hash` VARCHAR(255)  NOT NULL COMMENT '密码哈希（bcrypt）',
  `full_name`     VARCHAR(100)  DEFAULT NULL COMMENT '全名',
  `is_active`     TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否激活',
  `is_superuser`  TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否超级管理员',
  `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_username` (`username`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';


-- ============================================================
-- 2. LLM 服务配置表
-- ============================================================
DROP TABLE IF EXISTS `llm_configs`;
CREATE TABLE `llm_configs` (
  `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`          VARCHAR(128)  NOT NULL COMMENT '配置名称',
  `provider`      VARCHAR(20)   NOT NULL COMMENT '服务协议: openai / anthropic / qwen',
  `base_url`      VARCHAR(512)  NOT NULL COMMENT 'API Base URL',
  `api_key`       TEXT          NOT NULL COMMENT 'API Key（加密存储）',
  `model_name`    VARCHAR(256)  NOT NULL COMMENT '模型名称',
  `description`   VARCHAR(512)  DEFAULT NULL COMMENT '配置描述',
  `is_active`     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否设为默认使用',
  `extra_headers` TEXT          DEFAULT NULL COMMENT '额外请求头 JSON',
  `extra_body`    TEXT          DEFAULT NULL COMMENT '额外请求体参数 JSON',
  `timeout`       VARCHAR(16)   DEFAULT '60' COMMENT '请求超时（秒）',
  `max_retries`   VARCHAR(8)    DEFAULT '2' COMMENT '最大重试次数',
  `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_provider` (`provider`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 服务配置表';


-- ============================================================
-- 3. 数据源配置表
-- ============================================================
DROP TABLE IF EXISTS `data_sources`;
CREATE TABLE `data_sources` (
  `id`           INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`         VARCHAR(128)  NOT NULL COMMENT '数据源名称',
  `source_type`  VARCHAR(50)   NOT NULL COMMENT '类型: mysql/postgresql/doris/clickhouse/kafka/api/file',
  `host`         VARCHAR(255)  DEFAULT NULL COMMENT '主机地址',
  `port`         INT           DEFAULT NULL COMMENT '端口号',
  `username`     VARCHAR(100)  DEFAULT NULL COMMENT '用户名',
  `password`     VARCHAR(255)  DEFAULT NULL COMMENT '密码',
  `database`     VARCHAR(128)  DEFAULT NULL COMMENT '数据库名',
  `charset`      VARCHAR(32)   DEFAULT NULL COMMENT '字符集',
  `description`  VARCHAR(512)  DEFAULT NULL COMMENT '描述',
  `status`       VARCHAR(20)   DEFAULT 'inactive' COMMENT '状态: active/inactive/error',
  `extra_params` TEXT          DEFAULT NULL COMMENT '额外连接参数 JSON',
  `is_active`    TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`   DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_source_type` (`source_type`),
  KEY `idx_status` (`status`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据源连接配置表';


-- ============================================================
-- 4. 计算节点实例表
-- ============================================================
DROP TABLE IF EXISTS `instances`;
CREATE TABLE `instances` (
  `id`              INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`            VARCHAR(128)  NOT NULL COMMENT '节点名称',
  `host`            VARCHAR(255)  NOT NULL COMMENT 'IP/域名',
  `port`            INT           NOT NULL COMMENT '管理端口',
  `instance_type`   VARCHAR(20)   NOT NULL COMMENT '节点类型: physical / docker / k8s_pod',
  `protocol`        VARCHAR(20)   NOT NULL COMMENT '管理协议: ssh / docker_api',
  `credential`      JSON          DEFAULT NULL COMMENT '认证信息',
  `os`              VARCHAR(64)   DEFAULT NULL COMMENT '操作系统',
  `cpu_cores`       INT           DEFAULT NULL COMMENT 'CPU 核数',
  `memory_mb`       INT           DEFAULT NULL COMMENT '内存 MB',
  `disk_gb`         INT           DEFAULT NULL COMMENT '磁盘 GB',
  `labels`          JSON          DEFAULT NULL COMMENT '标签',
  `status`          VARCHAR(20)   DEFAULT 'offline' COMMENT '状态: online / offline / maintenance',
  `last_heartbeat`  DATETIME      DEFAULT NULL COMMENT '最后心跳时间',
  `description`     TEXT          DEFAULT NULL COMMENT '描述',
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`      DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_instance_type` (`instance_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='计算节点实例表';


-- ============================================================
-- 5. Agent 智能体定义表
-- ============================================================
DROP TABLE IF EXISTS `agents`;
CREATE TABLE `agents` (
  `id`              INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`            VARCHAR(128)  NOT NULL COMMENT 'Agent 名称',
  `agent_type`      VARCHAR(20)   NOT NULL COMMENT '类型: openclaw / opencode / harness / custom',
  `version`         VARCHAR(32)   DEFAULT 'latest' COMMENT '版本号',
  `runtime`         VARCHAR(20)   NOT NULL COMMENT '运行方式: docker / python / node / binary',
  `docker_image`    VARCHAR(256)  DEFAULT NULL COMMENT 'Docker 镜像地址',
  `entrypoint`      TEXT          DEFAULT NULL COMMENT '启动命令/入口',
  `env_template`    JSON          DEFAULT NULL COMMENT '环境变量模板',
  `config_template` TEXT          DEFAULT NULL COMMENT '配置文件模板',
  `ports`           JSON          DEFAULT NULL COMMENT '端口列表',
  `volume_mounts`   JSON          DEFAULT NULL COMMENT '挂载卷配置',
  `resource_limit`  JSON          DEFAULT NULL COMMENT '资源限制',
  `skill_ids`       JSON          DEFAULT NULL COMMENT '关联的技能 ID 列表',
  `description`     TEXT          DEFAULT NULL COMMENT '描述',
  `is_active`       TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`      DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_agent_type` (`agent_type`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent 智能体定义表';


-- ============================================================
-- 6. Skill 技能模块表
-- ============================================================
DROP TABLE IF EXISTS `skills`;
CREATE TABLE `skills` (
  `id`                INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`              VARCHAR(128)  NOT NULL COMMENT '技能名称',
  `skill_type`        VARCHAR(20)   NOT NULL COMMENT '类型: docker / mcp / script / api',
  `docker_image`      VARCHAR(256)  DEFAULT NULL COMMENT 'Docker 镜像',
  `entrypoint`        TEXT          DEFAULT NULL COMMENT '启动/入口命令',
  `install_cmd`       TEXT          DEFAULT NULL COMMENT '一键安装命令',
  `parameters_schema` JSON          DEFAULT NULL COMMENT '参数 JSON Schema',
  `output_schema`     JSON          DEFAULT NULL COMMENT '输出 JSON Schema',
  `env_vars`          JSON          DEFAULT NULL COMMENT '环境变量模板',
  `description`       TEXT          DEFAULT NULL COMMENT '描述',
  `tags`              JSON          DEFAULT NULL COMMENT '标签分类',
  `icon`              VARCHAR(128)  DEFAULT NULL COMMENT '图标名称',
  `is_installed`      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已安装',
  `installed_at`      DATETIME      DEFAULT NULL COMMENT '安装时间',
  `is_active`         TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`        DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_skill_type` (`skill_type`),
  KEY `idx_is_installed` (`is_installed`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Skill 技能模块表';


-- ============================================================
-- 7. MCP 工具/服务配置表
-- ============================================================
DROP TABLE IF EXISTS `mcp_configs`;
CREATE TABLE `mcp_configs` (
  `id`                     INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`                   VARCHAR(128)  NOT NULL COMMENT 'MCP 名称',
  `mcp_type`               VARCHAR(20)   NOT NULL COMMENT '类型: sse / stdio / http',
  `url`                    VARCHAR(512)  DEFAULT NULL COMMENT '连接地址',
  `command`                TEXT          DEFAULT NULL COMMENT '启动命令（stdio）',
  `args`                   JSON          DEFAULT NULL COMMENT '启动参数',
  `env_vars`               JSON          DEFAULT NULL COMMENT '环境变量',
  `headers`                JSON          DEFAULT NULL COMMENT '自定义请求头',
  `auto_discovery_url`     VARCHAR(512)  DEFAULT NULL COMMENT '自动发现 API URL',
  `auto_discovery_enabled` TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '自动发现开关',
  `tools_manifest`         JSON          DEFAULT NULL COMMENT '工具清单',
  `description`            TEXT          DEFAULT NULL COMMENT '描述',
  `is_active`              TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at`             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`             DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_mcp_type` (`mcp_type`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP 工具/服务配置表';


-- ============================================================
-- 8. AgentRun 运行实例表
-- ============================================================
DROP TABLE IF EXISTS `agent_runs`;
CREATE TABLE `agent_runs` (
  `id`              INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `agent_id`        INT           DEFAULT NULL COMMENT '关联 Agent ID',
  `instance_id`     INT           DEFAULT NULL COMMENT '关联 Instance ID',
  `run_name`        VARCHAR(128)  NOT NULL COMMENT '运行实例名称',
  `status`          VARCHAR(20)   DEFAULT 'initializing' COMMENT '状态: initializing / running / error / stopped',
  `container_id`    VARCHAR(128)  DEFAULT NULL COMMENT 'Docker 容器 ID',
  `pid`             INT           DEFAULT NULL COMMENT '进程 PID',
  `config_override` JSON          DEFAULT NULL COMMENT '运行时配置覆盖',
  `env_override`    JSON          DEFAULT NULL COMMENT '运行时环境变量覆盖',
  `started_at`      DATETIME      DEFAULT NULL COMMENT '启动时间',
  `stopped_at`      DATETIME      DEFAULT NULL COMMENT '停止时间',
  `exit_code`       INT           DEFAULT NULL COMMENT '退出码',
  `error_message`   TEXT          DEFAULT NULL COMMENT '错误信息',
  `log_offset`      INT           DEFAULT 0 COMMENT '日志偏移量',
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`      DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_instance_id` (`instance_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_agent_runs_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_agent_runs_instance` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent 运行实例追踪表';
