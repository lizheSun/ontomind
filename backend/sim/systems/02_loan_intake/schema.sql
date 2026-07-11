-- ============================================================
-- 进件受理系统 —— sim_loan_intake
-- 客户发起借款申请，收集资料，触发风控
-- ============================================================

DROP TABLE IF EXISTS intake_channel_ref;
DROP TABLE IF EXISTS credit_report_pull;
DROP TABLE IF EXISTS doc_upload;
DROP TABLE IF EXISTS application_status_log;
DROP TABLE IF EXISTS application;

-- 进件申请单
CREATE TABLE application (
    application_id VARCHAR(32) NOT NULL COMMENT '申请单号 APyyyyMMddNNNNNN',
    customer_id VARCHAR(16) NOT NULL,
    product_code VARCHAR(32) NOT NULL COMMENT 'SELF_LOAN/PLATFORM_LOAN/JOINT_LOAN/GUARANTEE_LOAN',
    apply_amount DECIMAL(12,2) NOT NULL COMMENT '申请金额',
    apply_term INT NOT NULL COMMENT '申请期数（月）',
    channel_code VARCHAR(32) NOT NULL COMMENT '来源渠道',
    campaign_id VARCHAR(32) COMMENT '关联营销活动',
    apply_purpose VARCHAR(32) COMMENT '借款用途',
    status VARCHAR(16) NOT NULL COMMENT 'INIT/PENDING/APPROVED/REJECTED/CANCELED',
    reject_code VARCHAR(32),
    apply_time DATETIME NOT NULL,
    decision_time DATETIME,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (application_id),
    KEY idx_customer (customer_id),
    KEY idx_apply_time (apply_time),
    KEY idx_product (product_code),
    KEY idx_channel (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '进件申请单';

-- 状态变更日志
CREATE TABLE application_status_log (
    log_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32) NOT NULL,
    from_status VARCHAR(16),
    to_status VARCHAR(16) NOT NULL,
    remark VARCHAR(255),
    changed_at DATETIME NOT NULL,
    changed_by VARCHAR(32) NOT NULL DEFAULT 'SYSTEM',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (log_id),
    KEY idx_app (application_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '进件状态流水';

-- 资料上传
CREATE TABLE doc_upload (
    doc_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32) NOT NULL,
    doc_type VARCHAR(32) NOT NULL COMMENT 'ID_FRONT/ID_BACK/FACE/INCOME_PROOF/CARD',
    doc_url VARCHAR(255) NOT NULL COMMENT '虚构 OSS 路径',
    uploaded_at DATETIME NOT NULL,
    verify_result VARCHAR(16) COMMENT 'PASS/FAIL/PENDING',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (doc_id),
    KEY idx_app (application_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '进件资料上传';

-- 征信报告拉取
CREATE TABLE credit_report_pull (
    pull_id BIGINT NOT NULL AUTO_INCREMENT,
    application_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    bureau VARCHAR(32) NOT NULL COMMENT 'PBOC/BAIRONG/TONGDUN',
    pull_time DATETIME NOT NULL,
    score INT COMMENT '征信分',
    overdue_count INT DEFAULT 0,
    query_count_1m INT DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (pull_id),
    KEY idx_app (application_id),
    KEY idx_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '征信报告拉取';

-- 渠道字典（进件系统本地缓存）
CREATE TABLE intake_channel_ref (
    channel_code VARCHAR(32) NOT NULL,
    channel_name VARCHAR(64) NOT NULL,
    channel_type VARCHAR(16) NOT NULL COMMENT 'ORGANIC/PAID/PARTNER',
    is_active TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '进件渠道字典';
