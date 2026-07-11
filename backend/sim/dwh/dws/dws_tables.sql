-- ============================================================
-- DWS 层表定义 (11 张表)
-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 dws_* 部分
-- ============================================================

DROP TABLE IF EXISTS dws_customer_active_day;
CREATE TABLE dws_customer_active_day (
    stat_date DATE NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    active_events INT NOT NULL DEFAULT 0,
    is_test_user TINYINT NOT NULL DEFAULT 0,
    is_robot TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日活跃客户';

DROP TABLE IF EXISTS dws_credit_customer_day;
CREATE TABLE dws_credit_customer_day (
    stat_date DATE NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    apply_count INT NOT NULL DEFAULT 0,
    approve_count INT NOT NULL DEFAULT 0,
    loan_count INT NOT NULL DEFAULT 0,
    loan_amount DECIMAL(14,2) DEFAULT 0,
    repay_amount DECIMAL(14,2) DEFAULT 0,
    outstanding_amount DECIMAL(14,2) DEFAULT 0,
    is_overdue_today TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, customer_id),
    KEY idx_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日客户信贷汇总';

DROP TABLE IF EXISTS dws_credit_product_day;
CREATE TABLE dws_credit_product_day (
    stat_date DATE NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    apply_count INT NOT NULL DEFAULT 0,
    approve_count INT NOT NULL DEFAULT 0,
    loan_count INT NOT NULL DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    avg_amount DECIMAL(12,2) DEFAULT 0,
    approve_rate DECIMAL(6,4) DEFAULT 0,
    m1_overdue_count INT DEFAULT 0,
    m3_overdue_count INT DEFAULT 0,
    PRIMARY KEY (stat_date, product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日产品信贷汇总';

DROP TABLE IF EXISTS dws_credit_channel_day;
CREATE TABLE dws_credit_channel_day (
    stat_date DATE NOT NULL,
    channel_code VARCHAR(32) NOT NULL,
    apply_count INT NOT NULL DEFAULT 0,
    approve_count INT NOT NULL DEFAULT 0,
    loan_count INT NOT NULL DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    new_customers INT DEFAULT 0,
    PRIMARY KEY (stat_date, channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日渠道汇总';

DROP TABLE IF EXISTS dws_credit_loan_day;
CREATE TABLE dws_credit_loan_day (
    stat_date DATE NOT NULL,
    loan_count INT NOT NULL DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    outstanding_balance DECIMAL(16,2) DEFAULT 0,
    overdue_balance DECIMAL(16,2) DEFAULT 0,
    m1_overdue_count INT DEFAULT 0,
    m2_overdue_count INT DEFAULT 0,
    m3_overdue_count INT DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日全公司信贷汇总';

DROP TABLE IF EXISTS dws_credit_overdue_day;
CREATE TABLE dws_credit_overdue_day (
    stat_date DATE NOT NULL,
    stage VARCHAR(8) NOT NULL,
    overdue_count INT NOT NULL DEFAULT 0,
    overdue_amount DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date, stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日逾期分级汇总';

DROP TABLE IF EXISTS dws_finance_income_day;
CREATE TABLE dws_finance_income_day (
    stat_date DATE NOT NULL,
    interest_income DECIMAL(16,2) DEFAULT 0,
    fee_income DECIMAL(16,2) DEFAULT 0,
    total_income DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日财务收入';

DROP TABLE IF EXISTS dws_marketing_channel_day;
CREATE TABLE dws_marketing_channel_day (
    stat_date DATE NOT NULL,
    channel_code VARCHAR(32) NOT NULL,
    ad_cost DECIMAL(14,2) DEFAULT 0,
    impression BIGINT DEFAULT 0,
    click BIGINT DEFAULT 0,
    new_reg INT DEFAULT 0,
    apply_count INT DEFAULT 0,
    loan_count INT DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date, channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日渠道营销汇总';

DROP TABLE IF EXISTS dws_risk_grade_day;
CREATE TABLE dws_risk_grade_day (
    stat_date DATE NOT NULL,
    grade VARCHAR(4) NOT NULL,
    customer_count INT NOT NULL DEFAULT 0,
    apply_count INT DEFAULT 0,
    approve_count INT DEFAULT 0,
    PRIMARY KEY (stat_date, grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日风险等级客户分布';

DROP TABLE IF EXISTS dws_funding_partner_month;
CREATE TABLE dws_funding_partner_month (
    stat_month VARCHAR(8) NOT NULL COMMENT 'yyyyMM',
    partner_code VARCHAR(32) NOT NULL,
    loan_count INT NOT NULL DEFAULT 0,
    funded_amount DECIMAL(16,2) DEFAULT 0,
    partner_income DECIMAL(16,2) DEFAULT 0,
    self_income DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_month, partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每月合作方汇总';

DROP TABLE IF EXISTS dws_csm_ticket_day;
CREATE TABLE dws_csm_ticket_day (
    stat_date DATE NOT NULL,
    category VARCHAR(32) NOT NULL,
    ticket_count INT NOT NULL DEFAULT 0,
    complaint_count INT NOT NULL DEFAULT 0,
    closed_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日工单汇总';
