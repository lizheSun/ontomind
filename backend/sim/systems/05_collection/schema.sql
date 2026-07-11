-- ============================================================
-- 催收管理 —— sim_collection
-- ============================================================

DROP TABLE IF EXISTS collector;
DROP TABLE IF EXISTS promise_to_pay;
DROP TABLE IF EXISTS collection_action;
DROP TABLE IF EXISTS collection_case;

CREATE TABLE collection_case (
    case_id BIGINT NOT NULL AUTO_INCREMENT,
    loan_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    open_date DATE NOT NULL,
    close_date DATE,
    stage_entered VARCHAR(8) NOT NULL COMMENT 'M1/M2/M3/M3+',
    priority TINYINT NOT NULL DEFAULT 3 COMMENT '1高 2中 3低',
    outstanding_amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(16) NOT NULL COMMENT 'OPEN/CLOSED_PAID/CLOSED_BAD',
    assignee VARCHAR(32) COMMENT '催收员工号',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (case_id),
    KEY idx_loan (loan_id),
    KEY idx_customer (customer_id),
    KEY idx_stage (stage_entered)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '催收案件';

CREATE TABLE collection_action (
    action_id BIGINT NOT NULL AUTO_INCREMENT,
    case_id BIGINT NOT NULL,
    action_type VARCHAR(16) NOT NULL COMMENT 'CALL/SMS/LETTER/VISIT/LEGAL',
    action_time DATETIME NOT NULL,
    talk_result VARCHAR(32) COMMENT 'PICK_UP/NO_ANSWER/REFUSE/PROMISE',
    remark VARCHAR(255),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (action_id),
    KEY idx_case (case_id),
    KEY idx_action_time (action_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '催收动作';

CREATE TABLE promise_to_pay (
    ptp_id BIGINT NOT NULL AUTO_INCREMENT,
    case_id BIGINT NOT NULL,
    promised_at DATETIME NOT NULL,
    promise_date DATE NOT NULL,
    promise_amount DECIMAL(12,2) NOT NULL,
    fulfilled TINYINT NOT NULL DEFAULT 0 COMMENT '0未 1已',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ptp_id),
    KEY idx_case (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '还款承诺';

CREATE TABLE collector (
    emp_no VARCHAR(32) NOT NULL,
    name VARCHAR(64) NOT NULL,
    team VARCHAR(32) NOT NULL COMMENT 'M1/M2/M3/M3+',
    branch_code VARCHAR(16),
    hire_date DATE NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (emp_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '催收员';
