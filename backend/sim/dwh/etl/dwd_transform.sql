-- ============================================================
-- DWD 层 ETL：11 步
-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）
-- 生产环境中，模板变量 ${today} / ${date} / ${month} 应由调度器填充
-- ============================================================

-- dwd_credit_application insert
INSERT INTO dwd_credit_application
        SELECT a.application_id, a.customer_id, a.product_code, p.product_kind,
               a.apply_amount, a.apply_term, a.channel_code, ch.channel_type,
               a.campaign_id, a.status, a.reject_code, a.apply_time, a.decision_time,
               DATE(a.apply_time), c.age, c.gender, id.province, 1
        FROM sim_loan_intake.application a
        LEFT JOIN sim_credit_core.product p ON p.product_code = a.product_code
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code
        LEFT JOIN sim_cust_cif.customer c ON c.customer_id = a.customer_id
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = a.customer_id;

-- dwd_credit_decision insert
INSERT INTO dwd_credit_decision
        SELECT application_id, customer_id, decision, reject_reasons,
               approve_amount, approve_apr, approve_term, decided_at,
               DATE(decided_at), 1
        FROM sim_risk_decision.decision_log;

-- dwd_credit_loan insert
INSERT INTO dwd_credit_loan
        SELECT l.loan_id, l.application_id, l.customer_id, l.product_code, p.product_kind,
               l.principal, l.term_months, l.apr, l.disburse_time, DATE(l.disburse_time),
               l.first_repay_date, l.maturity_date, l.status, l.fund_source_code, l.branch_code,
               a.channel_code, ch.channel_type,
               c.age, c.gender, id.province, 1
        FROM sim_credit_core.loan l
        LEFT JOIN sim_credit_core.product p ON p.product_code = l.product_code
        LEFT JOIN sim_loan_intake.application a ON a.application_id = l.application_id
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code
        LEFT JOIN sim_cust_cif.customer c ON c.customer_id = l.customer_id
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = l.customer_id;

-- dwd_credit_repayment insert
INSERT INTO dwd_credit_repayment
        SELECT r.repay_id, r.loan_id, l.customer_id, r.period_no, r.pay_time, DATE(r.pay_time),
               r.pay_amount, r.principal_paid, r.interest_paid, r.penalty_paid, r.pay_channel,
               IF(r.pay_channel='COLLECTION', 1, 0), 1
        FROM sim_credit_core.repayment_actual r
        JOIN sim_credit_core.loan l ON l.loan_id = r.loan_id;

-- dwd_credit_overdue insert
INSERT INTO dwd_credit_overdue
        SELECT o.overdue_id, o.loan_id, l.customer_id, o.period_no,
               o.overdue_start_date, o.overdue_end_date, o.overdue_days, o.overdue_amount, o.stage,
               l.product_code, p.product_kind, 1
        FROM sim_credit_core.overdue_record o
        JOIN sim_credit_core.loan l ON l.loan_id = o.loan_id
        JOIN sim_credit_core.product p ON p.product_code = l.product_code;

-- dwd_credit_collection insert
INSERT INTO dwd_credit_collection
        SELECT case_id, loan_id, customer_id, open_date, close_date,
               stage_entered, outstanding_amount, status,
               IF(status='CLOSED_PAID', 1, 0), 1
        FROM sim_collection.collection_case;

-- dwd_marketing_attribution insert
INSERT INTO dwd_marketing_attribution
        SELECT a.attr_id, a.customer_id, a.campaign_id, a.channel_code, ch.channel_type,
               a.attribute_time, DATE(a.attribute_time), a.event_type, a.weight, 1
        FROM sim_marketing.attribution a
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code;

-- dwd_marketing_ad_cost insert
INSERT INTO dwd_marketing_ad_cost
        SELECT a.cost_id, a.campaign_id, a.channel_code, ch.channel_type,
               a.cost_date, a.impression, a.click, a.cost, 1
        FROM sim_marketing.ad_cost a
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code;

-- dwd_finance_gl_journal insert
INSERT INTO dwd_finance_gl_journal
        SELECT j.journal_id, j.biz_date, j.account_code, a.account_name, a.account_kind,
               j.direction, j.amount, j.biz_ref_type, j.biz_ref_id, 1
        FROM sim_finance.gl_journal j
        LEFT JOIN sim_finance.gl_account a ON a.account_code = j.account_code;

-- dwd_events_app_event insert
INSERT INTO dwd_events_app_event
        SELECT event_id, customer_id, device_id, event_name, event_time, DATE(event_time),
               platform, channel_code, 1
        FROM sim_events.app_event;

-- dwd_csm_ticket insert
INSERT INTO dwd_csm_ticket
        SELECT ticket_id, customer_id, channel, category, priority, status,
               created_at, closed_at, DATE(created_at),
               IF(category='投诉', 1, 0), 1
        FROM sim_csm.ticket;

