-- ============================================================
-- 数仓 sample_queries.sql
-- 10+ 个典型业务问题的 SQL，验证数仓可用性 & 作为 NL2SQL 靶子
-- ============================================================

-- Q1: 过去 30 天每日放款金额与笔数（业务概览）
SELECT stat_date, loan_count, loan_amount
FROM sim_dw.dws_credit_loan_day
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
ORDER BY stat_date;

-- Q2: 各产品的通过率对比（信贷业务分析）
SELECT product_code, SUM(apply_count) apps, SUM(approve_count) approves,
       ROUND(SUM(approve_count)/SUM(apply_count)*100, 2) approve_rate_pct
FROM sim_dw.dws_credit_product_day
GROUP BY product_code
ORDER BY approve_rate_pct DESC;

-- Q3: 各渠道 6 月获客成本 CPA（营销分析）
SELECT channel_code,
       SUM(ad_cost) total_cost,
       SUM(new_reg) new_regs,
       ROUND(SUM(ad_cost)/NULLIF(SUM(new_reg),0), 2) cpa
FROM sim_dw.dws_marketing_channel_day
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
GROUP BY channel_code
ORDER BY total_cost DESC;

-- Q4: 各风险等级客户数（风险管理）
SELECT grade, SUM(customer_count) customers
FROM sim_dw.dws_risk_grade_day
GROUP BY grade
ORDER BY grade;

-- Q5: 逾期率 by 产品 & Vintage（风险指标核心）
SELECT
    l.product_code,
    DATE_FORMAT(l.disburse_date, '%Y-%m') vintage,
    COUNT(DISTINCT l.loan_id) loans,
    COUNT(DISTINCT CASE WHEN o.stage IN ('M1','M2','M3','M3+') THEN o.loan_id END) overdue_loans,
    ROUND(COUNT(DISTINCT CASE WHEN o.stage IN ('M1','M2','M3','M3+') THEN o.loan_id END)
          / COUNT(DISTINCT l.loan_id) * 100, 2) overdue_rate_pct
FROM sim_dw.dwd_credit_loan l
LEFT JOIN sim_dw.dwd_credit_overdue o ON o.loan_id = l.loan_id
GROUP BY l.product_code, DATE_FORMAT(l.disburse_date, '%Y-%m')
ORDER BY l.product_code, vintage;

-- Q6: 每日财务收入（利息 + 手续费）
SELECT stat_date, interest_income, fee_income, total_income
FROM sim_dw.dws_finance_income_day
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
ORDER BY stat_date;

-- Q7: 合作方分润月度汇总（资金业务）
SELECT partner_code, SUM(loan_count) loans, SUM(funded_amount) funded,
       SUM(partner_income) partner_inc, SUM(self_income) self_inc
FROM sim_dw.dws_funding_partner_month
GROUP BY partner_code
ORDER BY funded DESC;

-- Q8: 各年龄段客户放款分布（客户画像）
SELECT c.age_group,
       COUNT(DISTINCT l.customer_id) customers,
       COUNT(DISTINCT l.loan_id) loans,
       SUM(l.principal) total_amount,
       AVG(l.principal) avg_amount
FROM sim_dw.dwd_credit_loan l
JOIN sim_dw.dim_customer c ON c.customer_id = l.customer_id AND c.is_current=1
GROUP BY c.age_group
ORDER BY total_amount DESC;

-- Q9: 客服工单每日与投诉率（运营）
SELECT stat_date,
       SUM(ticket_count) tickets,
       SUM(complaint_count) complaints,
       ROUND(SUM(complaint_count)/NULLIF(SUM(ticket_count),0)*100, 2) complaint_rate_pct
FROM sim_dw.dws_csm_ticket_day
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
GROUP BY stat_date
ORDER BY stat_date;

-- Q10: 每日渠道 ROI（营销效率）
SELECT stat_date, channel_code, ad_cost, new_customers, loan_amount, cpa, roi
FROM sim_dw.ads_marketing_roi_daily
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
  AND channel_code = 'BYTEDANCE_AD'
ORDER BY stat_date;

-- Q11: DAU 每日活跃（用户）
SELECT stat_date, COUNT(DISTINCT customer_id) dau
FROM sim_dw.dws_customer_active_day
WHERE stat_date BETWEEN '2025-06-01' AND '2025-06-30'
GROUP BY stat_date
ORDER BY stat_date;

-- Q12: 支用率（授信 → 30 天内放款的比例）
SELECT
    DATE_FORMAT(cl.created_at, '%Y-%m') month,
    COUNT(DISTINCT cl.customer_id) approved,
    COUNT(DISTINCT l.customer_id) drawn,
    ROUND(COUNT(DISTINCT l.customer_id)*100.0/COUNT(DISTINCT cl.customer_id), 2) draw_rate_pct
FROM sim_credit_core.credit_limit cl
LEFT JOIN sim_credit_core.loan l
    ON l.customer_id = cl.customer_id
    AND l.disburse_time BETWEEN cl.created_at AND DATE_ADD(cl.created_at, INTERVAL 30 DAY)
GROUP BY month
ORDER BY month;
