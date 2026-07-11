# 消费金融公司业务环境模拟 —— sim/

> 为验证本体化语义层、NL2SQL、Data Agent 而构建的仿真环境。
> 公司：**信优消费金融有限公司**（虚构）
> 时间线：`2025-01-01 ~ 2025-06-30`（"今天" = 2025-07-01）
> 所有数据均为**虚构测试数据**，业务表带 `is_test_data=1` 标记。

## 目录导航

```
sim/
├── README.md                       ← 本文件
├── config/
│   ├── mysql.md                    ← MySQL 连接说明（root, 无密码）
│   └── databases.yaml              ← 全部 13 个数据库 + 系统 + 表清单
│
├── systems/                        ← Step 1: 业务系统（12 个）
│   ├── common.py                   ← 公共工具库（ID/身份证/时序）
│   ├── seed_all.py                 ← 主线数据生成器（一次跑通全流程）
│   ├── load_all.py                 ← 把 CSV 灌进 MySQL
│   ├── 01_cust_cif/                ← 客户中心
│   │   ├── schema.sql              ← DDL
│   │   ├── README.md               ← 系统说明
│   │   └── seed_data/*.csv         ← 种子数据
│   ├── 02_loan_intake/             ← 进件受理
│   ├── 03_risk_decision/           ← 风险决策
│   ├── 04_credit_core/             ← 信贷核心
│   ├── 05_collection/              ← 催收
│   ├── 06_funding/                 ← 资金/合作方
│   ├── 07_finance/                 ← 财务
│   ├── 08_marketing/               ← 营销
│   ├── 09_events/                  ← 埋点收集
│   ├── 10_csm/                     ← 客服
│   ├── 11_hr_iam/                  ← HR & 权限
│   └── 12_dp_meta/                 ← 数据平台元数据
│
├── docs/                           ← Step 2: 系统文档（BRD/PRD/TDD/PROJECT）
│                                     （由 Task 02 生成）
│
├── dwh/                            ← Step 3: 数据仓库（Kimball 星型）
│                                     （由 Task 03 生成）
│
├── metrics/                        ← Step 4: 指标体系（本体化的核心）
│                                     （由 Task 04 生成）
│
└── verify/                         ← 验证脚本
    └── task01_evals.py             ← Task 01 evals 检查
```

## 快速验证

```bash
# 连接查看
mysql -u root -e "SHOW DATABASES LIKE 'sim_%'"

# 客户数
mysql -u root -e "SELECT COUNT(*) FROM sim_cust_cif.customer"

# 跑 evals
cd backend/sim && python3 verify/task01_evals.py
```

## 关键业务分布（实际生成结果）

| 指标 | 目标 | 实际 |
|---|---|---|
| 客户数 | 10000 | 10000 |
| 申请数 | 15k-19k | 18000 |
| 放款数 | 7.5k-8.5k | 7709 |
| 通过率 | 40-60% | 53.0% |
| 30 天支用率 | 55-90% | 87.1% |
| M1 逾期率 | 2-6% | 3.15% |
| M3 逾期率 | 0.5-2% | 0.73% |
| 埋点事件数 | 400k-600k | 426k |
| 客户年龄均值 | 31-35 | 33.0 (σ=7.4) |
| 跨库 join 命中率 | >98% | 100% |

## 产品形态与占比

| 代号 | 名称 | 类型 | 占比目标 | 实际 |
|---|---|---|---|---|
| SELF_LOAN | 信优速贷 | 自营信贷 | 40% | 40.6% |
| PLATFORM_LOAN | 信优合作贷 | 助贷平台 | 30% | 29.8% |
| JOINT_LOAN | 信优联合贷 | 联合贷分润 | 20% | 19.9% |
| GUARANTEE_LOAN | 信优保贷 | 担保业务 | 10% | 9.7% |

## 已完成任务

| Task | 内容 | Evals | 状态 |
|---|---|---|---|
| **01** 业务系统 | 12 库 65 表，120 万行数据 | 19/19 ✅ | 完成 |
| **02** 系统文档 | 48 份（BRD/PRD/TDD/PROJECT） | 6/6 ✅ | 完成 |
| **03** 数据仓库 | sim_dw 49 张表，ETL 一键跑通 | 16/16 ✅ | 完成 |
| **04** 指标体系 | 4 份治理 + 200 指标 + 8 领域 + 6 部门 | 19/19 ✅ | 完成 |

**总 evals：60/60 通过。**

| # | 库名 | 系统 | 表数 |
|---|---|---|---|
| 1 | `sim_cust_cif` | 客户中心 | 6 |
| 2 | `sim_loan_intake` | 进件受理 | 5 |
| 3 | `sim_risk_decision` | 风险决策 | 7 |
| 4 | `sim_credit_core` | 信贷核心 | 10 |
| 5 | `sim_collection` | 催收 | 4 |
| 6 | `sim_funding` | 资金/合作方 | 6 |
| 7 | `sim_finance` | 财务 | 7 |
| 8 | `sim_marketing` | 营销 | 6 |
| 9 | `sim_events` | 埋点收集 | 3 |
| 10 | `sim_csm` | 客服 | 4 |
| 11 | `sim_hr_iam` | HR & 权限 | 4 |
| 12 | `sim_dp_meta` | 元数据 | 3 |
| DW | `sim_dw` | 数据仓库 | ~50（Task 03 填） |

**总计**：65 张业务表 + 数仓，**已生成 1.2M+ 行数据**。

## 主线时序（保证跨库一致性）

```
埋点(点击广告) → 注册(customer) → 实名/KYC(kyc_result) 
  → 授信申请(application) → 风控决策(decision_log/model_score)
  → 授信额度(credit_limit) → 支用申请(loan) → 放款
  → 还款计划(repayment_plan) → 还款流水(repayment_actual) / 逾期(overdue_record)
  → 催收(collection_case) → 结清 或 坏账
每个环节：客服工单、财务凭证(gl_journal)、资金分润(profit_share)、归因(attribution)、埋点(event)
```

## 如何重新生成

```bash
cd backend/sim

# 1. 重建库结构（会清空数据）
python3 -c "
import yaml, pymysql
c = yaml.safe_load(open('config/databases.yaml'))
conn = pymysql.connect(host='127.0.0.1', user='root', autocommit=True)
cur = conn.cursor()
for db in c['databases']:
    cur.execute(f\"DROP DATABASE IF EXISTS {db['name']}\")
    cur.execute(f\"CREATE DATABASE {db['name']} CHARACTER SET utf8mb4\")
"
for f in systems/*/schema.sql; do
    db=$(basename $(dirname $f) | sed 's/^[0-9]*_/sim_/')
    mysql -u root "$db" < "$f"
done

# 2. 生成 CSV 种子数据
python3 systems/seed_all.py

# 3. 灌入 MySQL
python3 systems/load_all.py

# 4. 验证
python3 verify/task01_evals.py
```

## 相关文档

- 数据字段字典：见每个 `systems/*/schema.sql`（COMMENT 注释）
- 业务分布规则：见 `systems/seed_all.py`
- 生成日志：见 `.blueprint/reviews/`
- Blueprint plan：`../.blueprint/plan.md`
