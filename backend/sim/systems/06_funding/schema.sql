-- ============================================================
-- 资金/合作方 —— sim_funding
-- ============================================================

DROP TABLE IF EXISTS guarantee_record;
DROP TABLE IF EXISTS partner_settle;
DROP TABLE IF EXISTS profit_share_record;
DROP TABLE IF EXISTS loan_funding_split;
DROP TABLE IF EXISTS funding_agreement;
DROP TABLE IF EXISTS funding_partner;

CREATE TABLE funding_partner (
    partner_code VARCHAR(32) NOT NULL,
    partner_name VARCHAR(128) NOT NULL,
    partner_type VARCHAR(16) NOT NULL COMMENT 'BANK/TRUST/GUARANTEE/PLATFORM',
    contact_person VARCHAR(64),
    contact_phone VARCHAR(32),
    onboarded_at DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金合作方';

CREATE TABLE funding_agreement (
    agreement_id VARCHAR(32) NOT NULL,
    partner_code VARCHAR(32) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    funding_share DECIMAL(6,4) NOT NULL COMMENT '出资比例',
    profit_share DECIMAL(6,4) NOT NULL COMMENT '分润比例',
    guarantee_ratio DECIMAL(6,4) DEFAULT 0.0 COMMENT '担保方兜底比例',
    cost_of_fund_apr DECIMAL(6,4) NOT NULL COMMENT '资金成本年化',
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (agreement_id),
    KEY idx_partner (partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '资金合作协议';

CREATE TABLE loan_funding_split (
    split_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    partner_code VARCHAR(32) NOT NULL,
    agreement_id VARCHAR(32) NOT NULL,
    funding_amount DECIMAL(12,2) NOT NULL COMMENT '该合作方出资金额',
    funding_ratio DECIMAL(6,4) NOT NULL,
    created_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (split_id),
    KEY idx_loan (loan_id),
    KEY idx_partner (partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '借据资金拆分';

CREATE TABLE profit_share_record (
    record_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    partner_code VARCHAR(32) NOT NULL,
    period_no INT NOT NULL,
    settle_date DATE NOT NULL,
    partner_income DECIMAL(12,2) NOT NULL COMMENT '合作方分润金额',
    self_income DECIMAL(12,2) NOT NULL COMMENT '自留金额',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (record_id),
    KEY idx_loan (loan_id, partner_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '分润记录';

CREATE TABLE partner_settle (
    settle_id BIGINT NOT NULL AUTO_INCREMENT,
    partner_code VARCHAR(32) NOT NULL,
    settle_period VARCHAR(8) NOT NULL COMMENT 'yyyyMM',
    total_income DECIMAL(14,2) NOT NULL,
    total_cost DECIMAL(14,2) NOT NULL,
    net_settle_amount DECIMAL(14,2) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PAID',
    settled_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (settle_id),
    UNIQUE KEY uk_partner_period (partner_code, settle_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '合作方月度结算';

CREATE TABLE guarantee_record (
    guarantee_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    partner_code VARCHAR(32) NOT NULL COMMENT '担保方',
    guarantee_amount DECIMAL(12,2) NOT NULL,
    guarantee_fee_rate DECIMAL(6,4) NOT NULL,
    claim_status VARCHAR(16) NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL/CLAIMED/PAID',
    claim_amount DECIMAL(12,2) DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (guarantee_id),
    KEY idx_loan (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '担保记录';
