-- ============================================================
-- 风险决策系统 —— sim_risk_decision
-- 反欺诈、准入规则、评分模型、黑名单、决策结果
-- ============================================================

DROP TABLE IF EXISTS policy_ref;
DROP TABLE IF EXISTS risk_grade;
DROP TABLE IF EXISTS antifraud_event;
DROP TABLE IF EXISTS blacklist;
DROP TABLE IF EXISTS model_score;
DROP TABLE IF EXISTS decision_log;
DROP TABLE IF EXISTS rule_set;

-- 规则集
CREATE TABLE rule_set (
    rule_id VARCHAR(32) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    rule_type VARCHAR(32) NOT NULL COMMENT 'HARD_REJECT/SOFT_REJECT/WARNING',
    domain VARCHAR(32) NOT NULL COMMENT 'ANTIFRAUD/CREDIT/COMPLIANCE',
    formula TEXT,
    is_active TINYINT NOT NULL DEFAULT 1,
    version INT NOT NULL DEFAULT 1,
    effective_from DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '风控规则集';

-- 决策日志（每次进件都有一条）
CREATE TABLE decision_log (
    decision_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    decision VARCHAR(16) NOT NULL COMMENT 'APPROVE/REJECT/REVIEW',
    reject_reasons VARCHAR(512) COMMENT '多个 rule_id 逗号分隔',
    approve_amount DECIMAL(12,2) COMMENT '审批额度',
    approve_apr DECIMAL(6,4) COMMENT '审批利率（年化）',
    approve_term INT COMMENT '审批期数',
    decided_at DATETIME NOT NULL,
    decision_ver VARCHAR(16) NOT NULL DEFAULT 'v1',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (decision_id),
    UNIQUE KEY uk_app (application_id),
    KEY idx_customer (customer_id),
    KEY idx_decided_at (decided_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '风控决策日志';

-- 模型评分
CREATE TABLE model_score (
    score_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    model_code VARCHAR(32) NOT NULL COMMENT 'A_SCORE/B_SCORE/FRAUD_SCORE',
    score DECIMAL(6,2) NOT NULL,
    grade VARCHAR(4) NOT NULL COMMENT 'A/B/C/D/E',
    computed_at DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (score_id),
    KEY idx_app (application_id),
    KEY idx_customer (customer_id, model_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '模型评分';

-- 黑名单
CREATE TABLE blacklist (
    bl_id BIGINT NOT NULL AUTO_INCREMENT,
    hit_type VARCHAR(16) NOT NULL COMMENT 'ID/PHONE/BANK',
    hit_value VARCHAR(64) NOT NULL,
    reason_code VARCHAR(32) NOT NULL,
    source VARCHAR(32) NOT NULL COMMENT 'INTERNAL/EXTERNAL',
    listed_at DATETIME NOT NULL,
    expire_at DATETIME,
    is_active TINYINT NOT NULL DEFAULT 1,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (bl_id),
    KEY idx_hit (hit_type, hit_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '黑名单';

-- 反欺诈事件
CREATE TABLE antifraud_event (
    event_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32),
    customer_id VARCHAR(16) NOT NULL,
    event_code VARCHAR(32) NOT NULL COMMENT 'DEVICE_SHARE/GPS_ABNORMAL/BATCH_APPLY',
    risk_level VARCHAR(8) NOT NULL COMMENT 'LOW/MID/HIGH',
    detected_at DATETIME NOT NULL,
    action_taken VARCHAR(32) COMMENT 'BLOCK/REVIEW/WATCH',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (event_id),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '反欺诈事件';

-- 客户风险等级快照
CREATE TABLE risk_grade (
    grade_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    grade VARCHAR(4) NOT NULL COMMENT 'A/B/C/D/E',
    valid_from DATE NOT NULL,
    valid_to DATE,
    computed_by VARCHAR(32) NOT NULL DEFAULT 'B_SCORE',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (grade_id),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户风险等级';

-- 政策字典（利率/额度上限）
CREATE TABLE policy_ref (
    policy_code VARCHAR(32) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    grade VARCHAR(4) NOT NULL,
    max_amount DECIMAL(12,2) NOT NULL,
    apr_min DECIMAL(6,4) NOT NULL,
    apr_max DECIMAL(6,4) NOT NULL,
    effective_from DATE NOT NULL,
    PRIMARY KEY (policy_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '风控政策字典';
