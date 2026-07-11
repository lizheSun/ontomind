"""
主线数据生成器 —— 一次生成保证跨库一致

核心策略：
1. 先生成 10000 客户（含身份、地址、联系方式、KYC、标签）
2. 生成营销渠道/活动/成本/优惠码
3. 客户从注册 → 生成 app_event → 授信申请 → 风控决策 → 授信额度 → 支用（放款） → 还款计划 → 还款流水 / 逾期 → 催收 → 财务凭证 / 资金分润 / 归因
4. 全部先落 CSV，然后 LOAD DATA 导入
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import random
import datetime as dt
import json
from collections import defaultdict, Counter
from decimal import Decimal, ROUND_HALF_UP

from faker import Faker
from common import (
    BASE_DIR, CONFIG, SEED, DATE_START, DATE_END, TODAY,
    customer_id, application_id, loan_id, contract_id,
    gen_id_card, gen_phone, gen_bank_card,
    weighted_date, dt_at, normal_age,
    choose_product, choose_branch, BRANCHES,
    CsvWriter, mysql_conn,
)

# 每个系统的 CSV 输出目录
SYSTEMS_DIR = BASE_DIR / "systems"
OUT = {}  # 记录所有 csv writer，最后关闭


def out_dir(sys_dir: str) -> Path:
    d = SYSTEMS_DIR / sys_dir / "seed_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


rng = random.Random(SEED)
faker = Faker("zh_CN")
Faker.seed(SEED)


N_CUSTOMERS = CONFIG["scale"]["customers"]
N_APPLICATIONS = CONFIG["scale"]["applications"]
N_LOANS = CONFIG["scale"]["loans"]
N_EVENTS = CONFIG["scale"]["events"]


def D(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


CHANNELS = [
    ("APP_ORG",       "APP 自然流量",  "ORGANIC",  "OPS"),
    ("BAIDU_SEM",     "百度 SEM",       "PAID",     "MKT"),
    ("TENCENT_AD",    "腾讯广告",       "PAID",     "MKT"),
    ("BYTEDANCE_AD",  "抖音/头条广告",  "PAID",     "MKT"),
    ("KUAISHOU_AD",   "快手广告",       "PAID",     "MKT"),
    ("REFERRAL",      "老客推荐",       "ORGANIC",  "OPS"),
    ("PARTNER_BANK1", "合作银行 A",     "PARTNER",  "BIZ"),
    ("PARTNER_MALL",  "电商合作方",     "PARTNER",  "BIZ"),
    ("H5_PROMO",      "H5 落地页",      "PAID",     "MKT"),
    ("WECHAT_MP",     "微信小程序",     "PAID",     "MKT"),
]
CHANNEL_WEIGHTS = [0.10, 0.18, 0.14, 0.20, 0.10, 0.08, 0.05, 0.04, 0.06, 0.05]

FUNDING_PARTNERS = [
    ("BANK_A", "阳光银行",          "BANK",       "SELF_LOAN", 0.0, 0.0, 0.0, 0.055),
    ("BANK_B", "华融银行",          "BANK",       "PLATFORM_LOAN", 0.7, 0.5, 0.0, 0.05),
    ("BANK_C", "农商银行",          "BANK",       "JOINT_LOAN", 0.6, 0.55, 0.0, 0.048),
    ("BANK_D", "城市商业银行",       "BANK",       "PLATFORM_LOAN", 0.8, 0.45, 0.0, 0.052),
    ("TRUST_A","中信资金信托",       "TRUST",      "JOINT_LOAN", 0.5, 0.6, 0.0, 0.06),
    ("GTE_A",  "融信担保有限公司",   "GUARANTEE",  "GUARANTEE_LOAN", 0.0, 0.4, 1.0, 0.0),
]

PRODUCTS_DDL = [
    ("SELF_LOAN",      "信优速贷",   "自营信贷",   1000,  50000, "3,6,12,18,24", 0.18,  0.02),
    ("PLATFORM_LOAN",  "信优合作贷", "助贷平台",   2000,  80000, "6,12,18,24,36", 0.16, 0.01),
    ("JOINT_LOAN",     "信优联合贷", "联合贷分润", 3000, 100000, "6,12,24,36",    0.15, 0.005),
    ("GUARANTEE_LOAN", "信优保贷",   "担保业务",   5000, 150000, "12,24,36",      0.20, 0.03),
]

OCCUPATIONS = [
    ("工程师",           7000, 25000),
    ("销售",             4000, 20000),
    ("教师",             6000, 15000),
    ("公务员",           6000, 14000),
    ("医生/护士",        5000, 20000),
    ("个体经营者",       3000, 30000),
    ("工人",             3000, 8000),
    ("服务员",           3000, 7000),
    ("学生",             1000, 3000),
    ("自由职业",         4000, 25000),
    ("公司职员",         5000, 15000),
    ("运营/客服",        4000, 12000),
]

EDUCATION = ["初中", "高中", "大专", "本科", "硕士", "博士"]
EDUCATION_WEIGHTS = [0.05, 0.15, 0.25, 0.40, 0.13, 0.02]

APPLY_PURPOSES = ["消费", "装修", "教育", "医疗", "旅游", "婚庆", "购车", "其他"]

REJECT_CODES = {
    "AGE_LIMIT":          "年龄超出准入范围",
    "BLACK_LIST":         "命中黑名单",
    "MULTI_APPLY":        "近期申请过多",
    "OVERDUE_HISTORY":    "存在历史逾期",
    "LOW_MODEL_SCORE":    "模型评分过低",
    "INCOMPLETE_KYC":     "KYC 认证失败",
    "INCOME_LOW":         "收入不足",
    "ANTIFRAUD":          "反欺诈拦截",
}


# ============================================================
# 阶段 1 —— 客户主档、身份、地址、联系、KYC、标签
# ============================================================
print(f"[Stage 1] Generating {N_CUSTOMERS} customers...")

w_cust = CsvWriter(out_dir("01_cust_cif") / "customer.csv",
    ["customer_id", "name", "gender", "birth_date", "age", "education",
     "marital", "occupation", "monthly_income", "reg_channel",
     "reg_time", "status", "is_test_data"])
w_id = CsvWriter(out_dir("01_cust_cif") / "identity.csv",
    ["customer_id", "id_type", "id_number", "id_issue_org", "province",
     "verified_at", "is_test_data"])
w_addr = CsvWriter(out_dir("01_cust_cif") / "address.csv",
    ["customer_id", "addr_type", "province", "city", "district", "detail",
     "is_current", "created_at", "is_test_data"])
w_contact = CsvWriter(out_dir("01_cust_cif") / "contact.csv",
    ["customer_id", "contact_type", "contact_value", "contact_name",
     "contact_relation", "is_current", "created_at", "is_test_data"])
w_kyc = CsvWriter(out_dir("01_cust_cif") / "kyc_result.csv",
    ["customer_id", "kyc_type", "result", "fail_reason", "completed_at",
     "is_test_data"])
w_tag = CsvWriter(out_dir("01_cust_cif") / "customer_tag.csv",
    ["customer_id", "tag_code", "tag_name", "tag_source", "valid_from",
     "valid_to", "is_test_data"])


class Customer:
    __slots__ = ("cid", "province", "reg_time", "reg_channel", "grade_hint",
                 "monthly_income", "phone", "birth", "age", "kyc_pass")


customers: list[Customer] = []

# 注册时间在 6 个月内均匀分布，前 1 个月的老客户占 30%
for i in range(1, N_CUSTOMERS + 1):
    cid = customer_id(i)

    # 40% 早期用户，60% 后期
    if rng.random() < 0.4:
        reg_day = DATE_START + dt.timedelta(days=rng.randint(0, 45))
    else:
        reg_day = weighted_date(rng, DATE_START, DATE_END)

    reg_time = dt_at(reg_day, rng)
    channel = rng.choices([c[0] for c in CHANNELS], weights=CHANNEL_WEIGHTS, k=1)[0]

    age = normal_age(rng)
    birth = dt.date(TODAY.year - age, rng.randint(1, 12), rng.randint(1, 28))
    gender = 1 if rng.random() < 0.55 else 2
    name = faker.name_male() if gender == 1 else faker.name_female()

    occ_name, inc_low, inc_high = rng.choice(OCCUPATIONS)
    monthly_income = D(rng.uniform(inc_low, inc_high))

    education = rng.choices(EDUCATION, weights=EDUCATION_WEIGHTS, k=1)[0]
    marital = rng.choices(["未婚", "已婚", "离异"], weights=[0.45, 0.50, 0.05], k=1)[0]

    id_no, province = gen_id_card(rng, birth)
    phone = gen_phone(rng)

    # KYC 通过率 92%
    kyc_pass = rng.random() < 0.92

    w_cust.row([cid, name, gender, birth, age, education, marital, occ_name,
                monthly_income, channel, reg_time, "ACTIVE", 1])
    w_id.row([cid, "ID", id_no, f"{province}公安局", province,
              reg_time + dt.timedelta(minutes=rng.randint(1, 60)), 1])
    # 家庭地址
    w_addr.row([cid, "HOME", province, faker.city_name(), faker.district(),
                faker.street_address(), 1, reg_time, 1])
    # 工作地址（60% 概率）
    if rng.random() < 0.6 and age >= 22:
        w_addr.row([cid, "WORK", province, faker.city_name(), faker.district(),
                    f"{faker.company()}办公楼", 1, reg_time, 1])
    # 手机
    w_contact.row([cid, "MOBILE", phone, None, None, 1, reg_time, 1])
    # 邮箱 30%
    if rng.random() < 0.3:
        email = faker.email()
        w_contact.row([cid, "EMAIL", email, None, None, 1, reg_time, 1])
    # 紧急联系人 70%
    if rng.random() < 0.7:
        rel = rng.choice(["父亲", "母亲", "配偶", "兄弟姐妹", "朋友"])
        emer_name = faker.name()
        emer_phone = gen_phone(rng)
        w_contact.row([cid, "EMER", emer_phone, emer_name, rel, 1, reg_time, 1])

    # KYC
    kyc_time_base = reg_time + dt.timedelta(minutes=rng.randint(2, 30))
    for kyc_type in ["REAL_NAME", "FACE", "BANK_CARD"]:
        if kyc_pass:
            result, reason = "PASS", None
        else:
            # 失败的用户在 3 步 KYC 中随机某一步失败
            if kyc_type == rng.choice(["REAL_NAME", "FACE", "BANK_CARD"]):
                result, reason = "FAIL", rng.choice(["活体检测未通过", "证件识别失败", "银行卡验证失败"])
            else:
                result, reason = "PASS", None
        w_kyc.row([cid, kyc_type, result, reason,
                   kyc_time_base + dt.timedelta(minutes=rng.randint(1, 20)), 1])

    # 客户标签（约 30% 客户有 1-2 个标签）
    if rng.random() < 0.3:
        tags = rng.sample([
            ("HIGH_QUALITY", "优质客户"),
            ("VIP", "VIP 客户"),
            ("NEW_CUSTOMER", "新客"),
            ("LOAN_RISK", "风险客户"),
            ("ACTIVE_USER", "活跃客户"),
            ("REFERRER", "推荐人"),
        ], k=rng.randint(1, 2))
        for tc, tn in tags:
            w_tag.row([cid, tc, tn, "MODEL", reg_day, None, 1])

    c = Customer()
    c.cid = cid
    c.province = province
    c.reg_time = reg_time
    c.reg_channel = channel
    c.monthly_income = monthly_income
    c.phone = phone
    c.birth = birth
    c.age = age
    c.kyc_pass = kyc_pass
    # 隐性风险等级：由收入+年龄+学历粗略估算，模拟"内部真值"
    score = 0
    if monthly_income >= 15000: score += 2
    elif monthly_income >= 8000: score += 1
    if 25 <= age <= 45: score += 1
    if education in ("本科", "硕士", "博士"): score += 1
    if not kyc_pass: score -= 3
    c.grade_hint = score
    customers.append(c)

for w in (w_cust, w_id, w_addr, w_contact, w_kyc, w_tag):
    w.close()
print(f"  ✓ customer.csv {w_cust.count}, identity {w_id.count}, kyc {w_kyc.count}")


# ============================================================
# 阶段 2 —— 营销渠道、活动、成本、优惠码
# ============================================================
print("[Stage 2] Generating marketing...")

w_channel = CsvWriter(out_dir("08_marketing") / "channel.csv",
    ["channel_code", "channel_name", "channel_type", "channel_owner", "is_active"])
w_campaign = CsvWriter(out_dir("08_marketing") / "campaign.csv",
    ["campaign_id", "campaign_name", "channel_code", "product_code", "start_date",
     "end_date", "budget", "status", "is_test_data"])
w_adcost = CsvWriter(out_dir("08_marketing") / "ad_cost.csv",
    ["campaign_id", "channel_code", "cost_date", "impression", "click", "cost",
     "is_test_data"])
w_promo = CsvWriter(out_dir("08_marketing") / "promo_code.csv",
    ["promo_code", "promo_name", "discount_type", "value_num", "start_date",
     "end_date", "quota", "used", "is_test_data"])

for code, name, ctype, owner in CHANNELS:
    w_channel.row([code, name, ctype, owner, 1])

# 也把渠道字典同步到进件系统
w_intake_ch = CsvWriter(out_dir("02_loan_intake") / "intake_channel_ref.csv",
    ["channel_code", "channel_name", "channel_type", "is_active"])
for code, name, ctype, owner in CHANNELS:
    w_intake_ch.row([code, name, ctype, 1])
w_intake_ch.close()

# 每渠道 5 个活动，共 50 活动
campaigns = []
camp_seq = 0
for code, name, ctype, _ in CHANNELS:
    if ctype == "ORGANIC":
        continue  # 自然流量不做活动
    for k in range(5):
        camp_seq += 1
        cid_camp = f"CAMP{camp_seq:04d}"
        start = DATE_START + dt.timedelta(days=rng.randint(0, 30))
        end = start + dt.timedelta(days=rng.randint(30, 120))
        end = min(end, DATE_END)
        budget = D(rng.uniform(50000, 500000))
        product = rng.choice(["SELF_LOAN", "PLATFORM_LOAN", "JOINT_LOAN", "GUARANTEE_LOAN"])
        w_campaign.row([cid_camp, f"{name}-{k+1}期", code, product,
                        start, end, budget, "RUNNING", 1])
        campaigns.append((cid_camp, code, start, end))

# 每活动每天一条成本
for cid_camp, ch, s, e in campaigns:
    d = s
    while d <= e and d <= DATE_END:
        impr = rng.randint(1000, 30000)
        clk = int(impr * rng.uniform(0.005, 0.05))
        cost = D(clk * rng.uniform(1.0, 8.0))
        w_adcost.row([cid_camp, ch, d, impr, clk, cost, 1])
        d += dt.timedelta(days=1)

# 优惠码 15 个
for i in range(15):
    pcode = f"PROMO{i+1:03d}"
    dtype = rng.choice(["APR_CUT", "AMOUNT_OFF"])
    val = D(rng.uniform(0.005, 0.03)) if dtype == "APR_CUT" else D(rng.randint(50, 300))
    start = DATE_START + dt.timedelta(days=rng.randint(0, 60))
    end = start + dt.timedelta(days=rng.randint(30, 120))
    w_promo.row([pcode, f"促销码-{i+1}", dtype, val, start, min(end, DATE_END),
                 rng.randint(1000, 5000), 0, 1])

for w in (w_channel, w_campaign, w_adcost, w_promo):
    w.close()
print(f"  ✓ channels {w_channel.count}, campaigns {w_campaign.count}, ad_cost {w_adcost.count}")


# ============================================================
# 阶段 3 —— 产品、资金合作方、协议
# ============================================================
print("[Stage 3] Generating products & funding partners...")

w_prod = CsvWriter(out_dir("04_credit_core") / "product.csv",
    ["product_code", "product_name", "product_kind", "min_amount", "max_amount",
     "term_options", "apr_default", "fee_rate", "is_active", "effective_from"])
for row in PRODUCTS_DDL:
    w_prod.row([*row, 1, DATE_START])
w_prod.close()

w_fpartner = CsvWriter(out_dir("06_funding") / "funding_partner.csv",
    ["partner_code", "partner_name", "partner_type", "contact_person",
     "contact_phone", "onboarded_at", "status", "is_test_data"])
w_fagr = CsvWriter(out_dir("06_funding") / "funding_agreement.csv",
    ["agreement_id", "partner_code", "product_code", "funding_share",
     "profit_share", "guarantee_ratio", "cost_of_fund_apr",
     "effective_from", "effective_to", "is_test_data"])

partner_agreements = {}  # partner_code+product -> agreement_id
for pcode, pname, ptype, pprod, fshare, pshare, gratio, cof in FUNDING_PARTNERS:
    w_fpartner.row([pcode, pname, ptype, faker.name(), gen_phone(rng),
                    dt.date(2024, 1, 1), "ACTIVE", 1])
    aid = f"FA{pcode}_{pprod}"
    w_fagr.row([aid, pcode, pprod, fshare, pshare, gratio, cof,
                dt.date(2024, 6, 1), dt.date(2026, 12, 31), 1])
    partner_agreements[(pcode, pprod)] = aid
w_fpartner.close()
w_fagr.close()

# 政策字典
w_policy = CsvWriter(out_dir("03_risk_decision") / "policy_ref.csv",
    ["policy_code", "product_code", "grade", "max_amount", "apr_min", "apr_max",
     "effective_from"])
for prod_code in ["SELF_LOAN", "PLATFORM_LOAN", "JOINT_LOAN", "GUARANTEE_LOAN"]:
    for grade, max_amt, apr_lo, apr_hi in [
        ("A", 100000, 0.10, 0.14),
        ("B", 60000,  0.14, 0.18),
        ("C", 30000,  0.18, 0.22),
        ("D", 10000,  0.22, 0.24),
        ("E",  5000,  0.24, 0.24),
    ]:
        w_policy.row([f"POL_{prod_code}_{grade}", prod_code, grade, max_amt,
                      apr_lo, apr_hi, DATE_START])
w_policy.close()

# 风控规则集
w_rules = CsvWriter(out_dir("03_risk_decision") / "rule_set.csv",
    ["rule_id", "rule_name", "rule_type", "domain", "formula",
     "is_active", "version", "effective_from", "is_test_data"])
rule_defs = [
    ("R001", "年龄准入", "HARD_REJECT", "COMPLIANCE", "age < 18 OR age > 60"),
    ("R002", "身份证黑名单", "HARD_REJECT", "ANTIFRAUD", "id_number IN blacklist"),
    ("R003", "手机号黑名单", "HARD_REJECT", "ANTIFRAUD", "phone IN blacklist"),
    ("R004", "多头申请", "SOFT_REJECT", "CREDIT", "apply_count_7d >= 5"),
    ("R005", "严重逾期历史", "HARD_REJECT", "CREDIT", "max_overdue_stage >= M3"),
    ("R006", "模型分低", "SOFT_REJECT", "CREDIT", "a_score < 500"),
    ("R007", "反欺诈拦截", "HARD_REJECT", "ANTIFRAUD", "fraud_score >= 800"),
    ("R008", "月收入不足", "SOFT_REJECT", "CREDIT", "monthly_income < 3000"),
    ("R009", "KYC 未通过", "HARD_REJECT", "COMPLIANCE", "kyc_status != PASS"),
    ("R010", "GPS 异常", "WARNING", "ANTIFRAUD", "gps_change_10min > 100km"),
]
for r in rule_defs:
    w_rules.row([*r, 1, 1, DATE_START, 1])
w_rules.close()

print(f"  ✓ products, partners, agreements, policies, rules")

# ============================================================
# 阶段 4 —— HR & 组织
# ============================================================
print("[Stage 4] Generating HR / Org...")

w_org = CsvWriter(out_dir("11_hr_iam") / "org_unit.csv",
    ["org_code", "org_name", "parent_code", "org_level", "org_type", "manager_emp_no"])
w_emp = CsvWriter(out_dir("11_hr_iam") / "employee.csv",
    ["emp_no", "name", "gender", "org_code", "position", "hire_date",
     "resign_date", "status", "email", "phone", "is_test_data"])
w_role = CsvWriter(out_dir("11_hr_iam") / "role.csv",
    ["role_code", "role_name", "description"])
w_ur = CsvWriter(out_dir("11_hr_iam") / "user_role.csv",
    ["emp_no", "role_code", "granted_at"])

# 顶层
w_org.row(["HQ", "信优消费金融总部", None, 1, "HQ", None])
depts = [
    ("D_RISK",   "风险管理部",       "HQ", 2, "DEPT"),
    ("D_FIN",    "财务部",           "HQ", 2, "DEPT"),
    ("D_SELF",   "自营信贷产品部",   "HQ", 2, "DEPT"),
    ("D_PLAT",   "平台业务产品部",   "HQ", 2, "DEPT"),
    ("D_JOINT",  "联合贷分润业务部", "HQ", 2, "DEPT"),
    ("D_MKT",    "营销部",           "HQ", 2, "DEPT"),
    ("D_OPS",    "运营部",           "HQ", 2, "DEPT"),
    ("D_TECH",   "技术部",           "HQ", 2, "DEPT"),
    ("D_DATA",   "数据部",           "HQ", 2, "DEPT"),
    ("D_HR",     "人力资源部",       "HQ", 2, "DEPT"),
    ("D_LEGAL",  "法务合规部",       "HQ", 2, "DEPT"),
    ("D_CS",     "客服中心",         "HQ", 2, "DEPT"),
]
for row in depts:
    w_org.row([*row, None])

# 6 家分公司
branches_data = [
    ("B_BJ", "华北分公司", "HQ", 2, "BRANCH"),
    ("B_SH", "华东分公司", "HQ", 2, "BRANCH"),
    ("B_SZ", "华南分公司", "HQ", 2, "BRANCH"),
    ("B_WH", "华中分公司", "HQ", 2, "BRANCH"),
    ("B_CD", "西南分公司", "HQ", 2, "BRANCH"),
    ("B_SY", "东北分公司", "HQ", 2, "BRANCH"),
]
for row in branches_data:
    w_org.row([*row, None])

# 员工
all_orgs = [d[0] for d in depts] + [b[0] for b in branches_data]
positions = ["专员", "高级专员", "主管", "经理", "高级经理", "总监", "副总", "分析师", "工程师"]
emp_no_seq = 0
for org in all_orgs:
    n_emp = rng.randint(15, 60)
    for _ in range(n_emp):
        emp_no_seq += 1
        eno = f"E{emp_no_seq:05d}"
        gender = 1 if rng.random() < 0.55 else 2
        name = faker.name_male() if gender == 1 else faker.name_female()
        pos = rng.choice(positions)
        hire = dt.date(2020 + rng.randint(0, 5), rng.randint(1, 12), rng.randint(1, 28))
        # 5% 离职
        resign = None
        status = "ACTIVE"
        if rng.random() < 0.05:
            resign = hire + dt.timedelta(days=rng.randint(180, 1500))
            if resign < TODAY:
                status = "RESIGNED"
            else:
                resign = None
        email = f"{eno.lower()}@simcf.com"
        phone = gen_phone(rng)
        w_emp.row([eno, name, gender, org, pos, hire, resign, status,
                   email, phone, 1])

# 角色
roles_data = [
    ("R_ADMIN", "系统管理员", "全权限"),
    ("R_RISK_MGR", "风险经理", "风控决策"),
    ("R_COLL", "催收员", "催收操作"),
    ("R_CS", "客服", "工单处理"),
    ("R_FIN", "财务", "凭证与结算"),
    ("R_DATA", "数据分析师", "查询数仓"),
    ("R_PRODUCT", "产品经理", "产品配置"),
]
for r in roles_data:
    w_role.row(list(r))

# 每个员工至少一个角色
for eid in range(1, emp_no_seq + 1):
    eno = f"E{eid:05d}"
    rc = rng.choice([r[0] for r in roles_data])
    w_ur.row([eno, rc, dt.datetime(2024, 1, 1)])

for w in (w_org, w_emp, w_role, w_ur):
    w.close()
print(f"  ✓ orgs {w_org.count}, employees {w_emp.count}")

# 催收员（约 30 个，专门从员工里挑）
w_collector = CsvWriter(out_dir("05_collection") / "collector.csv",
    ["emp_no", "name", "team", "branch_code", "hire_date", "is_active", "is_test_data"])
collector_pool = []
for i in range(1, 31):
    eno = f"E{i:05d}"
    team = rng.choice(["M1", "M2", "M3", "M3+"])
    bc = rng.choice([b[0] for b in branches_data])
    w_collector.row([eno, faker.name(), team, bc, dt.date(2023, rng.randint(1, 12), rng.randint(1, 28)), 1, 1])
    collector_pool.append(eno)
w_collector.close()


# ============================================================
# 阶段 5 —— 主流程：进件 → 决策 → 授信 → 支用 → 还款/逾期 → 催收 → 财务 → 分润 → 归因
# ============================================================
print(f"[Stage 5] Generating {N_APPLICATIONS} applications flow...")

w_app = CsvWriter(out_dir("02_loan_intake") / "application.csv",
    ["application_id", "customer_id", "product_code", "apply_amount", "apply_term",
     "channel_code", "campaign_id", "apply_purpose", "status", "reject_code",
     "apply_time", "decision_time", "is_test_data"])
w_app_log = CsvWriter(out_dir("02_loan_intake") / "application_status_log.csv",
    ["application_id", "from_status", "to_status", "remark", "changed_at",
     "changed_by", "is_test_data"])
w_doc = CsvWriter(out_dir("02_loan_intake") / "doc_upload.csv",
    ["application_id", "doc_type", "doc_url", "uploaded_at", "verify_result",
     "is_test_data"])
w_cr = CsvWriter(out_dir("02_loan_intake") / "credit_report_pull.csv",
    ["application_id", "customer_id", "bureau", "pull_time", "score",
     "overdue_count", "query_count_1m", "is_test_data"])

w_decision = CsvWriter(out_dir("03_risk_decision") / "decision_log.csv",
    ["application_id", "customer_id", "decision", "reject_reasons",
     "approve_amount", "approve_apr", "approve_term", "decided_at",
     "decision_ver", "is_test_data"])
w_score = CsvWriter(out_dir("03_risk_decision") / "model_score.csv",
    ["application_id", "customer_id", "model_code", "score", "grade",
     "computed_at", "is_test_data"])
w_grade = CsvWriter(out_dir("03_risk_decision") / "risk_grade.csv",
    ["customer_id", "grade", "valid_from", "valid_to", "computed_by",
     "is_test_data"])
w_bl = CsvWriter(out_dir("03_risk_decision") / "blacklist.csv",
    ["hit_type", "hit_value", "reason_code", "source", "listed_at",
     "expire_at", "is_active", "is_test_data"])
w_af = CsvWriter(out_dir("03_risk_decision") / "antifraud_event.csv",
    ["application_id", "customer_id", "event_code", "risk_level", "detected_at",
     "action_taken", "is_test_data"])

w_limit = CsvWriter(out_dir("04_credit_core") / "credit_limit.csv",
    ["customer_id", "product_code", "total_amount", "available_amount",
     "used_amount", "apr", "grade", "valid_from", "valid_to",
     "status", "created_at", "is_test_data"])
w_loan = CsvWriter(out_dir("04_credit_core") / "loan.csv",
    ["loan_id", "application_id", "customer_id", "product_code", "limit_id",
     "principal", "term_months", "apr", "disburse_time", "first_repay_date",
     "maturity_date", "disburse_account", "status", "fund_source_code",
     "branch_code", "is_test_data"])
w_ledger = CsvWriter(out_dir("04_credit_core") / "loan_ledger.csv",
    ["loan_id", "snap_date", "outstanding_principal", "outstanding_interest",
     "overdue_days", "is_test_data"])
w_plan = CsvWriter(out_dir("04_credit_core") / "repayment_plan.csv",
    ["loan_id", "period_no", "due_date", "principal", "interest", "fee",
     "total_amount", "status", "is_test_data"])
w_actual = CsvWriter(out_dir("04_credit_core") / "repayment_actual.csv",
    ["loan_id", "period_no", "plan_id", "pay_time", "pay_amount",
     "principal_paid", "interest_paid", "fee_paid", "penalty_paid",
     "pay_channel", "is_test_data"])
w_overdue = CsvWriter(out_dir("04_credit_core") / "overdue_record.csv",
    ["loan_id", "period_no", "overdue_start_date", "overdue_end_date",
     "overdue_days", "overdue_amount", "stage", "is_test_data"])
w_contract = CsvWriter(out_dir("04_credit_core") / "contract.csv",
    ["contract_id", "loan_id", "customer_id", "contract_type", "signed_at",
     "contract_url", "is_test_data"])
w_fee = CsvWriter(out_dir("04_credit_core") / "fee_charge.csv",
    ["loan_id", "fee_type", "fee_amount", "charge_time", "is_test_data"])
w_lsl = CsvWriter(out_dir("04_credit_core") / "loan_status_log.csv",
    ["loan_id", "from_status", "to_status", "remark", "changed_at",
     "is_test_data"])

w_split = CsvWriter(out_dir("06_funding") / "loan_funding_split.csv",
    ["loan_id", "partner_code", "agreement_id", "funding_amount",
     "funding_ratio", "created_at", "is_test_data"])
w_share = CsvWriter(out_dir("06_funding") / "profit_share_record.csv",
    ["loan_id", "partner_code", "period_no", "settle_date", "partner_income",
     "self_income", "is_test_data"])
w_guar = CsvWriter(out_dir("06_funding") / "guarantee_record.csv",
    ["loan_id", "partner_code", "guarantee_amount", "guarantee_fee_rate",
     "claim_status", "claim_amount", "is_test_data"])

w_attr = CsvWriter(out_dir("08_marketing") / "attribution.csv",
    ["customer_id", "campaign_id", "channel_code", "attribute_time",
     "event_type", "weight", "is_test_data"])
w_promo_use = CsvWriter(out_dir("08_marketing") / "user_promo_use.csv",
    ["customer_id", "promo_code", "used_at", "loan_id", "is_test_data"])

# 生成 300 条黑名单
for i in range(300):
    hit_type = rng.choice(["ID", "PHONE"])
    hit_val = f"BL{i:05d}"
    w_bl.row([hit_type, hit_val, rng.choice(["FRAUD", "MULTI_OVERDUE", "EXTERNAL_BL"]),
              rng.choice(["INTERNAL", "EXTERNAL"]),
              dt.datetime(2024, rng.randint(1, 12), rng.randint(1, 28)),
              None, 1, 1])

# ---------- 主循环：申请 -> 决策 -> 授信 -> 支用 ----------

# 客户可能有多次申请，按注册时间选客户
approved_by_customer = defaultdict(list)  # cid -> [approved_credit_dict]
apply_seq_by_day = defaultdict(int)  # day -> seq
loan_seq_by_day = defaultdict(int)

# 抽样：60% 客户会申请 1 次，25% 申请 2 次，5% 申请 3+ 次
# 目标总申请数 = N_APPLICATIONS
apply_plan = []  # list of (customer, apply_day_offset_range)
for c in customers:
    r = rng.random()
    if r < 0.10:
        n_apps = 0
    elif r < 0.45:
        n_apps = 1
    elif r < 0.80:
        n_apps = 2
    else:
        n_apps = rng.randint(3, 6)
    for _ in range(n_apps):
        apply_plan.append(c)

rng.shuffle(apply_plan)
apply_plan = apply_plan[:N_APPLICATIONS]

loans_created = []  # list of dict, for downstream

for cust in apply_plan:
    # 申请时间：注册时间 + [0, 60] 天，且不超过 DATE_END
    days_after_reg = int(rng.triangular(0, 60, 5))
    apply_day = cust.reg_time.date() + dt.timedelta(days=days_after_reg)
    if apply_day > DATE_END:
        apply_day = DATE_END - dt.timedelta(days=rng.randint(0, 30))
    if apply_day < cust.reg_time.date():
        apply_day = cust.reg_time.date()
    apply_time = dt_at(apply_day, rng)
    if apply_time < cust.reg_time:
        apply_time = cust.reg_time + dt.timedelta(hours=rng.randint(1, 48))

    apply_seq_by_day[apply_day] += 1
    aid = application_id(apply_day, apply_seq_by_day[apply_day])

    product = choose_product(rng)
    apply_amount = D(rng.choice([1000, 2000, 5000, 8000, 10000, 15000, 20000, 30000, 50000, 80000, 100000]))
    apply_term = rng.choice([3, 6, 12, 18, 24, 36])
    # 匹配 campaign
    valid_camps = [c for c in campaigns if c[2] <= apply_day <= c[3]]
    camp_choice = rng.choice(valid_camps)[0] if valid_camps and rng.random() < 0.5 else None
    purpose = rng.choice(APPLY_PURPOSES)

    w_app_log.row([aid, None, "INIT", "创建申请", apply_time, "SYSTEM", 1])

    # 上传资料（多数会上传）
    doc_time = apply_time + dt.timedelta(minutes=rng.randint(5, 30))
    if rng.random() < 0.95:
        for dt_type in ["ID_FRONT", "ID_BACK", "FACE", "CARD"]:
            w_doc.row([aid, dt_type, f"oss://sim/kyc/{aid}/{dt_type}.jpg",
                       doc_time, "PASS", 1])
        if rng.random() < 0.5:
            w_doc.row([aid, "INCOME_PROOF", f"oss://sim/kyc/{aid}/INCOME.pdf",
                       doc_time, rng.choice(["PASS", "PENDING"]), 1])

    # 征信查询
    cr_time = apply_time + dt.timedelta(minutes=rng.randint(1, 10))
    cr_score = int(rng.gauss(650, 80))
    cr_score = max(400, min(850, cr_score))
    w_cr.row([aid, cust.cid, rng.choice(["PBOC", "BAIRONG", "TONGDUN"]),
              cr_time, cr_score, rng.randint(0, 3), rng.randint(0, 8), 1])

    # 模型评分
    score_time = cr_time + dt.timedelta(seconds=rng.randint(10, 60))
    a_score = int(rng.gauss(600 + cust.grade_hint * 30, 80))
    a_score = max(300, min(900, a_score))
    b_score = int(rng.gauss(600 + cust.grade_hint * 25, 70))
    b_score = max(300, min(900, b_score))
    fraud_score = int(rng.gauss(200, 150))
    fraud_score = max(0, min(1000, fraud_score))
    # 反欺诈事件（5%）
    if rng.random() < 0.05:
        w_af.row([aid, cust.cid,
                  rng.choice(["DEVICE_SHARE", "GPS_ABNORMAL", "BATCH_APPLY"]),
                  rng.choice(["LOW", "MID", "HIGH"]), score_time,
                  rng.choice(["BLOCK", "REVIEW", "WATCH"]), 1])
        fraud_score = max(fraud_score, rng.randint(600, 900))

    # 评分 grade
    def score_to_grade(s):
        if s >= 720: return "A"
        if s >= 660: return "B"
        if s >= 600: return "C"
        if s >= 540: return "D"
        return "E"

    grade = score_to_grade(b_score)
    w_score.row([aid, cust.cid, "A_SCORE", a_score, score_to_grade(a_score), score_time, 1])
    w_score.row([aid, cust.cid, "B_SCORE", b_score, grade, score_time, 1])
    w_score.row([aid, cust.cid, "FRAUD_SCORE", fraud_score, "N/A", score_time, 1])

    # 决策规则（目标通过率 50-58%）
    reject_reasons = []
    if not cust.kyc_pass:
        reject_reasons.append("R009")
    if fraud_score >= 780:
        reject_reasons.append("R007")
    if a_score < 550:
        reject_reasons.append("R006")
    if float(cust.monthly_income) < 3500 and rng.random() < 0.7:
        reject_reasons.append("R008")
    if grade == "C" and rng.random() < 0.10:
        reject_reasons.append("R006")
    if grade == "D" and rng.random() < 0.4:
        reject_reasons.append("R006")
    if grade == "E" and rng.random() < 0.75:
        reject_reasons.append("R006")
    if rng.random() < 0.06:
        reject_reasons.append("R004")
    if not reject_reasons and rng.random() < 0.14:
        reject_reasons.append(rng.choice(["R004", "R006", "R008"]))

    decision_time = score_time + dt.timedelta(seconds=rng.randint(30, 300))

    if reject_reasons:
        decision = "REJECT"
        approve_amount = None
        approve_apr = None
        approve_term = None
        app_status = "REJECTED"
        rej_code = reject_reasons[0]
    else:
        decision = "APPROVE"
        # 按 grade 匹配政策
        policy_lookup = {
            "A": (100000, 0.10, 0.14),
            "B": (60000, 0.14, 0.18),
            "C": (30000, 0.18, 0.22),
            "D": (10000, 0.22, 0.24),
            "E": (5000, 0.24, 0.24),
        }
        max_amt, apr_lo, apr_hi = policy_lookup[grade]
        # 产品最大额度
        max_amt = min(max_amt, [p for p in PRODUCTS_DDL if p[0] == product["code"]][0][4])
        approve_amount = D(min(float(apply_amount), max_amt * rng.uniform(0.7, 1.0)))
        approve_apr = D(rng.uniform(apr_lo, apr_hi))
        approve_term = apply_term
        app_status = "APPROVED"
        rej_code = None

    w_decision.row([aid, cust.cid, decision, ",".join(reject_reasons) or None,
                    approve_amount, approve_apr, approve_term, decision_time,
                    "v1", 1])

    w_app.row([aid, cust.cid, product["code"], apply_amount, apply_term,
               cust.reg_channel, camp_choice, purpose, app_status,
               rej_code, apply_time, decision_time, 1])

    w_app_log.row([aid, "INIT", "PENDING", "进入审核", apply_time + dt.timedelta(minutes=1), "SYSTEM", 1])
    w_app_log.row([aid, "PENDING", app_status, decision, decision_time, "SYSTEM", 1])

    # 归因
    if camp_choice:
        w_attr.row([cust.cid, camp_choice, cust.reg_channel, apply_time,
                    "APPLY", 1.0, 1])

    # 客户风险等级（首次审批的时候写入）
    if cust.cid not in approved_by_customer or decision == "APPROVE":
        # 追加一条 grade（可能重复，简化处理）
        if decision == "APPROVE":
            w_grade.row([cust.cid, grade, apply_day, None, "B_SCORE", 1])

    if decision != "APPROVE":
        continue

    # ---------- 生成授信额度 ----------
    limit_id_val = None  # LOAD 后由 autoincrement 补，此处占位
    valid_to = min(apply_day + dt.timedelta(days=365), dt.date(2027, 12, 31))
    w_limit.row([cust.cid, product["code"], approve_amount, approve_amount,
                 0, approve_apr, grade, apply_day, valid_to,
                 "ACTIVE", decision_time, 1])

    # 保存 approved 用于后续支用
    approved_by_customer[cust.cid].append({
        "aid": aid,
        "product": product,
        "approve_amount": approve_amount,
        "approve_apr": approve_apr,
        "approve_term": approve_term,
        "decision_time": decision_time,
        "grade": grade,
    })

# ---------- 生成支用（放款）—— 按 approved 客户 60% 支用 ----------
loans_records = []  # 供后续还款/催收使用
for cid, approvals in approved_by_customer.items():
    cust = next(c for c in customers if c.cid == cid)
    for appr in approvals:
        # 支用率约 85%
        if rng.random() > 0.85:
            continue
        # 支用时间：审批后 [0,30] 天，严格晚于决策时间
        offset = int(rng.triangular(0, 30, 3))
        disburse_day = appr["decision_time"].date() + dt.timedelta(days=offset)
        if disburse_day > DATE_END:
            continue

        loan_seq_by_day[disburse_day] += 1
        lid = loan_id(disburse_day, loan_seq_by_day[disburse_day])
        disburse_time = dt_at(disburse_day, rng)
        # 保证 disburse_time 严格晚于 decision_time
        if disburse_time <= appr["decision_time"]:
            disburse_time = appr["decision_time"] + dt.timedelta(minutes=rng.randint(10, 240))

        # 首笔一般全额支用；后续可能部分支用
        principal = appr["approve_amount"]
        if rng.random() < 0.2:
            principal = D(float(principal) * rng.uniform(0.4, 0.95))

        term = appr["approve_term"] or rng.choice([6, 12, 18, 24])
        apr = appr["approve_apr"]
        first_repay = disburse_day + dt.timedelta(days=30)
        maturity = disburse_day + dt.timedelta(days=30 * term)

        branch = rng.choice(branches_data)[0]
        # 资金来源
        product_code = appr["product"]["code"]
        candidates = [p for p in FUNDING_PARTNERS if p[3] == product_code]
        if not candidates:
            candidates = FUNDING_PARTNERS
        fund_partner = candidates[0][0]

        w_loan.row([lid, appr["aid"], cid, product_code, None,
                    principal, term, apr, disburse_time, first_repay,
                    maturity, gen_bank_card(rng), "NORMAL", fund_partner,
                    branch, 1])

        # 合同
        w_contract.row([contract_id(lid), lid, cid, "LOAN",
                        disburse_time - dt.timedelta(minutes=5),
                        f"oss://sim/contract/{lid}.pdf", 1])

        # 服务费
        fee_rate = [p for p in PRODUCTS_DDL if p[0] == product_code][0][7]
        if float(fee_rate) > 0:
            w_fee.row([lid, "SERVICE_FEE", D(float(principal) * float(fee_rate)),
                       disburse_time, 1])

        # loan_status_log
        w_lsl.row([lid, None, "NORMAL", "放款成功", disburse_time, 1])

        # 归因（LOAN）
        w_attr.row([cid, None, cust.reg_channel, disburse_time, "LOAN", 1.0, 1])

        # 资金拆分
        aid_agr = partner_agreements.get((fund_partner, product_code))
        fpartner_info = next(p for p in FUNDING_PARTNERS if p[0] == fund_partner)
        f_share = float(fpartner_info[4])
        p_share = float(fpartner_info[5])
        gratio = float(fpartner_info[6])
        if product_code == "SELF_LOAN":
            # 100% 自有资金
            f_share_actual = 0.0
            partner_fund_amt = 0.0
        else:
            f_share_actual = f_share
            partner_fund_amt = float(principal) * f_share

        if partner_fund_amt > 0:
            w_split.row([lid, fund_partner, aid_agr, D(partner_fund_amt), f_share_actual,
                         disburse_time, 1])

        if product_code == "GUARANTEE_LOAN":
            w_guar.row([lid, fund_partner, principal, 0.03, "NORMAL", 0, 1])

        # 使用优惠码（20%）
        if rng.random() < 0.2:
            pcode = rng.choice([f"PROMO{i+1:03d}" for i in range(15)])
            w_promo_use.row([cid, pcode, disburse_time, lid, 1])

        loans_records.append({
            "lid": lid, "cid": cid, "product": product_code,
            "principal": float(principal), "term": term, "apr": float(apr),
            "disburse_day": disburse_day, "disburse_time": disburse_time,
            "first_repay": first_repay, "maturity": maturity,
            "grade": appr["grade"], "fund_partner": fund_partner,
            "profit_share": p_share, "branch": branch,
        })

for w in (w_app, w_app_log, w_doc, w_cr, w_decision, w_score, w_grade,
          w_bl, w_af, w_limit, w_loan, w_contract,
          w_split, w_attr, w_promo_use):
    w.close()
# w_fee / w_lsl 还要在 stage 6 用，延后关闭

print(f"  ✓ applications {w_app.count}, decisions {w_decision.count}, loans {w_loan.count}")
n_loans = w_loan.count
approve_rate = w_loan.count / max(w_app.count, 1)
print(f"  approve→loan ratio ~{approve_rate*100:.1f}%")


# ============================================================
# 阶段 6 —— 还款计划、还款流水、逾期、催收
# ============================================================
print(f"[Stage 6] Generating repayment plans and actuals for {n_loans} loans...")

# 等额本息：每期本息 = P * r / (1 - (1+r)^-n)
def eq_installment(P, apr, n):
    r = apr / 12.0
    if r == 0:
        return P / n
    return P * r / (1 - (1 + r) ** (-n))

overdue_case_seq = 0
open_cases = []  # for collection

for loan in loans_records:
    lid = loan["lid"]
    P = loan["principal"]
    apr = loan["apr"]
    n = loan["term"]

    payment = eq_installment(P, apr, n)
    remaining_principal = P

    # 决定该笔贷款的"命运"：正常还完 / M1 逾期后追回 / 直到 M3+ 变坏账
    # 3–5% M1，1–1.5% M3
    fate_rng = rng.random()
    grade_penalty = {"A": 0, "B": 0.005, "C": 0.02, "D": 0.05, "E": 0.09}.get(loan["grade"], 0)
    m1_prob = 0.035 + grade_penalty
    m3_prob = 0.012 + grade_penalty * 0.6

    if fate_rng < m3_prob:
        fate = "M3_BAD"  # 严重逾期 → 坏账，从早期就开始逾期
        overdue_from_period = 1 if rng.random() < 0.5 else rng.randint(1, min(n, 3))
    elif fate_rng < m3_prob + m1_prob:
        fate = "M1_RECOVER"  # M1 逾期后追回
        overdue_from_period = rng.randint(2, min(n, 8))
    elif fate_rng < 0.05 + m3_prob + m1_prob:
        fate = "EARLY_CLEAR"  # 提前结清
        overdue_from_period = None
    else:
        fate = "NORMAL"
        overdue_from_period = None

    plan_ids = []  # loan 内 period_no 序号
    plans_rows = []
    for period in range(1, n + 1):
        due_date = loan["first_repay"] + dt.timedelta(days=30 * (period - 1))
        interest = remaining_principal * apr / 12.0
        principal_part = payment - interest
        # 最后一期做尾差修正
        if period == n:
            principal_part = remaining_principal
            payment_this = interest + principal_part
        else:
            payment_this = payment
        remaining_principal -= principal_part
        plan_status = "PENDING"
        plans_rows.append({
            "period": period,
            "due_date": due_date,
            "principal": D(principal_part),
            "interest": D(interest),
            "total": D(payment_this),
        })
        w_plan.row([lid, period, due_date, D(principal_part), D(interest),
                    0, D(payment_this), plan_status, 1])

    # 实际还款
    if fate == "EARLY_CLEAR":
        # 假设在第 (n/3 - n/2) 期一次结清
        clear_period = rng.randint(max(1, n // 3), max(2, n // 2))
        for i, p in enumerate(plans_rows):
            if p["due_date"] > DATE_END:
                break
            if i + 1 < clear_period:
                pay_time = dt.datetime.combine(p["due_date"], dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                w_actual.row([lid, p["period"], None, pay_time, p["total"],
                              p["principal"], p["interest"], 0, 0,
                              rng.choice(["AUTO", "MANUAL"]), 1])
            elif i + 1 == clear_period:
                # 一次结清剩余本金
                remaining = float(sum(pp["principal"] for pp in plans_rows[i:]))
                pay_time = dt.datetime.combine(p["due_date"] - dt.timedelta(days=rng.randint(1, 10)),
                                                 dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                if pay_time.date() <= DATE_END:
                    w_actual.row([lid, p["period"], None, pay_time, D(remaining + float(p["interest"])),
                                  D(remaining), p["interest"], 0, 0, "MANUAL", 1])
                    w_lsl.row([lid, "NORMAL", "SETTLED", "提前结清", pay_time, 1])
                    w_fee.row([lid, "EARLY_CLEAR_FEE", D(remaining * 0.01),
                               pay_time, 1])
                break
    else:
        for i, p in enumerate(plans_rows):
            if p["due_date"] > DATE_END:
                break
            period = p["period"]
            if fate == "NORMAL" or (overdue_from_period is not None and period < overdue_from_period):
                # 按时还款（80% 前 3 天，20% 当天）
                if rng.random() < 0.8:
                    pay_time = dt.datetime.combine(p["due_date"] - dt.timedelta(days=rng.randint(1, 5)),
                                                     dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                else:
                    pay_time = dt.datetime.combine(p["due_date"], dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                w_actual.row([lid, period, None, pay_time, p["total"],
                              p["principal"], p["interest"], 0, 0,
                              rng.choice(["AUTO", "MANUAL"]), 1])
                if period == n:
                    w_lsl.row([lid, "NORMAL", "SETTLED", "按时结清", pay_time, 1])
            else:
                # 逾期开始，从 overdue_from_period 期起
                if period == overdue_from_period:
                    if fate == "M1_RECOVER":
                        # M1 追回：逾期 15-25 天后还上
                        overdue_days = rng.randint(15, 25)
                        stage = "M1"
                        pay_delay_time = dt.datetime.combine(
                            p["due_date"] + dt.timedelta(days=overdue_days),
                            dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                        if pay_delay_time.date() > DATE_END:
                            # 未追回，落入未结清
                            w_overdue.row([lid, period, p["due_date"] + dt.timedelta(days=1),
                                           None, (DATE_END - p["due_date"]).days,
                                           p["total"], stage, 1])
                            overdue_case_seq += 1
                            open_cases.append({
                                "loan": loan, "period": period,
                                "stage": stage, "amount": float(p["total"]),
                                "start": p["due_date"] + dt.timedelta(days=1),
                            })
                        else:
                            w_actual.row([lid, period, None, pay_delay_time,
                                          D(float(p["total"]) * 1.02),
                                          p["principal"], p["interest"], 0,
                                          D(float(p["total"]) * 0.02), "COLLECTION", 1])
                            w_overdue.row([lid, period,
                                           p["due_date"] + dt.timedelta(days=1),
                                           pay_delay_time.date(),
                                           (pay_delay_time.date() - p["due_date"]).days,
                                           p["total"], "M1", 1])
                            w_fee.row([lid, "PENALTY_FEE", D(float(p["total"]) * 0.02),
                                       pay_delay_time, 1])
                            overdue_case_seq += 1
                            open_cases.append({
                                "loan": loan, "period": period,
                                "stage": "M1", "amount": float(p["total"]),
                                "start": p["due_date"] + dt.timedelta(days=1),
                                "resolved_on": pay_delay_time.date(),
                            })
                        # M1 追回后，后续期数还是正常还款
                        fate = "NORMAL_AFTER_M1"
                    else:  # M3_BAD
                        # 从 overdue_from_period 起彻底不还
                        days_since_due = (DATE_END - p["due_date"]).days
                        if days_since_due >= 90:
                            stage = "M3+"
                        elif days_since_due >= 60:
                            stage = "M3"
                        elif days_since_due >= 30:
                            stage = "M2"
                        elif days_since_due >= 1:
                            stage = "M1"
                        else:
                            stage = "M0"
                        w_overdue.row([lid, period,
                                       p["due_date"] + dt.timedelta(days=1),
                                       None, days_since_due, p["total"], stage, 1])
                        w_lsl.row([lid, "NORMAL", "OVERDUE", "逾期",
                                   dt.datetime.combine(p["due_date"] + dt.timedelta(days=1), dt.time(9, 0)), 1])
                        overdue_case_seq += 1
                        open_cases.append({
                            "loan": loan, "period": period,
                            "stage": stage, "amount": float(p["total"]),
                            "start": p["due_date"] + dt.timedelta(days=1),
                        })
                        if stage in ("M3", "M3+"):
                            w_lsl.row([lid, "OVERDUE", "BAD_DEBT", "转坏账",
                                       dt.datetime.combine(DATE_END, dt.time(18, 0)), 1])
                        break
                elif fate == "NORMAL_AFTER_M1":
                    # 追回后按时还
                    if rng.random() < 0.8:
                        pay_time = dt.datetime.combine(p["due_date"] - dt.timedelta(days=rng.randint(1, 5)),
                                                         dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                    else:
                        pay_time = dt.datetime.combine(p["due_date"], dt.time(rng.randint(9, 20), rng.randint(0, 59)))
                    if pay_time.date() <= DATE_END:
                        w_actual.row([lid, period, None, pay_time, p["total"],
                                      p["principal"], p["interest"], 0, 0, "AUTO", 1])

# 循环结束
for w in (w_plan, w_actual, w_overdue):
    pass  # 已在循环中写
for w in (w_plan, w_actual, w_overdue, w_lsl, w_fee):
    w.close()

print(f"  ✓ repayment_plans {w_plan.count}, actuals {w_actual.count}, overdues {w_overdue.count}")


# ============================================================
# 阶段 7 —— 催收案件
# ============================================================
print("[Stage 7] Generating collection cases...")

w_case = CsvWriter(out_dir("05_collection") / "collection_case.csv",
    ["loan_id", "customer_id", "open_date", "close_date", "stage_entered",
     "priority", "outstanding_amount", "status", "assignee", "is_test_data"])
w_action = CsvWriter(out_dir("05_collection") / "collection_action.csv",
    ["case_id", "action_type", "action_time", "talk_result", "remark",
     "is_test_data"])
w_ptp = CsvWriter(out_dir("05_collection") / "promise_to_pay.csv",
    ["case_id", "promised_at", "promise_date", "promise_amount", "fulfilled",
     "is_test_data"])

# 每个逾期都开一个案件
case_seq = 0
for case in open_cases:
    case_seq += 1
    l = case["loan"]
    resolved = case.get("resolved_on")
    if resolved:
        status = "CLOSED_PAID"
        close_date = resolved
    elif case["stage"] in ("M3", "M3+"):
        status = "CLOSED_BAD"
        close_date = DATE_END
    else:
        status = "OPEN"
        close_date = None
    priority = 1 if case["stage"] in ("M3", "M3+") else (2 if case["stage"] == "M2" else 3)
    assignee = rng.choice(collector_pool)

    w_case.row([l["lid"], l["cid"], case["start"], close_date,
                case["stage"], priority, D(case["amount"]),
                status, assignee, 1])
    # 催收动作
    n_actions = rng.randint(3, 12)
    d = case["start"]
    end_action = close_date or DATE_END
    for _ in range(n_actions):
        d = d + dt.timedelta(days=rng.randint(1, 5))
        if d > end_action:
            break
        act_type = rng.choices(["CALL", "SMS", "LETTER", "VISIT"],
                               weights=[0.6, 0.25, 0.10, 0.05], k=1)[0]
        talk_result = rng.choice(["PICK_UP", "NO_ANSWER", "REFUSE", "PROMISE"]) if act_type == "CALL" else None
        w_action.row([case_seq, act_type,
                      dt.datetime.combine(d, dt.time(rng.randint(9, 20), rng.randint(0, 59))),
                      talk_result, faker.sentence(), 1])
        if talk_result == "PROMISE" and rng.random() < 0.7:
            ptp_date = d + dt.timedelta(days=rng.randint(1, 7))
            w_ptp.row([case_seq, dt.datetime.combine(d, dt.time(rng.randint(9, 20), rng.randint(0, 59))),
                       ptp_date, D(case["amount"] * rng.uniform(0.3, 1.0)),
                       1 if resolved else 0, 1])

for w in (w_case, w_action, w_ptp):
    w.close()
print(f"  ✓ cases {w_case.count}, actions {w_action.count}, ptps {w_ptp.count}")


# ============================================================
# 阶段 8 —— 财务：利息收入、手续费收入、总账凭证、结算
# ============================================================
print("[Stage 8] Generating finance journals & settlements...")

w_gl_acc = CsvWriter(out_dir("07_finance") / "gl_account.csv",
    ["account_code", "account_name", "account_kind", "parent_code", "is_active"])
w_gl_j = CsvWriter(out_dir("07_finance") / "gl_journal.csv",
    ["biz_date", "account_code", "direction", "amount", "biz_ref_type",
     "biz_ref_id", "remark", "posted_at", "is_test_data"])
w_settle = CsvWriter(out_dir("07_finance") / "settlement.csv",
    ["settle_date", "settle_type", "ref_id", "amount", "from_account",
     "to_account", "channel", "status", "is_test_data"])
w_tax = CsvWriter(out_dir("07_finance") / "tax_record.csv",
    ["tax_period", "tax_kind", "tax_base", "tax_amount", "filed_at",
     "is_test_data"])
w_recon = CsvWriter(out_dir("07_finance") / "reconcile_log.csv",
    ["reconcile_date", "system_name", "diff_count", "diff_amount", "status",
     "remark", "is_test_data"])
w_fi = CsvWriter(out_dir("07_finance") / "fee_income.csv",
    ["biz_date", "loan_id", "fee_type", "amount", "is_test_data"])
w_ii = CsvWriter(out_dir("07_finance") / "interest_income.csv",
    ["biz_date", "loan_id", "amount", "is_test_data"])

# 会计科目
gl_accounts = [
    ("1001", "库存现金", "ASSET", None),
    ("1002", "银行存款", "ASSET", None),
    ("1301", "应收贷款", "ASSET", None),
    ("1302", "应收利息", "ASSET", None),
    ("2001", "应付账款", "LIABILITY", None),
    ("2011", "应付合作方分润", "LIABILITY", None),
    ("6001", "利息收入", "INCOME", None),
    ("6002", "手续费收入", "INCOME", None),
    ("5001", "资金成本", "EXPENSE", None),
    ("5002", "营销费用", "EXPENSE", None),
    ("5003", "人力成本", "EXPENSE", None),
    ("5004", "催收成本", "EXPENSE", None),
    ("5005", "坏账损失", "EXPENSE", None),
]
for row in gl_accounts:
    w_gl_acc.row([*row, 1])

# 放款凭证（借：应收贷款 / 贷：银行存款）
for loan in loans_records:
    d = loan["disburse_time"]
    lid = loan["lid"]
    P = D(loan["principal"])
    w_gl_j.row([loan["disburse_day"], "1301", "DR", P, "LOAN", lid, "放款-应收贷款",
                d, 1])
    w_gl_j.row([loan["disburse_day"], "1002", "CR", P, "LOAN", lid, "放款-银行存款",
                d, 1])
    w_settle.row([loan["disburse_day"], "DISBURSE", lid, P, "COMPANY_ACC",
                  loan["fund_partner"], "BANK", "SUCCESS", 1])

# 还款凭证（借：银行存款 / 贷：应收贷款 + 利息收入）
# 简化：按 loan 汇总每期利息记入 interest_income + gl_journal
for loan in loans_records:
    lid = loan["lid"]
    P = loan["principal"]
    apr = loan["apr"]
    n = loan["term"]
    rem = P
    for period in range(1, n + 1):
        due = loan["first_repay"] + dt.timedelta(days=30 * (period - 1))
        if due > DATE_END:
            break
        interest = rem * apr / 12.0
        principal_part = eq_installment(P, apr, n) - interest
        if period == n:
            principal_part = rem
        rem -= principal_part
        # 每期利息记账
        w_ii.row([due, lid, D(interest), 1])
        w_gl_j.row([due, "6001", "CR", D(interest), "REPAY", lid, "计提利息收入",
                    dt.datetime.combine(due, dt.time(23, 0)), 1])
        # 服务费在第 1 期
        if period == 1:
            fee_rate = [p for p in PRODUCTS_DDL if p[0] == loan["product"]][0][7]
            if float(fee_rate) > 0:
                fee_amt = D(float(P) * float(fee_rate))
                w_fi.row([due, lid, "SERVICE_FEE", fee_amt, 1])
                w_gl_j.row([due, "6002", "CR", fee_amt, "FEE", lid, "手续费收入",
                            dt.datetime.combine(due, dt.time(23, 0)), 1])

# 月度税务凭证（6 个月）
for m in range(1, 7):
    period = f"2025{m:02d}"
    filed = dt.datetime(2025, m, 15)
    tax_base = D(rng.uniform(1000000, 5000000))
    w_tax.row([period, "VAT", tax_base, D(float(tax_base) * 0.06), filed, 1])
    w_tax.row([period, "INCOME_TAX", tax_base, D(float(tax_base) * 0.15), filed, 1])

# 对账日志（每日）
d = DATE_START
while d <= DATE_END:
    for sys in ["credit_core", "funding", "settlement_bank"]:
        diff_c = rng.randint(0, 3)
        diff_a = D(rng.uniform(0, 500)) if diff_c > 0 else D(0)
        w_recon.row([d, sys, diff_c, diff_a, "OK" if diff_c == 0 else "DIFF",
                     None, 1])
    d += dt.timedelta(days=1)

for w in (w_gl_acc, w_gl_j, w_settle, w_tax, w_recon, w_fi, w_ii):
    w.close()
print(f"  ✓ gl_journals {w_gl_j.count}, interest_income {w_ii.count}")


# ============================================================
# 阶段 9 —— 合作方分润 & 月度结算
# ============================================================
print("[Stage 9] Generating profit share & partner settlements...")

w_settle_p = CsvWriter(out_dir("06_funding") / "partner_settle.csv",
    ["partner_code", "settle_period", "total_income", "total_cost",
     "net_settle_amount", "status", "settled_at", "is_test_data"])

# 每 loan 每 period 生成分润
for loan in loans_records:
    lid = loan["lid"]
    partner = loan["fund_partner"]
    p_share = loan["profit_share"]
    if loan["product"] == "SELF_LOAN" or p_share == 0:
        continue
    P = loan["principal"]
    apr = loan["apr"]
    n = loan["term"]
    rem = P
    for period in range(1, n + 1):
        due = loan["first_repay"] + dt.timedelta(days=30 * (period - 1))
        if due > DATE_END:
            break
        interest = rem * apr / 12.0
        rem -= eq_installment(P, apr, n) - interest
        partner_inc = D(interest * p_share)
        self_inc = D(interest * (1 - p_share))
        w_share.row([lid, partner, period, due, partner_inc, self_inc, 1])
w_share.close()

# 月度合作方结算汇总
for pcode in [p[0] for p in FUNDING_PARTNERS]:
    for m in range(1, 7):
        period = f"2025{m:02d}"
        tot_inc = D(rng.uniform(50000, 500000))
        tot_cost = D(float(tot_inc) * rng.uniform(0.4, 0.7))
        w_settle_p.row([pcode, period, tot_inc, tot_cost,
                        D(float(tot_inc) - float(tot_cost)),
                        "PAID", dt.datetime(2025, m, 25), 1])
w_settle_p.close()

print(f"  ✓ profit_share {w_share.count}, partner_settle {w_settle_p.count}")


# ============================================================
# 阶段 10 —— 客服工单、通话、投诉
# ============================================================
print("[Stage 10] Generating customer service tickets...")

w_ticket = CsvWriter(out_dir("10_csm") / "ticket.csv",
    ["ticket_id", "customer_id", "channel", "category", "subject", "priority",
     "status", "created_at", "closed_at", "handler", "is_test_data"])
w_call = CsvWriter(out_dir("10_csm") / "call_record.csv",
    ["ticket_id", "customer_id", "direction", "call_time", "duration_sec",
     "csat_score", "is_test_data"])
w_cplt = CsvWriter(out_dir("10_csm") / "complaint.csv",
    ["ticket_id", "customer_id", "reason_code", "escalated", "reported_regulator",
     "filed_at", "resolved_at", "is_test_data"])
w_tact = CsvWriter(out_dir("10_csm") / "ticket_action.csv",
    ["ticket_id", "action", "remark", "acted_at", "actor", "is_test_data"])

n_tickets = int(N_CUSTOMERS * 0.15)  # 15% 客户开过工单
ticket_seq = 0
for _ in range(n_tickets):
    ticket_seq += 1
    tid = f"TK{ticket_seq:06d}"
    cust = rng.choice(customers)
    if cust.reg_time.date() > DATE_END - dt.timedelta(days=5):
        continue
    created = dt_at(weighted_date(rng, cust.reg_time.date(), DATE_END), rng)
    if created < cust.reg_time:
        continue
    category = rng.choices(["咨询", "投诉", "催收异议", "资料", "其他"],
                            weights=[0.5, 0.15, 0.1, 0.15, 0.1], k=1)[0]
    channel = rng.choice(["PHONE", "APP", "EMAIL", "WECHAT"])
    priority = 1 if category == "投诉" else (2 if category == "催收异议" else 3)
    subject_map = {
        "咨询": ["如何提额", "利率咨询", "还款方式", "提前结清"],
        "投诉": ["利率过高", "服务态度", "隐私泄露"],
        "催收异议": ["催收电话过多", "误催"],
        "资料": ["身份证过期", "补充证明"],
        "其他": ["其他问题"],
    }
    subject = rng.choice(subject_map[category])
    handler = f"E{rng.randint(1, emp_no_seq):05d}"
    closed_at = None
    status = "OPEN"
    if rng.random() < 0.85:
        status = "CLOSED"
        closed_at = created + dt.timedelta(hours=rng.randint(1, 72))
    w_ticket.row([tid, cust.cid, channel, category, subject, priority, status,
                  created, closed_at, handler, 1])
    if channel == "PHONE" and rng.random() < 0.9:
        w_call.row([tid, cust.cid, "IN", created, rng.randint(60, 1200),
                    rng.randint(3, 5), 1])
    if category == "投诉":
        w_cplt.row([tid, cust.cid,
                    rng.choice(["RATE_HIGH", "COLLECTION", "SERVICE", "PRIVACY"]),
                    1 if rng.random() < 0.1 else 0,
                    1 if rng.random() < 0.02 else 0,
                    created, closed_at, 1])
    w_tact.row([tid, "创建", "工单创建", created, handler, 1])
    if closed_at:
        w_tact.row([tid, "关闭", "问题已解决", closed_at, handler, 1])

for w in (w_ticket, w_call, w_cplt, w_tact):
    w.close()
print(f"  ✓ tickets {w_ticket.count}, calls {w_call.count}, complaints {w_cplt.count}")


# ============================================================
# 阶段 11 —— 埋点事件
# ============================================================
print(f"[Stage 11] Generating ~{N_EVENTS} events...")

w_event = CsvWriter(out_dir("09_events") / "app_event.csv",
    ["customer_id", "device_id", "event_name", "event_time", "platform",
     "app_version", "channel_code", "campaign_id", "props_json", "is_test_data"])
w_pv = CsvWriter(out_dir("09_events") / "page_view.csv",
    ["customer_id", "device_id", "page_path", "referrer", "view_time",
     "duration_ms", "platform", "is_test_data"])
w_click = CsvWriter(out_dir("09_events") / "click_stream.csv",
    ["customer_id", "device_id", "element_id", "element_text", "page_path",
     "click_time", "is_test_data"])

PAGES = ["/home", "/apply", "/product/list", "/product/detail", "/loan/repay",
         "/loan/history", "/profile", "/kyc", "/promo/list", "/help"]
CLICK_ELEMS = ["btn_apply", "btn_repay", "btn_login", "banner_promo",
               "link_help", "tab_home", "tab_product", "btn_confirm"]
EVENT_NAMES = ["app_open", "reg", "kyc_start", "kyc_pass", "apply_submit",
               "apply_approved", "apply_rejected", "loan_success",
               "repay_success", "repay_fail", "page_view", "click"]

# 使用客户样本 + 抽样事件生成
# 每个活跃客户 ~ 30 个事件
device_map = {c.cid: f"D{i:08d}" for i, c in enumerate(customers, 1)}
target_events = N_EVENTS
event_count = 0
for c in customers:
    if event_count >= target_events:
        break
    n = rng.randint(5, 80)
    for _ in range(n):
        if event_count >= target_events:
            break
        # 事件时间在 [reg_time, DATE_END]
        max_days = (DATE_END - c.reg_time.date()).days
        if max_days <= 0:
            continue
        offset = int(rng.triangular(0, max_days, 5))
        d = c.reg_time.date() + dt.timedelta(days=offset)
        t = dt_at(d, rng)
        if t < c.reg_time:
            t = c.reg_time + dt.timedelta(minutes=rng.randint(1, 60))
        platform = rng.choices(["iOS", "Android", "H5", "WeApp"],
                               weights=[0.35, 0.45, 0.10, 0.10], k=1)[0]
        version = rng.choice(["4.1.2", "4.2.0", "4.3.0", "4.3.1"])
        evname = rng.choices(EVENT_NAMES,
                             weights=[0.2, 0.02, 0.05, 0.04, 0.1, 0.08, 0.03,
                                      0.05, 0.08, 0.02, 0.20, 0.13], k=1)[0]
        page = rng.choice(PAGES)
        w_event.row([c.cid, device_map[c.cid], evname, t, platform, version,
                     c.reg_channel, None,
                     json.dumps({"page": page, "src": c.reg_channel}, ensure_ascii=False),
                     1])
        if evname == "page_view":
            w_pv.row([c.cid, device_map[c.cid], page, rng.choice(PAGES) if rng.random() < 0.5 else None,
                      t, rng.randint(500, 30000), platform, 1])
        if evname == "click":
            w_click.row([c.cid, device_map[c.cid], rng.choice(CLICK_ELEMS),
                         rng.choice(["点我", "确认", "取消"]),
                         page, t, 1])
        event_count += 1

for w in (w_event, w_pv, w_click):
    w.close()
print(f"  ✓ events {w_event.count}, pageviews {w_pv.count}, clicks {w_click.count}")


# ============================================================
# 阶段 12 —— 数据平台元数据 (只放一个占位，Task 03 补充)
# ============================================================
print("[Stage 12] Generating dp_meta (placeholder)...")

w_meta = CsvWriter(out_dir("12_dp_meta") / "table_meta.csv",
    ["database_name", "table_name", "table_comment", "business_domain",
     "owner_emp_no", "is_dw", "layer", "created_at"])
for db in CONFIG["databases"]:
    if db["name"] == "sim_dw":
        continue
    for t in db["tables"]:
        w_meta.row([db["name"], t, f"{db['system']}-{t}", db["domain"],
                    f"E{rng.randint(1, emp_no_seq):05d}", 0, None,
                    dt.datetime(2024, 12, 1)])
w_meta.close()

w_job = CsvWriter(out_dir("12_dp_meta") / "etl_job.csv",
    ["job_id", "job_name", "source_db", "source_table", "target_db",
     "target_table", "cron_expr", "owner_emp_no", "is_active", "created_at"])
w_lineage = CsvWriter(out_dir("12_dp_meta") / "data_lineage.csv",
    ["upstream_db", "upstream_table", "downstream_db", "downstream_table",
     "job_id", "created_at"])
w_job.close()
w_lineage.close()

print("\n=== Generation done ===")
print(f"Customers  : {N_CUSTOMERS}")
print(f"Applications: {w_app.count}")
print(f"Loans      : {n_loans}")
print(f"Events     : {w_event.count}")
