# OntoMind 深度调研文档 —— 本体驱动的 AIBI Data Agent 与 OpenCode Agent Loop 工程实践

> **作者**：opencode 调研 Agent
> **日期**：2026-07-09
> **读者**：OntoMind 产品/架构/研发
> **目的**：将「什么是本体」「LLM 如何造本体」「消费金融本体长啥样」「本体×Agent×AIBI」「Prompt/Context/Harness/Loop 四层工程」「OpenCode 如何落地 Agent Loop」串成一份可直接指导落地的调研文档，并与 OntoMind 当前仓库现状对齐。
> **信息源**：本仓库 `README.md` / `docs/ONTOLOGY_AIBI_DATA_AGENT.md` / `docs/project-plan.md` / `docs/RESOURCE_MANAGEMENT_DESIGN.md` + 豆包联网搜索（本体论/知识图谱/LLM 本体构建/FIBO/信贷图谱/Data Agent/dbt Semantic Layer benchmark/Palantir Foundry/Prompt-Context-Harness-Loop Engineering/OpenCode 官方 & 中文社区文档）

---

## 0. TL;DR（一页读懂）

1. **本体（Ontology） ≠ 知识图谱（KG） ≠ 语义层（Semantic Layer）**：本体定义"能有什么"（Schema+公理+规则），KG 承载"实际有什么"（实例三元组），语义层规范"业务怎么说指标"（口径）。三者叠加才是 AI 时代的"业务操作系统"。Palantir Foundry 靠"动态本体"把这三层做成产品级壁垒。
2. **LLM 建本体 = 迭代小步 delta**：不是"一次生成完整 OWL"。业界主流管道（NeOn-GPT / OntoGenia / RIGOR / IORAG / LOM 等）都是 **"Retrieve → LLM 生成 delta → Judge/CQ 校验 → 版本化合并"** 的可校验循环，并允许对齐 FIBO 等标准片段。
3. **消费金融本体的主干**：Party（Person/Org）→ LoanApplication → LoanContract/Product → LoanAccount → Transaction/RepaymentBehavior → RiskEvent；旁系包含 Channel/Campaign、Scorecard/Feature/StrategyRule。**治理硬点在实体解析、指标口径、物理表映射与血缘**，而不是画得多花哨。
4. **AIBI Data Agent 的正确形态**：不是"NL → 拼 SQL"，而是"NL → Ontology Router → Semantic Composer → Grounded Query → Evidence Binder"。dbt 2026 Benchmark 证实：**Text-to-SQL 与 Semantic Layer 各有失效模式；本体化语义层在 100+ 指标企业级场景仍显著更稳**。业界产品趋同（Snowflake Cortex Analyst、Databricks Genie、Fabric Data Agent、迈富时/亿问/OntoFlow）。
5. **四层工程栈**：Prompt Engineering（怎么说）→ Context Engineering（看什么）→ Harness Engineering（怎么稳跑）→ Loop Engineering（怎么循环收敛）。**本体是每一层都能被引用的一等资产**，尤其在 Context 检索与 Harness 白名单校验里"最值钱"。
6. **OpenCode 是把 Agent Loop 做成可落地终端 CLI 的开源方案**：Plan/Build 双模式 + Primary/Subagent 分层 + Skill + MCP + Permission + AGENTS.md，天然对应 Prompt/Context/Harness/Loop 四层，是 OntoMind 应用层 AIBI Data Agent Harness 的现成骨架候选。
7. **OntoMind 目前的位置**：感知层（元数据/文档标注）与认知层（本体 build+G6 可视化）骨架已在；**缺口在"图进 loop"**——本体查询 API、类↔表映射、CQ 评测、AIBI Orchestrator/Evidence Binder，以及资源管理（Instance/Agent/Skill/MCP/AgentRun）与本体校验的挂钩。

---

## 1. OntoMind 项目当前形态梳理

### 1.1 五层架构（README + project-plan）

```
应用层 Application     AIbi 智能分析 · 数据可视化 · 策略工作台 · 本体探索器
执行层 Execution       策略下发 · 风控/营销适配 · 灰度回滚 · 执行监控
决策层 Decision        特征挖掘 · ML 训练 · 规则策略引擎 · 仿真评估
认知层 Cognition       本体构建 · 知识图谱 · 语义搜索 · 向量库 · 融合对齐
感知层 Perception      RDB 连接器 · 文档解析 · 数仓/湖 · 代码库 · 元数据发现
```

技术栈：**FastAPI + SQLAlchemy 2 + MySQL 8 + Redis 7 + React 19 + AntD 5 + Vite + LangChain**。

### 1.2 目录结构关键位（已存在，可加载）

- 后端 API：`backend/app/api/v1/{perception,cognition,decision,execution,application,resources,knowledge_base,llm,source_code}.py`
- 后端服务：`backend/app/services/{ontology_service, metadata_service, knowledge_service, agent_service, agent_runner, agent_run_service, mcp_service, skill_service, instance_service, ...}.py`
- 前端页面：`frontend/src/pages/{perception, cognition, decision, execution, application, resources, knowledge, ...}`

**观察**：认知层的 `ontology_service.py`、`metadata_service.py`、`knowledge_service.py` 已经存在；资源管理层（`agent_service` / `mcp_service` / `skill_service` / `instance_service` / `agent_runner` / `agent_run_service`）已经存在——这是把 Agent Loop 工程化落地的关键底座。

### 1.3 已有的三份关键文档

- `docs/project-plan.md`：五层 + 14 个月 5 阶段路线图
- `docs/ONTOLOGY_AIBI_DATA_AGENT.md`：本体 × AIBI 愿景（本文档在其基础上扩写）
- `docs/RESOURCE_MANAGEMENT_DESIGN.md`：Instance / Agent / Skill / MCP / AgentRun 五实体

### 1.4 现状粗评（对照愿景）

| 层 | 现状 | 目标缺口 |
|----|------|----------|
| 感知 | 元数据 + 流式标注较成熟 | 字段语义质量与血缘的持续治理 |
| 认知 | 本体 build（rules/llm/agent）+ G6 可视化 | 服务化查询 API、CQ 回归、类→表映射、Judge 产品化 |
| 决策 | 骨架 | 概念级特征注册（特征绑定本体类/属性 ID）|
| 执行 | 骨架 | 策略实体携带本体 ID，可追溯下发 |
| 应用（AIBI） | 骨架 | Orchestrator + Ontology Router + Grounded SQL + Evidence Binder |
| 资源管理 | 五实体设计 + 部分实现 | 与本体校验挂钩；生产 Agent 执行面鉴权 |

---

## 2. 什么是本体？为什么它在 AI 时代复活了？

### 2.1 三层概念对齐

| 维度 | Ontology（本体） | Knowledge Graph（知识图谱） | Semantic Layer（语义层） |
|------|------------------|---------------------------|--------------------------|
| 定位 | Schema 层：类/属性/关系/公理/约束 | 实例层：真实三元组数据 | 分析口径层：指标/维度/权限/血缘 |
| 建筑类比 | 建筑设计图 | 已建成的房子 + 住户 | 房子的使用手册与合同条款 |
| 回答问题 | "领域中能有什么" | "现实中实际有什么" | "业务上怎么统一表达指标" |
| 典型技术 | OWL / RDFS / SHACL / Protégé | Neo4j / NebulaGraph / SPARQL | dbt Semantic Layer / Cube / MetricFlow |

> 引用：CSDN 石榴姐 2026-04《本体论与知识图谱有什么区别》与 51CTO《本体论在 AI 时代的复兴》均反复强调"本体是 KG 的骨架和规矩，KG 是本体的血肉"。

### 2.2 Gruber 经典定义 vs 工程口径

- 学术：`An ontology is a formal, explicit specification of a shared conceptualization.`（Gruber, 1993）
- 工程：**本体 = 类集合 + 关系集合 + 属性集合 + 公理/规则集合**（五大元语 Class/Relation/Attribute/Axiom/Instance）。

### 2.3 为什么 Agent 时代本体重新火了

搜索结果中最凝练的一句（51CTO 博客）：
> "本体论重新变重要，不是因为哲学复兴，而是因为 Agent 需要一个可依赖的**世界模型**来做可靠推理——而本体是目前最成熟的结构化世界表示方案。**LLM 有知识无结构，本体有结构无知识——两者正好互补。**"

Palantir Foundry 的三层落地被反复引用为标杆：
1. **语义层**：把"客户 ID / 客户编号 / 用户编码"等异构数据映射到同一"客户"对象——从根上解决语义割裂
2. **动力/动作层**：不仅是分类表，还包含 Actions/Functions（如批准采购、调度技术员），做权限管控与逻辑校验
3. **AI 翻译官**：LLM 不直接触底层 SQL，而是与本体对话——因果关系清晰，推理"接近无幻觉"

### 2.4 相对纯向量 RAG 的核心优势

| 能力 | 纯 RAG（文本向量） | 本体加持 |
|------|---------------------|----------|
| 消歧 | 弱：靠语义相似 | 强：同一 Party ID 跨系统对齐 |
| 多跳推理 | 靠 chunk 拼接 | 沿显式关系跳（人 → 合约 → 账户 → 风险事件） |
| 可审计 | 引用文档段 | 结论 = 实体路径 + Competency Question + 查询引用 |
| 幻觉边界 | 靠 Prompt 约束 | 词表校验 / 表白名单 / 边类型契约硬约束 |
| 联合价值 | / | **本体约束语义与可达性 + 向量补充文档/注释**——互补而非替代 |

---

## 3. LLM 如何构建本体（业界主流路线）

### 3.1 反直觉的第一原则

**不是"扔一张大表让 GPT 生成完整 OWL"**。所有正经研究方向（NeOn-GPT / OntoGenia / RIGOR / IORAG / LOM / DeepOnto）都归结为一条：

> **小步、可校验、可版本化的 delta 迭代。**

### 3.2 五阶段管道（可直接落 OntoMind 认知层）

```
┌──────────────────────────────────────────────────────────────────┐
│  1. 输入采集                                                       │
│     RDB Schema + 字段注释 + 业务文档 + 已有领域片段（FIBO 等）      │
├──────────────────────────────────────────────────────────────────┤
│  2. 检索（Retriever）                                              │
│     针对当前 CQ / 一批实体，检索相关上下文和标准本体片段            │
├──────────────────────────────────────────────────────────────────┤
│  3. 生成（Gen-LLM）→ delta 本体                                   │
│     产出增量类、对象属性、数据属性、SHACL 约束、Turtle/OWL          │
├──────────────────────────────────────────────────────────────────┤
│  4. 校验（Judge-LLM + 专家 + Competency Question）                │
│     一致性、完整性、简洁性、CQ 通过率、OOPS! 检测                    │
├──────────────────────────────────────────────────────────────────┤
│  5. 版本化合并 → 回到步骤 2 处理下一批                             │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 三类被反复验证的 Prompt 技术

1. **CQbyCQ / Memoryless CQbyCQ**：每次只喂一个 Competency Question，逐题建模，减小干扰（Ontogenia 论文 2025）
2. **Ontogenia**：要求同时输出 label / annotation / inverseOf / individuals，用元认知 prompt 覆盖更多元素
3. **IORAG（工业本体）**：多级层次检索，从本体库中先取相关概念、再取字段、再取属性，作为增强上下文

### 3.4 LLM 建本体的常见陷阱

| 陷阱 | 现象 | 对策 |
|------|------|------|
| 概念粒度不一 | 同层出现"客户"和"新客户 30 天首借"混在一起 | 分层建模 + Judge 强制归入正确父类 |
| 隐含关系抽不出 | 只识别"has" 泛化关系 | 加领域词典 + Few-shot + 交叉验证 |
| 生成不一致 | 同一实体多次生成名字不同 | 版本化 + 命名对齐（对 FIBO/schema.org）|
| 长文本 context 掉 | 表越多信息越乱 | 分块 + 相似度合并（cos > 0.85） |
| 幻觉字段 | 猜出根本不存在的列 | 用表 schema 做硬约束 + SHACL 校验 |

### 3.5 与 OntoMind 认知层的映射

`ontology_service.py` 中的 `rules / llm / agent` 三种构建方式已具备管道形态，**推荐补齐**：
1. `retriever`：把 FIBO / 已有片段做为一等资产，用 embedding 检索
2. `judge`：新增独立的 Judge-LLM 路径，跑 SHACL 与 CQ 集合
3. `cq_registry`：每个类/关系挂一组 Competency Questions，作为回归测试
4. `mapping_registry`：类/关系 → 物理表/列的映射，供 AIBI 查询代理消费

---

## 4. 消费金融"轻量本体"参考骨架

### 4.1 一期先回答的四个问题

> 客户是谁 → 申请了什么 → 合约/账户状态 → 为何逾期/风险

### 4.2 主干结构（已在仓库文档中，本文补充）

```
Party (Person / Organization / Household)
 └─ applies_for ────────► LoanApplication ── results_in ──► LoanContract
                              │                                 │
                              ├─ sourced_from ► Channel         ├─ secured_by ► Collateral
                              └─ scored_by ►  ScorecardModel    ├─ opens ─────► LoanAccount
                                                                │                 │
                                                                │                 ├─ has ────► Transaction
                                                                │                 ├─ exhibits ► RepaymentBehavior
                                                                │                 └─ triggers ► RiskEvent
                          Product ─ offered_as ►                                    │
                          Feature ─ feeds ► ScorecardModel                          └─ investigated_as ► CollectionCase / FraudSignal
```

### 4.3 六大类簇速查表

| 类簇 | 核心类 | 典型属性 | 典型关系 |
|------|--------|----------|----------|
| 主体 | Person, Organization, Household | 身份证/统一社会信用代码、职业、收入区间、居住城市 | belongs_to, related_party, has_household |
| 产品与合约 | CreditProduct, LoanContract, CreditLimit | 利率、额度、期限、费项、担保方式 | issues, underwrites |
| 账户与行为 | LoanAccount, Transaction, RepaymentBehavior | 余额、逾期天数、动支频次、DPD | posts_to, pays, has |
| 风险 | RiskEvent, CollectionCase, FraudSignal | 等级、时间、处置状态、责任方 | triggers, investigated_as |
| 获客与运营 | AcquisitionChannel, Campaign, Case | 渠道成本、转化率、有效期 | sources, engaged_by |
| 决策资产 | ScorecardModel, RiskFeature, StrategyRule | 分数、口径、版本、AUC/KS | derived_from, feeds, applied_by |

### 4.4 三个不能"画完就走"的治理硬点

1. **实体解析（Entity Resolution）**：同一人在核心系统、征信、场景方、催收系统里可能有 5 个 ID —— 得对齐到同一 Party 主键（Palantir 的核心秘密武器之一）
2. **指标口径（Semantic Layer）**：M1/M3/DPD30 逾期定义、GMV 含不含退款、活跃客户按什么统计……**这就是 dbt Semantic Layer / Aloudata 四层语义层解决的问题**
3. **物理映射与血缘**：类/关系 → 数仓表/字段的映射注册；一旦口径变化，Agent 应立刻感知（这是 Fabric Data Agent、Snowflake Cortex Analyst 都强调的合规基线）

### 4.5 可对齐的行业标准（一期不必全导）

- **FIBO（Financial Industry Business Ontology / EDM Council）**：金融机构、金融工具、交易、合约、风险暴露、监管
- **schema.org / GoodRelations**：产品、组织、Person 的通用词表
- **国内监管**：《商业银行互联网贷款管理暂行办法》《消费金融公司试点管理办法》的口径（如利率上限、逾期口径）

> 迈富时 Data Agent（2026-03）、Agentic Ontology 平台（2026-04）已经在金融场景做 FIBO 对齐的产品化尝试，可作为对标。

### 4.6 一个具体的 CQ 集合示例

```
CQ-01 某客户过去 12 个月的最高逾期天数是多少？
CQ-02 A 产品在 2025 年 Q3 的 M3+ 逾期率？
CQ-03 有多少客户既是 CashLoan 借款人又是 CreditCard 持卡人？
CQ-04 打分卡 v3.2 在渠道 X 的当前拒绝率对比 v3.1 变化多少？
CQ-05 风险事件 R-001 涉及的所有账户/合约/客户？
CQ-06 客户 P-1234 的所有申请→合约→账户→交易链路？
```

这些 CQ 直接落到 `cognition/ontology_service.py` 的评测入口，作为回归指标。

---

## 5. 本体 + Agent → AIBI Data Agent

### 5.1 dbt Semantic Layer 2026 Benchmark 的核心结论

> Text-to-SQL 与 Semantic Layer 都能工作，但**失效模式完全不同**：
> - Text-to-SQL 简单 schema 好使；一旦到"多张表 + 多口径 + 多权限"就会漂
> - Semantic Layer 前期治理成本高，但**长期收益指数级放大**：新增指标边际成本递减、追溯性、权限一致性、口径统一

搜索结果中另一句更狠（亿问 Data Agent 团队）：
> "如果我们把语义层只定义成指标、维度和统计分析对象，这个定义不是错，而是太窄。**它是 BI 时代的语义层，不是 Data Agent 时代真正需要的语义基础。**"

Aloudata / 亿问的"五层能力模型"：**指标 → 对象 → 事件 → 规则 → 动作**，前两层几乎就是本体。

### 5.2 AIBI Data Agent 参考架构

```
User / Analyst
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    AIBI Orchestrator                         │
│  （opencode/harness/自研 —— 决定 plan → subagent 路由）      │
└──┬──────────────┬──────────────┬──────────────┬─────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
Ontology       Metric         Grounded       Insight
Router         Composer       Query Agent    Narrative Agent
   │              │              │              │
   ▼              ▼              ▼              ▼
Ontology+KG   SemanticDB     DW / OLAP / KG   Evidence Binder
（认知层）    （语义层）      （数据面）        → 返回 User
```

### 5.3 六个必要能力切片

1. **Ontology Router**：把用户问题落到"应触达哪些类/关系/CQ 模板"
2. **Semantic Composer**：只允许使用本体登记过的指标/维度，**禁止自由发明字段**
3. **Grounded Query Agent**：SQL / Cypher / OLAP 只能触达已映射到本体的物理对象（"表白名单"）
4. **Evidence Binder**：答案附带实体路径 + 查询语句 + 数据版本 + 口径 ID
5. **Guardrails**：租户隔离、敏感列脱敏、结果一致性校验（同问两次答案要一致）
6. **Memory**：跨会话保留"我们上次约定的口径"——由 Harness 调度写入/读出

### 5.4 与业界产品的对照（可作为选型参考）

| 产品 | 核心机制 | 与 OntoMind 的关系 |
|------|----------|--------------------|
| Palantir Foundry / AIP | 动态本体 + Actions + AIP | 目标形态标杆 |
| Snowflake Cortex Analyst | Semantic Views + RBAC 联动 | 语义层的"最小落地" |
| Databricks AI/BI Genie | Unity Catalog 治理边界 | 治理挂钩范式 |
| Microsoft Fabric Data Agent | Ontology / Warehouse / Lakehouse / PBI SM | 直接消费"ontology 数据源"的产品化 |
| dbt Semantic Layer | Metric-first + benchmark | Metric 层参考实现 |
| 迈富时 Data Agent | Ontology + 全程可溯源 + 自证报告 | 国内金融/营销场景对标 |
| 亿问 Data Agent (NL2LF2SQL) | Semantic DB + LogicForm 复用 | 国内工程化路径对标 |
| Timbr / OntoFlow | SQL Ontology / 一体化本体智能平台 | 结构化 + 非结构化双源本体 |
| Aloudata | 数据/指标/对象/行动四层语义 | 语义层分层参考 |

### 5.5 "本体接地"下 Agent Loop 的改动

| 阶段 | 无本体 | 有本体 |
|------|--------|--------|
| Observe | 用户话 + 原始表名 | 映射到类 / 关系 / 指标 ID |
| Plan | 猜表 join | 只沿允许边 + CQ 引导子目标 |
| Act (tool) | 任意 SQL / 任意 MCP | 参数词表校验；表白名单 |
| Validate | "看着像" | 类型一致 + 口径一致 + 实体可达 |
| Compress | 粗暴截断 | 保留子图摘要 |

---

## 6. 四层工程栈：Prompt / Context / Harness / Loop

搜索关键结论汇总：**这四层不是替代关系，而是层层递进**。同一份模型能力下，工程质量拉开的差距远大于换模型。

### 6.1 一张表看清差异

| 维度 | Prompt Engineering | Context Engineering | Harness Engineering | Loop Engineering |
|------|--------------------|---------------------|---------------------|-------------------|
| 核心问题 | 怎么问？ | 给它看什么？ | 怎么稳定跑？ | 怎么反复行动并收敛？ |
| 作用范围 | 单次调用 | 单轮上下文组织 | 系统架构/生命周期 | 多步反馈循环 |
| 输入对象 | 指令文本 | 上下文数据 | 整个系统 | 目标 + 停止条件 |
| 主要技术 | 角色/CoT/Few-shot/格式约束 | RAG / 结构化上下文 / Memory / 压缩 | 权限白名单 / 沙箱 / 重试 / 监控 / Sub-agent / A/B / 评测 | ReAct / Reflection / Plan-and-Execute / 评判者 / 终止条件 |
| 失败表现 | 听不懂/跑偏 | 噪音/缺失/冲突 | 工具失败/无恢复/无观测/无鉴权 | 死循环 / 提前收手 / Context Rot |
| 本体角色 | 术语写入 System Prompt（弱） | **可检索的系统语义层（强）** | **路由与校验的一等资产（最强）** | **停止条件与 Evidence 校验的锚点** |

### 6.2 Karpathy 隐喻的更新版

- LLM = CPU
- Context Window = RAM
- Prompt = 一条汇编指令
- Context = 每一步塞进 RAM 的数据段
- Harness = 操作系统 + 外设 + 权限
- Loop = 事件循环 + 状态机 + 中断处理

### 6.3 Boris Cherny（Claude Code 作者）名言的意义

> "我已经不写 prompt 了，我写 loop。"

拆开看：Agent 的核心循环其实就是 6 行代码（`while True: response = model(context); if tool_calls: context += run(tools); else: break`）。**大家在工程的从来不是 while 本身，而是循环外面那一切**——即 Harness/Context 决定的世界。

### 6.4 Context Engineering 三原则（Select / Compress / Isolate）

1. **Select**：按问题只拉相关子图（类 + 1-2 跳邻居 + 相关 CQ），不要全量 DDL
2. **Compress**：类级摘要 + 关键属性 + 最近工具调用摘要，不要塞历史全文
3. **Isolate**：风控子本体 vs 营销子本体不要串扰；把大块工具输出**卸载到文件**，只把结论回流

### 6.5 Harness Engineering 的三根支柱（来自 Anthropic / NxCode 归纳）

1. **上下文管理**：静态（AGENTS.md / API 契约）+ 动态（CI 失败堆栈实时注入）+ 压缩 + 分阶段暴露
2. **约束即生产力**：越严格的护栏，AI 收敛越快（Claude Code / Codex 反复验证）
3. **产验分离**：Planner / Generator / Evaluator 不要一个 Agent 又当运动员又当裁判

搜索资料里最有意思的一句：**"Agent 反复失败时，不要再调 Prompt 或换模型，去问'环境里缺了什么能力'——然后把那能力补进 Harness。"** —— OpenAI Codex 团队实践总结。

### 6.6 Loop Engineering 的 7 条最佳实践

来自 Addy Osmani《Loop Engineering》与国内多个转载：

1. 从最基本的循环开始，先加**最大迭代次数、超时、成本上限**（三个止损位）
2. 任务开始前定义**成功标准**，而不是事后主观判断
3. 压缩长历史、卸载大输出、隔离混乱子任务
4. 执行时保持**工具数量少且功能集中**（工具越多越容易选错）
5. 确保写入操作**可以安全重复执行**（idempotent）
6. 错误信息要写成"**下一步该干什么**"的形式
7. 引入 Evaluator，只有你足够信任它，才让 loop 真的放手

### 6.7 本体作为四层贯穿的一等资产

| 层 | 本体扮演什么 | 具体做法 |
|----|--------------|----------|
| Prompt | 术语表 + 角色（信贷分析师）+ 输出格式（含 evidence 字段） | 把本体词表短表写进 System Prompt |
| Context | **可检索子图 + 相关 CQ + 表白名单** | Retriever 每轮从 Ontology Service 拉子图 |
| Harness | **工具参数词表校验 + 表白名单 + 停止条件** | tool schema 引用本体 ID；SHACL 前置校验 |
| Loop | **成功标准：CQ 通过 + Evidence 一致 + 类型一致** | Evaluator agent 消费本体做 Judge |

---

## 7. OpenCode：Agent Loop 落地骨架

OntoMind 的资源管理设计已经把 `type=opencode` 作为 Agent 类型之一（`RESOURCE_MANAGEMENT_DESIGN.md`），因此 **OpenCode 是应用层 AIBI Data Agent Harness 的最现实候选之一**（另一路线是自研 Harness 或使用 openclaw 等）。

### 7.1 OpenCode 是什么

- 开源 CLI/终端 Agent（MIT），Anthropic 2026 年 1 月封第三方后爆发，被视为 Claude Code 的替代
- 统一接口对接 **75+ LLM 提供商**（Anthropic / OpenAI / Gemini / DeepSeek / GLM / Ollama / LM Studio ...）
- 核心设计：**Plan / Build 双模式**（默认 Plan 只读，Build 全权限），**Primary / Subagent 分层**，**Skill 系统**，**MCP 协议接入**，**Permission 精细化**
- 官方文档：[opencode.ai/docs](https://opencode.ai/docs)

### 7.2 OpenCode 的层次映射（正好对应四层工程）

| 工程层 | OpenCode 落点 |
|--------|---------------|
| Prompt | `AGENTS.md`（项目级 System Prompt） + `~/.config/opencode/AGENTS.md`（全局） + Agent Markdown frontmatter |
| Context | Skill 内容（`SKILL.md` + `references/`）+ `@filename` 引用 + `/add`  + subagent 独立子会话 |
| Harness | `opencode.json` 里的 `permission` / `mcp` / `agent` / `provider` 配置 + LSP + Watcher + Snapshot + Autoupdate + Server |
| Loop | 内建 while 循环：`request → tool_calls → observe → next` + Plan/Build 切换 + Task 工具 spawn subagent |

### 7.3 六件必须配的事

#### 7.3.1 `opencode.json` 骨架（项目根）

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "autoupdate": true,
  "permission": {
    "edit": "ask",
    "bash": "ask",
    "webfetch": "allow",
    "websearch": "allow",
    "skill": "allow",
    "mymcp_*": "ask"
  },
  "mcp": {
    "context7":       { "type": "local",  "command": ["npx","-y","@upstash/context7-mcp"], "enabled": true },
    "sequential-thinking": { "type": "local", "command": ["npx","-y","@modelcontextprotocol/server-sequential-thinking"], "enabled": true },
    "playwright":     { "type": "local",  "command": ["npx","-y","@playwright/mcp"], "enabled": true },
    "ontomind-onto":  { "type": "remote", "url": "https://onto.internal/mcp", "headers": {"Authorization":"Bearer ${ONTOMIND_TOKEN}"} }
  },
  "agent": {
    "aibi-planner":    { "mode": "primary",  "model": "anthropic/claude-sonnet-4-5" },
    "ontology-router": { "mode": "subagent", "permissions": ["read","grep","glob","skill","websearch"] },
    "sql-runner":      { "mode": "subagent", "permissions": ["read","bash"], "task": { "permissions": { "bash": "ask" } } },
    "evidence-binder": { "mode": "subagent", "permissions": ["read","edit"] }
  }
}
```

#### 7.3.2 `AGENTS.md`：项目级 System Prompt（Prompt 层）

推荐结构：
```
# OntoMind AIBI Data Agent
## Role
你是 OntoMind 的 AIBI 数据分析 Agent，遵守本体接地原则……
## 术语（本体词表最短表）
Party / LoanApplication / LoanContract / LoanAccount / RiskEvent / RepaymentBehavior / ...
## 输出契约
所有回答必须包含 evidence 字段：{entity_path, cq_id, sql, semantic_version}
## 禁令
- 禁止在未确认口径的情况下自由发明字段
- 禁止跨租户查询
- 禁止在 Plan 模式修改代码/数据
## 常用命令
python backend/... / npm run dev ...
```

#### 7.3.3 Subagent 拆分（Harness + Loop 层）

**Plan → Sub-agent 分工** 是 OpenCode 的最佳实践（Anthropic Planner/Generator/Evaluator 三角分工，与 Boris Cherny 的 orchestrator 思想一致）：

- `aibi-planner`（primary，Plan 模式起手）：把用户问题拆成 CQ
- `ontology-router`（subagent，只读）：查询本体服务，产出「候选类/关系/表白名单」
- `sql-runner`（subagent，写权限受控）：只按白名单执行 SQL
- `evidence-binder`（subagent，只读+写报告）：把结果绑上路径与版本，产 Evidence 报告
- `explore`（内置 subagent）：只读代码库/文档探索
- `general`（内置 subagent）：兜底并行任务

**关键收益**：子会话独立上下文——**不污染主对话，还能省 token**（第九章级别的实践）。

#### 7.3.4 Skill 系统（Context 层复用）

- 每个 Skill = 一个 `SKILL.md` + 可选 `references/` `scripts/` `assets/`
- Skill 支持 YAML frontmatter 内嵌 `mcp:`——**MCP 依赖跟 Skill 一起走，不用改全局配置**
- Skill 是 OpenCode 独有的"可复用工程经验"，天然对应 Context Engineering 的静态部分

**建议为 OntoMind 落 4 个 Skill**：
1. `ontology-query`：定义如何查询 OntoMind 认知层 API（含常用 CQ、路径查询、类映射）
2. `consumer-finance-glossary`：消金术语与口径口袋书（DPD/M1/GMV/首借/复借……）
3. `evidence-report`：Evidence 格式规范与模板
4. `data-source-registry`：数据源与表白名单的引用说明

#### 7.3.5 MCP 服务（Harness 工具面）

**优先接入的 4 个 MCP**：
1. `ontomind-ontology`（自研远程 MCP）：暴露认知层的检索/映射 API
2. `ontomind-warehouse`（自研）：受控的 SQL/OLAP 执行入口（白名单在服务端强制）
3. `context7`（社区）：官方文档搜索
4. `sequential-thinking`（Anthropic）：显式的多步推理外挂

**关键护栏**：`permission` 里把 `mymcp_*` 设为 `ask` 或 `deny`，让越权工具触发人工审批。

#### 7.3.6 Permission（Harness 安全边界）

```jsonc
"permission": {
  "edit": "ask",
  "bash": { "npm run *": "allow", "rm -rf *": "deny", "*": "ask" },
  "webfetch": "allow",
  "skill": "allow",
  "ontomind-warehouse_*": "ask"
}
```

配合 Plan 模式（默认 edit/bash = ask），可以做到"看方案 → 审 → 再放手"，与消金合规诉求匹配。

### 7.4 与 OntoMind 资源管理挂钩

`RESOURCE_MANAGEMENT_DESIGN.md` 已定义：

- **Instance** = 计算节点（SSH/Docker/K8s）
- **Agent**（type=opencode）= 内含 OpenCode 二进制 + 挂载 Skill 集
- **Skill** = 全局共享
- **MCP** = 从任意 HTTP API + LLM 自动推断 MCP 配置（sse/stdio/http）
- **AgentRun** = 运行日志 + WebSocket 流式推送

**建议做的挂钩**：
1. `Skill` 挂到 `Agent` 时同步注入 OpenCode 全局 `~/.config/opencode/` 或项目 `.opencode/`
2. `MCP` 生成后自动注入到目标 Agent 的 `opencode.json`
3. `AgentRun` 直接聚合 OpenCode 的 stdout/stderr/session 日志
4. 生产 Agent 执行面必须开鉴权（本文档反复强调的合规硬点）

### 7.5 一个完整的 AIBI 提问 → 回答流（示例）

```
用户："我们 A 产品 2025Q3 M3+ 逾期率 vs Q2，按渠道拆分为什么变化？"

OpenCode Loop:
1. aibi-planner (Plan 模式) → 拆成 3 个 CQ:
   CQ-A: 计算 A 产品 2025Q3/Q2 M3+ 逾期率（按渠道）
   CQ-B: 找出最大变化的渠道 Top 3
   CQ-C: 归因（申请量 / 通过率 / 打分卡版本 / 客群漂移）

2. ontology-router (subagent) → 调用 ontomind-ontology MCP:
   返回：LoanContract, LoanAccount, RepaymentBehavior, RiskEvent, AcquisitionChannel
        + 允许表: dw.fact_repay_daily / dim_product / dim_channel
        + 口径: metric_dpd_m3_v2 (version 2026-06-01)

3. sql-runner (subagent, Plan 通过后 Build):
   调用 ontomind-warehouse MCP，只能触达白名单表
   返回结果集 df_1, df_2

4. evidence-binder (subagent):
   产出 Evidence 报告：
     - CQ 通过率: 3/3
     - 使用口径: metric_dpd_m3_v2
     - 数据版本: dw@2026-07-08
     - 涉及实体: A 产品 → 3 个渠道 → N 个账户
     - 归因结论 + SQL 全文

5. Plan 模式最后一句："上面的分析可信可复现，是否执行推送到经营看板？(y/N)"
```

### 7.6 OpenCode 落地清单（可当 checklist）

- [ ] 项目根写 `AGENTS.md`（+ `~/.config/opencode/AGENTS.md` 全局约束）
- [ ] 项目根写 `opencode.json`（模型/权限/mcp/agent）
- [ ] 在 `.opencode/skills/` 下放 4 个自研 Skill
- [ ] 在 `.opencode/agent/` 下放 4 个自研 Agent（也可用 JSON 内联）
- [ ] 起 2 个自研 MCP（`ontomind-ontology` + `ontomind-warehouse`）+ 挂官方 MCP（context7 / sequential-thinking / playwright）
- [ ] `opencode agent list` 验证；`/init` 生成初版 AGENTS.md
- [ ] 内嵌 CQ 回归 + Evidence 报告作为持续评测
- [ ] AgentRun 日志接入 OntoMind Web UI

---

## 8. OntoMind 的行动清单（结合本调研）

### 8.1 认知层（Ontology / KG）

1. 认知层暴露"检索子图 + 类→表映射 + CQ 评测 + 版本 diff" 四个 API
2. 提供 FIBO 片段库作为可复用起点（不必一期全量导入）
3. 用户点"生成本体" → 走 delta 迭代管道（Retriever → Gen-LLM → Judge → CQ → 合并）
4. Judge-LLM 与专家评审做成流水线（SegmentFault Astrobee 的 Git-Diff 式协作值得借鉴）

### 8.2 应用层（AIBI Data Agent）

1. 应用层 Orchestrator = OpenCode Agent（type=opencode）承担
2. 自研 4 个子 Agent（planner / router / sql-runner / evidence-binder）
3. 自研 2 个 MCP（ontology / warehouse），warehouse 服务端硬做白名单
4. 提供 Evidence Binder UI，把"分析结论 + 自证报告"呈现给分析师
5. 落地 6-8 个 MVP CQ 作为首批场景（消金域）

### 8.3 资源管理

1. `opencode` 类型 Agent 一键部署到 Instance，自动挂载 Skill/MCP 配置
2. MCP 自动发现（URL + LLM 推断参数）作为差异化能力（RESOURCE_MANAGEMENT_DESIGN 已规划）
3. AgentRun 日志 WebSocket 流式，是 Harness 可观测性的核心

### 8.4 合规硬点

1. 生产 Agent 执行面必须鉴权（本地 CLI 不能直接顶生产）
2. `bash` / warehouse MCP 至少 `ask`，最好用租户隔离
3. 消费金融口径变动 → 语义层版本号必须变 → Agent 必须看到

---

## 9. 关键参考资料清单

### 9.1 本体论与知识图谱基础
- CSDN 石榴姐《本体论与知识图谱有什么区别？》2026-04
- 51CTO《本体论在 AI 时代的复兴：从哲学概念到 Agent 的世界模型》
- 腾讯云《硬核拆解：本体论到底是什么？Palantir 靠它做对了什么？》
- 阿里今日头条《本体论 vs 语义层：两种 AI 业务语义底座》
- GitCode《本体论（Ontology）基础知识》
- 51CTO《引入本体论以解决工业 AI 中的确定性与概率性冲突》

### 9.2 LLM 建本体
- 浙大宁波理工院《NeOn-GPT：基于 LLM 的本体学习管道》
- arXiv 2604.20795《Automatic Ontology Construction Using LLMs as an External Layer》
- arXiv 2604.09608《LOM: Unifying Ontology Construction and Semantic Alignment》
- Moonlight《Ontology Generation using Large Language Models》（Ontogenia / Memoryless CQbyCQ）
- 万方《一种基于大模型的工业领域本体自动化构建方法》（IORAG）
- DeepOnto（东南大学 & 阿姆斯特丹大学）本体嵌入与构建库

### 9.3 消费金融/信贷图谱
- 腾讯云《知识图谱技术在信贷领域的应用》（工行软开中心）
- CSDN《风控域——信贷风控知识图谱实战》
- 财富号《Agentic Ontology 平台，打造企业级 AI 知识基础设施》（FIBO 对齐）
- 《2026 中国消费金融市场风险控制与创新模式研究报告》

### 9.4 AIBI Data Agent / 语义层
- dbt docs《Semantic Layer vs. Text-to-SQL: 2026 Benchmark Update》
- SegmentFault 亿问《为什么指标语义层撑不住 Data Agent？》《BI 沉淀报表，Data Agent 沉淀什么？》
- SegmentFault 迈富时《Data Agent：以本体语义模型重构可信企业数据决策》
- 火山引擎 DataAgent OnPremise 文档
- Microsoft Learn《Create a Fabric data agent》（ontology 数据源）
- 墨天轮《Data Agent（ChatBI）生产落地：从"能演示"到"可规模化"》
- CSDN《本体论语境下的 Semantic Layer》

### 9.5 Prompt / Context / Harness / Loop Engineering
- 华为开发者《Prompt、Context、Harness Engineering：AI 工程化的三层进化之路》
- CSDN《AI 工程范式的三次演化：Prompt → Context → Harness》
- 掘金《Prompt Engineering、Harness Engineering 和 Context Engineering》
- 腾讯云《Loop Engineering 是什么？与 Prompt/Context/Harness 的区别》
- 腾讯云《从 Prompt 到 Harness：AI Agent 工程的三次范式迁移》
- MCP 技术社区《Agent Loop / Loop Engineering / Harness Engineering》
- InfoQ《AI 面试八股文 - Agent Loop 范式》
- DZone《Engineering Agentic AI for Production: A Distributed Systems Perspective》
- 墨天轮《Agent Harness：把"会说话的大脑"变成能干活的 Agent》
- Anthropic《Harness design for long-running application development》（Planner/Generator/Evaluator）
- Addy Osmani《Loop Engineering》
- 头条《别再死扣提示词，AI 智能体开始卷 Loop》

### 9.6 OpenCode 官方与实践
- 官方：opencode.ai/docs（config / agents / tools / mcp-servers）
- CSDN《OpenCode 入门宝典》《opencode Agent 详解》《第六章：Agent 与子代理自定义》
- SegmentFault《OpenCode 插件生态完整指南》
- 华为云社区《OpenCode 是什么？》《为什么 2026 年开发者都在谈论 OpenCode？》《从零开始学 OpenCode》
- 阿里云开发者社区《OpenCode 是什么？——终端里的开源 AI 编程 Agent 完全解读》
- B 站《OpenCode 新手教程》（Anthropic 官方视频转译）
- 51CTO《OpenCode 深入解析：使用 AI 编码助手提升开发效率的最佳实践》

---

## 10. 附录：可以直接抄的三份文件模板

### 10.1 `AGENTS.md`（放到项目根）
```markdown
# OntoMind — AIBI Data Agent System Instructions

## Role
你是 OntoMind 应用层的 AIBI Data Agent。所有回答必须**本体接地**：
- 使用认知层已登记的类/关系/指标
- 触达的数据源必须在白名单里
- 输出必须携带 evidence

## Domain Glossary (short)
- Party / Person / Organization
- LoanApplication / LoanContract / CreditProduct / LoanAccount
- Transaction / RepaymentBehavior / RiskEvent
- ScorecardModel / RiskFeature / StrategyRule
- Channel / Campaign / Case

## Output Contract
{
  "answer": "...",
  "evidence": {
    "entity_path": [...],
    "cq_ids": [...],
    "sql": "...",
    "semantic_version": "..."
  }
}

## Commands
- Backend dev: uvicorn app.main:app --reload --port 8000
- Frontend dev: npm run dev
- Tests: pytest / npm test

## Forbidden
- 自由发明字段
- 跨租户查询
- 未鉴权调用 warehouse MCP
```

### 10.2 `opencode.json`（放到项目根）
参见 §7.3.1。

### 10.3 `.opencode/agent/ontology-router.md`
```markdown
---
name: ontology-router
description: 把用户问题落到 OntoMind 本体的类/关系/CQ/表白名单
mode: subagent
model: anthropic/claude-sonnet-4-5
permission:
  edit: deny
  bash:
    "*": deny
  webfetch: allow
  websearch: allow
  skill: allow
---

# Ontology Router

任务：
1. 读取用户问题
2. 调用 `ontomind-ontology` MCP 的 `search_subgraph` 工具
3. 返回：类清单、关系清单、命中 CQ、表白名单、口径版本
4. **不要**生成 SQL / **不要**编造字段
```

---

## 11. 一句话收尾

> OntoMind 的胜负手，不在"能不能自动画出漂亮的本体图"，而在"**图能不能进 loop**"——
> 让 AIBI Data Agent 在 OpenCode / Harness 的循环里，把每一次分析都**约束在本体之上、可被 CQ 验证、带证据、能审计、可复现**。
> 这就是 Palantir 用十年时间证明的路径，也是 dbt 2026 Benchmark、迈富时/亿问/OntoFlow 正在国内本土化的方向——**OntoMind 恰好在窗口期**。
