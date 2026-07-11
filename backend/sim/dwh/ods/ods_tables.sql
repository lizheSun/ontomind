-- ============================================================
-- ODS 层表定义 (16 张表)
-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 ods_* 部分
-- ============================================================

DROP TABLE IF EXISTS ods_cif_customer;
CREATE TABLE ods_cif_customer (
    customer_id VARCHAR(16) NOT NULL,
    name VARCHAR(64),
    gender TINYINT,
    birth_date DATE,
    age INT,
    education VARCHAR(16),
    marital VARCHAR(16),
    occupation VARCHAR(32),
    monthly_income DECIMAL(12,2),
    reg_channel VARCHAR(32),
    reg_time DATETIME,
    status VARCHAR(16),
    ods_stat_date DATE NOT NULL COMMENT '抽数日期',
    PRIMARY KEY (customer_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户主档 ODS';

DROP TABLE IF EXISTS ods_intake_application;
CREATE TABLE ods_intake_application (
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32),
    apply_amount DECIMAL(12,2),
    apply_term INT,
    channel_code VARCHAR(32),
    campaign_id VARCHAR(32),
    status VARCHAR(16),
    reject_code VARCHAR(32),
    apply_time DATETIME,
    decision_time DATETIME,
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (application_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '进件 ODS';

DROP TABLE IF EXISTS ods_risk_decision;
CREATE TABLE ods_risk_decision (
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16),
    decision VARCHAR(16),
    reject_reasons VARCHAR(512),
    approve_amount DECIMAL(12,2),
    approve_apr DECIMAL(6,4),
    approve_term INT,
    decided_at DATETIME,
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (application_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '风控决策 ODS';

DROP TABLE IF EXISTS ods_credit_limit;
CREATE TABLE ods_credit_limit (
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    total_amount DECIMAL(12,2),
    apr DECIMAL(6,4),
    grade VARCHAR(4),
    valid_from DATE,
    status VARCHAR(16),
    created_at DATETIME,
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (customer_id, product_code, created_at, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '授信额度 ODS';

DROP TABLE IF EXISTS ods_credit_loan;
CREATE TABLE ods_credit_loan (
    loan_id VARCHAR(32) NOT NULL,
    application_id VARCHAR(32),
    customer_id VARCHAR(16),
    product_code VARCHAR(32),
    principal DECIMAL(12,2),
    term_months INT,
    apr DECIMAL(6,4),
    disburse_time DATETIME,
    maturity_date DATE,
    status VARCHAR(16),
    fund_source_code VARCHAR(32),
    branch_code VARCHAR(16),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (loan_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据 ODS';

DROP TABLE IF EXISTS ods_credit_repayment_plan;
CREATE TABLE ods_credit_repayment_plan (
    plan_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    period_no INT,
    due_date DATE,
    principal DECIMAL(12,2),
    interest DECIMAL(12,2),
    total_amount DECIMAL(12,2),
    status VARCHAR(16),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (plan_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款计划 ODS';

DROP TABLE IF EXISTS ods_credit_repayment_actual;
CREATE TABLE ods_credit_repayment_actual (
    repay_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    period_no INT,
    pay_time DATETIME,
    pay_amount DECIMAL(12,2),
    principal_paid DECIMAL(12,2),
    interest_paid DECIMAL(12,2),
    penalty_paid DECIMAL(12,2),
    pay_channel VARCHAR(16),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (repay_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款流水 ODS';

DROP TABLE IF EXISTS ods_credit_overdue;
CREATE TABLE ods_credit_overdue (
    overdue_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    period_no INT,
    overdue_start_date DATE,
    overdue_end_date DATE,
    overdue_days INT,
    overdue_amount DECIMAL(12,2),
    stage VARCHAR(8),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (overdue_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '逾期 ODS';

DROP TABLE IF EXISTS ods_collection_case;
CREATE TABLE ods_collection_case (
    case_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    customer_id VARCHAR(16),
    open_date DATE,
    close_date DATE,
    stage_entered VARCHAR(8),
    outstanding_amount DECIMAL(12,2),
    status VARCHAR(16),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (case_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '催收案件 ODS';

DROP TABLE IF EXISTS ods_funding_split;
CREATE TABLE ods_funding_split (
    split_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    partner_code VARCHAR(32),
    funding_amount DECIMAL(12,2),
    funding_ratio DECIMAL(6,4),
    created_at DATETIME,
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (split_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金拆分 ODS';

DROP TABLE IF EXISTS ods_funding_share;
CREATE TABLE ods_funding_share (
    record_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    partner_code VARCHAR(32),
    period_no INT,
    settle_date DATE,
    partner_income DECIMAL(12,2),
    self_income DECIMAL(12,2),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (record_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '分润 ODS';

DROP TABLE IF EXISTS ods_marketing_ad_cost;
CREATE TABLE ods_marketing_ad_cost (
    cost_id BIGINT NOT NULL,
    campaign_id VARCHAR(32),
    channel_code VARCHAR(32),
    cost_date DATE,
    impression BIGINT,
    click BIGINT,
    cost DECIMAL(14,2),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (cost_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '广告成本 ODS';

DROP TABLE IF EXISTS ods_marketing_attribution;
CREATE TABLE ods_marketing_attribution (
    attr_id BIGINT NOT NULL,
    customer_id VARCHAR(16),
    campaign_id VARCHAR(32),
    channel_code VARCHAR(32),
    attribute_time DATETIME,
    event_type VARCHAR(16),
    weight DECIMAL(6,4),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (attr_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '归因 ODS';

DROP TABLE IF EXISTS ods_finance_gl_journal;
CREATE TABLE ods_finance_gl_journal (
    journal_id BIGINT NOT NULL,
    biz_date DATE,
    account_code VARCHAR(32),
    direction VARCHAR(4),
    amount DECIMAL(14,2),
    biz_ref_type VARCHAR(16),
    biz_ref_id VARCHAR(32),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (journal_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '总账凭证 ODS';

DROP TABLE IF EXISTS ods_events_app_event;
CREATE TABLE ods_events_app_event (
    event_id BIGINT NOT NULL,
    customer_id VARCHAR(16),
    device_id VARCHAR(64),
    event_name VARCHAR(64),
    event_time DATETIME,
    platform VARCHAR(16),
    channel_code VARCHAR(32),
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (event_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT 'APP 事件 ODS';

DROP TABLE IF EXISTS ods_csm_ticket;
CREATE TABLE ods_csm_ticket (
    ticket_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16),
    channel VARCHAR(16),
    category VARCHAR(32),
    priority TINYINT,
    status VARCHAR(16),
    created_at DATETIME,
    closed_at DATETIME,
    ods_stat_date DATE NOT NULL,
    PRIMARY KEY (ticket_id, ods_stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客服工单 ODS';
