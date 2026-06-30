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
