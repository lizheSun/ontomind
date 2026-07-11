# Blueprint Plan：消费金融公司业务环境模拟

> 目标：为后续本体 / 语义层 / NL2SQL / Data Agent 验证工作，构建一套逼真的消费金融生产环境模拟。
> 生成时间：2026-07-09
> 用户确认参数：小规模 (1a) + 单 MySQL 多库 (2a) + 混合生成 (3c) + 时序真实 (4c) + 文档完整 (5b) + 维度建模 (6b) + `backend/sim/` 组织 (7a)
>
> **执行策略**：Blueprint 原生是"每 task 一个 git worktree"。本次是**纯生成任务**（造数据 + 造文档），不改现有代码，所以我们**不开 worktree**，直接在 `backend/sim/` 下顺序执行 4 个 task。用户在每步完成后验收，再进下一步。

---

## 一、总体架构

### 1.1 输出目录结构

```
backend/sim/
├── README.md                       ← 总入口，四步产出的地图与验证指南
├── config/
│   ├── mysql.cnf                   ← 本地连接串（root, no password）
│   └── databases.yaml              ← 12 个数据库清单 + 系统映射
│
├── systems/                        ← Step 1：业务系统
│   ├── 01_cust_cif/                ← 每个系统一个目录
│   │   ├── README.md               ← 系统说明 + 表清单 + 数据分布
│   │   ├── schema.sql              ← DDL
│   │   ├── seed.py                 ← 生成脚本（Faker + 业务规则）
│   │   ├── seed_data/*.csv         ← 生成的种子数据
│   │   └── load.sh                 ← LOAD DATA INFILE 脚本
│   ├── 02_loan_intake/
│   ├── ...
│   └── 12_dp_meta/
│
├── docs/                           ← Step 2：系统文档
│   ├── 01_cust_cif/
│   │   ├── BRD_业务需求.md
│   │   ├── PRD_产品需求.md
│   │   ├── TDD_技术设计.md
│   │   └── PROJECT_项目管理.md
│   └── ...
│
├── dwh/                            ← Step 3：数据仓库
│   ├── README.md                   ← 分层规范 + 命名规范 + ETL 逻辑
│   ├── ods/*.sql                   ← 贴源层
│   ├── dwd/*.sql                   ← 明细事实层
│   ├── dws/*.sql                   ← 汇总层
│   ├── ads/*.sql                   ← 应用层
│   ├── dim/*.sql                   ← 维度表（Kimball 星型）
│   ├── etl/                        ← 抽数逻辑
│   │   ├── ods_from_systems.sql
│   │   ├── dwd_transform.sql
│   │   └── dws_aggregate.sql
│   └── etl.py                      ← 一键跑通 ODS→DWD→DWS→ADS
│
├── metrics/                        ← Step 4：指标体系
│   ├── README.md                   ← 索引
│   ├── governance/
│   │   ├── 01_管理办法.md          ← 顶层制度
│   │   ├── 02_命名规范.md          ← 中英文对照、大小写、缩写
│   │   ├── 03_口径管理.md          ← 变更流程、版本、责任人
│   │   └── 04_分级分类.md          ← 一级/二级/三级
│   ├── catalog/                    ← 指标目录
│   │   ├── metrics.yaml            ← 所有指标（本体数据字典层）
│   │   └── metrics.md              ← 可读版
│   └── domains/                    ← 分领域细化
│       ├── user_domain.md          ← 用户域
│       ├── credit_domain.md        ← 信贷域
│       ├── finance_domain.md       ← 财务域
│       ├── risk_domain.md          ← 风险域
│       ├── marketing_domain.md     ← 营销域
│       ├── operation_domain.md     ← 经营管理域
│       └── departments/            ← 部门级指标看板
│           ├── risk_mgmt.md
│           ├── finance.md
│           ├── self_credit_product.md
│           ├── platform_product.md
│           ├── profit_share_product.md
│           └── marketing.md
│
└── verify/                         ← 验证脚本
    ├── check_data_integrity.sql    ← 外键完整性、时序合理性
    ├── check_business_logic.py     ← 逾期率、审批率等业务分布检查
    └── sample_queries.sql          ← 几个典型的分析问题 + SQL
```

**用户查阅路径**：
- **总览** → `backend/sim/README.md`
- **数据库** → `mysql -u root` 连上，看 `sim_*` 前缀的库
- **指标验证** → `backend/sim/metrics/catalog/metrics.md`

### 1.2 数据库清单（12 个业务库 + 1 个数仓库）

| # | 库名 | 系统名 | 归属域 | 表数 | 主要实体 |
|---|---|---|---|---|---|
| 1 | `sim_cust_cif` | 客户中心 (CIF) | 客户 | 6 | customer, identity, address, contact, kyc_result |
| 2 | `sim_loan_intake` | 进件受理 | 进件 | 5 | application, doc_upload, credit_report_pull |
| 3 | `sim_risk_decision` | 风险决策 | 风险 | 7 | rule_set, decision_log, model_score, blacklist, antifraud_event |
| 4 | `sim_credit_core` | 信贷核心 | 信贷 | 10 | credit_limit, loan, repayment_plan, repayment_actual, overdue |
| 5 | `sim_collection` | 催收 | 信贷 | 4 | case, action_log, promise_to_pay |
| 6 | `sim_funding` | 资金/合作方 | 资金 | 6 | funding_partner, funding_agreement, loan_funding_split, profit_share |
| 7 | `sim_finance` | 财务 | 财务 | 7 | gl_account, gl_journal, settlement, tax_record, reconcile |
| 8 | `sim_marketing` | 营销 | 营销 | 6 | channel, campaign, ad_cost, attribution, promo_code |
| 9 | `sim_events` | 埋点收集 | 数据平台 | 3 | app_event, page_view, click_stream |
| 10 | `sim_csm` | 客服 | 运营 | 4 | ticket, call_record, complaint |
| 11 | `sim_hr_iam` | HR & 权限 | 内控 | 4 | employee, role, permission, org |
| 12 | `sim_dp_meta` | 元数据 | 数据平台 | 3 | table_meta, etl_job, data_lineage |
| **DW** | `sim_dw` | 数据仓库 | — | ~50 | ods_*, dwd_*, dws_*, ads_*, dim_* |

**总计**：约 65 张业务表 + 50 张数仓表 = **115 张表**。

### 1.3 数据规模（小规模 demo）

| 实体 | 量级 | 时间跨度 |
|---|---|---|
| 客户 | 10,000 | — |
| 授信申请 | 15,000 | 6 个月 |
| 放款订单 | 8,000 | 6 个月 |
| 还款计划 | ~90,000 | 6 个月+ |
| 还款流水 | ~70,000 | 6 个月 |
| 逾期事件 | ~2,000 | 6 个月 |
| 埋点事件 | 500,000 | 6 个月 |
| 营销投放 | 500 广告位 × 6 月 | 6 个月 |
| 财务凭证 | ~50,000 | 6 个月 |

预计存储：**~500 MB**。

### 1.4 数据时序 & 关联性约束

**核心时序链**（关键，Data Agent 验证依赖这条）：

```
埋点(点击广告) → 注册 → 实名/KYC → 授信申请 → 风控决策
    → 授信额度 → 支用申请 → 放款 → 还款计划 → 还款流水/逾期
    → 催收 → 结清 或 坏账
每个环节：客服工单、财务凭证、资金分润、埋点跟随
```

**分布约束**（尽量真实，见 [DESIGN NOTES.md](./design-notes.md)）：
- 授信申请通过率 40–55%
- 支用率（授信后 30 天内用信）60%
- 逾期率 M1 3–5%，M3 1–1.5%
- 客户年龄正态分布：均值 33，σ=8，截断 [18, 60]
- 客户地域按人口比例：广东/江苏/山东/浙江/河南...
- 时间分布：工作日多于周末，晚上 20–22 点是高峰

---

## 二、任务拆分

四个原子任务，**顺序执行**，每步用户验收。

### Task 01：业务系统数据库 + 种子数据

**目标**：建 12 个 MySQL 库，共 65 张表，导入合规业务数据。

**产出**：
- `backend/sim/systems/*/schema.sql`
- `backend/sim/systems/*/seed.py`
- `backend/sim/systems/*/seed_data/*.csv`
- `backend/sim/systems/*/README.md`
- `backend/sim/config/databases.yaml`
- `backend/sim/README.md`（首个版本）

**关键决策**：
- 用 Python + Faker + mimesis + 自定义业务规则，先出 CSV，再 `LOAD DATA LOCAL INFILE` 导入
- 每个系统的 `seed.py` **单进程可复现**（固定 random seed）
- 表结构参考真实消金系统（自营 + 助贷 + 联合贷 + 分润 4 种业务形态）
- 客户/订单/还款主线用**统一 ID 生成器**保证跨库外键一致
- 敏感字段（身份证、手机号、银行卡）用 **虚构规则** 生成，明确标注"测试数据"

**依赖**：无
**验收**：
- `mysql -u root -e "SHOW DATABASES LIKE 'sim_%'"` 返回 12 行
- 每库 `SELECT COUNT(*)` 与文档中"预计规模"一致（±10%）
- `verify/check_business_logic.py` 通过所有分布检查（逾期率、通过率、时序）

---

### Task 02：系统文档（BRD/PRD/TDD/PROJECT）

**目标**：为 12 个业务系统生成 4 类文档，共 48 份。

**产出**：
- `backend/sim/docs/<system>/BRD_业务需求.md`
- `backend/sim/docs/<system>/PRD_产品需求.md`
- `backend/sim/docs/<system>/TDD_技术设计.md`
- `backend/sim/docs/<system>/PROJECT_项目管理.md`

**每类文档内容规范**（"完整级"，每份 2000–3000 字）：

| 类型 | 关键章节 |
|---|---|
| **BRD 业务需求** | 业务背景 / 目标用户 / 业务价值 / 关键流程 / 相关系统 / 合规要求 / 业务指标 |
| **PRD 产品需求** | 产品范围 / 用户角色 / 用例 / 功能列表 / 流程图（mermaid）/ 交互规则 / 数据规则 / 验收标准 |
| **TDD 技术设计** | 架构图（mermaid）/ 技术选型 / 数据模型 ER（引用 schema.sql）/ 接口清单（伪 OpenAPI）/ 关键算法 / 部署 / 监控 / 安全 |
| **PROJECT 项目管理** | 项目里程碑 / 团队角色（RACI）/ 依赖 / 风险登记表 / 上线 checklist / 迭代记录（3–5 期虚构） |

**关键决策**：
- 每个系统 4 份，但**重点系统** (CIF、进件、风控决策、信贷核心、财务) 写完整，其余可精简到 1500 字
- 文档里的**表名、字段、数据分布**必须与 Task 01 生成的实际 schema/数据对得上（这是后续 Data Agent 用来"看文档→找表"的关键）
- 用 mermaid 画图，都能在 markdown 里直接渲染

**依赖**：Task 01（要引用真实 schema）
**验收**：
- 48 份 md 文件齐全
- 文档中提到的表名、字段名 100% 存在于 Task 01 的 schema.sql（可自动 diff）
- 至少每个系统有 1 张 mermaid 流程/架构图

---

### Task 03：数据仓库（Kimball 维度建模）

**目标**：从业务系统抽数到 `sim_dw`，分层建表 + ETL 逻辑 + 抽样数据。

**产出**：
- `backend/sim/dwh/README.md`（分层规范 + 命名规范）
- `backend/sim/dwh/ods/*.sql`（贴源，几乎 1:1 复制业务库）
- `backend/sim/dwh/dim/*.sql`（维度：dim_customer, dim_product, dim_date, dim_channel, dim_org, ...）
- `backend/sim/dwh/dwd/*.sql`（明细事实：fact_application, fact_loan, fact_repayment, fact_overdue, fact_event, ...）
- `backend/sim/dwh/dws/*.sql`（汇总：dws_customer_day, dws_loan_day, dws_channel_day, ...）
- `backend/sim/dwh/ads/*.sql`（应用：ads_risk_daily, ads_finance_daily, ads_marketing_roi, ...）
- `backend/sim/dwh/etl/*.sql`（每一层的抽取/转换 SQL）
- `backend/sim/dwh/etl.py`（一键跑通脚本）

**数仓规范**：
- **命名规范**：`<layer>_<domain>_<entity>_<grain>`（如 `dws_credit_customer_day`）
- **分层**：ODS（贴源）→ DWD（明细事实 + 维度）→ DWS（主题汇总）→ ADS（应用集市）
- **维度建模**：**星型**为主，客户/商品/机构/日期/渠道 5 大共享维度
- **缓慢变化维**：客户维度 SCD Type 2（保留历史）
- **数据字典**：每张表带 `COMMENT`，字段带 `COMMENT`（后续本体化的关键）

**关键决策**：
- 数仓维度设计要能直接支撑 Task 04 的指标计算（DWS 层 = 指标的"物理载体"）
- ETL 用纯 SQL（`INSERT ... SELECT`），不用 Airflow 之类，便于查看
- 提供 `sample_queries.sql`：10 个典型分析问题（"过去 30 天各渠道 GMV"、"各产品逾期率排名"…），既是数据自检，也是后续 NL2SQL 靶子

**依赖**：Task 01
**验收**：
- `sim_dw` 库存在，约 50 张表
- `etl.py` 一键跑通，无错
- `sample_queries.sql` 10 个 SQL 都能出结果
- DWS 层的数据能和 Task 04 定义的指标口径**对齐**（在 Task 04 中反向验证）

---

### Task 04：指标体系（**最关键，本体化验证靶子**）

**目标**：完整的指标体系管理制度 + 目录 + 6 领域 × 部门级细化。

**产出**：
- `backend/sim/metrics/governance/01_管理办法.md`（3000+ 字，涵盖管理组织、变更流程、生命周期、责任分工、审计）
- `backend/sim/metrics/governance/02_命名规范.md`（命名规则、缩写表、示例、反例）
- `backend/sim/metrics/governance/03_口径管理.md`（口径定义、版本、变更审批、并存策略）
- `backend/sim/metrics/governance/04_分级分类.md`（一/二/三级、领域分类、责任部门）
- `backend/sim/metrics/catalog/metrics.yaml`（**200+ 个指标的结构化定义**）
- `backend/sim/metrics/catalog/metrics.md`（可读版）
- `backend/sim/metrics/domains/*.md`（6 个领域 + 6 个部门）

**指标 YAML 结构**（每个指标）：

```yaml
- id: M0001
  name_zh: 日活跃用户数
  name_en: dau
  aliases: [日活, DAU, active_users_daily]
  level: 一级
  domain: 用户
  department: 运营部
  owner: data-ops@sim.com
  definition: 当日在 App 有登录/浏览/操作行为的去重用户数
  formula: COUNT(DISTINCT user_id)
  filters:
    - is_test_user = 0
    - is_robot = 0
  dedup_key: user_id
  time_grain: day
  source_tables:
    - sim_dw.dws_customer_active_day
  sql_template: |
    SELECT stat_date, COUNT(DISTINCT user_id) AS dau
    FROM sim_dw.dws_customer_active_day
    WHERE stat_date = '${date}'
      AND is_test_user = 0 AND is_robot = 0
    GROUP BY stat_date
  related_metrics: [M0002 (MAU), M0003 (WAU), M0010 (新增用户)]
  version: 1.0
  effective_from: 2025-01-01
```

**领域覆盖**（约 200–250 个指标）：

| 领域 | 一级指标（示例） | 数量 |
|---|---|---|
| 用户 | DAU, MAU, 新增用户, 留存率, 转化率 | 30 |
| 信贷 | 授信申请量, 授信通过率, 放款金额, 在贷余额, 支用率, 户均放款 | 45 |
| 财务 | 营业收入, 净利润, 净息差, ROA, 拨备覆盖率 | 30 |
| 风险 | M1 逾期率, M3 逾期率, 首逾率, Vintage, 客户风险等级分布, 反欺诈拦截率 | 40 |
| 营销 | 获客成本 CPA, ROI, 渠道转化率, LTV, 广告曝光量 | 25 |
| 经营管理 | 员工人均产能, 单位客户成本, 单笔放款成本, 客服接通率 | 20 |
| 资金/合作方 | 资金成本, 分润金额, 资金到位率, 合作方数量 | 15 |
| 合规 | 客户投诉率, 监管报送及时率, 数据质量得分 | 10 |

**部门级看板**（每部门 1 份 md，聚合本部门关心的 20–30 个指标）：
- 风险管理部
- 财务部
- 自营信贷产品部
- 平台业务产品部（助贷/联合贷）
- 分润业务产品部
- 营销部

**关键决策**：
- **每个指标必须能跑通**：`sql_template` 直接执行返回结果，与 DWS 层对齐
- **同义词表**：为后续 NL2SQL 消歧，每个指标至少 3 个别名
- **责任分工**：owner、审批人显式化
- **本体化预留**：metrics.yaml 的结构就是数据字典本体（Level 1），后续可直接翻译成 Turtle/JSON-LD
- **变更历史**：管理办法里定义"废弃、拆分、合并"三种变更路径

**依赖**：Task 03（要有真实 DWS 表可查）
**验收**：
- 至少 200 个指标有完整字段
- 100% 指标的 `sql_template` 在 `sim_dw` 上跑得通
- 6 领域 + 6 部门文档齐全
- 命名规范中的 20 个示例，在 metrics.yaml 里都能找到对应实例

---

## 三、执行时序与依赖

```mermaid
graph LR
    T1[Task 01: 业务系统 + 数据] --> T2[Task 02: 系统文档]
    T1 --> T3[Task 03: 数据仓库]
    T3 --> T4[Task 04: 指标体系]
    T2 -.可并行.-> T3
```

**顺序**：Task 01 → (Task 02 + Task 03 可并行) → Task 04

**用户验收点**：每个 Task 完成后暂停，等待用户确认再进下一步（用户可 `/nudge` 修改要求）。

---

## 四、跨任务的公共约定

### 4.1 时间线一致性
所有数据以 **2025-01-01 至 2025-06-30**（6 个月）为跨度。当前"今天"设为 **2025-07-01**（便于计算"过去 30 天"等指标）。

### 4.2 ID 生成规则
- customer_id: `C` + 8 位数字，如 `C00000001`
- application_id: `AP` + yyyyMMdd + 6 位序号
- loan_id: `LN` + yyyyMMdd + 6 位序号
- 保证跨库外键完全对齐

### 4.3 敏感字段策略
- 姓名：Faker `zh_CN`
- 身份证：**前 6 位为真实行政区划**，后 12 位随机但校验位正确
- 手机号：`13800000001` 到 `13800009999` 段（虚构）
- 银行卡：`6222**********00XX` 格式（虚构）
- 所有生成的数据表都带 `is_test_data=1` 标记，可全局过滤

### 4.4 业务产品形态
覆盖 4 种产品，方便后续验证不同业务场景：
- **自营信贷产品** `SELF_LOAN`：全额自营，资金/风控/放款/催收都自己做
- **助贷平台业务** `PLATFORM_LOAN`：客户导流给资金方，风控辅助
- **联合贷分润业务** `JOINT_LOAN`：与合作方按比例出资、分润
- **担保业务** `GUARANTEE_LOAN`：担保方兜底

### 4.5 组织结构
虚构公司："**信优消费金融有限公司**"（Sim Consumer Finance），总部北京，10 家分公司（华北/华东/华南/华中/西南/东北），员工约 500 人。

---

## 五、需要用户在开跑前确认（很少几件）

1. **虚构公司名**"信优消费金融"你 OK 还是想换个（比如"星宇消金"、"云锦消金"）？
2. **产品名**：自营产品叫 "**信优速贷**"、助贷叫 "**信优合作贷**"、联合贷叫 "**信优联合贷**"、担保叫 "**信优保贷**"—— 可换
3. **时间线**：默认 **2025-01-01 至 2025-06-30**，用户是否希望改到最近（比如 2025-12-31，让"当前日期"更接近今天）？
4. **执行方式**：是**每个 Task 跑完你 review 一次**（推荐），还是**四个连续跑完再看**？

---

## 六、下一步

用户回复上面 4 点后：
1. 我把回答写进 `.blueprint/tasks/` 生成 4 个 task 详细规格文件
2. 用户敲 `/execute` → orchestrator 逐个 task 派 worker 落地（不开 worktree，因为纯生成任务无冲突风险）
3. 每个 task 完成后打印验收清单，等你 OK 再进下一个

**如果你等不及**，回一句"用默认，直接干"，我按上面所有默认参数直接生成 tasks 然后开跑。
