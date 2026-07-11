-- ============================================================
-- ADS 层表定义 (5 张表)
-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 ads_* 部分
-- ============================================================

DROP TABLE IF EXISTS ads_credit_daily_dashboard;
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

DROP TABLE IF EXISTS ads_risk_daily_dashboard;
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

DROP TABLE IF EXISTS ads_finance_daily_dashboard;
CREATE TABLE ads_finance_daily_dashboard (
    stat_date DATE NOT NULL,
    interest_income DECIMAL(16,2) DEFAULT 0,
    fee_income DECIMAL(16,2) DEFAULT 0,
    total_income DECIMAL(16,2) DEFAULT 0,
    partner_cost DECIMAL(16,2) DEFAULT 0,
    net_profit DECIMAL(16,2) DEFAULT 0,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日财务驾驶舱';

DROP TABLE IF EXISTS ads_marketing_roi_daily;
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

DROP TABLE IF EXISTS ads_operation_daily;
CREATE TABLE ads_operation_daily (
    stat_date DATE NOT NULL,
    active_users INT DEFAULT 0,
    new_users INT DEFAULT 0,
    total_tickets INT DEFAULT 0,
    complaint_rate DECIMAL(6,4) DEFAULT 0,
    csat_avg DECIMAL(4,2),
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '每日运营驾驶舱';
