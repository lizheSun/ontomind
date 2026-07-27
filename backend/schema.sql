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
-- 8. OpenCode 对话工作台业务映射表
-- ============================================================
-- 前端直连本机 opencode serve 拿到 session.id 后，通过
-- POST /api/v1/opencode/session-link 把 (opencode_session_id, user_id) 落到本表，
-- 供业务审计使用。
-- ⚠️ 本表不是 opencode 会话数据源，opencode session 元数据/消息以 opencode server 为准。
DROP TABLE IF EXISTS `opencode_sessions`;
CREATE TABLE `opencode_sessions` (
  `id`                    INT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `opencode_session_id`   VARCHAR(64)  NOT NULL COMMENT 'opencode server 侧的 session.id',
  `user_id`               INT          NOT NULL COMMENT '业务侧用户',
  `title`                 VARCHAR(255) DEFAULT NULL COMMENT '会话标题（冗余，便于列表查询）',
  `created_at`            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`            DATETIME     DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_opencode_session_id` (`opencode_session_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_ocsession_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OpenCode 对话工作台业务映射';


-- ============================================================
-- 9. 专家团（Expert Team）
-- ============================================================
-- 一个专家 = 一份 opencode agent 定义（~/.config/opencode/agent/{slug}.md）
-- + 模型 / Skill / MCP / SOP 配置。
-- 启动时生成 agent.md 文件；opencode 重启后自动 discover 该 agent。
-- 前端 ExpertPicker 选中后注入 role+sop 为 system prompt，用 build agent 发消息。
DROP TABLE IF EXISTS `experts`;
CREATE TABLE `experts` (
  `id`                    INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`                  VARCHAR(128)  NOT NULL COMMENT '专家显示名称',
  `slug`                  VARCHAR(64)   NOT NULL COMMENT '唯一标识符 / opencode agent 名',
  `avatar`                VARCHAR(256)  DEFAULT NULL COMMENT 'emoji 或 URL',
  `description`           TEXT          DEFAULT NULL COMMENT '一句话描述',
  `role`                  TEXT          DEFAULT NULL COMMENT '角色定位（写进 agent md）',
  `sop`                   TEXT          DEFAULT NULL COMMENT 'SOP 工作流程',
  `provider`              VARCHAR(64)   DEFAULT NULL COMMENT 'opencode providerID',
  `model`                 VARCHAR(128)  DEFAULT NULL COMMENT 'opencode modelID',
  `temperature`           VARCHAR(16)   DEFAULT NULL COMMENT '采样温度',
  `skills`                JSON          NOT NULL COMMENT 'Skill 名称数组',
  `mcps`                  JSON          NOT NULL COMMENT 'MCP 名称数组',
  `tools`                 JSON          NOT NULL COMMENT '工具开关 {read,write,bash,todo}',
  `image`                 VARCHAR(256)  DEFAULT NULL COMMENT 'Docker 镜像名（可选）',
  `container_name`        VARCHAR(128)  DEFAULT NULL COMMENT 'Docker 容器名',
  `container_id`          VARCHAR(64)   DEFAULT NULL COMMENT 'Docker 容器 ID',
  `host_port`             INT           DEFAULT NULL COMMENT '本机映射端口',
  `host`                  VARCHAR(64)   NOT NULL DEFAULT '127.0.0.1' COMMENT 'opencode 服务地址',
  `port`                  INT           NOT NULL DEFAULT 4096 COMMENT 'opencode 服务端口',
  `status`                VARCHAR(20)   NOT NULL DEFAULT 'offline' COMMENT 'offline / online / error',
  `agent_file_path`       VARCHAR(512)  DEFAULT NULL COMMENT 'agent md 文件路径',
  `started_at`            DATETIME      DEFAULT NULL,
  `stopped_at`            DATETIME      DEFAULT NULL,
  `error_message`         TEXT          DEFAULT NULL,
  `sort_order`            INT           NOT NULL DEFAULT 0,
  `created_by_user_id`    INT           DEFAULT NULL,
  `created_at`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`            DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_expert_slug` (`slug`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_expert_user` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专家团配置表';


-- ============================================================
-- 10. 算力调度 — Docker 服务
-- ============================================================
-- 每个 opencode docker 容器 = 一个 DockerService；可关联 Expert
DROP TABLE IF EXISTS `docker_services`;
CREATE TABLE `docker_services` (
  `id`                 INT           NOT NULL AUTO_INCREMENT,
  `name`               VARCHAR(128)  NOT NULL,
  `slug`               VARCHAR(64)   NOT NULL,
  `expert_id`          INT           DEFAULT NULL,
  `image`              VARCHAR(256)  NOT NULL,
  `container_name`     VARCHAR(128)  DEFAULT NULL,
  `container_id`       VARCHAR(64)   DEFAULT NULL,
  `host`               VARCHAR(64)   NOT NULL DEFAULT '127.0.0.1',
  `host_port`          INT           DEFAULT NULL,
  `container_port`     INT           NOT NULL DEFAULT 4096,
  `opencode_args`      JSON          NOT NULL,
  `env`                JSON          NOT NULL,
  `volumes`            JSON          NOT NULL,
  `status`             VARCHAR(20)   NOT NULL DEFAULT 'stopped' COMMENT 'stopped / starting / running / error',
  `started_at`         DATETIME      DEFAULT NULL,
  `stopped_at`         DATETIME      DEFAULT NULL,
  `error_message`      TEXT          DEFAULT NULL,
  `description`        TEXT          DEFAULT NULL,
  `created_by_user_id` INT           DEFAULT NULL,
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`         DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ds_slug` (`slug`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_ds_expert` FOREIGN KEY (`expert_id`) REFERENCES `experts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_ds_user` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算力调度-Docker 服务';


-- ============================================================
-- 11. 算力调度 — 调度任务
-- ============================================================
DROP TABLE IF EXISTS `schedule_tasks`;
CREATE TABLE `schedule_tasks` (
  `id`                 INT           NOT NULL AUTO_INCREMENT,
  `name`               VARCHAR(128)  NOT NULL,
  `description`        TEXT          DEFAULT NULL,
  `task_type`          VARCHAR(32)   NOT NULL DEFAULT 'opencode',
  `schedule_type`      VARCHAR(20)   NOT NULL DEFAULT 'manual' COMMENT 'manual / once / interval / cron',
  `schedule_expr`      VARCHAR(256)  DEFAULT NULL,
  `docker_service_id`  INT           DEFAULT NULL,
  `opencode_config`    JSON          NOT NULL,
  `env`                JSON          NOT NULL,
  `timeout_seconds`    INT           NOT NULL DEFAULT 600,
  `enabled`            TINYINT(1)    NOT NULL DEFAULT 1,
  `status`             VARCHAR(20)   NOT NULL DEFAULT 'idle' COMMENT 'idle / running / paused / disabled',
  `last_run_at`        DATETIME      DEFAULT NULL,
  `next_run_at`        DATETIME      DEFAULT NULL,
  `total_runs`         INT           NOT NULL DEFAULT 0,
  `success_runs`       INT           NOT NULL DEFAULT 0,
  `failed_runs`        INT           NOT NULL DEFAULT 0,
  `created_by_user_id` INT           DEFAULT NULL,
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`         DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_next_run` (`next_run_at`),
  KEY `idx_docker_service` (`docker_service_id`),
  CONSTRAINT `fk_task_ds` FOREIGN KEY (`docker_service_id`) REFERENCES `docker_services` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_task_user` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算力调度-任务';


-- ============================================================
-- 12. 算力调度 — 运行记录
-- ============================================================
DROP TABLE IF EXISTS `task_runs`;
CREATE TABLE `task_runs` (
  `id`                    INT           NOT NULL AUTO_INCREMENT,
  `task_id`               INT           NOT NULL,
  `trigger`               VARCHAR(20)   NOT NULL DEFAULT 'manual',
  `status`                VARCHAR(20)   NOT NULL DEFAULT 'pending',
  `started_at`            DATETIME      DEFAULT NULL,
  `finished_at`           DATETIME      DEFAULT NULL,
  `duration_ms`           INT           DEFAULT NULL,
  `snapshot`              JSON          NOT NULL,
  `exit_code`             INT           DEFAULT NULL,
  `output_summary`        TEXT          DEFAULT NULL,
  `error_message`         TEXT          DEFAULT NULL,
  `opencode_session_id`   VARCHAR(64)   DEFAULT NULL,
  `triggered_by_user_id`  INT           DEFAULT NULL,
  `created_at`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task` (`task_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_run_task` FOREIGN KEY (`task_id`) REFERENCES `schedule_tasks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_run_user` FOREIGN KEY (`triggered_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算力调度-运行记录';


-- ============================================================
-- 13. 算力调度 — 运行日志
-- ============================================================
DROP TABLE IF EXISTS `task_log_entries`;
CREATE TABLE `task_log_entries` (
  `id`         INT           NOT NULL AUTO_INCREMENT,
  `run_id`     INT           NOT NULL,
  `sequence`   INT           NOT NULL,
  `level`      VARCHAR(10)   NOT NULL DEFAULT 'info',
  `message`    TEXT          NOT NULL,
  `created_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_run` (`run_id`),
  CONSTRAINT `fk_log_run` FOREIGN KEY (`run_id`) REFERENCES `task_runs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算力调度-运行日志';
