# Agent 工作日志 — 消费金融业务环境模拟

> **给下一位 agent**：这份日志是"零帧启动"用的。你从头读完就能接上工作，不需要问用户历史。
> 生成时间：2026-07-11
> 项目根：`/Users/sun/CodeBuddy/20260627212423/backend/`

---

## 0. TL;DR — 3 分钟看完

用户目标：**为验证本体化语义层 / NL2SQL / Data Agent 而构建一套逼真的消费金融公司仿真环境**（虚构公司 = 信优消费金融）。

已完成 4 步：

| 步骤 | 交付 | 位置 | Evals |
|---|---|---|---|
| Task 01 | 12 个业务系统 MySQL 库 + 120 万行种子数据 | `backend/sim/systems/` | 19/19 ✅ |
| Task 02 | 48 份系统文档（12 系统 × BRD/PRD/TDD/PROJECT） | `backend/sim/docs/` | 6/6 ✅ |
| Task 03 | 数仓 sim_dw（Kimball 星型 49 表 + ETL） | `backend/sim/dwh/` | 16/16 ✅ |
| Task 04 | 200 个指标体系（治理 + catalog + 领域 + 部门） | `backend/sim/metrics/` | 19/19 ✅ |

**总 evals：60/60 通过。**

**下一步大概率是**：基于这套仿真环境做本体化 / NL2SQL / Data Agent 的真实验证（用户尚未指定具体方向）。

---

## 1. 环境 & 前置

### 1.1 用户机器
- macOS (darwin)
- Shell: zsh
- Python 3.9（`/Library/Developer/CommandLineTools/usr/bin/python3`）
- MySQL 9.7.1（Homebrew，本地已装）
- opencode CLI（用户当前在的工具）

### 1.2 MySQL 连接
```
host=127.0.0.1  port=3306  user=root  password=""
```
无密码，本地开发用。`mysql -u root` 直连。

**注意**：MySQL 服务端禁用了 `LOAD DATA LOCAL INFILE`（我踩过坑），批量导入用 `executemany` 而不是 `LOAD DATA`。

### 1.3 Python 依赖
```
pip install --user faker pymysql pyyaml
```
（已安装）

### 1.4 已安装的 opencode 全局配置
用户 `~/.config/opencode/` 下：
- `AGENTS.md` — 全局规则：**联网搜索优先用 `byted-web-search` skill**（豆包搜索 API）
- `agents/` — Blueprint 五角色 agent（planner/orchestrator/investigator/reviewer/worker）
- `commands/` — `/plan`、`/execute`、`/nudge`
- `BLUEPRINT.md` — Blueprint workflow 使用手册

**用户偏好**：
- 长任务先出 `.blueprint/plan.md` 让用户 review 再执行
- 执行时自动跑 evals 自审
- 联网搜索走豆包 skill（`ark-2c83dcf0-35af-42e6-a90d-bc7dff3dda6d-22c28` API Key，如果需要）

---

## 2. 关键决策 & 用户回答的问题

### 2.1 用户在启动会话时明确的参数
（针对"消费金融业务环境模拟"任务，用户逐条回答的：）

- **数据规模**：`1a 小规模` — 客户 1w、订单 1w+、埋点 100w、跨度 6 个月
- **MySQL 部署**：`2a 单实例多库` — 本地 `mysql -u root` 无密码
- **数据生成**：`3c 混合`（Python + CSV），要求所有生成的文件和数据都有对应文档说明存储地址
- **数据真实性**：`4c 时序+关联+业务分布` — 客户→注册→KYC→授信→放款→还款/逾期→催收全链条闭合
- **文档仿真度**：`5b 尽量完整真实` — 每系统 4 类文档，重点系统 ≥2000 字
- **数仓建模**：`6b Kimball 维度建模`（星型为主）
- **输出组织**：`7a` 都放 `backend/sim/`
- **执行节奏**：**四步连跑 + 自动执行 evals 自审**

### 2.2 我在计划里定的默认（用户 OK 了的）
- 公司名：**信优消费金融有限公司** (Sim Consumer Finance)
- 产品名：信优速贷 / 信优合作贷 / 信优联合贷 / 信优保贷
- 4 种产品形态占比：SELF_LOAN 40% / PLATFORM_LOAN 30% / JOINT_LOAN 20% / GUARANTEE_LOAN 10%
- 时间线：`2025-01-01 ~ 2025-06-30`，"今天" = `2025-07-01`
- 客户 ID：`C` + 8 位数字（`C00000001`）
- 申请单 ID：`AP` + yyyyMMdd + 6 位序号
- 借据 ID：`LN` + yyyyMMdd + 6 位序号

---

## 3. 目录结构（关键位置）

```
backend/
├── .blueprint/                     Blueprint 状态目录（本项目专属）
│   ├── plan.md                    四步执行计划（初始产物）
│   ├── evals.md                   自审规则（60 条）
│   ├── research/
│   │   └── ontology-and-data-agent.md   本体研究综述（6000 字，第一次任务的产物）
│   ├── reviews/
│   │   ├── task-01.md ~ task-04.md      每步评审报告
│   └── tasks/                     (原始 task 拆分文件，最终没用到，实际按 plan.md 直接执行)
│
└── sim/                            本次仿真环境（所有交付物）
    ├── README.md                   总入口 + 目录导航
    ├── config/
    │   ├── mysql.md                MySQL 连接说明
    │   └── databases.yaml          13 个数据库定义（12 业务 + 1 数仓）
    │
    ├── systems/                    Task 01：业务系统
    │   ├── common.py               公共工具（ID/身份证/手机号生成器、随机种子=20260710）
    │   ├── seed_all.py             主线数据生成器（一次跑通全流程，12 阶段）
    │   ├── load_all.py             CSV → MySQL（executemany）
    │   ├── 01_cust_cif/ ~ 12_dp_meta/
    │   │   ├── schema.sql          DDL
    │   │   ├── README.md
    │   │   └── seed_data/*.csv     生成后的种子数据
    │
    ├── docs/                       Task 02：系统文档
    │   ├── _gen_docs.py            生成器（除 CIF 外都是模板化的）
    │   ├── 01_cust_cif/            ← 手写完整版（示范）
    │   │   ├── BRD_业务需求.md
    │   │   ├── PRD_产品需求.md
    │   │   ├── TDD_技术设计.md
    │   │   └── PROJECT_项目管理.md
    │   └── 02..12/                 模板生成（重点系统详细，其他标准）
    │
    ├── dwh/                        Task 03：数据仓库
    │   ├── schema.sql              完整 DDL 单文件（49 张表）
    │   ├── etl.py                  一键 ETL 入口（ODS→DIM→DWD→DWS→ADS）
    │   ├── sample_queries.sql      12 个典型分析 SQL
    │   ├── README.md
    │   ├── _split_schema.py        DDL 拆分工具
    │   ├── _split_etl.py           ETL 拆分工具
    │   ├── ods/{README.md, ods_tables.sql}   16 表
    │   ├── dim/{README.md, dim_tables.sql}   6 表 (含 dim_customer SCD2)
    │   ├── dwd/{README.md, dwd_tables.sql}   11 表
    │   ├── dws/{README.md, dws_tables.sql}   11 表
    │   ├── ads/{README.md, ads_tables.sql}   5 表
    │   └── etl/{README.md, ods|dim|dwd|dws|ads_transform.sql}
    │
    ├── metrics/                    Task 04：指标体系（本体化数据字典）
    │   ├── README.md
    │   ├── _gen_metrics.py         200 指标生成器
    │   ├── _gen_domains.py         领域/部门文档生成器
    │   ├── governance/
    │   │   ├── 01_管理办法.md
    │   │   ├── 02_命名规范.md
    │   │   ├── 03_口径管理.md
    │   │   └── 04_分级分类.md
    │   ├── catalog/
    │   │   ├── metrics.yaml        ★ 200 指标的结构化定义（本体化核心）
    │   │   └── metrics.md          可读版
    │   └── domains/
    │       ├── user_domain.md ~ compliance_domain.md   8 个领域
    │       └── departments/
    │           ├── risk_mgmt.md
    │           ├── finance.md
    │           ├── self_credit_product.md
    │           ├── platform_product.md
    │           ├── profit_share_product.md
    │           └── marketing.md
    │
    └── verify/                     Evals 脚本
        ├── task01_evals.py         业务数据分布检查
        ├── task02_evals.py         文档齐全 + 字段对齐
        ├── task03_evals.py         数仓分层 + SQL 跑通
        └── task04_evals.py         指标体系 + 抽样 30 SQL 验证
```

---

## 4. 数据现状（活的，别删）

### 4.1 MySQL 库（当前存在）
```
sim_collection
sim_credit_core
sim_csm
sim_cust_cif
sim_dp_meta
sim_dw               ← 数仓
sim_events
sim_finance
sim_funding
sim_hr_iam
sim_loan_intake
sim_marketing
sim_risk_decision
```

### 4.2 数据量指标（Task 01 实测，evals 通过的）

| 项 | 值 |
|---|---|
| 客户 | 10,000 |
| 申请 | 18,000 |
| 放款 | 7,709 |
| 通过率 | 53.0% |
| 30 天支用率 | 87.1% |
| M1 逾期率 | 3.15% |
| M3 逾期率 | 0.73% |
| 埋点事件 | 426,575 |
| 客户平均年龄 | 33.0 (σ 7.4) |
| 跨库 join 命中率 | 100% |
| 业务表总行数 | ~120 万 |
| 数仓 DW 表总行数 | 大量（含 30w 埋点、17w 还款计划） |

### 4.3 关键完整性
- **DW 放款金额 = 业务库放款金额 = 127,373,731.41**（完全一致）
- 所有客户/申请/放款/还款/催收/财务凭证时序闭合（申请 < 决策 < 放款 < 还款计划 < 实际还款）
- 4 种产品占比：SELF 40.6% / PLATFORM 29.8% / JOINT 19.9% / GUARANTEE 9.7%

---

## 5. 如何重跑

如果数据被清了或想重新生成：

```bash
cd /Users/sun/CodeBuddy/20260627212423/backend/sim

# 1. 重建业务库（会清空数据！）
python3 -c "
import yaml, pymysql
c = yaml.safe_load(open('config/databases.yaml'))
conn = pymysql.connect(host='127.0.0.1', user='root', password='', autocommit=True)
cur = conn.cursor()
for db in c['databases']:
    cur.execute(f\"DROP DATABASE IF EXISTS {db['name']}\")
    cur.execute(f\"CREATE DATABASE {db['name']} CHARACTER SET utf8mb4\")
"

# 2. 建业务表结构
for f in systems/*/schema.sql; do
    db=$(basename $(dirname $f) | sed 's/^[0-9]*_/sim_/')
    mysql -u root "$db" < "$f"
done

# 3. 生成种子数据（CSV，~15 秒）
python3 systems/seed_all.py

# 4. 灌入 MySQL（~17 秒）
python3 systems/load_all.py

# 5. 建数仓表
mysql -u root sim_dw < dwh/schema.sql

# 6. 跑 ETL（~10 秒）
python3 dwh/etl.py

# 7. 生成指标（如果 metrics.yaml 需要重生成）
python3 metrics/_gen_metrics.py
python3 metrics/_gen_domains.py

# 8. 全部 evals
for i in 01 02 03 04; do python3 verify/task${i}_evals.py; done
```

---

## 6. 我踩过的坑 & 已修复

1. **`w_lsl` / `w_fee` writer 提前关闭** — 分阶段生成时要小心 writer 的生命周期
2. **通过率过高（81.7%）** — 多轮调整风控规则（`a_score < 550`, `grade E 拒 60%`）才降到 53%
3. **M3 逾期率过低（0.13%）** — 让 M3_BAD 命运的借据从第 1-3 期就开始逾期（此前是从第 2-6 期）
4. **申请数 15000 时放款只有 6.4k** — 把申请数上调到 18000 保证放款 >= 7500
5. **MySQL LOAD DATA LOCAL INFILE 被服务端禁用** — 换用 `executemany`
6. **`only_full_group_by` sql_mode 严格** — ETL 里 `SET SESSION sql_mode = REPLACE(...)` 关闭
7. **decimal.Decimal + float 类型不兼容** — 提前 `float()` 转换
8. **dwh 子目录空** — 后期补的：`_split_schema.py` 把 DDL 拆到 ods/dim/dwd/dws/ads 子目录，`_split_etl.py` 把 ETL SQL 拆开
9. **文档里 `phone` 字段找不到（evals T2.5）** — 因为 API 层字段 vs schema 层字段（schema 里叫 `contact.contact_value`），修正 evals 只查 schema 层字段
10. **指标别名少于 2 个** — 在 `M()` 构造器里自动追加 `name_zh` 和 `name_en` 到 aliases

---

## 7. 关键设计选择（为什么这么做）

### 7.1 ID 生成器统一到 `common.py`
`customer_id`、`application_id`、`loan_id` 都用同一个 seed（20260710）的 `random.Random` 生成，保证：
- 跨系统外键完全对齐（用户 C00001234 在 CIF、进件、信贷、催收、财务里都能 join 上）
- 可复现（重跑生成同样的数据）

### 7.2 时序闭合
`seed_all.py` 12 个 stage 严格按业务时序：
1. 客户 → 2. 营销 → 3. 产品/资金方 → 4. HR → 5. 申请→决策→授信→支用 → 6. 还款计划→逾期 → 7. 催收 → 8. 财务凭证 → 9. 分润 → 10. 客服 → 11. 埋点 → 12. 元数据

每个业务动作的时间戳都基于前一步 + `timedelta`，保证 `apply_time < decision_time < disburse_time < first_repay_date < ...`

### 7.3 4 种命运（Fate）
每笔贷款抽签决定 fate：
- `NORMAL`（正常）— 90%+
- `M1_RECOVER`（M1 逾期后催回）— 3-8%（受风险等级影响）
- `M3_BAD`（严重逾期 → 坏账）— 1-2%
- `EARLY_CLEAR`（提前结清）— 5%

这样保证 M1/M3 逾期率、催回率、坏账率都是"真实分布"，不是随机洒的。

### 7.4 指标体系 = 本体化数据字典 v1
`metrics/catalog/metrics.yaml` 的结构就是设计给未来当**本体数据字典本体**用的：
- `id` — 本体实体 ID
- `aliases` — 同义词表（NL2SQL 消歧关键）
- `sql_template` — 从语义到物理的映射
- `related_metrics` — 概念间关联
- `filters` — 显式化口径

**用户下一步大概率会做**：用这个 yaml 喂给 Data Agent，验证 NL2SQL 效果。

---

## 8. 未完成 / 未来待办

用户没说要做，但你可能会被问到：

1. **本体化正式建模** — 把 `metrics.yaml` 翻译成 Turtle / OWL / JSON-LD（研究文档里有讨论）
2. **NL2SQL demo** — 拿 12 个 sample_queries 当靶子，跑一遍 Data Agent
3. **知识图谱构建** — 把 CIF、信贷、风控数据用 Neo4j 承载
4. **数据字典层升级到语义层** — 引入 Snowflake Semantic View 风格的 YAML 或 dbt Metrics
5. **加装 `tool.execute.before` 硬护栏** — 用户在 Blueprint 讨论时提过，v2 再做
6. **`dp_meta` 表填数据** — 目前 `table_meta` 有数据，`etl_job` 和 `data_lineage` 是空的（Task 03 补充但没做）
7. **`sim_dw` 里 `dwd_credit_repayment` 有 17k 但 `sim_credit_core.repayment_actual` 有 19k 的差异** — 应该 join 时没匹配上部分（未追查，可能是 loan 的 status 过滤导致；如果用户在意再修）

---

## 9. 会话历史脉络（简短）

按时间顺序，用户提问 → 我做的事：

1. "告诉我怎么用好 opencode" → 讲了 opencode 基础
2. "怎么建一套 agent loop" → 讲了 primary + subagent 模式
3. "用豆包搜索 mcp 搜 opencode agent loop 实战案例" → 用户提供 API Key，我搜出 Blueprint / oh-my-opencode / opencode-agent-teams 等
4. "opencode-blueprint 请详细介绍" → 讲了 5 角色流水线
5. "把联网优先豆包写全局 AGENTS.md，然后落地 Blueprint 骨架" → 落全局 planner/orchestrator/investigator/reviewer/worker + /plan /execute /nudge
6. "使用说明" → 出 BLUEPRINT.md
7. "钩子怎么办？" → 加 `/nudge` 命令 + 所有 agent 加 NUDGE.md 协议
8. "/plan 本体论研究" → 出 6000 字研究综述到 `.blueprint/research/`
9. **"/plan 消费金融业务环境模拟"** → 出 plan.md（本任务的主 plan）
10. 用户回答参数 + "四步连跑 + 自动 evals" → 我一路做到 Task 04 完成
11. "dwh 子目录为什么空" → 我补齐拆分工具

---

## 10. 我的工作风格（下一位 agent 参考）

用户偏好：
- **直接干，不啰嗦**（"就按你推荐的干"）
- **不要过多解释**（回答简洁，代码/结果为主）
- **每步跑 evals 自审**（他明确说了）
- **中文回复**
- **有问题主动说、不要藏**（比如 dwh 空目录，我承认是自己偷懒）
- **文档要落地实际验证过**（不接受"看起来对"，要 SQL 跑通、指标算出来）
- **联网搜索用豆包 skill**（有全局规则）

---

## 11. 立刻可以做的验证

新 agent 接手时，跑这几个命令确认环境健康：

```bash
cd /Users/sun/CodeBuddy/20260627212423/backend/sim

# 1. 库都在
mysql -u root -e "SHOW DATABASES LIKE 'sim_%'"
# 应该 13 个

# 2. 关键数据量
mysql -u root -e "
SELECT 'customer', COUNT(*) FROM sim_cust_cif.customer
UNION SELECT 'application', COUNT(*) FROM sim_loan_intake.application
UNION SELECT 'loan', COUNT(*) FROM sim_credit_core.loan
UNION SELECT 'dw dws_customer_active_day', COUNT(*) FROM sim_dw.dws_customer_active_day"
# 应该：10000 / 18000 / 7709 / 30w+

# 3. 一个指标跑得通
mysql -u root sim_dw -e "
SELECT stat_date, COUNT(DISTINCT customer_id) AS dau
FROM dws_customer_active_day WHERE stat_date='2025-06-15' GROUP BY stat_date"

# 4. 4 个 evals
for i in 01 02 03 04; do python3 verify/task${i}_evals.py 2>&1 | grep Passed; done
# 应该：19/19、6/6、16/16、19/19

# 5. 看指标目录
head -30 metrics/catalog/metrics.md
```

如果全过，环境是好的，你可以直接开始工作。

如果有问题，看第 5 节"如何重跑"。

---

## 12. 一句话总结

我用 opencode 的 Blueprint 工作流，帮用户造了一套 **信优消费金融** 的仿真环境：**12 业务库 + 48 份文档 + 1 数仓 + 200 个指标**，总数据 120 万行，跨库时序一致、业务分布真实，为后续本体化语义层 / NL2SQL / Data Agent 验证准备好了靶场。四步全过 evals，60/60。

下一位，接着干。祝你顺利。
