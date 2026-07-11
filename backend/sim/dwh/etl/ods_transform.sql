-- ============================================================
-- ODS 层 ETL：16 步
-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）
-- 生产环境中，模板变量 ${today} / ${date} / ${month} 应由调度器填充
-- ============================================================

-- ods_cif_customer insert
TRUNCATE ods_cif_customer;
INSERT INTO ods_cif_customer SELECT customer_id, name, gender, birth_date, age, education, marital,
                   occupation, monthly_income, reg_channel, reg_time, status,
                   '2025-07-01' FROM sim_cust_cif.customer;;

-- ods_intake_application insert
TRUNCATE ods_intake_application;
INSERT INTO ods_intake_application SELECT application_id, customer_id, product_code, apply_amount, apply_term,
                   channel_code, campaign_id, status, reject_code, apply_time, decision_time,
                   '2025-07-01' FROM sim_loan_intake.application;;

-- ods_risk_decision insert
TRUNCATE ods_risk_decision;
INSERT INTO ods_risk_decision SELECT application_id, customer_id, decision, reject_reasons,
                   approve_amount, approve_apr, approve_term, decided_at,
                   '2025-07-01' FROM sim_risk_decision.decision_log;;

-- ods_credit_limit insert
TRUNCATE ods_credit_limit;
INSERT INTO ods_credit_limit SELECT customer_id, product_code, total_amount, apr, grade,
                   valid_from, status, created_at, '2025-07-01' FROM sim_credit_core.credit_limit;;

-- ods_credit_loan insert
TRUNCATE ods_credit_loan;
INSERT INTO ods_credit_loan SELECT loan_id, application_id, customer_id, product_code,
                   principal, term_months, apr, disburse_time, maturity_date,
                   status, fund_source_code, branch_code, '2025-07-01' FROM sim_credit_core.loan;;

-- ods_credit_repayment_plan insert
TRUNCATE ods_credit_repayment_plan;
INSERT INTO ods_credit_repayment_plan SELECT plan_id, loan_id, period_no, due_date, principal, interest,
                   total_amount, status, '2025-07-01' FROM sim_credit_core.repayment_plan;;

-- ods_credit_repayment_actual insert
TRUNCATE ods_credit_repayment_actual;
INSERT INTO ods_credit_repayment_actual SELECT repay_id, loan_id, period_no, pay_time, pay_amount,
                   principal_paid, interest_paid, penalty_paid, pay_channel,
                   '2025-07-01' FROM sim_credit_core.repayment_actual;;

-- ods_credit_overdue insert
TRUNCATE ods_credit_overdue;
INSERT INTO ods_credit_overdue SELECT overdue_id, loan_id, period_no, overdue_start_date, overdue_end_date,
                   overdue_days, overdue_amount, stage, '2025-07-01' FROM sim_credit_core.overdue_record;;

-- ods_collection_case insert
TRUNCATE ods_collection_case;
INSERT INTO ods_collection_case SELECT case_id, loan_id, customer_id, open_date, close_date,
                   stage_entered, outstanding_amount, status, '2025-07-01' FROM sim_collection.collection_case;;

-- ods_funding_split insert
TRUNCATE ods_funding_split;
INSERT INTO ods_funding_split SELECT split_id, loan_id, partner_code, funding_amount, funding_ratio,
                   created_at, '2025-07-01' FROM sim_funding.loan_funding_split;;

-- ods_funding_share insert
TRUNCATE ods_funding_share;
INSERT INTO ods_funding_share SELECT record_id, loan_id, partner_code, period_no, settle_date,
                   partner_income, self_income, '2025-07-01' FROM sim_funding.profit_share_record;;

-- ods_marketing_ad_cost insert
TRUNCATE ods_marketing_ad_cost;
INSERT INTO ods_marketing_ad_cost SELECT cost_id, campaign_id, channel_code, cost_date, impression, click, cost,
                   '2025-07-01' FROM sim_marketing.ad_cost;;

-- ods_marketing_attribution insert
TRUNCATE ods_marketing_attribution;
INSERT INTO ods_marketing_attribution SELECT attr_id, customer_id, campaign_id, channel_code, attribute_time,
                   event_type, weight, '2025-07-01' FROM sim_marketing.attribution;;

-- ods_finance_gl_journal insert
TRUNCATE ods_finance_gl_journal;
INSERT INTO ods_finance_gl_journal SELECT journal_id, biz_date, account_code, direction, amount,
                   biz_ref_type, biz_ref_id, '2025-07-01' FROM sim_finance.gl_journal;;

-- ods_events_app_event insert
TRUNCATE ods_events_app_event;
INSERT INTO ods_events_app_event SELECT event_id, customer_id, device_id, event_name, event_time, platform,
                   channel_code, '2025-07-01' FROM sim_events.app_event;;

-- ods_csm_ticket insert
TRUNCATE ods_csm_ticket;
INSERT INTO ods_csm_ticket SELECT ticket_id, customer_id, channel, category, priority, status,
                   created_at, closed_at, '2025-07-01' FROM sim_csm.ticket;;

