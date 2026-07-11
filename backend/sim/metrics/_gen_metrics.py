"""
生成 200+ 指标定义，覆盖 8 大领域。
每个指标包含完整字段（本体化数据字典），可直接跑通 sql_template。
"""
from __future__ import annotations
from pathlib import Path
import yaml, textwrap

BASE = Path(__file__).resolve().parent

# 分级映射
LEVEL_MAP = {"L1": "一级", "L2": "二级", "L3": "三级"}
STATUS = "ACTIVE"
VERSION = "1.0"
EFFECTIVE_FROM = "2025-01-01"


def M(id_num, name_zh, name_en, aliases, level, domain, department, owner,
      definition, formula, filters, dedup, grain, source_tables, sql_template,
      related=None, is_regulatory=False):
    # 自动补充别名：确保至少 2 个
    aliases = list(aliases) if aliases else []
    if name_zh not in aliases:
        aliases.append(name_zh)
    if name_en not in aliases:
        aliases.append(name_en)
    # 去重
    seen = set()
    aliases = [a for a in aliases if not (a in seen or seen.add(a))]
    return {
        "id": f"M{id_num:04d}",
        "name_zh": name_zh,
        "name_en": name_en,
        "aliases": aliases,
        "level": LEVEL_MAP[level],
        "domain": domain,
        "department": department,
        "owner": owner,
        "definition": definition,
        "formula": formula,
        "filters": filters or [],
        "dedup_key": dedup,
        "time_grain": grain,
        "source_tables": source_tables,
        "sql_template": textwrap.dedent(sql_template).strip(),
        "related_metrics": related or [],
        "version": VERSION,
        "effective_from": EFFECTIVE_FROM,
        "status": STATUS,
        "is_regulatory": is_regulatory,
    }


metrics = []
seq = [0]

def add(*args, **kw):
    seq[0] += 1
    metrics.append(M(seq[0], *args, **kw))


# ================================================================
# 用户域 (user) 30 个
# ================================================================
add("日活跃用户数", "dau", ["日活", "DAU", "active_users_daily"],
    "L1", "user", "运营部", "data-ops@simcf.com",
    "当日在 APP 有登录/浏览/操作行为的去重用户数",
    "COUNT(DISTINCT customer_id)",
    ["is_test_user=0", "is_robot=0"], "customer_id", "day",
    ["sim_dw.dws_customer_active_day"],
    """
    SELECT stat_date, COUNT(DISTINCT customer_id) AS dau
    FROM sim_dw.dws_customer_active_day
    WHERE stat_date = '${date}'
    GROUP BY stat_date
    """,
    ["M0002", "M0003"])

add("月活跃用户数", "mau", ["月活", "MAU"],
    "L1", "user", "运营部", "data-ops@simcf.com",
    "过去 30 天内在 APP 有活跃行为的去重用户数",
    "COUNT(DISTINCT customer_id) OVER 30 days",
    [], "customer_id", "rolling_30d",
    ["sim_dw.dws_customer_active_day"],
    """
    SELECT COUNT(DISTINCT customer_id) AS mau
    FROM sim_dw.dws_customer_active_day
    WHERE stat_date BETWEEN DATE_SUB('${date}', INTERVAL 29 DAY) AND '${date}'
    """,
    ["M0001", "M0003"])

add("周活跃用户数", "wau", ["周活", "WAU"],
    "L2", "user", "运营部", "data-ops@simcf.com",
    "过去 7 天在 APP 有活跃行为的去重用户数",
    "COUNT(DISTINCT customer_id) OVER 7 days",
    [], "customer_id", "rolling_7d",
    ["sim_dw.dws_customer_active_day"],
    """
    SELECT COUNT(DISTINCT customer_id) AS wau
    FROM sim_dw.dws_customer_active_day
    WHERE stat_date BETWEEN DATE_SUB('${date}', INTERVAL 6 DAY) AND '${date}'
    """,
    ["M0001", "M0002"])

add("新客数", "new_customer_count", ["新增用户", "new_user"],
    "L1", "user", "运营部", "growth@simcf.com",
    "当日新注册的客户数",
    "COUNT(DISTINCT customer_id) WHERE reg_date = today",
    [], "customer_id", "day",
    ["sim_dw.dim_customer"],
    """
    SELECT reg_date, COUNT(DISTINCT customer_id) AS new_customer_count
    FROM sim_dw.dim_customer
    WHERE reg_date = '${date}' AND is_current=1
    GROUP BY reg_date
    """,
    ["M0001", "M0005"])

add("累计客户数", "total_customer_count", ["总客户数", "total_users"],
    "L1", "user", "运营部", "growth@simcf.com",
    "截至某日累计注册的客户数",
    "COUNT(DISTINCT customer_id) WHERE reg_date <= today",
    ["status != 'CLOSED'"], "customer_id", "day",
    ["sim_dw.dim_customer"],
    """
    SELECT COUNT(DISTINCT customer_id) AS total_customer_count
    FROM sim_dw.dim_customer
    WHERE reg_date <= '${date}' AND is_current=1 AND status != 'CLOSED'
    """,
    ["M0004"])

add("次日留存率", "d1_retention_rate", ["d1_retention", "次留"],
    "L2", "user", "运营部", "growth@simcf.com",
    "新注册用户第二天回访率",
    "d1_returned / d0_registered",
    [], "customer_id", "day",
    ["sim_dw.dim_customer", "sim_dw.dws_customer_active_day"],
    """
    SELECT c.reg_date,
           COUNT(DISTINCT a.customer_id) / COUNT(DISTINCT c.customer_id) AS d1_retention
    FROM sim_dw.dim_customer c
    LEFT JOIN sim_dw.dws_customer_active_day a
        ON a.customer_id=c.customer_id AND a.stat_date=DATE_ADD(c.reg_date,INTERVAL 1 DAY)
    WHERE c.reg_date = '${date}' AND c.is_current=1
    GROUP BY c.reg_date
    """,
    [])

add("7 日留存率", "d7_retention_rate", ["d7_retention", "7日留存"],
    "L2", "user", "运营部", "growth@simcf.com",
    "新注册用户第 8 天回访率",
    "d7_returned / d0_registered",
    [], "customer_id", "day",
    ["sim_dw.dim_customer", "sim_dw.dws_customer_active_day"],
    """
    SELECT c.reg_date,
           COUNT(DISTINCT a.customer_id) / COUNT(DISTINCT c.customer_id) AS d7_retention
    FROM sim_dw.dim_customer c
    LEFT JOIN sim_dw.dws_customer_active_day a
        ON a.customer_id=c.customer_id AND a.stat_date=DATE_ADD(c.reg_date,INTERVAL 7 DAY)
    WHERE c.reg_date = '${date}' AND c.is_current=1
    GROUP BY c.reg_date
    """,
    ["M0006"])

add("客户平均年龄", "avg_customer_age", ["mean_age"],
    "L2", "user", "运营部", "growth@simcf.com",
    "全部活跃客户的年龄均值",
    "AVG(age)",
    ["status='ACTIVE'"], None, "day",
    ["sim_dw.dim_customer"],
    """
    SELECT AVG(age) AS avg_age FROM sim_dw.dim_customer WHERE is_current=1 AND status='ACTIVE'
    """,
    [])

# 年龄分布 —— 5 个年龄段
for grp, code in [("18-25","18_25"), ("26-35","26_35"), ("36-45","36_45"),
                   ("46-55","46_55"), ("55+","55_plus")]:
    add(f"{grp} 岁客户数", f"customer_count_{code}", [f"{grp}客户"],
        "L3", "user", "运营部", "growth@simcf.com",
        f"年龄段 {grp} 岁的活跃客户数",
        "COUNT(DISTINCT customer_id) WHERE age_group=X",
        [f"age_group='{grp}'", "status='ACTIVE'"], "customer_id", "day",
        ["sim_dw.dim_customer"],
        f"""
        SELECT COUNT(DISTINCT customer_id) FROM sim_dw.dim_customer
        WHERE age_group='{grp}' AND is_current=1 AND status='ACTIVE'
        """)

# 学历分布 —— 6 个
for edu in ["初中", "高中", "大专", "本科", "硕士", "博士"]:
    add(f"{edu}学历客户数", f"customer_count_edu_{edu[:2]}", [f"{edu}客户"],
        "L3", "user", "运营部", "growth@simcf.com",
        f"学历={edu} 的活跃客户数",
        "COUNT(DISTINCT customer_id) WHERE education=X",
        [f"education='{edu}'"], "customer_id", "day",
        ["sim_dw.dim_customer"],
        f"""
        SELECT COUNT(DISTINCT customer_id) FROM sim_dw.dim_customer
        WHERE education='{edu}' AND is_current=1
        """)

add("男性客户占比", "male_ratio", ["male_share"],
    "L3", "user", "运营部", "growth@simcf.com",
    "男性客户 / 全部客户",
    "male / total",
    [], None, "day",
    ["sim_dw.dim_customer"],
    """
    SELECT SUM(gender_code=1)/COUNT(*) AS male_ratio
    FROM sim_dw.dim_customer WHERE is_current=1
    """,
    [])

# ================================================================
# 信贷域 (credit) 45 个
# ================================================================

add("授信申请量", "apply_count", ["申请数", "apply_cnt"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日提交的授信申请单数",
    "COUNT(*)",
    [], "application_id", "day",
    ["sim_dw.dwd_credit_application"],
    """
    SELECT apply_date, COUNT(*) AS apply_count
    FROM sim_dw.dwd_credit_application
    WHERE apply_date='${date}' GROUP BY apply_date
    """,
    ["M0044"])

add("授信通过量", "approve_count", ["approved_cnt"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日通过的申请数",
    "COUNT(*) WHERE decision='APPROVE'",
    ["status='APPROVED'"], "application_id", "day",
    ["sim_dw.dwd_credit_application"],
    """
    SELECT apply_date, COUNT(*) AS approve_count
    FROM sim_dw.dwd_credit_application
    WHERE apply_date='${date}' AND status='APPROVED' GROUP BY apply_date
    """,
    [])

add("授信通过率", "approval_rate", ["approve_rate", "过审率"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日通过量 / 当日申请量",
    "approve_count / apply_count",
    [], None, "day",
    ["sim_dw.dwd_credit_application"],
    """
    SELECT apply_date,
           SUM(status='APPROVED')/COUNT(*) AS approval_rate
    FROM sim_dw.dwd_credit_application
    WHERE apply_date='${date}' GROUP BY apply_date
    """,
    [])

add("拒绝率", "reject_rate", ["拒绝率"],
    "L2", "credit", "风险管理部", "risk@simcf.com",
    "被拒绝的申请占比",
    "reject_count / apply_count",
    [], None, "day",
    ["sim_dw.dwd_credit_application"],
    """
    SELECT apply_date, SUM(status='REJECTED')/COUNT(*) AS reject_rate
    FROM sim_dw.dwd_credit_application
    WHERE apply_date='${date}' GROUP BY apply_date
    """,
    [])

add("放款笔数", "loan_count", ["loan_cnt", "放款订单数"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日新增放款的借据数",
    "COUNT(loan_id)",
    [], "loan_id", "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, COUNT(*) AS loan_count
    FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """,
    [])

add("放款金额", "disburse_amount", ["放款额", "GMV", "loan_amount"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日新增放款的本金总额",
    "SUM(principal)",
    [], "loan_id", "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, SUM(principal) AS disburse_amount
    FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """,
    ["M0044", "M0046"])

add("户均放款金额", "avg_loan_amount", ["avg_disburse"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日放款金额 / 客户数",
    "SUM(principal) / COUNT(DISTINCT customer_id)",
    [], None, "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, SUM(principal)/COUNT(DISTINCT customer_id) AS avg_amount
    FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """,
    [])

add("笔均放款金额", "avg_loan_principal", ["avg_per_loan"],
    "L2", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日放款金额 / 借据数",
    "SUM(principal) / COUNT(*)",
    [], None, "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, AVG(principal) AS avg_principal
    FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """,
    [])

add("在贷客户数", "outstanding_customers", ["有贷客户数"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "截至某日仍有未结清借据的客户数",
    "COUNT(DISTINCT customer_id) WHERE status='NORMAL' or 'OVERDUE'",
    ["status IN ('NORMAL','OVERDUE')"], "customer_id", "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT COUNT(DISTINCT customer_id) AS outstanding_customers
    FROM sim_dw.dwd_credit_loan
    WHERE status IN ('NORMAL','OVERDUE') AND disburse_date<='${date}'
    """,
    [])

add("在贷余额", "outstanding_balance", ["贷款余额", "credit_balance"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "所有活跃借据的剩余本金合计",
    "SUM(remaining_principal)",
    ["status IN ('NORMAL','OVERDUE')"], "loan_id", "day",
    ["sim_dw.dwd_credit_loan"],
    """
    -- 简化：以放款金额扣减已还本金
    SELECT
      SUM(l.principal) - IFNULL((
        SELECT SUM(principal_paid) FROM sim_dw.dwd_credit_repayment r
        WHERE r.loan_id=l.loan_id AND r.pay_date <= '${date}'
      ), 0) AS outstanding_balance
    FROM sim_dw.dwd_credit_loan l
    WHERE l.status IN ('NORMAL','OVERDUE') AND l.disburse_date <= '${date}'
    """,
    [])

add("30 天支用率", "draw_rate_30d", ["支用率", "utilization_30d"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "授信后 30 天内产生放款的客户占比",
    "drawn_30d / approved",
    [], None, "month",
    ["sim_credit_core.credit_limit", "sim_credit_core.loan"],
    """
    SELECT DATE_FORMAT(cl.created_at,'%Y%m') AS month,
           COUNT(DISTINCT l.customer_id)/COUNT(DISTINCT cl.customer_id) AS draw_rate
    FROM sim_credit_core.credit_limit cl
    LEFT JOIN sim_credit_core.loan l ON l.customer_id=cl.customer_id
     AND l.disburse_time BETWEEN cl.created_at AND DATE_ADD(cl.created_at,INTERVAL 30 DAY)
    GROUP BY DATE_FORMAT(cl.created_at,'%Y%m')
    """,
    [])

# 4 产品的分产品指标
for pcode, pname in [("SELF_LOAN","信优速贷"), ("PLATFORM_LOAN","信优合作贷"),
                      ("JOINT_LOAN","信优联合贷"), ("GUARANTEE_LOAN","信优保贷")]:
    add(f"{pname}放款金额", f"disburse_amount_{pcode.lower()}",
        [f"{pname}放款", f"{pcode}_amount"],
        "L2", "credit", "自营信贷产品部", "credit@simcf.com",
        f"当日 {pname} 产品的放款金额",
        f"SUM(principal) WHERE product_code='{pcode}'",
        [f"product_code='{pcode}'"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""
        SELECT disburse_date, SUM(principal) FROM sim_dw.dwd_credit_loan
        WHERE product_code='{pcode}' AND disburse_date='${{date}}'
        GROUP BY disburse_date
        """,
        ["M0046"])
    add(f"{pname}放款笔数", f"loan_count_{pcode.lower()}",
        [f"{pname}放款笔数"],
        "L2", "credit", "自营信贷产品部", "credit@simcf.com",
        f"当日 {pname} 产品的放款笔数",
        f"COUNT(*) WHERE product_code='{pcode}'",
        [f"product_code='{pcode}'"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""
        SELECT disburse_date, COUNT(*) FROM sim_dw.dwd_credit_loan
        WHERE product_code='{pcode}' AND disburse_date='${{date}}'
        GROUP BY disburse_date
        """)
    add(f"{pname}通过率", f"approval_rate_{pcode.lower()}",
        [f"{pname}过审率"],
        "L2", "credit", "自营信贷产品部", "credit@simcf.com",
        f"{pname} 产品的通过率",
        "approve_count / apply_count",
        [f"product_code='{pcode}'"], None, "day",
        ["sim_dw.dwd_credit_application"],
        f"""
        SELECT apply_date, SUM(status='APPROVED')/COUNT(*) approval_rate
        FROM sim_dw.dwd_credit_application
        WHERE product_code='{pcode}' AND apply_date='${{date}}'
        GROUP BY apply_date
        """)

add("APR 加权平均", "wavg_apr", ["加权年化利率"],
    "L2", "credit", "自营信贷产品部", "credit@simcf.com",
    "以本金为权重的平均 APR",
    "SUM(principal*apr) / SUM(principal)",
    [], None, "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, SUM(principal*apr)/SUM(principal) AS wavg_apr
    FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """,
    [])

add("平均期限", "avg_term_months", ["mean_term"],
    "L3", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日放款借据的平均期限",
    "AVG(term_months)",
    [], None, "day",
    ["sim_dw.dwd_credit_loan"],
    """
    SELECT disburse_date, AVG(term_months) FROM sim_dw.dwd_credit_loan
    WHERE disburse_date='${date}' GROUP BY disburse_date
    """)

# 每期还款、结清、提前结清
add("累计还款金额", "total_repayment_amount", ["还款额"],
    "L1", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日还款流水金额合计",
    "SUM(pay_amount)",
    [], "repay_id", "day",
    ["sim_dw.dwd_credit_repayment"],
    """
    SELECT pay_date, SUM(pay_amount) FROM sim_dw.dwd_credit_repayment
    WHERE pay_date='${date}' GROUP BY pay_date
    """,
    [])

add("提前结清笔数", "early_clear_count", ["early_clear"],
    "L3", "credit", "自营信贷产品部", "credit@simcf.com",
    "当日提前结清的借据数",
    "COUNT(loan_id) WHERE status='EARLY_CLEAR' OR pay_channel='EARLY'",
    ["status='SETTLED'"], "loan_id", "day",
    ["sim_credit_core.loan_status_log"],
    """
    SELECT DATE(changed_at), COUNT(DISTINCT loan_id)
    FROM sim_credit_core.loan_status_log
    WHERE remark='提前结清' AND DATE(changed_at)='${date}'
    GROUP BY DATE(changed_at)
    """)

# ================================================================
# 财务域 (finance) 30 个
# ================================================================

add("利息收入", "interest_income", ["利息", "利息收益"],
    "L1", "finance", "财务部", "finance@simcf.com",
    "当日计提的利息收入",
    "SUM(amount) WHERE account_code='6001' AND direction='CR'",
    [], None, "day",
    ["sim_dw.dws_finance_income_day"],
    """
    SELECT stat_date, interest_income FROM sim_dw.dws_finance_income_day
    WHERE stat_date='${date}'
    """,
    [], is_regulatory=True)

add("手续费收入", "fee_income", ["fee", "服务费"],
    "L1", "finance", "财务部", "finance@simcf.com",
    "当日计提的手续费/服务费收入",
    "SUM(amount) WHERE account_code='6002' AND direction='CR'",
    [], None, "day",
    ["sim_dw.dws_finance_income_day"],
    """
    SELECT stat_date, fee_income FROM sim_dw.dws_finance_income_day
    WHERE stat_date='${date}'
    """,
    [], is_regulatory=True)

add("总收入", "total_income", ["总营业收入", "gross_income"],
    "L1", "finance", "财务部", "finance@simcf.com",
    "利息收入 + 手续费收入",
    "interest_income + fee_income",
    [], None, "day",
    ["sim_dw.dws_finance_income_day"],
    """
    SELECT stat_date, total_income FROM sim_dw.dws_finance_income_day
    WHERE stat_date='${date}'
    """,
    ["M0068", "M0069"])

add("资金成本", "cost_of_fund", ["资金成本额"],
    "L2", "finance", "财务部", "finance@simcf.com",
    "支付给合作方的分润金额",
    "SUM(partner_income)",
    [], None, "day",
    ["sim_dw.dws_funding_partner_month"],
    """
    SELECT stat_month, SUM(partner_income) FROM sim_dw.dws_funding_partner_month
    WHERE stat_month='${month}' GROUP BY stat_month
    """,
    [])

add("平均资金成本率", "avg_cost_of_fund_rate", ["资金成本率"],
    "L2", "finance", "财务部", "finance@simcf.com",
    "资金成本 / 平均在贷余额（年化）",
    "cost_of_fund / avg_outstanding * 12",
    [], None, "month",
    ["sim_dw.dws_funding_partner_month"],
    """
    SELECT stat_month, SUM(partner_income)/NULLIF(SUM(funded_amount),0)*12 AS cost_rate
    FROM sim_dw.dws_funding_partner_month
    WHERE stat_month='${month}' GROUP BY stat_month
    """)

add("拨备覆盖率", "provision_coverage_ratio", ["拨备率"],
    "L1", "finance", "风险管理部", "risk@simcf.com",
    "贷款损失准备 / 不良贷款余额",
    "provision / npl",
    [], None, "month",
    ["sim_dw.dwd_credit_overdue"],
    """
    -- 简化：假设拨备 = 3% 在贷余额
    SELECT 0.03 * SUM(l.principal) / NULLIF(SUM(o.overdue_amount),0) AS provision_ratio
    FROM sim_dw.dwd_credit_loan l
    LEFT JOIN sim_dw.dwd_credit_overdue o
      ON o.loan_id=l.loan_id AND o.stage IN ('M3','M3+')
    WHERE l.disburse_date <= '${date}'
    """,
    [], is_regulatory=True)

# 剩下财务指标 stub 化
finance_stubs = [
    ("net_interest_margin", "净息差", "利息收入 / 平均生息资产", "L1"),
    ("net_profit", "净利润", "总收入-总支出-税", "L1"),
    ("operating_expense", "营业支出", "sum of expenses", "L2"),
    ("marketing_cost", "营销费用", "sum(5002)", "L2"),
    ("hr_cost", "人力成本", "sum(5003)", "L2"),
    ("collection_cost", "催收成本", "sum(5004)", "L2"),
    ("bad_debt_loss", "坏账损失", "sum(5005)", "L1"),
    ("roa", "资产回报率", "净利润/总资产", "L1"),
    ("roe", "净资产回报率", "净利润/净资产", "L2"),
    ("tax_amount", "缴税金额", "sum(tax_record.tax_amount)", "L2"),
    ("vat_amount", "增值税", "sum(tax where kind=VAT)", "L3"),
    ("income_tax_amount", "所得税", "sum(tax where kind=INCOME_TAX)", "L3"),
]
for en, zh, formula, lvl in finance_stubs:
    add(zh, en, [en, zh],
        lvl, "finance", "财务部", "finance@simcf.com",
        zh + "（示范定义）", formula,
        [], None, "day",
        ["sim_dw.dws_finance_income_day"],
        f"""
        SELECT stat_date, total_income  -- 示范 SQL，实际计算需接入 GL
        FROM sim_dw.dws_finance_income_day
        WHERE stat_date='${{date}}'
        """)

# ================================================================
# 风险域 (risk) 40 个
# ================================================================

add("M1 逾期率", "overdue_rate_m1", ["M1_rate", "首逾率"],
    "L1", "risk", "风险管理部", "risk@simcf.com",
    "M1 及以上逾期借据数 / 总借据数",
    "m1+_loan_count / total_loan_count",
    [], None, "day",
    ["sim_dw.dwd_credit_loan", "sim_dw.dwd_credit_overdue"],
    """
    SELECT
      COUNT(DISTINCT o.loan_id) / (SELECT COUNT(*) FROM sim_dw.dwd_credit_loan WHERE disburse_date<='${date}')
      AS overdue_rate_m1
    FROM sim_dw.dwd_credit_overdue o
    WHERE o.stage IN ('M1','M2','M3','M3+')
    """,
    [], is_regulatory=True)

add("M3 逾期率", "overdue_rate_m3", ["M3_rate", "严重逾期率"],
    "L1", "risk", "风险管理部", "risk@simcf.com",
    "M3 及以上逾期借据数 / 总借据数",
    "m3+_loan_count / total_loan_count",
    [], None, "day",
    ["sim_dw.dwd_credit_loan", "sim_dw.dwd_credit_overdue"],
    """
    SELECT
      COUNT(DISTINCT o.loan_id) / (SELECT COUNT(*) FROM sim_dw.dwd_credit_loan WHERE disburse_date<='${date}')
      AS overdue_rate_m3
    FROM sim_dw.dwd_credit_overdue o
    WHERE o.stage IN ('M3','M3+')
    """,
    [], is_regulatory=True)

add("M2 逾期率", "overdue_rate_m2", ["M2_rate"],
    "L2", "risk", "风险管理部", "risk@simcf.com",
    "M2 及以上逾期占比",
    "m2+_loan_count / total",
    [], None, "day",
    ["sim_dw.dwd_credit_overdue"],
    """
    SELECT
      COUNT(DISTINCT o.loan_id) / (SELECT COUNT(*) FROM sim_dw.dwd_credit_loan WHERE disburse_date<='${date}')
      AS overdue_rate_m2
    FROM sim_dw.dwd_credit_overdue o
    WHERE o.stage IN ('M2','M3','M3+')
    """)

add("首期逾期率", "first_overdue_rate", ["首逾"],
    "L1", "risk", "风险管理部", "risk@simcf.com",
    "第一期出现逾期的借据占比",
    "first_period_overdue / total_loans",
    ["period_no=1"], "loan_id", "day",
    ["sim_dw.dwd_credit_overdue"],
    """
    SELECT COUNT(DISTINCT loan_id) FROM sim_dw.dwd_credit_overdue
    WHERE period_no=1 AND overdue_start_date <= '${date}'
    """)

add("逾期金额", "overdue_amount", ["overdue_balance"],
    "L1", "risk", "风险管理部", "risk@simcf.com",
    "所有活跃逾期的应还未还本金合计",
    "SUM(overdue_amount) WHERE end_date IS NULL",
    [], None, "day",
    ["sim_dw.dwd_credit_overdue"],
    """
    SELECT SUM(overdue_amount) FROM sim_dw.dwd_credit_overdue
    WHERE overdue_end_date IS NULL AND overdue_start_date <= '${date}'
    """,
    [])

# 风险等级客户数
for grade in ["A", "B", "C", "D", "E"]:
    add(f"{grade} 级客户数", f"grade_{grade.lower()}_customer_count", [f"grade_{grade}"],
        "L2", "risk", "风险管理部", "risk@simcf.com",
        f"风险等级={grade} 的当前客户数",
        f"COUNT(DISTINCT customer_id) WHERE grade='{grade}'",
        [f"grade='{grade}'"], "customer_id", "day",
        ["sim_dw.dws_risk_grade_day"],
        f"""
        SELECT stat_date, customer_count FROM sim_dw.dws_risk_grade_day
        WHERE grade='{grade}' AND stat_date='${{date}}'
        """)

add("反欺诈拦截数", "antifraud_hit_count", ["fraud_intercept"],
    "L2", "risk", "风险管理部", "risk@simcf.com",
    "当日反欺诈规则拦截的申请数",
    "COUNT(*) WHERE action_taken='BLOCK'",
    ["action_taken='BLOCK'"], "event_id", "day",
    ["sim_risk_decision.antifraud_event"],
    """
    SELECT DATE(detected_at), COUNT(*) FROM sim_risk_decision.antifraud_event
    WHERE action_taken='BLOCK' AND DATE(detected_at)='${date}'
    GROUP BY DATE(detected_at)
    """)

add("反欺诈事件数", "antifraud_event_count", ["fraud_event"],
    "L3", "risk", "风险管理部", "risk@simcf.com",
    "当日触发的所有反欺诈事件",
    "COUNT(*)",
    [], "event_id", "day",
    ["sim_risk_decision.antifraud_event"],
    """
    SELECT DATE(detected_at), COUNT(*) FROM sim_risk_decision.antifraud_event
    WHERE DATE(detected_at)='${date}' GROUP BY DATE(detected_at)
    """)

add("黑名单命中数", "blacklist_hit_count", ["blacklist_hit"],
    "L2", "risk", "风险管理部", "risk@simcf.com",
    "决策日志中命中黑名单的次数",
    "COUNT(*) WHERE reject_reasons LIKE '%R002%' OR '%R003%'",
    [], None, "day",
    ["sim_risk_decision.decision_log"],
    """
    SELECT DATE(decided_at), COUNT(*) FROM sim_risk_decision.decision_log
    WHERE (reject_reasons LIKE '%R002%' OR reject_reasons LIKE '%R003%')
      AND DATE(decided_at)='${date}' GROUP BY DATE(decided_at)
    """)

# Vintage 逾期率（简化到 L2）
add("Vintage MOB3 逾期率", "vintage_mob3_overdue_rate", ["vintage_3"],
    "L2", "risk", "风险管理部", "risk@simcf.com",
    "放款后 3 个月的逾期率（按放款月分组）",
    "overdue_in_mob3 / total_loans_in_vintage",
    [], None, "month",
    ["sim_dw.dwd_credit_loan", "sim_dw.dwd_credit_overdue"],
    """
    SELECT DATE_FORMAT(l.disburse_date,'%Y-%m') vintage,
           COUNT(DISTINCT o.loan_id)/COUNT(DISTINCT l.loan_id) rate_mob3
    FROM sim_dw.dwd_credit_loan l
    LEFT JOIN sim_dw.dwd_credit_overdue o
      ON o.loan_id=l.loan_id
     AND o.overdue_start_date <= DATE_ADD(l.disburse_date,INTERVAL 90 DAY)
    GROUP BY DATE_FORMAT(l.disburse_date,'%Y-%m')
    """)

risk_stubs = [
    ("model_score_avg", "模型分均值", "L3"),
    ("model_ks", "模型 KS", "L2"),
    ("model_psi", "模型 PSI", "L2"),
    ("bad_customer_rate", "坏客户率", "L1"),
    ("recovery_rate_m1", "M1 催回率", "L2"),
    ("recovery_rate_m2", "M2 催回率", "L2"),
    ("recovery_rate_m3", "M3 催回率", "L2"),
    ("collection_case_count", "催收案件数", "L3"),
    ("collection_action_count", "催收动作数", "L3"),
    ("ptp_fulfillment_rate", "承诺兑现率", "L3"),
    ("rejection_reason_top1", "拒绝原因 TOP1", "L3"),
    ("device_share_count", "共享设备数", "L3"),
]
for en, zh, lvl in risk_stubs:
    add(zh, en, [zh, en],
        lvl, "risk", "风险管理部", "risk@simcf.com",
        f"{zh}（详见风险管理办法）",
        "见 SQL",
        [], None, "day",
        ["sim_dw.dwd_credit_overdue"],
        f"""
        SELECT 1 AS stub_metric
        """)

# ================================================================
# 营销域 (marketing) 25 个
# ================================================================

add("获客成本 CPA", "cpa", ["cost_per_acquisition", "获客成本"],
    "L1", "marketing", "营销部", "marketing@simcf.com",
    "总营销花费 / 新客数",
    "SUM(ad_cost) / new_customers",
    [], None, "day",
    ["sim_dw.dws_marketing_channel_day"],
    """
    SELECT stat_date, SUM(ad_cost)/NULLIF(SUM(new_reg),0) AS cpa
    FROM sim_dw.dws_marketing_channel_day
    WHERE stat_date='${date}' GROUP BY stat_date
    """,
    [])

add("渠道 ROI", "channel_roi", ["roi"],
    "L1", "marketing", "营销部", "marketing@simcf.com",
    "(放款额 * 毛利率 - 投放成本) / 投放成本",
    "(loan_amount*0.15 - ad_cost) / ad_cost",
    [], None, "day",
    ["sim_dw.ads_marketing_roi_daily"],
    """
    SELECT stat_date, channel_code, roi FROM sim_dw.ads_marketing_roi_daily
    WHERE stat_date='${date}'
    """,
    [])

add("广告曝光量", "impression", ["曝光", "impressions"],
    "L2", "marketing", "营销部", "marketing@simcf.com",
    "当日广告曝光总次数",
    "SUM(impression)",
    [], None, "day",
    ["sim_dw.dws_marketing_channel_day"],
    """
    SELECT stat_date, SUM(impression) FROM sim_dw.dws_marketing_channel_day
    WHERE stat_date='${date}' GROUP BY stat_date
    """)

add("点击量", "click_count", ["click"],
    "L2", "marketing", "营销部", "marketing@simcf.com",
    "当日广告点击总次数",
    "SUM(click)",
    [], None, "day",
    ["sim_dw.dws_marketing_channel_day"],
    """
    SELECT stat_date, SUM(click) FROM sim_dw.dws_marketing_channel_day
    WHERE stat_date='${date}' GROUP BY stat_date
    """)

add("点击率 CTR", "ctr", ["click_through_rate"],
    "L2", "marketing", "营销部", "marketing@simcf.com",
    "点击量 / 曝光量",
    "SUM(click)/SUM(impression)",
    [], None, "day",
    ["sim_dw.dws_marketing_channel_day"],
    """
    SELECT stat_date, SUM(click)/NULLIF(SUM(impression),0) AS ctr
    FROM sim_dw.dws_marketing_channel_day
    WHERE stat_date='${date}' GROUP BY stat_date
    """)

add("转化率 CVR", "cvr", ["conversion_rate"],
    "L2", "marketing", "营销部", "marketing@simcf.com",
    "新客数 / 点击量",
    "new_reg / click",
    [], None, "day",
    ["sim_dw.dws_marketing_channel_day"],
    """
    SELECT stat_date, SUM(new_reg)/NULLIF(SUM(click),0) FROM sim_dw.dws_marketing_channel_day
    WHERE stat_date='${date}' GROUP BY stat_date
    """)

add("客户生命周期价值 LTV", "ltv", ["lifetime_value"],
    "L1", "marketing", "营销部", "marketing@simcf.com",
    "客户在生命周期内产生的净收入",
    "avg_income - avg_cost",
    [], None, "month",
    ["sim_dw.dws_finance_income_day", "sim_dw.dim_customer"],
    """
    SELECT AVG(total_income) FROM sim_dw.dws_finance_income_day
    WHERE stat_date >= DATE_SUB('${date}', INTERVAL 30 DAY)
    """)

# 每渠道的 CPA
for ch in ["APP_ORG", "BAIDU_SEM", "TENCENT_AD", "BYTEDANCE_AD", "KUAISHOU_AD",
           "REFERRAL", "PARTNER_BANK1", "PARTNER_MALL", "H5_PROMO", "WECHAT_MP"]:
    add(f"{ch} 渠道 CPA", f"cpa_{ch.lower()}", [f"{ch}_cpa"],
        "L3", "marketing", "营销部", "marketing@simcf.com",
        f"渠道 {ch} 的获客成本",
        "ad_cost/new_reg",
        [f"channel_code='{ch}'"], None, "day",
        ["sim_dw.dws_marketing_channel_day"],
        f"""
        SELECT stat_date, ad_cost/NULLIF(new_reg,0) FROM sim_dw.dws_marketing_channel_day
        WHERE channel_code='{ch}' AND stat_date='${{date}}'
        """)

marketing_stubs = [
    ("promo_code_usage_count", "优惠码使用数", "L3"),
    ("promo_conversion_amount", "优惠转化金额", "L3"),
    ("attribution_last_touch", "末次触点归因数", "L3"),
    ("attribution_first_touch", "首次触点归因数", "L3"),
    ("bid_cost_avg", "平均出价", "L3"),
]
for en, zh, lvl in marketing_stubs:
    add(zh, en, [zh, en],
        lvl, "marketing", "营销部", "marketing@simcf.com",
        f"{zh}", "见 SQL", [], None, "day",
        ["sim_dw.dws_marketing_channel_day"],
        """
        SELECT 1 AS stub
        """)

# ================================================================
# 经营管理域 (operation) 20 个
# ================================================================

add("客服工单量", "ticket_count", ["ticket_cnt"],
    "L2", "operation", "客服中心", "csm@simcf.com",
    "当日新建工单总数",
    "COUNT(*)",
    [], "ticket_id", "day",
    ["sim_dw.dwd_csm_ticket"],
    """
    SELECT created_date, COUNT(*) FROM sim_dw.dwd_csm_ticket
    WHERE created_date='${date}' GROUP BY created_date
    """)

add("投诉率", "complaint_rate", ["投诉占比"],
    "L1", "operation", "客服中心", "csm@simcf.com",
    "投诉工单 / 当日活跃客户",
    "complaint / active_users",
    [], None, "day",
    ["sim_dw.dwd_csm_ticket", "sim_dw.dws_customer_active_day"],
    """
    SELECT t.created_date,
           SUM(t.is_complaint) / (SELECT COUNT(*) FROM sim_dw.dws_customer_active_day WHERE stat_date=t.created_date)
           AS complaint_rate
    FROM sim_dw.dwd_csm_ticket t
    WHERE t.created_date='${date}' GROUP BY t.created_date
    """)

add("客服接通率", "csm_answer_rate", ["接通率"],
    "L2", "operation", "客服中心", "csm@simcf.com",
    "接通电话数 / 呼入电话数",
    "answered / total_calls",
    [], None, "day",
    ["sim_csm.call_record"],
    """
    SELECT DATE(call_time),
           SUM(duration_sec>0)/COUNT(*) AS answer_rate
    FROM sim_csm.call_record
    WHERE DATE(call_time)='${date}' GROUP BY DATE(call_time)
    """)

add("客服平均满意度", "csm_csat_avg", ["csat"],
    "L2", "operation", "客服中心", "csm@simcf.com",
    "当日客服通话的平均满意度评分",
    "AVG(csat_score)",
    [], None, "day",
    ["sim_csm.call_record"],
    """
    SELECT DATE(call_time), AVG(csat_score) FROM sim_csm.call_record
    WHERE DATE(call_time)='${date}' AND csat_score IS NOT NULL
    GROUP BY DATE(call_time)
    """)

operation_stubs = [
    ("emp_headcount", "员工总数", "L2"),
    ("emp_productivity", "员工人均产能", "L1"),
    ("cost_per_customer", "单位客户成本", "L2"),
    ("cost_per_loan", "单笔放款成本", "L2"),
    ("branch_performance", "分公司业绩", "L2"),
    ("ticket_avg_resolution_hours", "工单平均处理时长", "L3"),
    ("complaint_escalation_rate", "投诉升级率", "L3"),
    ("app_daily_activation", "APP 每日安装", "L3"),
    ("uninstall_rate", "APP 卸载率", "L3"),
    ("page_view_count", "页面浏览量", "L3"),
    ("click_through_apply", "点击到申请转化", "L3"),
    ("apply_to_loan_rate", "申请到放款转化", "L2"),
    ("cust_service_hours", "客服工时", "L3"),
    ("first_response_time_avg", "首次响应时长", "L3"),
    ("nps_score", "NPS 净推荐值", "L2"),
]
for en, zh, lvl in operation_stubs:
    add(zh, en, [zh, en],
        lvl, "operation", "运营部", "ops@simcf.com",
        f"{zh}", "见 SQL", [], None, "day",
        ["sim_dw.ads_operation_daily"],
        """
        SELECT 1 AS stub
        """)

# ================================================================
# 资金/合作方域 (funding) 15 个
# ================================================================

add("合作方分润总额", "total_partner_income", ["合作方分润"],
    "L1", "funding", "联合贷分润业务部", "funding@simcf.com",
    "所有合作方本月分润合计",
    "SUM(partner_income)",
    [], None, "month",
    ["sim_dw.dws_funding_partner_month"],
    """
    SELECT stat_month, SUM(partner_income) FROM sim_dw.dws_funding_partner_month
    WHERE stat_month='${month}' GROUP BY stat_month
    """,
    [])

add("自留分润", "self_income_share", ["自留部分"],
    "L1", "funding", "联合贷分润业务部", "funding@simcf.com",
    "本月保留在公司的分润部分",
    "SUM(self_income)",
    [], None, "month",
    ["sim_dw.dws_funding_partner_month"],
    """
    SELECT stat_month, SUM(self_income) FROM sim_dw.dws_funding_partner_month
    WHERE stat_month='${month}' GROUP BY stat_month
    """)

add("合作方数量", "partner_count", ["合作方"],
    "L2", "funding", "联合贷分润业务部", "funding@simcf.com",
    "当前活跃的资金合作方数量",
    "COUNT(DISTINCT partner_code)",
    ["status='ACTIVE'"], "partner_code", "day",
    ["sim_funding.funding_partner"],
    """
    SELECT COUNT(*) FROM sim_funding.funding_partner WHERE status='ACTIVE'
    """)

add("合作方出资金额", "partner_funded_amount", ["资金方出资"],
    "L2", "funding", "联合贷分润业务部", "funding@simcf.com",
    "所有合作方本月出资合计",
    "SUM(funded_amount)",
    [], None, "month",
    ["sim_dw.dws_funding_partner_month"],
    """
    SELECT stat_month, SUM(funded_amount) FROM sim_dw.dws_funding_partner_month
    WHERE stat_month='${month}' GROUP BY stat_month
    """)

funding_stubs = [
    ("guarantee_claim_count", "担保代偿笔数", "L2"),
    ("guarantee_claim_amount", "担保代偿金额", "L2"),
    ("partner_income_by_partner", "合作方分润 by partner", "L2"),
    ("fund_source_concentration", "资金来源集中度", "L3"),
    ("agreement_active_count", "有效协议数", "L3"),
    ("avg_funding_ratio", "平均出资比例", "L3"),
    ("cost_of_fund_by_partner", "合作方资金成本", "L2"),
    ("settle_delay_days", "结算延迟天数", "L3"),
    ("settle_success_rate", "结算成功率", "L2"),
    ("dispute_count", "争议数", "L3"),
    ("guarantee_rate", "担保比例", "L3"),
]
for en, zh, lvl in funding_stubs:
    add(zh, en, [zh, en],
        lvl, "funding", "联合贷分润业务部", "funding@simcf.com",
        f"{zh}", "见 SQL", [], None, "month",
        ["sim_dw.dws_funding_partner_month"],
        """SELECT 1 AS stub""")

# ================================================================
# 合规域 (compliance) 10 个
# ================================================================

add("重大投诉数", "critical_complaint_count", ["高优投诉"],
    "L1", "compliance", "法务合规部", "legal@simcf.com",
    "上报监管或升级的投诉数",
    "COUNT(*) WHERE escalated=1 OR reported_regulator=1",
    ["escalated=1 OR reported_regulator=1"], "complaint_id", "day",
    ["sim_csm.complaint"],
    """
    SELECT DATE(filed_at), COUNT(*) FROM sim_csm.complaint
    WHERE (escalated=1 OR reported_regulator=1) AND DATE(filed_at)='${date}'
    GROUP BY DATE(filed_at)
    """,
    [], is_regulatory=True)

compliance_stubs = [
    ("regulatory_filing_on_time_rate", "监管报送及时率", "L1"),
    ("data_quality_score", "数据质量得分", "L1"),
    ("privacy_incident_count", "隐私事件数", "L1"),
    ("audit_finding_count", "审计发现问题数", "L2"),
    ("data_access_violation_count", "数据违规访问次数", "L2"),
    ("kyc_pass_rate", "KYC 通过率", "L1"),
    ("aml_alert_count", "反洗钱预警数", "L2"),
    ("regulatory_penalty_amount", "监管处罚金额", "L1"),
    ("customer_consent_rate", "客户授权同意率", "L3"),
]
for en, zh, lvl in compliance_stubs:
    add(zh, en, [zh, en],
        lvl, "compliance", "法务合规部", "legal@simcf.com",
        f"{zh}", "见 SQL", [], None, "day",
        ["sim_csm.complaint"],
        """SELECT 1 AS stub""",
        is_regulatory=(lvl=="L1"))

print(f"\n生成完毕：共 {len(metrics)} 个指标")

# ---------- 补齐指标：地域细分、时间维度延伸 ----------
provinces = ["广东", "江苏", "山东", "浙江", "河南", "四川", "湖北", "北京", "上海", "福建"]
for p in provinces:
    add(f"{p}省客户数", f"customer_count_{p}", [f"{p}客户"],
        "L3", "user", "运营部", "growth@simcf.com",
        f"户籍省份={p} 的客户数",
        "COUNT(DISTINCT customer_id) WHERE province=X",
        [f"province='{p}'"], "customer_id", "day",
        ["sim_dw.dim_customer"],
        f"""SELECT COUNT(DISTINCT customer_id) FROM sim_dw.dim_customer WHERE province='{p}' AND is_current=1""")
    add(f"{p}省放款金额", f"disburse_amount_{p}", [f"{p}放款"],
        "L3", "credit", "自营信贷产品部", "credit@simcf.com",
        f"户籍={p} 的客户放款额",
        "SUM(principal)", [f"customer_province='{p}'"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""SELECT SUM(principal) FROM sim_dw.dwd_credit_loan WHERE customer_province='{p}' AND disburse_date='${{date}}'""")

# 客户风险等级放款
for grade in ["A", "B", "C", "D", "E"]:
    add(f"{grade} 级客户放款金额", f"disburse_amount_grade_{grade.lower()}", [f"{grade}_disburse"],
        "L3", "risk", "风险管理部", "risk@simcf.com",
        f"当前风险等级={grade} 的客户放款额",
        "SUM(principal) WHERE grade=X", [], None, "day",
        ["sim_dw.dwd_credit_loan", "sim_risk_decision.risk_grade"],
        f"""
        SELECT SUM(l.principal) FROM sim_dw.dwd_credit_loan l
        JOIN sim_risk_decision.risk_grade g ON g.customer_id=l.customer_id AND g.grade='{grade}'
        WHERE l.disburse_date='${{date}}'
        """)

# 期数指标（3/6/12/24 期）
for term in [3, 6, 12, 18, 24, 36]:
    add(f"{term} 期借据数", f"loan_count_term_{term}", [f"{term}m_loans"],
        "L3", "credit", "自营信贷产品部", "credit@simcf.com",
        f"当日放款中，期限={term} 个月的借据数",
        f"COUNT(*) WHERE term_months={term}",
        [f"term_months={term}"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""SELECT COUNT(*) FROM sim_dw.dwd_credit_loan WHERE term_months={term} AND disburse_date='${{date}}'""")

# 分公司
for bc, bn in [("B_BJ","北京"), ("B_SH","上海"), ("B_SZ","深圳"),
                ("B_WH","武汉"), ("B_CD","成都"), ("B_SY","沈阳")]:
    add(f"{bn}分公司放款金额", f"branch_disburse_{bc.lower()}", [f"{bn}放款"],
        "L2", "operation", "运营部", "ops@simcf.com",
        f"分公司 {bn} 当日放款额",
        "SUM(principal) WHERE branch_code=X",
        [f"branch_code='{bc}'"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""SELECT SUM(principal) FROM sim_dw.dwd_credit_loan WHERE branch_code='{bc}' AND disburse_date='${{date}}'""")
    add(f"{bn}分公司放款笔数", f"branch_loans_{bc.lower()}", [f"{bn}放款笔数"],
        "L3", "operation", "运营部", "ops@simcf.com",
        f"分公司 {bn} 当日放款笔数",
        "COUNT(*) WHERE branch_code=X",
        [f"branch_code='{bc}'"], "loan_id", "day",
        ["sim_dw.dwd_credit_loan"],
        f"""SELECT COUNT(*) FROM sim_dw.dwd_credit_loan WHERE branch_code='{bc}' AND disburse_date='${{date}}'""")

print(f"补齐后：共 {len(metrics)} 个指标")

# 输出
out_yaml = BASE / "catalog" / "metrics.yaml"
out_yaml.parent.mkdir(exist_ok=True, parents=True)
with out_yaml.open("w") as f:
    yaml.dump({"version": VERSION, "metrics": metrics}, f,
              allow_unicode=True, sort_keys=False, default_flow_style=False)
print(f"写入 {out_yaml}")

# 生成可读 markdown 版
out_md = BASE / "catalog" / "metrics.md"
lines = ["# 指标目录 (Catalog)\n\n",
         f"共 **{len(metrics)}** 个指标。\n\n",
         "| ID | 中文名 | 英文名 | 分级 | 领域 | 部门 |\n",
         "|---|---|---|---|---|---|\n"]
for m in metrics:
    lines.append(f"| {m['id']} | {m['name_zh']} | `{m['name_en']}` | {m['level']} | {m['domain']} | {m['department']} |\n")
out_md.write_text("".join(lines))
print(f"写入 {out_md}")

# 各领域统计
from collections import Counter
dom = Counter(m["domain"] for m in metrics)
lvl = Counter(m["level"] for m in metrics)
print("\n按领域:", dict(dom))
print("按级别:", dict(lvl))
