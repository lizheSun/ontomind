-- ============================================================
-- ADS 层 ETL：5 步
-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）
-- 生产环境中，模板变量 ${today} / ${date} / ${month} 应由调度器填充
-- ============================================================

-- ads_credit_daily_dashboard insert
INSERT INTO ads_credit_daily_dashboard
        SELECT
            a.apply_date,
            COUNT(*) apply_count,
            SUM(a.status='APPROVED') approve_count,
            SUM(a.status='APPROVED')/COUNT(*),
            IFNULL(l.loan_count, 0),
            IFNULL(l.loan_amount, 0),
            IFNULL(l.avg_amount, 0),
            0,
            (SELECT COUNT(*) FROM dim_customer dc WHERE dc.reg_date = a.apply_date)
        FROM dwd_credit_application a
        LEFT JOIN (
            SELECT disburse_date, COUNT(*) loan_count, SUM(principal) loan_amount, AVG(principal) avg_amount
            FROM dwd_credit_loan GROUP BY disburse_date
        ) l ON l.disburse_date = a.apply_date
        GROUP BY a.apply_date, l.loan_count, l.loan_amount, l.avg_amount;

-- ads_risk_daily_dashboard insert
INSERT INTO ads_risk_daily_dashboard
        SELECT
            d.date_value,
            IFNULL((SELECT COUNT(*) FROM dwd_credit_loan WHERE disburse_date <= d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM dwd_credit_overdue WHERE stage IN ('M1','M2','M3','M3+') AND overdue_start_date <= d.date_value AND (overdue_end_date IS NULL OR overdue_end_date > d.date_value)), 0),
            IFNULL((SELECT COUNT(*) FROM dwd_credit_overdue WHERE stage IN ('M3','M3+') AND overdue_start_date <= d.date_value AND (overdue_end_date IS NULL OR overdue_end_date > d.date_value)), 0),
            0, 0,
            IFNULL((SELECT AVG(a.status='REJECTED') FROM dwd_credit_application a WHERE a.apply_date=d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM sim_risk_decision.antifraud_event WHERE DATE(detected_at)=d.date_value), 0)
        FROM dim_date d;

-- ads_finance_daily_dashboard insert
INSERT INTO ads_finance_daily_dashboard
        SELECT stat_date, interest_income, fee_income, total_income, 0, total_income
        FROM dws_finance_income_day;

-- ads_marketing_roi_daily insert
INSERT INTO ads_marketing_roi_daily
        SELECT
            stat_date, channel_code, ad_cost, new_reg, loan_count, loan_amount,
            IF(new_reg > 0, ad_cost / new_reg, NULL),
            IF(ad_cost > 0, (loan_amount * 0.15 - ad_cost) / ad_cost, NULL)
        FROM dws_marketing_channel_day;

-- ads_operation_daily insert
INSERT INTO ads_operation_daily
        SELECT
            d.date_value,
            IFNULL((SELECT COUNT(DISTINCT customer_id) FROM dws_customer_active_day WHERE stat_date=d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM dim_customer WHERE reg_date=d.date_value), 0),
            IFNULL((SELECT SUM(ticket_count) FROM dws_csm_ticket_day WHERE stat_date=d.date_value), 0),
            0, NULL
        FROM dim_date d;

