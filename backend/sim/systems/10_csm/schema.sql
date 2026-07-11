-- ============================================================
-- 客服 —— sim_csm
-- ============================================================

DROP TABLE IF EXISTS ticket_action;
DROP TABLE IF EXISTS complaint;
DROP TABLE IF EXISTS call_record;
DROP TABLE IF EXISTS ticket;

CREATE TABLE ticket (
    ticket_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    channel VARCHAR(16) NOT NULL COMMENT 'PHONE/APP/EMAIL/WECHAT',
    category VARCHAR(32) NOT NULL COMMENT '咨询/投诉/催收异议/资料/其他',
    subject VARCHAR(255) NOT NULL,
    priority TINYINT NOT NULL DEFAULT 3 COMMENT '1高 2中 3低',
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/PROCESSING/CLOSED',
    created_at DATETIME NOT NULL,
    closed_at DATETIME,
    handler VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ticket_id),
    KEY idx_customer (customer_id),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客服工单';

CREATE TABLE call_record (
    call_id BIGINT NOT NULL AUTO_INCREMENT,
    ticket_id VARCHAR(32),
    customer_id VARCHAR(16) NOT NULL,
    direction VARCHAR(8) NOT NULL COMMENT 'IN/OUT',
    call_time DATETIME NOT NULL,
    duration_sec INT NOT NULL DEFAULT 0,
    csat_score TINYINT COMMENT '满意度 1-5',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (call_id),
    KEY idx_customer (customer_id),
    KEY idx_call_time (call_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '通话记录';

CREATE TABLE complaint (
    complaint_id BIGINT NOT NULL AUTO_INCREMENT,
    ticket_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    reason_code VARCHAR(32) NOT NULL COMMENT 'RATE_HIGH/COLLECTION/SERVICE/PRIVACY',
    escalated TINYINT NOT NULL DEFAULT 0,
    reported_regulator TINYINT NOT NULL DEFAULT 0,
    filed_at DATETIME NOT NULL,
    resolved_at DATETIME,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (complaint_id),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '投诉';

CREATE TABLE ticket_action (
    action_id BIGINT NOT NULL AUTO_INCREMENT,
    ticket_id VARCHAR(32) NOT NULL,
    action VARCHAR(32) NOT NULL COMMENT '备注/转派/升级/回访/关闭',
    remark VARCHAR(255),
    acted_at DATETIME NOT NULL,
    actor VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (action_id),
    KEY idx_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '工单动作';
