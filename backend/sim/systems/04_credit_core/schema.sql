-- ============================================================
-- 信贷核心系统 —— sim_credit_core
-- 授信、支用（放款）、还款、账务、状态
-- ============================================================

DROP TABLE IF EXISTS loan_status_log;
DROP TABLE IF EXISTS fee_charge;
DROP TABLE IF EXISTS contract;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS overdue_record;
DROP TABLE IF EXISTS repayment_actual;
DROP TABLE IF EXISTS repayment_plan;
DROP TABLE IF EXISTS loan_ledger;
DROP TABLE IF EXISTS loan;
DROP TABLE IF EXISTS credit_limit;

-- 产品目录
CREATE TABLE product (
    product_code VARCHAR(32) NOT NULL,
    product_name VARCHAR(64) NOT NULL,
    product_kind VARCHAR(32) NOT NULL COMMENT '自营/助贷/联合贷/担保',
    min_amount DECIMAL(12,2) NOT NULL,
    max_amount DECIMAL(12,2) NOT NULL,
    term_options VARCHAR(64) COMMENT '3,6,12,18,24',
    apr_default DECIMAL(6,4) NOT NULL,
    fee_rate DECIMAL(6,4) DEFAULT 0.0,
    is_active TINYINT NOT NULL DEFAULT 1,
    effective_from DATE NOT NULL,
    PRIMARY KEY (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '产品目录';

-- 授信额度
CREATE TABLE credit_limit (
    limit_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL COMMENT '总授信额度',
    available_amount DECIMAL(12,2) NOT NULL COMMENT '可用额度',
    used_amount DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '已用额度',
    apr DECIMAL(6,4) NOT NULL COMMENT '批复年化利率',
    grade VARCHAR(4) COMMENT '关联风险等级',
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/FROZEN/EXPIRED',
    created_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (limit_id),
    KEY idx_customer_product (customer_id, product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '授信额度';

-- 借据（支用/放款订单）
CREATE TABLE loan (
    loan_id VARCHAR(32) NOT NULL COMMENT 'LNyyyyMMddNNNNNN',
    application_id VARCHAR(32) COMMENT '关联进件',
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    limit_id BIGINT COMMENT '关联授信额度',
    principal DECIMAL(12,2) NOT NULL COMMENT '本金',
    term_months INT NOT NULL,
    apr DECIMAL(6,4) NOT NULL,
    disburse_time DATETIME NOT NULL COMMENT '放款时间',
    first_repay_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    disburse_account VARCHAR(32) NOT NULL COMMENT '打款账户（虚构）',
    status VARCHAR(16) NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL/OVERDUE/SETTLED/BAD_DEBT/EARLY_CLEAR',
    fund_source_code VARCHAR(32) COMMENT '资金来源 partner_id',
    branch_code VARCHAR(16) COMMENT '归属分公司',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (loan_id),
    KEY idx_customer (customer_id),
    KEY idx_product (product_code),
    KEY idx_disburse_time (disburse_time),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据主表';

-- 借据台账（余额快照）
CREATE TABLE loan_ledger (
    ledger_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    snap_date DATE NOT NULL,
    outstanding_principal DECIMAL(12,2) NOT NULL COMMENT '剩余本金',
    outstanding_interest DECIMAL(12,2) NOT NULL COMMENT '剩余利息',
    overdue_days INT NOT NULL DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ledger_id),
    UNIQUE KEY uk_loan_date (loan_id, snap_date),
    KEY idx_snap_date (snap_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据每日快照';

-- 还款计划
CREATE TABLE repayment_plan (
    plan_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    period_no INT NOT NULL COMMENT '第几期',
    due_date DATE NOT NULL,
    principal DECIMAL(12,2) NOT NULL,
    interest DECIMAL(12,2) NOT NULL,
    fee DECIMAL(12,2) DEFAULT 0.0,
    total_amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/PAID/OVERDUE/PARTIAL',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (plan_id),
    UNIQUE KEY uk_loan_period (loan_id, period_no),
    KEY idx_due_date (due_date, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款计划';

-- 还款实际流水
CREATE TABLE repayment_actual (
    repay_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    period_no INT NOT NULL,
    plan_id BIGINT,
    pay_time DATETIME NOT NULL,
    pay_amount DECIMAL(12,2) NOT NULL,
    principal_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
    interest_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
    fee_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
    penalty_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
    pay_channel VARCHAR(16) NOT NULL COMMENT 'AUTO/MANUAL/COLLECTION',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (repay_id),
    KEY idx_loan_period (loan_id, period_no),
    KEY idx_pay_time (pay_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款实际流水';

-- 逾期记录
CREATE TABLE overdue_record (
    overdue_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    period_no INT NOT NULL,
    overdue_start_date DATE NOT NULL,
    overdue_end_date DATE COMMENT 'NULL 表示仍在逾期',
    overdue_days INT NOT NULL,
    overdue_amount DECIMAL(12,2) NOT NULL,
    stage VARCHAR(8) NOT NULL COMMENT 'M0/M1/M2/M3/M3+',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (overdue_id),
    KEY idx_loan (loan_id),
    KEY idx_stage (stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '逾期记录';

-- 合同
CREATE TABLE contract (
    contract_id VARCHAR(32) NOT NULL,
    loan_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    contract_type VARCHAR(32) NOT NULL COMMENT 'LOAN/GUARANTEE/JOINT',
    signed_at DATETIME NOT NULL,
    contract_url VARCHAR(255),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (contract_id),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '合同';

-- 费用/收费
CREATE TABLE fee_charge (
    fee_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    fee_type VARCHAR(32) NOT NULL COMMENT 'SERVICE_FEE/PENALTY_FEE/EARLY_CLEAR_FEE',
    fee_amount DECIMAL(12,2) NOT NULL,
    charge_time DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (fee_id),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '费用';

-- 借据状态流水
CREATE TABLE loan_status_log (
    log_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    from_status VARCHAR(16),
    to_status VARCHAR(16) NOT NULL,
    remark VARCHAR(255),
    changed_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (log_id),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据状态流水';
