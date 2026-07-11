"""
一键 ETL：sim_* 业务库 → sim_dw
执行顺序：DIM → ODS → DWD → DWS → ADS
"""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "systems"))
from common import mysql_conn, CONFIG, DATE_START, DATE_END

TODAY_STR = CONFIG["timeline"]["today"]  # '2025-07-01'


def exec_sql(cur, sql: str, label: str = ""):
    t = time.time()
    cur.execute(sql)
    n = cur.rowcount
    print(f"  {label:<50} {n:>10} rows   {time.time()-t:.2f}s")


def main():
    conn = mysql_conn("sim_dw")
    cur = conn.cursor()
    # 关闭本会话的 only_full_group_by，允许简化的聚合语法
    cur.execute("SET SESSION sql_mode = REPLACE(REPLACE(@@sql_mode, 'ONLY_FULL_GROUP_BY', ''), ',,', ',')")

    # ------------------------------------------------------------
    # DIM 层
    # ------------------------------------------------------------
    print("\n===== DIM 层 =====")

    # dim_date
    exec_sql(cur, "TRUNCATE dim_date", "dim_date truncate")
    exec_sql(cur, f"""
        INSERT INTO dim_date
        SELECT
            DATE_FORMAT(d, '%Y%m%d') + 0 AS date_key,
            d AS date_value,
            YEAR(d), QUARTER(d), MONTH(d), MONTHNAME(d),
            WEEK(d), DAY(d), DAYOFWEEK(d),
            IF(DAYOFWEEK(d) IN (1,7), 1, 0),
            0
        FROM (
            SELECT DATE('{DATE_START}') + INTERVAL n DAY AS d
            FROM (SELECT a.i + b.i*10 + c.i*100 + d.i*1000 AS n
                  FROM (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
                       (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
                       (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) c,
                       (SELECT 0 i UNION SELECT 1) d) t
            WHERE DATE('{DATE_START}') + INTERVAL n DAY <= '{DATE_END}'
        ) dates
    """, "dim_date insert")

    # dim_customer (SCD Type 2: 首次装载都是 is_current=1)
    exec_sql(cur, "TRUNCATE dim_customer", "dim_customer truncate")
    exec_sql(cur, f"""
        INSERT INTO dim_customer
          (customer_id, name, gender_code, gender_name, age, age_group,
           education, marital, occupation, monthly_income, income_grade,
           province, reg_channel, reg_date, status, valid_from, valid_to, is_current)
        SELECT c.customer_id, c.name, c.gender,
               CASE c.gender WHEN 1 THEN '男' WHEN 2 THEN '女' END,
               c.age,
               CASE
                 WHEN c.age < 26 THEN '18-25'
                 WHEN c.age < 36 THEN '26-35'
                 WHEN c.age < 46 THEN '36-45'
                 WHEN c.age < 56 THEN '46-55'
                 ELSE '55+' END,
               c.education, c.marital, c.occupation, c.monthly_income,
               CASE
                 WHEN c.monthly_income < 5000 THEN '低收入(<5k)'
                 WHEN c.monthly_income < 10000 THEN '中低(5-10k)'
                 WHEN c.monthly_income < 20000 THEN '中(10-20k)'
                 WHEN c.monthly_income < 50000 THEN '中高(20-50k)'
                 ELSE '高(50k+)' END,
               id.province, c.reg_channel, DATE(c.reg_time), c.status,
               c.reg_time, '9999-12-31 23:59:59', 1
        FROM sim_cust_cif.customer c
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = c.customer_id
    """, "dim_customer insert")

    exec_sql(cur, "TRUNCATE dim_product", "dim_product truncate")
    exec_sql(cur, """
        INSERT INTO dim_product (product_code, product_name, product_kind,
                                  min_amount, max_amount, apr_default, is_active)
        SELECT product_code, product_name, product_kind,
               min_amount, max_amount, apr_default, is_active
        FROM sim_credit_core.product
    """, "dim_product insert")

    exec_sql(cur, "TRUNCATE dim_channel", "dim_channel truncate")
    exec_sql(cur, """
        INSERT INTO dim_channel (channel_code, channel_name, channel_type, channel_owner)
        SELECT channel_code, channel_name, channel_type, channel_owner
        FROM sim_marketing.channel
    """, "dim_channel insert")

    exec_sql(cur, "TRUNCATE dim_org", "dim_org truncate")
    exec_sql(cur, """
        INSERT INTO dim_org (org_code, org_name, parent_code, org_level, org_type)
        SELECT org_code, org_name, parent_code, org_level, org_type
        FROM sim_hr_iam.org_unit
    """, "dim_org insert")

    exec_sql(cur, "TRUNCATE dim_funding_partner", "dim_funding_partner truncate")
    exec_sql(cur, """
        INSERT INTO dim_funding_partner (partner_code, partner_name, partner_type)
        SELECT partner_code, partner_name, partner_type FROM sim_funding.funding_partner
    """, "dim_funding_partner insert")

    # ------------------------------------------------------------
    # ODS 层：贴源，以当前批次日期为 ods_stat_date
    # ------------------------------------------------------------
    print("\n===== ODS 层 =====")

    ods_tables = [
        ("ods_cif_customer", "sim_cust_cif.customer", """
            SELECT customer_id, name, gender, birth_date, age, education, marital,
                   occupation, monthly_income, reg_channel, reg_time, status,
                   '{today}'
        """),
        ("ods_intake_application", "sim_loan_intake.application", """
            SELECT application_id, customer_id, product_code, apply_amount, apply_term,
                   channel_code, campaign_id, status, reject_code, apply_time, decision_time,
                   '{today}'
        """),
        ("ods_risk_decision", "sim_risk_decision.decision_log", """
            SELECT application_id, customer_id, decision, reject_reasons,
                   approve_amount, approve_apr, approve_term, decided_at,
                   '{today}'
        """),
        ("ods_credit_limit", "sim_credit_core.credit_limit", """
            SELECT customer_id, product_code, total_amount, apr, grade,
                   valid_from, status, created_at, '{today}'
        """),
        ("ods_credit_loan", "sim_credit_core.loan", """
            SELECT loan_id, application_id, customer_id, product_code,
                   principal, term_months, apr, disburse_time, maturity_date,
                   status, fund_source_code, branch_code, '{today}'
        """),
        ("ods_credit_repayment_plan", "sim_credit_core.repayment_plan", """
            SELECT plan_id, loan_id, period_no, due_date, principal, interest,
                   total_amount, status, '{today}'
        """),
        ("ods_credit_repayment_actual", "sim_credit_core.repayment_actual", """
            SELECT repay_id, loan_id, period_no, pay_time, pay_amount,
                   principal_paid, interest_paid, penalty_paid, pay_channel,
                   '{today}'
        """),
        ("ods_credit_overdue", "sim_credit_core.overdue_record", """
            SELECT overdue_id, loan_id, period_no, overdue_start_date, overdue_end_date,
                   overdue_days, overdue_amount, stage, '{today}'
        """),
        ("ods_collection_case", "sim_collection.collection_case", """
            SELECT case_id, loan_id, customer_id, open_date, close_date,
                   stage_entered, outstanding_amount, status, '{today}'
        """),
        ("ods_funding_split", "sim_funding.loan_funding_split", """
            SELECT split_id, loan_id, partner_code, funding_amount, funding_ratio,
                   created_at, '{today}'
        """),
        ("ods_funding_share", "sim_funding.profit_share_record", """
            SELECT record_id, loan_id, partner_code, period_no, settle_date,
                   partner_income, self_income, '{today}'
        """),
        ("ods_marketing_ad_cost", "sim_marketing.ad_cost", """
            SELECT cost_id, campaign_id, channel_code, cost_date, impression, click, cost,
                   '{today}'
        """),
        ("ods_marketing_attribution", "sim_marketing.attribution", """
            SELECT attr_id, customer_id, campaign_id, channel_code, attribute_time,
                   event_type, weight, '{today}'
        """),
        ("ods_finance_gl_journal", "sim_finance.gl_journal", """
            SELECT journal_id, biz_date, account_code, direction, amount,
                   biz_ref_type, biz_ref_id, '{today}'
        """),
        ("ods_events_app_event", "sim_events.app_event", """
            SELECT event_id, customer_id, device_id, event_name, event_time, platform,
                   channel_code, '{today}'
        """),
        ("ods_csm_ticket", "sim_csm.ticket", """
            SELECT ticket_id, customer_id, channel, category, priority, status,
                   created_at, closed_at, '{today}'
        """),
    ]
    for tbl, src, sel in ods_tables:
        exec_sql(cur, f"TRUNCATE {tbl}", f"{tbl} truncate")
        exec_sql(cur, f"INSERT INTO {tbl} {sel.format(today=TODAY_STR)} FROM {src}",
                 f"{tbl} insert")

    # ------------------------------------------------------------
    # DWD 层
    # ------------------------------------------------------------
    print("\n===== DWD 层 =====")

    exec_sql(cur, "TRUNCATE dwd_credit_application", "dwd_credit_application truncate")
    exec_sql(cur, """
        INSERT INTO dwd_credit_application
        SELECT a.application_id, a.customer_id, a.product_code, p.product_kind,
               a.apply_amount, a.apply_term, a.channel_code, ch.channel_type,
               a.campaign_id, a.status, a.reject_code, a.apply_time, a.decision_time,
               DATE(a.apply_time), c.age, c.gender, id.province, 1
        FROM sim_loan_intake.application a
        LEFT JOIN sim_credit_core.product p ON p.product_code = a.product_code
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code
        LEFT JOIN sim_cust_cif.customer c ON c.customer_id = a.customer_id
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = a.customer_id
    """, "dwd_credit_application insert")

    exec_sql(cur, "TRUNCATE dwd_credit_decision", "dwd_credit_decision truncate")
    exec_sql(cur, """
        INSERT INTO dwd_credit_decision
        SELECT application_id, customer_id, decision, reject_reasons,
               approve_amount, approve_apr, approve_term, decided_at,
               DATE(decided_at), 1
        FROM sim_risk_decision.decision_log
    """, "dwd_credit_decision insert")

    exec_sql(cur, "TRUNCATE dwd_credit_loan", "dwd_credit_loan truncate")
    exec_sql(cur, """
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
        LEFT JOIN sim_cust_cif.identity id ON id.customer_id = l.customer_id
    """, "dwd_credit_loan insert")

    exec_sql(cur, "TRUNCATE dwd_credit_repayment", "dwd_credit_repayment truncate")
    exec_sql(cur, """
        INSERT INTO dwd_credit_repayment
        SELECT r.repay_id, r.loan_id, l.customer_id, r.period_no, r.pay_time, DATE(r.pay_time),
               r.pay_amount, r.principal_paid, r.interest_paid, r.penalty_paid, r.pay_channel,
               IF(r.pay_channel='COLLECTION', 1, 0), 1
        FROM sim_credit_core.repayment_actual r
        JOIN sim_credit_core.loan l ON l.loan_id = r.loan_id
    """, "dwd_credit_repayment insert")

    exec_sql(cur, "TRUNCATE dwd_credit_overdue", "dwd_credit_overdue truncate")
    exec_sql(cur, """
        INSERT INTO dwd_credit_overdue
        SELECT o.overdue_id, o.loan_id, l.customer_id, o.period_no,
               o.overdue_start_date, o.overdue_end_date, o.overdue_days, o.overdue_amount, o.stage,
               l.product_code, p.product_kind, 1
        FROM sim_credit_core.overdue_record o
        JOIN sim_credit_core.loan l ON l.loan_id = o.loan_id
        JOIN sim_credit_core.product p ON p.product_code = l.product_code
    """, "dwd_credit_overdue insert")

    exec_sql(cur, "TRUNCATE dwd_credit_collection", "dwd_credit_collection truncate")
    exec_sql(cur, """
        INSERT INTO dwd_credit_collection
        SELECT case_id, loan_id, customer_id, open_date, close_date,
               stage_entered, outstanding_amount, status,
               IF(status='CLOSED_PAID', 1, 0), 1
        FROM sim_collection.collection_case
    """, "dwd_credit_collection insert")

    exec_sql(cur, "TRUNCATE dwd_marketing_attribution", "dwd_marketing_attribution truncate")
    exec_sql(cur, """
        INSERT INTO dwd_marketing_attribution
        SELECT a.attr_id, a.customer_id, a.campaign_id, a.channel_code, ch.channel_type,
               a.attribute_time, DATE(a.attribute_time), a.event_type, a.weight, 1
        FROM sim_marketing.attribution a
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code
    """, "dwd_marketing_attribution insert")

    exec_sql(cur, "TRUNCATE dwd_marketing_ad_cost", "dwd_marketing_ad_cost truncate")
    exec_sql(cur, """
        INSERT INTO dwd_marketing_ad_cost
        SELECT a.cost_id, a.campaign_id, a.channel_code, ch.channel_type,
               a.cost_date, a.impression, a.click, a.cost, 1
        FROM sim_marketing.ad_cost a
        LEFT JOIN sim_marketing.channel ch ON ch.channel_code = a.channel_code
    """, "dwd_marketing_ad_cost insert")

    exec_sql(cur, "TRUNCATE dwd_finance_gl_journal", "dwd_finance_gl_journal truncate")
    exec_sql(cur, """
        INSERT INTO dwd_finance_gl_journal
        SELECT j.journal_id, j.biz_date, j.account_code, a.account_name, a.account_kind,
               j.direction, j.amount, j.biz_ref_type, j.biz_ref_id, 1
        FROM sim_finance.gl_journal j
        LEFT JOIN sim_finance.gl_account a ON a.account_code = j.account_code
    """, "dwd_finance_gl_journal insert")

    exec_sql(cur, "TRUNCATE dwd_events_app_event", "dwd_events_app_event truncate")
    exec_sql(cur, """
        INSERT INTO dwd_events_app_event
        SELECT event_id, customer_id, device_id, event_name, event_time, DATE(event_time),
               platform, channel_code, 1
        FROM sim_events.app_event
    """, "dwd_events_app_event insert")

    exec_sql(cur, "TRUNCATE dwd_csm_ticket", "dwd_csm_ticket truncate")
    exec_sql(cur, """
        INSERT INTO dwd_csm_ticket
        SELECT ticket_id, customer_id, channel, category, priority, status,
               created_at, closed_at, DATE(created_at),
               IF(category='投诉', 1, 0), 1
        FROM sim_csm.ticket
    """, "dwd_csm_ticket insert")

    # ------------------------------------------------------------
    # DWS 层
    # ------------------------------------------------------------
    print("\n===== DWS 层 =====")

    exec_sql(cur, "TRUNCATE dws_customer_active_day", "dws_customer_active_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_customer_active_day
        SELECT event_date, customer_id, COUNT(*), 0, 0
        FROM dwd_events_app_event
        WHERE customer_id IS NOT NULL
        GROUP BY event_date, customer_id
    """, "dws_customer_active_day insert")

    exec_sql(cur, "TRUNCATE dws_credit_customer_day", "dws_credit_customer_day truncate")
    exec_sql(cur, """
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
        ) r ON r.pay_date = a.apply_date AND r.customer_id = a.customer_id
    """, "dws_credit_customer_day insert")

    exec_sql(cur, "TRUNCATE dws_credit_product_day", "dws_credit_product_day truncate")
    exec_sql(cur, """
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
        GROUP BY a.apply_date, a.product_code
    """, "dws_credit_product_day insert")

    exec_sql(cur, "TRUNCATE dws_credit_channel_day", "dws_credit_channel_day truncate")
    exec_sql(cur, """
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
        GROUP BY a.apply_date, a.channel_code
    """, "dws_credit_channel_day insert")

    exec_sql(cur, "TRUNCATE dws_credit_loan_day", "dws_credit_loan_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_credit_loan_day (stat_date, loan_count, loan_amount,
                                          outstanding_balance, overdue_balance,
                                          m1_overdue_count, m2_overdue_count, m3_overdue_count)
        SELECT disburse_date, COUNT(*), SUM(principal), 0, 0, 0, 0, 0
        FROM dwd_credit_loan GROUP BY disburse_date
    """, "dws_credit_loan_day insert")

    exec_sql(cur, "TRUNCATE dws_credit_overdue_day", "dws_credit_overdue_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_credit_overdue_day
        SELECT overdue_start_date, stage, COUNT(*), SUM(overdue_amount)
        FROM dwd_credit_overdue GROUP BY overdue_start_date, stage
    """, "dws_credit_overdue_day insert")

    exec_sql(cur, "TRUNCATE dws_finance_income_day", "dws_finance_income_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_finance_income_day
        SELECT biz_date,
               SUM(CASE WHEN account_code='6001' AND direction='CR' THEN amount ELSE 0 END),
               SUM(CASE WHEN account_code='6002' AND direction='CR' THEN amount ELSE 0 END),
               SUM(CASE WHEN account_kind='INCOME' AND direction='CR' THEN amount ELSE 0 END)
        FROM dwd_finance_gl_journal
        GROUP BY biz_date
    """, "dws_finance_income_day insert")

    exec_sql(cur, "TRUNCATE dws_marketing_channel_day", "dws_marketing_channel_day truncate")
    exec_sql(cur, """
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
        GROUP BY c.cost_date, c.channel_code
    """, "dws_marketing_channel_day insert")

    exec_sql(cur, "TRUNCATE dws_risk_grade_day", "dws_risk_grade_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_risk_grade_day (stat_date, grade, customer_count, apply_count, approve_count)
        SELECT valid_from, grade, COUNT(DISTINCT customer_id), 0, 0
        FROM sim_risk_decision.risk_grade
        GROUP BY valid_from, grade
    """, "dws_risk_grade_day insert")

    exec_sql(cur, "TRUNCATE dws_funding_partner_month", "dws_funding_partner_month truncate")
    exec_sql(cur, """
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
        GROUP BY DATE_FORMAT(created_at, '%Y%m'), partner_code
    """, "dws_funding_partner_month insert")

    exec_sql(cur, "TRUNCATE dws_csm_ticket_day", "dws_csm_ticket_day truncate")
    exec_sql(cur, """
        INSERT INTO dws_csm_ticket_day
        SELECT created_date, category, COUNT(*), SUM(is_complaint), SUM(status='CLOSED')
        FROM dwd_csm_ticket GROUP BY created_date, category
    """, "dws_csm_ticket_day insert")

    # ------------------------------------------------------------
    # ADS 层
    # ------------------------------------------------------------
    print("\n===== ADS 层 =====")

    exec_sql(cur, "TRUNCATE ads_credit_daily_dashboard", "ads_credit_daily_dashboard truncate")
    exec_sql(cur, """
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
        GROUP BY a.apply_date, l.loan_count, l.loan_amount, l.avg_amount
    """, "ads_credit_daily_dashboard insert")

    exec_sql(cur, "TRUNCATE ads_risk_daily_dashboard", "ads_risk_daily_dashboard truncate")
    exec_sql(cur, """
        INSERT INTO ads_risk_daily_dashboard
        SELECT
            d.date_value,
            IFNULL((SELECT COUNT(*) FROM dwd_credit_loan WHERE disburse_date <= d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM dwd_credit_overdue WHERE stage IN ('M1','M2','M3','M3+') AND overdue_start_date <= d.date_value AND (overdue_end_date IS NULL OR overdue_end_date > d.date_value)), 0),
            IFNULL((SELECT COUNT(*) FROM dwd_credit_overdue WHERE stage IN ('M3','M3+') AND overdue_start_date <= d.date_value AND (overdue_end_date IS NULL OR overdue_end_date > d.date_value)), 0),
            0, 0,
            IFNULL((SELECT AVG(a.status='REJECTED') FROM dwd_credit_application a WHERE a.apply_date=d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM sim_risk_decision.antifraud_event WHERE DATE(detected_at)=d.date_value), 0)
        FROM dim_date d
    """, "ads_risk_daily_dashboard insert")

    exec_sql(cur, "TRUNCATE ads_finance_daily_dashboard", "ads_finance_daily_dashboard truncate")
    exec_sql(cur, """
        INSERT INTO ads_finance_daily_dashboard
        SELECT stat_date, interest_income, fee_income, total_income, 0, total_income
        FROM dws_finance_income_day
    """, "ads_finance_daily_dashboard insert")

    exec_sql(cur, "TRUNCATE ads_marketing_roi_daily", "ads_marketing_roi_daily truncate")
    exec_sql(cur, """
        INSERT INTO ads_marketing_roi_daily
        SELECT
            stat_date, channel_code, ad_cost, new_reg, loan_count, loan_amount,
            IF(new_reg > 0, ad_cost / new_reg, NULL),
            IF(ad_cost > 0, (loan_amount * 0.15 - ad_cost) / ad_cost, NULL)
        FROM dws_marketing_channel_day
    """, "ads_marketing_roi_daily insert")

    exec_sql(cur, "TRUNCATE ads_operation_daily", "ads_operation_daily truncate")
    exec_sql(cur, """
        INSERT INTO ads_operation_daily
        SELECT
            d.date_value,
            IFNULL((SELECT COUNT(DISTINCT customer_id) FROM dws_customer_active_day WHERE stat_date=d.date_value), 0),
            IFNULL((SELECT COUNT(*) FROM dim_customer WHERE reg_date=d.date_value), 0),
            IFNULL((SELECT SUM(ticket_count) FROM dws_csm_ticket_day WHERE stat_date=d.date_value), 0),
            0, NULL
        FROM dim_date d
    """, "ads_operation_daily insert")

    # 完成
    conn.commit()
    conn.close()
    print("\n✅ ETL 完成")


if __name__ == "__main__":
    main()
