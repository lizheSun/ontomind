-- ============================================================
-- 埋点收集 —— sim_events
-- ============================================================

DROP TABLE IF EXISTS click_stream;
DROP TABLE IF EXISTS page_view;
DROP TABLE IF EXISTS app_event;

CREATE TABLE app_event (
    event_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) COMMENT '未登录时可空',
    device_id VARCHAR(64) NOT NULL,
    event_name VARCHAR(64) NOT NULL COMMENT 'app_open/reg/apply_submit/loan_success/repay',
    event_time DATETIME NOT NULL,
    platform VARCHAR(16) NOT NULL COMMENT 'iOS/Android/H5/WeApp',
    app_version VARCHAR(16),
    channel_code VARCHAR(32),
    campaign_id VARCHAR(32),
    props_json TEXT COMMENT 'JSON 事件属性',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (event_id),
    KEY idx_customer (customer_id),
    KEY idx_event_time (event_time),
    KEY idx_event_name (event_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT 'APP 事件';

CREATE TABLE page_view (
    pv_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16),
    device_id VARCHAR(64) NOT NULL,
    page_path VARCHAR(128) NOT NULL,
    referrer VARCHAR(128),
    view_time DATETIME NOT NULL,
    duration_ms INT DEFAULT 0,
    platform VARCHAR(16) NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (pv_id),
    KEY idx_view_time (view_time),
    KEY idx_page (page_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '页面浏览';

CREATE TABLE click_stream (
    click_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16),
    device_id VARCHAR(64) NOT NULL,
    element_id VARCHAR(64) NOT NULL,
    element_text VARCHAR(64),
    page_path VARCHAR(128) NOT NULL,
    click_time DATETIME NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (click_id),
    KEY idx_click_time (click_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '点击流';
