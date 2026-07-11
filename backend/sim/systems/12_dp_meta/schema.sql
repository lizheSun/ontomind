-- ============================================================
-- 数据平台元数据 —— sim_dp_meta
-- ============================================================

DROP TABLE IF EXISTS data_lineage;
DROP TABLE IF EXISTS etl_job;
DROP TABLE IF EXISTS table_meta;

CREATE TABLE table_meta (
    meta_id BIGINT NOT NULL AUTO_INCREMENT,
    database_name VARCHAR(64) NOT NULL,
    table_name VARCHAR(128) NOT NULL,
    table_comment VARCHAR(255),
    business_domain VARCHAR(32),
    owner_emp_no VARCHAR(16),
    is_dw TINYINT NOT NULL DEFAULT 0,
    layer VARCHAR(8) COMMENT 'ODS/DWD/DWS/ADS/DIM',
    created_at DATETIME NOT NULL,
    PRIMARY KEY (meta_id),
    UNIQUE KEY uk_db_tbl (database_name, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '表元数据';

CREATE TABLE etl_job (
    job_id VARCHAR(64) NOT NULL,
    job_name VARCHAR(128) NOT NULL,
    source_db VARCHAR(64) NOT NULL,
    source_table VARCHAR(128) NOT NULL,
    target_db VARCHAR(64) NOT NULL,
    target_table VARCHAR(128) NOT NULL,
    cron_expr VARCHAR(64) NOT NULL DEFAULT '0 0 2 * * ?',
    owner_emp_no VARCHAR(16),
    is_active TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT 'ETL 任务';

CREATE TABLE data_lineage (
    lin_id BIGINT NOT NULL AUTO_INCREMENT,
    upstream_db VARCHAR(64) NOT NULL,
    upstream_table VARCHAR(128) NOT NULL,
    downstream_db VARCHAR(64) NOT NULL,
    downstream_table VARCHAR(128) NOT NULL,
    job_id VARCHAR(64),
    created_at DATETIME NOT NULL,
    PRIMARY KEY (lin_id),
    KEY idx_up (upstream_db, upstream_table),
    KEY idx_down (downstream_db, downstream_table)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '数据血缘';
