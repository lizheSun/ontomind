-- ============================================================
-- 营销 —— sim_marketing
-- ============================================================

DROP TABLE IF EXISTS user_promo_use;
DROP TABLE IF EXISTS promo_code;
DROP TABLE IF EXISTS attribution;
DROP TABLE IF EXISTS ad_cost;
DROP TABLE IF EXISTS campaign;
DROP TABLE IF EXISTS channel;

CREATE TABLE channel (
    channel_code VARCHAR(32) NOT NULL,
    channel_name VARCHAR(64) NOT NULL,
    channel_type VARCHAR(16) NOT NULL COMMENT 'ORGANIC/PAID/PARTNER',
    channel_owner VARCHAR(32),
    is_active TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '渠道';

CREATE TABLE campaign (
    campaign_id VARCHAR(32) NOT NULL,
    campaign_name VARCHAR(128) NOT NULL,
    channel_code VARCHAR(32) NOT NULL,
    product_code VARCHAR(32),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget DECIMAL(14,2) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (campaign_id),
    KEY idx_channel (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '营销活动';

CREATE TABLE ad_cost (
    cost_id BIGINT NOT NULL AUTO_INCREMENT,
    campaign_id VARCHAR(32) NOT NULL,
    channel_code VARCHAR(32) NOT NULL,
    cost_date DATE NOT NULL,
    impression BIGINT NOT NULL DEFAULT 0,
    click BIGINT NOT NULL DEFAULT 0,
    cost DECIMAL(14,2) NOT NULL,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (cost_id),
    KEY idx_campaign_date (campaign_id, cost_date),
    KEY idx_cost_date (cost_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '广告投放成本';

CREATE TABLE attribution (
    attr_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    campaign_id VARCHAR(32),
    channel_code VARCHAR(32) NOT NULL,
    attribute_time DATETIME NOT NULL,
    event_type VARCHAR(16) NOT NULL COMMENT 'REG/APPLY/LOAN',
    weight DECIMAL(6,4) DEFAULT 1.0 COMMENT '归因权重（多触点场景）',
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (attr_id),
    KEY idx_customer (customer_id),
    KEY idx_campaign (campaign_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '归因';

CREATE TABLE promo_code (
    promo_code VARCHAR(32) NOT NULL,
    promo_name VARCHAR(64) NOT NULL,
    discount_type VARCHAR(16) NOT NULL COMMENT 'APR_CUT/AMOUNT_OFF/GIFT',
    value_num DECIMAL(10,4) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    quota INT DEFAULT 0,
    used INT DEFAULT 0,
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (promo_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '优惠码';

CREATE TABLE user_promo_use (
    use_id BIGINT NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(16) NOT NULL,
    promo_code VARCHAR(32) NOT NULL,
    used_at DATETIME NOT NULL,
    loan_id VARCHAR(32),
    is_test_data TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (use_id),
    KEY idx_customer (customer_id),
    KEY idx_promo (promo_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '客户优惠码使用';
