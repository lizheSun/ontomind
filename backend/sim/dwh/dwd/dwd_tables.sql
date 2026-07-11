-- ============================================================
-- DWD 层表定义 (11 张表)
-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 dwd_* 部分
-- ============================================================

DROP TABLE IF EXISTS dwd_credit_application;
CREATE TABLE dwd_credit_application (
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    product_kind VARCHAR(32),
    apply_amount DECIMAL(12,2),
    apply_term INT,
    channel_code VARCHAR(32),
    channel_type VARCHAR(16),
    campaign_id VARCHAR(32),
    status VARCHAR(16),
    reject_code VARCHAR(32),
    apply_time DATETIME NOT NULL,
    decision_time DATETIME,
    apply_date DATE NOT NULL,
    -- 维度打宽
    customer_age INT,
    customer_gender TINYINT,
    customer_province VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (application_id),
    KEY idx_apply_date (apply_date),
    KEY idx_customer (customer_id),
    KEY idx_product (product_code),
    KEY idx_channel (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '申请事实明细';

DROP TABLE IF EXISTS dwd_credit_decision;
CREATE TABLE dwd_credit_decision (
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    decision VARCHAR(16) NOT NULL,
    reject_reasons VARCHAR(512),
    approve_amount DECIMAL(12,2),
    approve_apr DECIMAL(6,4),
    approve_term INT,
    decided_at DATETIME NOT NULL,
    decision_date DATE NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (application_id),
    KEY idx_decision_date (decision_date),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '风控决策事实明细';

DROP TABLE IF EXISTS dwd_credit_loan;
CREATE TABLE dwd_credit_loan (
    loan_id VARCHAR(32) NOT NULL,
    application_id VARCHAR(32),
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    product_kind VARCHAR(32),
    principal DECIMAL(12,2) NOT NULL,
    term_months INT NOT NULL,
    apr DECIMAL(6,4),
    disburse_time DATETIME NOT NULL,
    disburse_date DATE NOT NULL,
    first_repay_date DATE,
    maturity_date DATE,
    status VARCHAR(16),
    fund_source_code VARCHAR(32),
    branch_code VARCHAR(16),
    channel_code VARCHAR(32),
    channel_type VARCHAR(16),
    customer_age INT,
    customer_gender TINYINT,
    customer_province VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (loan_id),
    KEY idx_disburse_date (disburse_date),
    KEY idx_customer (customer_id),
    KEY idx_product (product_code),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据事实明细';

DROP TABLE IF EXISTS dwd_credit_repayment;
CREATE TABLE dwd_credit_repayment (
    repay_id BIGINT NOT NULL,
    loan_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    period_no INT NOT NULL,
    pay_time DATETIME NOT NULL,
    pay_date DATE NOT NULL,
    pay_amount DECIMAL(12,2) NOT NULL,
    principal_paid DECIMAL(12,2),
    interest_paid DECIMAL(12,2),
    penalty_paid DECIMAL(12,2),
    pay_channel VARCHAR(16),
    is_overdue_paid TINYINT NOT NULL DEFAULT 0 COMMENT '是否催回',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (repay_id),
    KEY idx_pay_date (pay_date),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款事实明细';

DROP TABLE IF EXISTS dwd_credit_overdue;
CREATE TABLE dwd_credit_overdue (
    overdue_id BIGINT NOT NULL,
    loan_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16),
    period_no INT,
    overdue_start_date DATE,
    overdue_end_date DATE,
    overdue_days INT,
    overdue_amount DECIMAL(12,2),
    stage VARCHAR(8),
    product_code VARCHAR(32),
    product_kind VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (overdue_id),
    KEY idx_loan (loan_id),
    KEY idx_stage (stage),
    KEY idx_start_date (overdue_start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '逾期事实明细';

DROP TABLE IF EXISTS dwd_credit_collection;
CREATE TABLE dwd_credit_collection (
    case_id BIGINT NOT NULL,
    loan_id VARCHAR(32),
    customer_id VARCHAR(16),
    open_date DATE,
    close_date DATE,
    stage_entered VARCHAR(8),
    outstanding_amount DECIMAL(12,2),
    status VARCHAR(16),
    is_recovered TINYINT NOT NULL DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (case_id),
    KEY idx_open_date (open_date),
    KEY idx_stage (stage_entered)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '催收事实明细';

DROP TABLE IF EXISTS dwd_marketing_attribution;
CREATE TABLE dwd_marketing_attribution (
    attr_id BIGINT NOT NULL,
    customer_id VARCHAR(16),
    campaign_id VARCHAR(32),
    channel_code VARCHAR(32),
    channel_type VARCHAR(16),
    attribute_time DATETIME,
    attribute_date DATE,
    event_type VARCHAR(16),
    weight DECIMAL(6,4),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (attr_id),
    KEY idx_attribute_date (attribute_date),
    KEY idx_channel (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '归因事实明细';

DROP TABLE IF EXISTS dwd_marketing_ad_cost;
CREATE TABLE dwd_marketing_ad_cost (
    cost_id BIGINT NOT NULL,
    campaign_id VARCHAR(32),
    channel_code VARCHAR(32),
    channel_type VARCHAR(16),
    cost_date DATE,
    impression BIGINT,
    click BIGINT,
    cost DECIMAL(14,2),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (cost_id),
    KEY idx_cost_date (cost_date),
    KEY idx_channel (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '广告成本事实明细';

DROP TABLE IF EXISTS dwd_finance_gl_journal;
CREATE TABLE dwd_finance_gl_journal (
    journal_id BIGINT NOT NULL,
    biz_date DATE NOT NULL,
    account_code VARCHAR(32),
    account_name VARCHAR(128),
    account_kind VARCHAR(16),
    direction VARCHAR(4),
    amount DECIMAL(14,2),
    biz_ref_type VARCHAR(16),
    biz_ref_id VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (journal_id),
    KEY idx_biz_date (biz_date),
    KEY idx_account (account_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '总账凭证明细';

DROP TABLE IF EXISTS dwd_events_app_event;
CREATE TABLE dwd_events_app_event (
    event_id BIGINT NOT NULL,
    customer_id VARCHAR(16),
    device_id VARCHAR(64),
    event_name VARCHAR(64),
    event_time DATETIME,
    event_date DATE,
    platform VARCHAR(16),
    channel_code VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (event_id),
    KEY idx_event_date (event_date),
    KEY idx_event_name (event_name),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT 'APP 事件明细';

DROP TABLE IF EXISTS dwd_csm_ticket;
CREATE TABLE dwd_csm_ticket (
    ticket_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16),
    channel VARCHAR(16),
    category VARCHAR(32),
    priority TINYINT,
    status VARCHAR(16),
    created_at DATETIME,
    closed_at DATETIME,
    created_date DATE,
    is_complaint TINYINT NOT NULL DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ticket_id),
    KEY idx_created_date (created_date),
    KEY idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客服工单明细';
