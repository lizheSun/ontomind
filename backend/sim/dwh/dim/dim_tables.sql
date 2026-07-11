-- ============================================================
-- DIM 层表定义 (6 张表)
-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 dim_* 部分
-- ============================================================

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date_key INT NOT NULL COMMENT 'yyyymmdd',
    date_value DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(16),
    week_of_year INT NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week INT NOT NULL,
    is_weekend TINYINT NOT NULL,
    is_holiday TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (date_key),
    UNIQUE KEY uk_date (date_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '日期维度';

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer (
    dim_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL COMMENT '业务主键',
    name VARCHAR(64),
    gender_code TINYINT,
    gender_name VARCHAR(8),
    age INT,
    age_group VARCHAR(16) COMMENT '18-25/26-35/36-45/46-55/55+',
    education VARCHAR(16),
    marital VARCHAR(16),
    occupation VARCHAR(32),
    monthly_income DECIMAL(12,2),
    income_grade VARCHAR(16) COMMENT '低收入(<5k)/中低(5-10k)/中(10-20k)/中高(20-50k)/高(50k+)',
    province VARCHAR(32),
    reg_channel VARCHAR(32),
    reg_date DATE,
    status VARCHAR(16),
    valid_from DATETIME NOT NULL COMMENT 'SCD2 有效开始',
    valid_to DATETIME NOT NULL DEFAULT '9999-12-31 23:59:59' COMMENT 'SCD2 有效结束',
    is_current TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (dim_id),
    KEY idx_customer (customer_id, is_current),
    KEY idx_reg_date (reg_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户维度 (SCD Type 2)';

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    dim_id INT NOT NULL AUTO_INCREMENT,
    product_code VARCHAR(32) NOT NULL,
    product_name VARCHAR(64) NOT NULL,
    product_kind VARCHAR(32) NOT NULL COMMENT '自营/助贷/联合贷/担保',
    min_amount DECIMAL(12,2),
    max_amount DECIMAL(12,2),
    apr_default DECIMAL(6,4),
    is_active TINYINT NOT NULL,
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '产品维度';

DROP TABLE IF EXISTS dim_channel;
CREATE TABLE dim_channel (
    dim_id INT NOT NULL AUTO_INCREMENT,
    channel_code VARCHAR(32) NOT NULL,
    channel_name VARCHAR(64) NOT NULL,
    channel_type VARCHAR(16) NOT NULL COMMENT 'ORGANIC/PAID/PARTNER',
    channel_owner VARCHAR(32),
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '渠道维度';

DROP TABLE IF EXISTS dim_org;
CREATE TABLE dim_org (
    dim_id INT NOT NULL AUTO_INCREMENT,
    org_code VARCHAR(16) NOT NULL,
    org_name VARCHAR(64) NOT NULL,
    parent_code VARCHAR(16),
    org_level TINYINT NOT NULL,
    org_type VARCHAR(16) NOT NULL,
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (org_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '组织维度';

DROP TABLE IF EXISTS dim_funding_partner;
CREATE TABLE dim_funding_partner (
    dim_id INT NOT NULL AUTO_INCREMENT,
    partner_code VARCHAR(32) NOT NULL,
    partner_name VARCHAR(128) NOT NULL,
    partner_type VARCHAR(16) NOT NULL COMMENT 'BANK/TRUST/GUARANTEE/PLATFORM',
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金合作方维度';
