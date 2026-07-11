"""生成剩余 11 个系统的 4 份文档。CIF 已手写为示范。

策略：
- 重点系统（进件/风控/信贷核心/财务）—— 每份 2000-3000 字
- 其他系统 —— 每份 1200-2000 字

模板结构固定，内容按系统职责填充。
"""
from __future__ import annotations
from pathlib import Path
import textwrap

BASE = Path(__file__).resolve().parent

# 系统元数据
SYSTEMS = [
    {
        "code": "02_loan_intake",
        "name_zh": "进件受理",
        "name_en": "Loan Intake",
        "db": "sim_loan_intake",
        "importance": "core",
        "purpose": "承接客户借款申请，收集必需资料，触发风控决策",
        "position": "中台",
        "tables": ["application", "application_status_log", "doc_upload",
                   "credit_report_pull", "intake_channel_ref"],
        "key_flows": ["申请提交", "资料上传", "征信拉取", "触发风控", "结果回调"],
        "upstream": ["APP/H5", "客户中心 CIF"],
        "downstream": ["风险决策 risk_decision", "信贷核心 credit_core"],
        "sla": {"availability": "99.9%", "P95_read": "200ms", "P95_write": "600ms"},
        "team_size": 6,
    },
    {
        "code": "03_risk_decision",
        "name_zh": "风险决策",
        "name_en": "Risk Decision",
        "db": "sim_risk_decision",
        "importance": "core",
        "purpose": "在申请、放款、贷中等关键节点执行规则+模型决策，返回批准/拒绝/复审",
        "position": "决策中枢",
        "tables": ["rule_set", "decision_log", "model_score",
                   "blacklist", "antifraud_event", "risk_grade", "policy_ref"],
        "key_flows": ["规则集编排", "模型评分", "反欺诈事件流处理", "决策落地", "客户风险等级维护"],
        "upstream": ["进件 loan_intake", "客户中心 CIF"],
        "downstream": ["信贷核心 credit_core", "催收 collection"],
        "sla": {"availability": "99.95%", "P95_read": "150ms", "P95_write": "500ms"},
        "team_size": 8,
    },
    {
        "code": "04_credit_core",
        "name_zh": "信贷核心",
        "name_en": "Credit Core",
        "db": "sim_credit_core",
        "importance": "core",
        "purpose": "承载授信额度、支用（放款）、还款计划、还款流水、逾期状态的全生命周期",
        "position": "业务中枢",
        "tables": ["product", "credit_limit", "loan", "loan_ledger", "repayment_plan",
                   "repayment_actual", "overdue_record", "contract", "fee_charge", "loan_status_log"],
        "key_flows": ["产品配置", "授信创建", "支用放款", "生成还款计划",
                      "还款处理", "逾期识别", "结清/坏账"],
        "upstream": ["风控决策 risk_decision", "进件 loan_intake"],
        "downstream": ["催收 collection", "财务 finance", "资金 funding"],
        "sla": {"availability": "99.99%", "P95_read": "180ms", "P95_write": "800ms"},
        "team_size": 10,
    },
    {
        "code": "05_collection",
        "name_zh": "催收管理",
        "name_en": "Collection",
        "db": "sim_collection",
        "importance": "std",
        "purpose": "接收逾期借据，编排催收案件，跟踪催收动作与还款承诺",
        "position": "后置",
        "tables": ["collection_case", "collection_action", "promise_to_pay", "collector"],
        "key_flows": ["逾期案件生成", "催收员分派", "多手段催收（电话/短信/上门）",
                      "承诺还款跟踪", "M1/M2/M3 升级"],
        "upstream": ["信贷核心 credit_core"],
        "downstream": ["客服 csm", "财务 finance"],
        "sla": {"availability": "99.5%", "P95_read": "300ms", "P95_write": "800ms"},
        "team_size": 5,
    },
    {
        "code": "06_funding",
        "name_zh": "资金/合作方",
        "name_en": "Funding & Partner",
        "db": "sim_funding",
        "importance": "std",
        "purpose": "管理资金合作方、协议、每笔借据的资金拆分与分润记录",
        "position": "中台",
        "tables": ["funding_partner", "funding_agreement", "loan_funding_split",
                   "profit_share_record", "partner_settle", "guarantee_record"],
        "key_flows": ["合作方入驻", "协议签订", "放款时资金拆分",
                      "每期分润计算", "月度结算"],
        "upstream": ["信贷核心 credit_core"],
        "downstream": ["财务 finance"],
        "sla": {"availability": "99.9%", "P95_read": "200ms", "P95_write": "500ms"},
        "team_size": 4,
    },
    {
        "code": "07_finance",
        "name_zh": "财务",
        "name_en": "Finance",
        "db": "sim_finance",
        "importance": "core",
        "purpose": "总账凭证、资金结算、税务、对账、利息与手续费收入记录",
        "position": "后置",
        "tables": ["gl_account", "gl_journal", "settlement", "tax_record",
                   "reconcile_log", "fee_income", "interest_income"],
        "key_flows": ["会计科目维护", "凭证生成", "资金结算",
                      "月度税务申报", "日终对账"],
        "upstream": ["信贷核心 credit_core", "资金 funding"],
        "downstream": ["数仓 dw", "外部税务系统"],
        "sla": {"availability": "99.9%", "P95_read": "500ms", "P95_write": "1s"},
        "team_size": 6,
    },
    {
        "code": "08_marketing",
        "name_zh": "营销",
        "name_en": "Marketing",
        "db": "sim_marketing",
        "importance": "std",
        "purpose": "渠道、活动、投放成本、归因、优惠码的管理",
        "position": "前置",
        "tables": ["channel", "campaign", "ad_cost",
                   "attribution", "promo_code", "user_promo_use"],
        "key_flows": ["渠道接入", "活动上线", "每日成本回传",
                      "归因计算", "优惠码使用"],
        "upstream": ["外部广告平台"],
        "downstream": ["进件 loan_intake", "客户中心 CIF", "数仓"],
        "sla": {"availability": "99.5%", "P95_read": "300ms", "P95_write": "1s"},
        "team_size": 5,
    },
    {
        "code": "09_events",
        "name_zh": "埋点收集",
        "name_en": "Events",
        "db": "sim_events",
        "importance": "std",
        "purpose": "APP/H5 埋点接入，页面浏览、事件、点击流三个粒度",
        "position": "前置",
        "tables": ["app_event", "page_view", "click_stream"],
        "key_flows": ["埋点 SDK 上报", "服务端校验", "落库", "实时推送数仓"],
        "upstream": ["APP", "H5", "微信小程序"],
        "downstream": ["数仓 dw", "营销 marketing"],
        "sla": {"availability": "99.5%", "P95_read": "N/A", "P95_write": "500ms"},
        "team_size": 3,
    },
    {
        "code": "10_csm",
        "name_zh": "客服",
        "name_en": "CSM",
        "db": "sim_csm",
        "importance": "std",
        "purpose": "客户工单、通话记录、投诉的统一处理",
        "position": "后置",
        "tables": ["ticket", "call_record", "complaint", "ticket_action"],
        "key_flows": ["工单创建", "分派处理", "通话录音关联", "投诉升级",
                      "满意度调研"],
        "upstream": ["APP", "电话呼叫中心", "微信"],
        "downstream": ["合规 legal", "运营"],
        "sla": {"availability": "99.5%", "P95_read": "300ms", "P95_write": "800ms"},
        "team_size": 4,
    },
    {
        "code": "11_hr_iam",
        "name_zh": "HR & 权限",
        "name_en": "HR & IAM",
        "db": "sim_hr_iam",
        "importance": "std",
        "purpose": "组织架构、员工、角色、权限统一管理",
        "position": "后台",
        "tables": ["org_unit", "employee", "role", "user_role"],
        "key_flows": ["组织架构维护", "员工入离职", "角色分配", "权限校验"],
        "upstream": ["HR 系统"],
        "downstream": ["全部业务系统"],
        "sla": {"availability": "99.9%", "P95_read": "150ms", "P95_write": "500ms"},
        "team_size": 3,
    },
    {
        "code": "12_dp_meta",
        "name_zh": "数据平台元数据",
        "name_en": "DP Meta",
        "db": "sim_dp_meta",
        "importance": "std",
        "purpose": "维护数仓表元数据、ETL 任务、数据血缘",
        "position": "后台",
        "tables": ["table_meta", "etl_job", "data_lineage"],
        "key_flows": ["元数据登记", "血缘图谱构建", "任务调度记录"],
        "upstream": ["数仓开发人员"],
        "downstream": ["数据部门内部使用"],
        "sla": {"availability": "99%", "P95_read": "500ms", "P95_write": "1s"},
        "team_size": 2,
    },
]


def gen_brd(s):
    tables_list = "\n".join(f"- `{t}`" for t in s["tables"])
    flows_list = "\n".join(f"{i+1}. {f}" for i, f in enumerate(s["key_flows"]))
    is_core = s["importance"] == "core"

    core_extra = ""
    if is_core:
        core_extra = textwrap.dedent(f"""\

        ## 附：{s['name_zh']}系统的核心业务价值深挖

        作为公司**核心业务系统之一**，{s['name_zh']}的成败直接影响以下 KPI：

        1. **业务连续性**：作为{s['position']}系统，一旦出现故障将阻塞主流程
        2. **数据资产质量**：本系统数据是数仓 DWD/DWS 层的核心来源
        3. **合规风险控制**：直接对接监管报送需求
        4. **业务快速迭代**：新产品接入依赖本系统的能力扩展

        ### 关键业务场景说明

        本系统在四大产品形态（自营/助贷/联合贷/担保）中承担关键节点：
        - **自营信贷（信优速贷）**：全流程自主决策
        - **助贷（信优合作贷）**：与资金方共担部分决策
        - **联合贷（信优联合贷）**：与合作方并联决策
        - **担保业务（信优保贷）**：担保方兜底约束

        ### 业务规则示例

        - 单客户日申请限流 3 次
        - 相同产品 30 天内重复申请须触发额外校验
        - 高风险产品（如担保业务）需二次人工审核
        - 拒绝原因需分级：HARD_REJECT (硬拒) / SOFT_REJECT (软拒可复议) / WARNING

        ### 关键运营策略

        - **产品差异化定价**：不同风险等级 (A/B/C/D/E) 匹配不同利率区间
        - **额度动态调整**：客户历史行为决定授信额度动态调整
        - **风控策略灰度**：新规则先小流量灰度验证 A/B 效果

        ### 度量口径明细

        - 系统 SLA 100% 覆盖生产变更
        - 每季度输出 KPI 复盘报告
        - 与业务、数据、财务三方对齐口径
        """)

    return textwrap.dedent(f"""\
    # {s['name_zh']} ({s['name_en']}) — BRD 业务需求文档

    - **系统代号**：{s['name_en']}
    - **文档版本**：v1.0
    - **发布日期**：2024-11-30
    - **系统位置**：{s['position']}
    - **数据库**：`{s['db']}`
    - **文档负责人**：产品经理

    ## 一、业务背景

    信优消费金融公司在业务快速发展过程中，需要一套专门的**{s['name_zh']}系统**来支撑核心业务能力。该系统的核心职责是**{s['purpose']}**。

    在没有该系统之前，公司相关能力散落于其他业务系统中，存在以下问题：
    - 职责边界不清晰，跨系统协同复杂，故障排查耗时长
    - 数据口径不一致，同一业务概念多种叫法
    - 变更影响面难以评估，重构风险高
    - 无法独立扩展与治理，性能瓶颈难以突破
    - 合规审计流程混乱，报送耗时高

    独立建设 {s['name_zh']} 系统，可以：
    - **清晰边界**：单一职责，便于维护与迭代
    - **能力复用**：跨产品线共享，避免重复造轮子
    - **精细度量**：单独度量该系统 SLA 与业务贡献
    - **合规可控**：单独设置访问权限与审计
    - **技术演进**：可独立升级技术栈

    ## 二、目标用户

    | 角色 | 主要诉求 | 使用场景 |
    |---|---|---|
    | 内部业务人员 | 通过该系统完成日常业务操作 | 每日高频使用 |
    | 上游系统 ({', '.join(s['upstream'])}) | 提交业务请求，获取处理结果 | API 集成 |
    | 下游系统 ({', '.join(s['downstream'])}) | 消费该系统产生的业务事件 | 事件订阅 |
    | 数据部门 | 从该系统抽数入仓，做分析报表 | T+1 抽数 |
    | 合规部门 | 审计业务操作，输出监管报送 | 每月/季度 |
    | 运维/技术 | 监控告警、故障排查 | 全时段 |

    ## 三、业务价值

    1. **业务闭环**：让 {s['name_zh']} 业务在系统层面完整落地
    2. **数据资产**：沉淀高质量业务数据，供 Data Agent、指标平台使用
    3. **服务可用性**：独立部署、独立扩展、独立监控
    4. **组织协同**：明确团队职责，减少跨部门推诿
    5. **快速迭代**：新需求 1-2 周即可上线小改动
    6. **合规达标**：满足《消费金融公司管理办法》相关要求

    ## 四、关键业务流程

    该系统覆盖以下核心流程：

    {flows_list}

    每个流程都要求：
    - **可观测**：全链路埋点，可追溯每次业务动作
    - **可回滚**：状态机保证异常时可回退到前一态
    - **可审计**：所有关键操作留日志 ≥ 3 年
    - **可扩展**：新增业务场景无需大改主流程

    ## 五、关联表清单

    {tables_list}

    详见 `../../systems/{s['code']}/schema.sql`。表结构设计遵循：
    - 主键使用递增或雪花 ID
    - 状态字段带索引
    - 时间字段带索引（`created_at`、`updated_at`）
    - 敏感字段加密存储

    ## 六、相关系统

    - **上游**：{', '.join(s['upstream'])}
    - **下游**：{', '.join(s['downstream'])}

    上下游之间通过以下方式集成：
    - 同步：REST/gRPC API
    - 异步：RocketMQ 事件驱动
    - 批量：数仓 T+1 抽取

    ## 七、关键业务指标

    | 指标 | 目标 |
    |---|---|
    | 系统可用性 | {s['sla']['availability']} |
    | 数据完整率 | ≥ 99.5% |
    | 相关业务量 | 见数仓 DWS 层 |
    | 数据一致性 | 与上游 100% 对齐 |
    | 平均响应时间 | 见 TDD 文档 |
    | 客服投诉率 | ≤ 0.1% |

    ## 八、合规要求

    - 《消费金融公司管理办法》相关条款
    - 数据保留 ≥ 5 年
    - 敏感字段加密存储（AES-256）
    - 审计日志保留 ≥ 3 年
    - 数据脱敏展示

    ## 九、里程碑

    | 阶段 | 时间 | 交付 |
    |---|---|---|
    | V1 需求评审 | 2024-11-30 | 本 BRD 通过 |
    | V1 上线 | 2025-01-01 | 覆盖核心流程 |
    | V1.1 规划 | 2025-Q3 | 优化与扩展 |
    | V2.0 规划 | 2026-H1 | 深度集成 AI Agent |
    {core_extra}
    """)


def gen_prd(s):
    tables_list = "\n".join(f"| {t} | 详见 schema.sql |" for t in s["tables"])
    flows_list = "\n".join(f"### UC-{i+1:02d} {f}\n\n**触发条件**：见 BRD 章节四\n**前置条件**：上游系统已完成前置动作\n**主流程**：\n1. 接收业务请求\n2. 参数校验 + 幂等去重\n3. 调用领域服务处理\n4. 持久化 + 发消息\n5. 返回结果\n\n**异常处理**：熔断降级；重试 3 次后转异步补偿。\n" for i, f in enumerate(s["key_flows"]))

    is_core = s["importance"] == "core"
    core_extra = ""
    if is_core:
        core_extra = textwrap.dedent(f"""\

        ## 十、核心业务规则详细说明（重点系统必备）

        ### 10.1 幂等设计
        所有写接口必须支持幂等，客户端传 `Idempotency-Key`，服务端 Redis 存 24 小时。

        ### 10.2 状态机
        核心业务实体的状态转移需通过状态机管理，非法状态转移直接拒绝并记录。

        ### 10.3 事件发布
        每个关键业务动作发布事件到 RocketMQ，事件包含：
        - `event_id`（UUID）
        - `event_type`
        - `occurred_at`
        - `payload`
        - `trace_id`

        ### 10.4 灰度发布
        新规则/新流程支持按客户 / 按渠道 / 按比例灰度。

        ### 10.5 数据完整性
        跨系统同步采用最终一致性，通过每日对账脚本兜底。

        ### 10.6 全链路 trace
        通过 `trace_id` 串联所有服务的日志，便于故障排查。
        """)

    return textwrap.dedent(f"""\
    # {s['name_zh']} — PRD 产品需求文档

    - **产品名称**：{s['name_zh']} ({s['name_en']})
    - **版本**：v1.0
    - **数据库**：`{s['db']}`
    - **产品负责人**：产品经理

    ## 一、产品范围

    {s['name_zh']}系统提供 **{s['purpose']}** 的完整产品能力。

    **在范围内**：
    {chr(10).join(f'- {f}' for f in s['key_flows'])}

    **不在范围内**：
    - 属于上游系统的能力（如客户主档由 CIF 负责）
    - 属于下游系统的能力（如财务凭证由 finance 负责）
    - 属于数仓的能力（原始明细汇总由 dw 负责）

    ## 二、用户角色 & 权限

    | 角色 | 权限 |
    |---|---|
    | 系统对接账号 | API 读写（白名单） |
    | 业务操作员 | 台内操作 |
    | 审核员 | 只读 + 审批 |
    | 管理员 | 全部 + 配置 |
    | 合规官 | 只读 + 审计 |

    ## 三、核心用例

    {flows_list}

    ## 四、功能列表

    | 表/资源 | 提供的能力 |
    |---|---|
    {tables_list}

    ## 五、流程图

    ```mermaid
    graph LR
        A[{', '.join(s['upstream'])}] --> B[{s['name_zh']}]
        B --> C[{', '.join(s['downstream'])}]
        B --> D[(MySQL {s['db']})]
    ```

    ## 六、交互规则

    - **幂等性**：所有写接口幂等（客户端提供 idempotency-key）
    - **审计**：核心状态变更留 audit trail
    - **限流**：单客户 QPS ≤ 20，单接口 QPS ≤ 1000
    - **异常回滚**：分布式事务用 Saga，失败自动补偿
    - **异步优先**：非关键路径全部异步化
    - **降级策略**：依赖故障时按预定义降级方案继续提供有限能力

    ## 七、数据规则

    - 主键：见 schema.sql
    - 索引：详见 schema.sql
    - 唯一性：见 UNIQUE KEY
    - 状态机：核心表带 `status` 字段，转换需通过状态日志表记录

    ## 八、验收标准

    - [x] 覆盖 {len(s['key_flows'])} 个核心用例
    - [x] 与上游/下游联调通过
    - [x] 单元测试覆盖率 ≥ 80%
    - [x] 通过安全测试
    - [x] 通过性能压测（QPS 达标）

    ## 九、非功能需求

    - **可用性**：{s['sla']['availability']}
    - **性能**：P95 读 {s['sla']['P95_read']}，写 {s['sla']['P95_write']}
    - **安全**：全链路 TLS 1.3；等保 3.0
    {core_extra}
    """)


def gen_tdd(s):
    tables_list = "\n".join(f"    {t} : (详见 schema.sql)" for t in s["tables"])
    is_core = s["importance"] == "core"

    core_extra = ""
    if is_core:
        core_extra = textwrap.dedent(f"""\

        ## 十一、系统架构关键决策

        ### 11.1 分层架构
        - **接入层**：API Gateway，负责鉴权/限流/路由
        - **业务层**：领域服务，纯业务逻辑
        - **数据层**：Repository 模式封装 DAO
        - **消息层**：MQ Producer/Consumer

        ### 11.2 数据一致性策略
        - 同库跨表：本地事务
        - 跨库跨系统：Saga 长事务 + 事件补偿
        - 读写分离：读走从库（可能有 100ms 延迟）
        - 强一致读：显式指定走主库

        ### 11.3 高可用
        - 多可用区部署
        - 自动故障切换
        - 熔断限流（Sentinel）
        - 全链路压测（每季度）

        ### 11.4 可观测性
        - Metrics：Prometheus
        - Tracing：SkyWalking
        - Logs：ELK
        - APM：全链路 trace

        ### 11.5 数据加密
        - 传输：TLS 1.3
        - 存储：字段级 + 表级 TDE
        - KMS：托管密钥轮换

        ## 十二、生产环境规格

        - 服务 Pod：4 replicas × 2 core / 4G RAM
        - MySQL：主 8C32G，从 x 2
        - Redis：3 主 3 从
        - MQ：3 broker 集群
        - 日均调用量：~ 100 万次
        - 峰值 QPS：预留 3 倍容量
        """)

    return textwrap.dedent(f"""\
    # {s['name_zh']} — TDD 技术设计文档

    - **技术负责人**：架构师
    - **版本**：v1.0
    - **数据库**：`{s['db']}`

    ## 一、总体架构

    ```mermaid
    graph LR
        subgraph 上游
            U[{', '.join(s['upstream'])}]
        end
        subgraph {s['name_zh']} 服务
            API[REST/gRPC API]
            SVC[Service Layer]
            DAL[Data Access Layer]
            MQ_P[MQ Producer]
        end
        subgraph 下游
            D[{', '.join(s['downstream'])}]
        end
        U --> API
        API --> SVC
        SVC --> DAL
        SVC --> MQ_P
        DAL --> DB[(MySQL {s['db']})]
        MQ_P --> D
    ```

    ## 二、技术选型

    | 层 | 技术 |
    |---|---|
    | 语言 | Java 17 / Spring Boot 3 |
    | 数据库 | MySQL 8.0（主从） |
    | 缓存 | Redis 7 |
    | MQ | RocketMQ 5 |
    | 网关 | Spring Cloud Gateway |
    | 监控 | Prometheus + Grafana + SkyWalking |
    | 部署 | Kubernetes |

    ## 三、数据模型

    表清单（DDL 见 `../../systems/{s['code']}/schema.sql`）：

    {tables_list}

    ## 四、关键接口清单

    - `POST /{s['name_en'].lower().replace(' ', '-')}/...`
    - `GET  /{s['name_en'].lower().replace(' ', '-')}/...`
    - `PUT  /{s['name_en'].lower().replace(' ', '-')}/...`

    详细契约见 OpenAPI 附件。

    ## 五、关键算法/机制

    ### 5.1 唯一 ID 生成
    使用 Snowflake（或 UUID v7）保证全局唯一 & 时序单调。

    ### 5.2 状态机
    核心业务表状态流转：
    - 通过 `*_status_log` 表记录每次变更
    - 变更需经过状态机校验合法性

    ### 5.3 事件通知
    写事件到 RocketMQ Topic，下游消费。

    ## 六、部署 & 环境

    - dev / test / staging / prod
    - MySQL 主从
    - Pod 副本数：4

    ## 七、监控 & 告警

    | 监控项 | 阈值 |
    |---|---|
    | P95 读 | {s['sla']['P95_read']} |
    | P95 写 | {s['sla']['P95_write']} |
    | 错误率 | > 1% 告警 |
    | 连接池 | > 80% 告警 |

    ## 八、安全设计

    - TLS 1.3
    - 字段级加密（敏感数据）
    - RBAC
    - 全量审计

    ## 九、容量规划

    | 项 | 当前 | 3 年后 |
    |---|---|---|
    | QPS | 见基线 | 3–5x |
    | 存储 | 见基线 | 需分库分表 |

    ## 十、风险与降级

    - 依赖故障：熔断 + 降级
    - 数据库故障：主从切换
    - 缓存穿透：布隆过滤器
    {core_extra}
    """)


def gen_project(s):
    is_core = s["importance"] == "core"
    core_extra = ""
    if is_core:
        core_extra = textwrap.dedent(f"""\

        ## 十、详细项目治理

        ### 10.1 需求管理流程
        - 每周需求评审会（周二 10:00）
        - 需求走 Jira，从 Backlog → In Progress → In Review → Done
        - PRD 需 PM + 架构师双签才能进开发

        ### 10.2 代码质量
        - 每次 MR 至少 2 人 review
        - CI 强制：单测 + 集成测 + 静态扫描
        - 覆盖率不达标不允许合并
        - Java 用 Google Java Style，Python 用 Black + Ruff

        ### 10.3 变更管理
        - 所有生产变更走 CAB 评审
        - 高风险变更需在周会讨论
        - 变更窗口：非高峰期（工作日 22:00-2:00）

        ### 10.4 应急响应
        - P0 事件：15 分钟内响应，1 小时内恢复
        - P1 事件：30 分钟响应，4 小时恢复
        - 事后必写 RCA（Root Cause Analysis），每季度复盘

        ### 10.5 团队协同
        - Daily standup（15 分钟）
        - Sprint 双周迭代
        - 每季度 OKR review
        - 半年一次团队建设

        ### 10.6 知识管理
        - 所有决策留在 Confluence
        - Runbook 每季度更新
        - 新人 Onboarding SOP

        ### 10.7 数据治理
        - 敏感数据分级分类
        - 数据访问权限审批
        - 每季度数据质量报告

        ### 10.8 供应商管理
        - 三方 API 服务定期评估
        - 备用供应商预案
        - SLA 违约条款
        """)

    return textwrap.dedent(f"""\
    # {s['name_zh']} — 项目管理文档

    - **项目代号**：Project-{s['name_en'].replace(' ', '')}
    - **周期**：2024-09-01 ~ 2025-03-31
    - **团队规模**：{s['team_size']} 人

    ## 一、里程碑

    | 阶段 | 起止 | 关键交付 | 状态 |
    |---|---|---|---|
    | M1 需求 | 09/01–10/15 | BRD/PRD 通过 | ✅ |
    | M2 设计 | 10/16–11/30 | TDD 定稿 | ✅ |
    | M3 开发 | 12/01–01/31 | 后端 + 前端 | ✅ |
    | M4 联调 | 02/01–02/20 | 与上下游联调 | ✅ |
    | M5 测试 | 02/21–03/10 | 功能/性能/安全 | ✅ |
    | M6 灰度 | 03/11–03/20 | 5% 流量 | ✅ |
    | M7 上线 | 03/21 | 全量 | ✅ |
    | M8 优化 | 03/22–03/31 | 监控 + bug 修复 | ✅ |

    ## 二、团队（RACI）

    | 任务 | R | A | C | I |
    |---|---|---|---|---|
    | 需求 | PM | 产品总监 | 业务/合规 | 全体 |
    | 设计 | 架构师 | CTO | PM | 团队 |
    | 开发 | 后端 Lead | 架构师 | DBA | QA |
    | 测试 | QA Lead | QA Mgr | 开发 | PM |
    | 部署 | 运维 | 运维总监 | 架构 | 全体 |
    | 合规审计 | 合规官 | CCO | 法务 | CTO |

    ## 三、依赖

    - 上游系统 API：{', '.join(s['upstream'])}
    - 下游系统事件订阅：{', '.join(s['downstream'])}
    - 基础设施：MySQL、Redis、RocketMQ、K8s
    - 第三方 SDK/API：见 TDD 文档

    ## 四、风险登记

    | # | 风险 | 概率 | 影响 | 应对 | 状态 |
    |---|---|---|---|---|---|
    | R1 | 依赖系统不稳定 | 中 | 高 | 熔断 + 降级 | 已闭环 |
    | R2 | 数据一致性 | 中 | 中 | 双写校验 + 补偿 | 已闭环 |
    | R3 | 性能不达标 | 低 | 高 | 压测 + 优化 | 已闭环 |
    | R4 | 合规审计不通过 | 低 | 极高 | 合规提前介入 | 已闭环 |
    | R5 | 上下游联调阻塞 | 中 | 中 | 提前定义 Mock，允许并行开发 | 已闭环 |

    ## 五、上线 Checklist

    - [x] BRD/PRD/TDD 全部评审
    - [x] 代码 review 100%
    - [x] 单测 ≥ 80%
    - [x] 压测通过
    - [x] 安全测试通过
    - [x] 灰度观察 3 天
    - [x] 监控告警到位
    - [x] 应急预案
    - [x] 合规审计通过
    - [x] 关键指标 dashboard 上线
    - [x] Runbook 完成

    ## 六、迭代记录

    ### v1.0.0（2025-03-21）
    - 首次上线，覆盖核心用例
    - 完成上下游联调

    ### v1.0.1（2025-04-15）
    - 修复：状态机异常回滚逻辑
    - 优化：批量接口 P95 从 800ms → 300ms

    ### v1.0.2（2025-05-10）
    - 新增：审计日志字段完善
    - 优化：数据库慢查询治理

    ### v1.1.0-alpha（规划中）
    - 集成 AI Agent 能力
    - 支持更细粒度的灰度发布

    ## 七、上线后关键指标

    | 指标 | 目标 | 实际 |
    |---|---|---|
    | 可用性 | {s['sla']['availability']} | 达标 |
    | P95 读 | {s['sla']['P95_read']} | 达标 |
    | P95 写 | {s['sla']['P95_write']} | 达标 |
    | 错误率 | < 0.1% | 0.03% |
    | 客户投诉相关工单 | ≤ 20/月 | 12/月 |

    ## 八、经验教训

    1. **依赖前置**：提前和上下游系统对齐接口契约
    2. **灰度充分**：不要跳过灰度直接全量
    3. **监控先行**：上线前监控必须到位
    4. **合规同步**：合规团队从需求阶段就介入
    5. **文档留存**：所有决策必须落到 Confluence

    ## 九、后续 Roadmap

    - 2025 Q3: 能力扩展、性能优化
    - 2025 Q4: 数据治理深化
    - 2026 H1: 与 AI Agent 集成
    - 2026 H2: 多租户能力预研
    {core_extra}
    """)


def main():
    docs_dir = BASE.parent / "docs"
    for s in SYSTEMS:
        dir_ = docs_dir / s["code"]
        dir_.mkdir(parents=True, exist_ok=True)
        (dir_ / "BRD_业务需求.md").write_text(gen_brd(s))
        (dir_ / "PRD_产品需求.md").write_text(gen_prd(s))
        (dir_ / "TDD_技术设计.md").write_text(gen_tdd(s))
        (dir_ / "PROJECT_项目管理.md").write_text(gen_project(s))
        print(f"  ✓ {s['code']}: 4 docs")
    print(f"\n总计生成 {len(SYSTEMS)*4} 份文档")


if __name__ == "__main__":
    main()
