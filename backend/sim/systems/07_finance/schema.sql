-- ============================================================
-- 财务 —— sim_finance
-- ============================================================

DROP TABLE IF EXISTS interest_income;
DROP TABLE IF EXISTS fee_income;
DROP TABLE IF EXISTS reconcile_log;
DROP TABLE IF EXISTS tax_record;
DROP TABLE IF EXISTS settlement;
DROP TABLE IF EXISTS gl_journal;
DROP TABLE IF EXISTS gl_account;

CREATE TABLE gl_account (
    account_code VARCHAR(32) NOT NULL COMMENT '会计科目',
    account_name VARCHAR(128) NOT NULL,
    account_kind VARCHAR(16) NOT NULL COMMENT 'ASSET/LIABILITY/EQUITY/INCOME/EXPENSE',
    parent_code VARCHAR(32),
    is_active TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (account_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '会计科目表';

CREATE TABLE gl_journal (
    journal_id BIGINT NOT NULL AUTO_INCREMENT,
    biz_date DATE NOT NULL,
    account_code VARCHAR(32) NOT NULL,
    direction VARCHAR(4) NOT NULL COMMENT 'DR/CR',
    amount DECIMAL(14,2) NOT NULL,
    biz_ref_type VARCHAR(16) COMMENT 'LOAN/REPAY/FEE/COST',
    biz_ref_id VARCHAR(32),
    remark VARCHAR(255),
    posted_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (journal_id),
    KEY idx_biz_date (biz_date),
    KEY idx_account (account_code),
    KEY idx_biz_ref (biz_ref_type, biz_ref_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '总账凭证';

CREATE TABLE settlement (
    settle_id BIGINT NOT NULL AUTO_INCREMENT,
    settle_date DATE NOT NULL,
    settle_type VARCHAR(16) NOT NULL COMMENT 'DISBURSE/REPAY/PARTNER',
    ref_id VARCHAR(32) NOT NULL,
    amount DECIMAL(14,2) NOT NULL,
    from_account VARCHAR(64) NOT NULL,
    to_account VARCHAR(64) NOT NULL,
    channel VARCHAR(16) NOT NULL COMMENT 'BANK/OTHER',
    status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (settle_id),
    KEY idx_settle_date (settle_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金结算流水';

CREATE TABLE tax_record (
    tax_id BIGINT NOT NULL AUTO_INCREMENT,
    tax_period VARCHAR(8) NOT NULL COMMENT 'yyyyMM',
    tax_kind VARCHAR(32) NOT NULL COMMENT 'VAT/INCOME_TAX/STAMP',
    tax_base DECIMAL(14,2) NOT NULL,
    tax_amount DECIMAL(14,2) NOT NULL,
    filed_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (tax_id),
    KEY idx_period (tax_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '税务记录';

CREATE TABLE reconcile_log (
    log_id BIGINT NOT NULL AUTO_INCREMENT,
    reconcile_date DATE NOT NULL,
    system_name VARCHAR(32) NOT NULL COMMENT '对账对象',
    diff_count INT NOT NULL DEFAULT 0,
    diff_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'OK',
    remark VARCHAR(255),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (log_id),
    KEY idx_date (reconcile_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '对账日志';

CREATE TABLE fee_income (
    fi_id BIGINT NOT NULL AUTO_INCREMENT,
    biz_date DATE NOT NULL,
    loan_id VARCHAR(32) NOT NULL,
    fee_type VARCHAR(32) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (fi_id),
    KEY idx_biz_date (biz_date),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '手续费收入';

CREATE TABLE interest_income (
    ii_id BIGINT NOT NULL AUTO_INCREMENT,
    biz_date DATE NOT NULL,
    loan_id VARCHAR(32) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ii_id),
    KEY idx_biz_date (biz_date),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '利息收入';
