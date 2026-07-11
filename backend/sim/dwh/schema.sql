-- ============================================================
-- 数据仓库 sim_dw
-- 分层：ODS（贴源）→ DIM（维度）→ DWD（明细事实）→ DWS（汇总）→ ADS（应用）
-- 建模：Kimball 星型
-- 命名：<layer>_<domain>_<entity>[_<grain>]
-- ============================================================

DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_channel;
DROP TABLE IF EXISTS dim_org;
DROP TABLE IF EXISTS dim_funding_partner;

DROP TABLE IF EXISTS ods_cif_customer;
DROP TABLE IF EXISTS ods_intake_application;
DROP TABLE IF EXISTS ods_risk_decision;
DROP TABLE IF EXISTS ods_credit_loan;
DROP TABLE IF EXISTS ods_credit_repayment_plan;
DROP TABLE IF EXISTS ods_credit_repayment_actual;
DROP TABLE IF EXISTS ods_credit_overdue;
DROP TABLE IF EXISTS ods_credit_limit;
DROP TABLE IF EXISTS ods_collection_case;
DROP TABLE IF EXISTS ods_funding_split;
DROP TABLE IF EXISTS ods_funding_share;
DROP TABLE IF EXISTS ods_marketing_ad_cost;
DROP TABLE IF EXISTS ods_marketing_attribution;
DROP TABLE IF EXISTS ods_finance_gl_journal;
DROP TABLE IF EXISTS ods_events_app_event;
DROP TABLE IF EXISTS ods_csm_ticket;

DROP TABLE IF EXISTS dwd_credit_application;
DROP TABLE IF EXISTS dwd_credit_decision;
DROP TABLE IF EXISTS dwd_credit_loan;
DROP TABLE IF EXISTS dwd_credit_repayment;
DROP TABLE IF EXISTS dwd_credit_overdue;
DROP TABLE IF EXISTS dwd_credit_collection;
DROP TABLE IF EXISTS dwd_marketing_attribution;
DROP TABLE IF EXISTS dwd_marketing_ad_cost;
DROP TABLE IF EXISTS dwd_finance_gl_journal;
DROP TABLE IF EXISTS dwd_events_app_event;
DROP TABLE IF EXISTS dwd_csm_ticket;

DROP TABLE IF EXISTS dws_credit_customer_day;
DROP TABLE IF EXISTS dws_credit_product_day;
DROP TABLE IF EXISTS dws_credit_channel_day;
DROP TABLE IF EXISTS dws_credit_loan_day;
DROP TABLE IF EXISTS dws_credit_overdue_day;
DROP TABLE IF EXISTS dws_customer_active_day;
DROP TABLE IF EXISTS dws_finance_income_day;
DROP TABLE IF EXISTS dws_marketing_channel_day;
DROP TABLE IF EXISTS dws_risk_grade_day;
DROP TABLE IF EXISTS dws_funding_partner_month;
DROP TABLE IF EXISTS dws_csm_ticket_day;

DROP TABLE IF EXISTS ads_credit_daily_dashboard;
DROP TABLE IF EXISTS ads_risk_daily_dashboard;
DROP TABLE IF EXISTS ads_finance_daily_dashboard;
DROP TABLE IF EXISTS ads_marketing_roi_daily;
DROP TABLE IF EXISTS ads_operation_daily;


-- ============================================================
-- DIM 层：共享维度
-- ============================================================

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

CREATE TABLE dim_channel (
    dim_id INT NOT NULL AUTO_INCREMENT,
    channel_code VARCHAR(32) NOT NULL,
    channel_name VARCHAR(64) NOT NULL,
    channel_type VARCHAR(16) NOT NULL COMMENT 'ORGANIC/PAID/PARTNER',
    channel_owner VARCHAR(32),
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '渠道维度';

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

CREATE TABLE dim_funding_partner (
    dim_id INT NOT NULL AUTO_INCREMENT,
    partner_code VARCHAR(32) NOT NULL,
    partner_name VARCHAR(128) NOT NULL,
    partner_type VARCHAR(16) NOT NULL COMMENT 'BANK/TRUST/GUARANTEE/PLATFORM',
    PRIMARY KEY (dim_id),
    UNIQUE KEY uk_code (partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金合作方维度';


-- ============================================================
-- ODS 层：贴源，尽量原样复制业务系统关键表
-- ============================================================

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


-- ============================================================
-- DWD 层：明细事实（清洗、维度打宽）
-- ============================================================

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


-- ============================================================
-- DWS 层：按主题按粒度的聚合
-- ============================================================

CREATE TABLE dws_customer_active_day (
    stat_date DATE NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    active_events INT NOT NULL DEFAULT 0,
    is_test_user TINYINT NOT NULL DEFAULT 0,
    is_robot TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日活跃客户';

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

CREATE TABLE dws_credit_overdue_day (
    stat_date DATE NOT NULL,
    stage VARCHAR(8) NOT NULL,
    overdue_count INT NOT NULL DEFAULT 0,
    overdue_amount DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date, stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日逾期分级汇总';

CREATE TABLE dws_finance_income_day (
    stat_date DATE NOT NULL,
    interest_income DECIMAL(16,2) DEFAULT 0,
    fee_income DECIMAL(16,2) DEFAULT 0,
    total_income DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日财务收入';

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

CREATE TABLE dws_risk_grade_day (
    stat_date DATE NOT NULL,
    grade VARCHAR(4) NOT NULL,
    customer_count INT NOT NULL DEFAULT 0,
    apply_count INT DEFAULT 0,
    approve_count INT DEFAULT 0,
    PRIMARY KEY (stat_date, grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日风险等级客户分布';

CREATE TABLE dws_funding_partner_month (
    stat_month VARCHAR(8) NOT NULL COMMENT 'yyyyMM',
    partner_code VARCHAR(32) NOT NULL,
    loan_count INT NOT NULL DEFAULT 0,
    funded_amount DECIMAL(16,2) DEFAULT 0,
    partner_income DECIMAL(16,2) DEFAULT 0,
    self_income DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_month, partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每月合作方汇总';

CREATE TABLE dws_csm_ticket_day (
    stat_date DATE NOT NULL,
    category VARCHAR(32) NOT NULL,
    ticket_count INT NOT NULL DEFAULT 0,
    complaint_count INT NOT NULL DEFAULT 0,
    closed_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_date, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日工单汇总';


-- ============================================================
-- ADS 层：应用集市（面向具体报表）
-- ============================================================

CREATE TABLE ads_credit_daily_dashboard (
    stat_date DATE NOT NULL,
    apply_count INT DEFAULT 0,
    approve_count INT DEFAULT 0,
    approve_rate DECIMAL(6,4) DEFAULT 0,
    loan_count INT DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    avg_amount DECIMAL(12,2) DEFAULT 0,
    active_customers INT DEFAULT 0,
    new_customers INT DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日信贷驾驶舱';

CREATE TABLE ads_risk_daily_dashboard (
    stat_date DATE NOT NULL,
    total_loan_count INT DEFAULT 0,
    m1_count INT DEFAULT 0,
    m3_count INT DEFAULT 0,
    m1_rate DECIMAL(6,4) DEFAULT 0,
    m3_rate DECIMAL(6,4) DEFAULT 0,
    reject_rate DECIMAL(6,4) DEFAULT 0,
    fraud_hit_count INT DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日风险驾驶舱';

CREATE TABLE ads_finance_daily_dashboard (
    stat_date DATE NOT NULL,
    interest_income DECIMAL(16,2) DEFAULT 0,
    fee_income DECIMAL(16,2) DEFAULT 0,
    total_income DECIMAL(16,2) DEFAULT 0,
    partner_cost DECIMAL(16,2) DEFAULT 0,
    net_profit DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日财务驾驶舱';

CREATE TABLE ads_marketing_roi_daily (
    stat_date DATE NOT NULL,
    channel_code VARCHAR(32) NOT NULL,
    ad_cost DECIMAL(14,2) DEFAULT 0,
    new_customers INT DEFAULT 0,
    loan_count INT DEFAULT 0,
    loan_amount DECIMAL(16,2) DEFAULT 0,
    cpa DECIMAL(12,2) COMMENT '获客成本 = cost / new_customers',
    roi DECIMAL(8,4) COMMENT '毛 ROI',
    PRIMARY KEY (stat_date, channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日渠道 ROI';

CREATE TABLE ads_operation_daily (
    stat_date DATE NOT NULL,
    active_users INT DEFAULT 0,
    new_users INT DEFAULT 0,
    total_tickets INT DEFAULT 0,
    complaint_rate DECIMAL(6,4) DEFAULT 0,
    csat_avg DECIMAL(4,2),
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日运营驾驶舱';
