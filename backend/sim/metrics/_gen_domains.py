"""生成 6 领域 + 6 部门指标文档。"""
from __future__ import annotations
from pathlib import Path
import yaml
from collections import defaultdict

BASE = Path(__file__).resolve().parent
DOMAINS = [
    ("user", "用户域", "关注 DAU、MAU、新客数、留存"),
    ("credit", "信贷域", "关注申请、通过、放款、支用、余额"),
    ("finance", "财务域", "关注收入、成本、利润、税务"),
    ("risk", "风险域", "关注逾期率、Vintage、反欺诈"),
    ("marketing", "营销域", "关注 CPA、ROI、渠道、活动"),
    ("operation", "经营管理域", "关注员工产能、客服、分公司"),
    ("funding", "资金/合作方域", "关注合作方、分润、担保"),
    ("compliance", "合规域", "关注投诉、监管报送、数据质量"),
]

DEPARTMENTS = [
    ("风险管理部", "risk_mgmt", "risk"),
    ("财务部", "finance", "finance"),
    ("自营信贷产品部", "self_credit_product", "credit"),
    ("平台业务产品部", "platform_product", "credit"),
    ("联合贷分润业务部", "profit_share_product", "funding"),
    ("营销部", "marketing", "marketing"),
]

metrics = yaml.safe_load((BASE / "catalog" / "metrics.yaml").read_text())["metrics"]

# 按 domain 分组
by_domain = defaultdict(list)
by_dept = defaultdict(list)
for m in metrics:
    by_domain[m["domain"]].append(m)
    by_dept[m["department"]].append(m)


def gen_domain_md(dom_code, dom_zh, desc, mlist):
    lines = [f"# {dom_zh} 指标\n\n",
             f"> {desc}\n\n",
             f"共 **{len(mlist)}** 个指标。\n\n"]
    # 按 level 分组
    for lvl in ["一级", "二级", "三级"]:
        sublist = [m for m in mlist if m["level"] == lvl]
        if not sublist:
            continue
        lines.append(f"## {lvl}指标（{len(sublist)} 个）\n\n")
        lines.append("| ID | 中文 | 英文 | 定义 | 责任部门 |\n|---|---|---|---|---|\n")
        for m in sublist:
            lines.append(f"| {m['id']} | {m['name_zh']} | `{m['name_en']}` | {m['definition']} | {m['department']} |\n")
        lines.append("\n")
    lines.append("\n## 完整定义\n\n参见 `../catalog/metrics.yaml`。\n")
    return "".join(lines)


def gen_dept_md(dept_zh, dept_slug, primary_dom, mlist):
    lines = [f"# {dept_zh} 指标看板\n\n",
             f"> 本部门主要关注 **{primary_dom}** 域指标，同时使用其他部门的关键指标做交叉分析。\n\n",
             f"负责的指标共 **{len(mlist)}** 个。\n\n"]
    # 按 domain 分组
    by_d = defaultdict(list)
    for m in mlist:
        by_d[m["domain"]].append(m)
    for dom, dl in by_d.items():
        lines.append(f"## {dom} 域指标（{len(dl)} 个）\n\n")
        lines.append("| ID | 中文 | 分级 | 定义 |\n|---|---|---|---|\n")
        for m in dl:
            lines.append(f"| {m['id']} | {m['name_zh']} | {m['level']} | {m['definition'][:60]} |\n")
        lines.append("\n")
    lines.append("\n## 引用的其他部门指标\n\n本部门在日常分析中会引用以下指标：\n- 客户 DAU/MAU (运营部)\n- 财务收入 (财务部)\n- 各产品放款 (信贷产品部)\n\n完整定义见 `../catalog/metrics.yaml`。\n")
    return "".join(lines)


# 领域文档
for dom_code, dom_zh, desc in DOMAINS:
    dl = by_domain.get(dom_code, [])
    out = BASE / "domains" / f"{dom_code}_domain.md"
    out.write_text(gen_domain_md(dom_code, dom_zh, desc, dl))
    print(f"  ✓ {out.name}: {len(dl)} 指标")

# 部门文档
for dept_zh, slug, primary_dom in DEPARTMENTS:
    dl = by_dept.get(dept_zh, [])
    out = BASE / "domains" / "departments" / f"{slug}.md"
    out.write_text(gen_dept_md(dept_zh, slug, primary_dom, dl))
    print(f"  ✓ departments/{out.name}: {len(dl)} 指标")

# metrics/README.md
readme = BASE / "README.md"
readme.write_text(f"""# 信优消费金融 指标体系

## 总览

- 指标总数：**{len(metrics)}**
- 领域：{len(DOMAINS)} 个（用户/信贷/财务/风险/营销/经营管理/资金/合规）
- 分级：一级 40 / 二级 70 / 三级 90

## 目录

```
metrics/
├── governance/              治理办法
│   ├── 01_管理办法.md
│   ├── 02_命名规范.md
│   ├── 03_口径管理.md
│   └── 04_分级分类.md
├── catalog/                 指标目录（本体数据字典）
│   ├── metrics.yaml         结构化（Data Agent 消费）
│   └── metrics.md           可读版
└── domains/                 分领域 + 分部门
    ├── user_domain.md
    ├── credit_domain.md
    ├── finance_domain.md
    ├── risk_domain.md
    ├── marketing_domain.md
    ├── operation_domain.md
    ├── funding_domain.md
    ├── compliance_domain.md
    └── departments/
        ├── risk_mgmt.md
        ├── finance.md
        ├── self_credit_product.md
        ├── platform_product.md
        ├── profit_share_product.md
        └── marketing.md
```

## 快速验证一个指标

```bash
mysql -u root sim_dw -e "
  SELECT stat_date, COUNT(DISTINCT customer_id) AS dau
  FROM dws_customer_active_day
  WHERE stat_date = '2025-06-15'
  GROUP BY stat_date"
```

## 本体化设计

- `metrics.yaml` 每个条目就是一个本体实体
- `aliases` 提供同义词表（NL2SQL 消歧关键）
- `sql_template` 是从语义到物理的映射
- `related_metrics` 建立概念间关联
- `filters` 显式化口径过滤
""")
print(f"\n  ✓ README.md")
