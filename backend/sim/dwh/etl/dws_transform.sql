-- ============================================================
-- DWS 层 ETL：11 步
-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）
-- 生产环境中，模板变量 ${today} / ${date} / ${month} 应由调度器填充
-- ============================================================

-- dws_customer_active_day insert
INSERT INTO dws_customer_active_day
        SELECT event_date, customer_id, COUNT(*), 0, 0
        FROM dwd_events_app_event
        WHERE customer_id IS NOT NULL
        GROUP BY event_date, customer_id;

-- dws_credit_customer_day insert
INSERT INTO dws_credit_customer_day
        SELECT
            COALESCE(a.apply_date, l.disburse_date, r.pay_date) AS stat_date,
            COALESCE(a.customer_id, l.customer_id, r.customer_id) AS customer_id,
            IFNULL(a.apply_count, 0),
            IFNULL(a.approve_count, 0),
            IFNULL(l.loan_count, 0),
            IFNULL(l.loan_amount, 0),
            IFNULL(r.repay_amount, 0),
            0, 0
        FROM (
            SELECT apply_date, customer_id, COUNT(*) apply_count,
                   SUM(status='APPROVED') approve_count
            FROM dwd_credit_application GROUP BY apply_date, customer_id
        ) a
        LEFT JOIN (
            SELECT disburse_date, customer_id, COUNT(*) loan_count, SUM(principal) loan_amount
            FROM dwd_credit_loan GROUP BY disburse_date, customer_id
        ) l ON l.disburse_date = a.apply_date AND l.customer_id = a.customer_id
        LEFT JOIN (
            SELECT pay_date, customer_id, SUM(pay_amount) repay_amount
            FROM dwd_credit_repayment GROUP BY pay_date, customer_id
        ) r ON r.pay_date = a.apply_date AND r.customer_id = a.customer_id;

-- dws_credit_product_day insert
INSERT INTO dws_credit_product_day (stat_date, product_code, apply_count,
                                              approve_count, loan_count, loan_amount,
                                              avg_amount, approve_rate,
                                              m1_overdue_count, m3_overdue_count)
        SELECT
            a.apply_date, a.product_code,
            COUNT(*) apply_count,
            SUM(a.status='APPROVED') approve_count,
            (SELECT COUNT(*) FROM dwd_credit_loan l
             WHERE l.disburse_date=a.apply_date AND l.product_code=a.product_code),
            (SELECT SUM(principal) FROM dwd_credit_loan l
             WHERE l.disburse_date=a.apply_date AND l.product_code=a.product_code),
            (SELECT AVG(principal) FROM dwd_credit_loan l
             WHERE l.disburse_date=a.apply_date AND l.product_code=a.product_code),
            SUM(a.status='APPROVED')/COUNT(*),
            0, 0
        FROM dwd_credit_application a
        GROUP BY a.apply_date, a.product_code;

-- dws_credit_channel_day insert
INSERT INTO dws_credit_channel_day (stat_date, channel_code, apply_count,
                                              approve_count, loan_count, loan_amount, new_customers)
        SELECT
            a.apply_date, a.channel_code,
            COUNT(*), SUM(a.status='APPROVED'),
            (SELECT COUNT(*) FROM dwd_credit_loan l WHERE l.disburse_date=a.apply_date AND l.channel_code=a.channel_code),
            (SELECT COALESCE(SUM(principal),0) FROM dwd_credit_loan l WHERE l.disburse_date=a.apply_date AND l.channel_code=a.channel_code),
            0
        FROM dwd_credit_application a
        WHERE a.channel_code IS NOT NULL
        GROUP BY a.apply_date, a.channel_code;

-- dws_credit_loan_day insert
INSERT INTO dws_credit_loan_day (stat_date, loan_count, loan_amount,
                                          outstanding_balance, overdue_balance,
                                          m1_overdue_count, m2_overdue_count, m3_overdue_count)
        SELECT disburse_date, COUNT(*), SUM(principal), 0, 0, 0, 0, 0
        FROM dwd_credit_loan GROUP BY disburse_date;

-- dws_credit_overdue_day insert
INSERT INTO dws_credit_overdue_day
        SELECT overdue_start_date, stage, COUNT(*), SUM(overdue_amount)
        FROM dwd_credit_overdue GROUP BY overdue_start_date, stage;

-- dws_finance_income_day insert
INSERT INTO dws_finance_income_day
        SELECT biz_date,
               SUM(CASE WHEN account_code='6001' AND direction='CR' THEN amount ELSE 0 END),
               SUM(CASE WHEN account_code='6002' AND direction='CR' THEN amount ELSE 0 END),
               SUM(CASE WHEN account_kind='INCOME' AND direction='CR' THEN amount ELSE 0 END)
        FROM dwd_finance_gl_journal
        GROUP BY biz_date;

-- dws_marketing_channel_day insert
INSERT INTO dws_marketing_channel_day (stat_date, channel_code, ad_cost,
                                                 impression, click, new_reg, apply_count,
                                                 loan_count, loan_amount)
        SELECT
            c.cost_date, c.channel_code,
            SUM(c.cost), SUM(c.impression), SUM(c.click),
            0,
            (SELECT COUNT(*) FROM dwd_credit_application a WHERE a.apply_date=c.cost_date AND a.channel_code=c.channel_code),
            (SELECT COUNT(*) FROM dwd_credit_loan l WHERE l.disburse_date=c.cost_date AND l.channel_code=c.channel_code),
            (SELECT COALESCE(SUM(principal),0) FROM dwd_credit_loan l WHERE l.disburse_date=c.cost_date AND l.channel_code=c.channel_code)
        FROM dwd_marketing_ad_cost c
        GROUP BY c.cost_date, c.channel_code;

-- dws_risk_grade_day insert
INSERT INTO dws_risk_grade_day (stat_date, grade, customer_count, apply_count, approve_count)
        SELECT valid_from, grade, COUNT(DISTINCT customer_id), 0, 0
        FROM sim_risk_decision.risk_grade
        GROUP BY valid_from, grade;

-- dws_funding_partner_month insert
INSERT INTO dws_funding_partner_month
        SELECT DATE_FORMAT(created_at, '%Y%m') AS stat_month, partner_code,
               COUNT(*), SUM(funding_amount),
               (SELECT COALESCE(SUM(partner_income),0)
                FROM sim_funding.profit_share_record ps
                WHERE ps.partner_code = s.partner_code
                  AND DATE_FORMAT(ps.settle_date, '%Y%m') = DATE_FORMAT(s.created_at, '%Y%m')),
               (SELECT COALESCE(SUM(self_income),0)
                FROM sim_funding.profit_share_record ps
                WHERE ps.partner_code = s.partner_code
                  AND DATE_FORMAT(ps.settle_date, '%Y%m') = DATE_FORMAT(s.created_at, '%Y%m'))
        FROM sim_funding.loan_funding_split s
        GROUP BY DATE_FORMAT(created_at, '%Y%m'), partner_code;

-- dws_csm_ticket_day insert
INSERT INTO dws_csm_ticket_day
        SELECT created_date, category, COUNT(*), SUM(is_complaint), SUM(status='CLOSED')
        FROM dwd_csm_ticket GROUP BY created_date, category;

