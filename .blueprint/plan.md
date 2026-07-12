# Wave 10 — 智能体资源平台重构 (Agent Resource Platform)

## 背景
用户对 Wave 9 的 Agent Looper 功能做完后，觉得资源管理页面（`/resources`）设计太传统、缺乏创新性、功能不完整。需要彻底重构：

1. **命名体系**：计算节点 → 智能体容器 → 智能体 → Skill → MCP 的五层体系
2. **自动发现**：从用户的 opencode 配置中自动发现 MCP、Skill、Agent、智能体容器
3. **Agent Looper SOP**：基于 eval hooks 的面向结果的 agent 流程定制
4. **Agent 嵌入**：定制好的 agent 可以嵌入到其他页面（如 AIBI、元数据标注）
5. **长任务管理**：类似 ETL 的 job 管理，短任务对话交互，长任务 task job 可追踪
6. **UX 创新**：Cmd+K 全能搜索栏、Zen/God 双模式、渐进式披露、零学习曲线

## 名词体系（命名的语义）

- **计算节点** (Compute Node) — 一台物理机/虚拟机，运行智能体容器的宿主机。自动发现本地机器作为第一个节点。
- **智能体容器** (Agent Container) — 运行在计算节点上的 AI Agent 运行时，如 opencode、openclaw、harness。每个容器可以运行多个智能体。
- **智能体** (Agent) — 运行在智能体容器里的 AI Agent 实例。类似 opencode 的 subagent 概念。Agent Looper 定制的就是智能体。
- **Skill** (技能模块) — 给智能体加载的能力模块。对应 opencode 里 `~/.config/opencode/skills/*/SKILL.md`。Skill 可以被多个智能体共享。
- **MCP** (工具连接) — Model Context Protocol 工具。对应 opencode 里 `opencode.json` 的 `mcp:*` 配置。MCP 也可以被多个智能体共享。

## 共享原则
- Skill 和 MCP 在**智能体容器级别**配置（opencode 本身就支持全局 mcp 和 skills）
- 默认所有智能体自动继承容器的 Skill 和 MCP
- 也支持智能体级别单独绑定/排除 Skill 和 MCP

## 架构决策

### 数据模型（5 张核心表 + 7 张关联表）
- `compute_nodes` — 计算节点（原 instances 表扩展）
- `agent_containers` — 智能体容器（NEW，代替原 agents 表的部分功能）
- `agents` — 智能体（原 agent_looper_configs 更名为 agents，与 opencode 的 agent 概念统一）
- `skills` — 技能模块（原 skills 表，扩展 opencode SKILL.md 支持）
- `mcps` — 工具连接（原 mcp_configs 表，扩展 opencode 原生支持）
- `node_containers` — 节点↔容器关联（NEW）
- `container_agents` — 容器↔智能体关联（NEW）
- `container_skills` — 容器↔Skill 关联（NEW）
- `container_mcps` — 容器↔MCP 关联（NEW）
- `agent_skills` — 智能体↔Skill 绑定/排除（NEW）
- `agent_mcps` — 智能体↔MCP 绑定/排除（NEW）
- `agent_run_jobs` — 长任务 job（NEW，替代原 agent_run + task 的乱象）

### 后端（8 个新服务 + 3 个扩展）
- `ComputeNodeService` — 注册/发现/心跳
- `AgentContainerDiscoveryService` — 扫描 opencode/openclaw/harness 进程
- `AgentService` — 智能体 CRUD（原 AgentLooperService 升级）
- `SkillService` — 技能模块管理 + opencode 同步
- `MCPService` — 工具连接管理 + opencode 同步
- `OpencodeConfigDiscoveryService` — 从 `~/.config/opencode/` 发现 MCP/Skill/Agent
- `AgentLoopService` — Agent Loop SOP 引擎（状态机 + eval hooks）
- `AgentJobService` — 长任务生命周期管理
- `AgentEmbedService` — 智能体嵌入其他页面的桥接服务

### 前端（重构 `/resources` + 新增 3 个页面）
- 重构 `resources/index.tsx` — 计算节点/容器/智能体/Skill/MCP 五层导航
- 新增 `AgentJobPage` — 长任务管理仪表盘（ETL 风格）
- 新增 `AgentLooperPage` — 向导 rumiš 升级版（SOP + eval hooks）
- 新增 `CmdKOmnibar` — 全局 Cmd+K 全能搜索栏
- 新增 `<AgentEmbedRunner>` — 嵌入其他页面的 agent 运行组件

### UX 原则
- **Cmd+K 第一入口** — 从任何页面按 Cmd+K 打开全能搜索栏，覆盖搜索/助手/操作
- **Zen/God 双模式** — 默认 Zen（简洁卡片），点击卡片翻转查看 God 模式（原始 JSON/日志）
- **渐进式披露** — 高级功能需要时才显示，从不出现在第一屏
- **零学习曲线** — 3-5 个模板作为 onboarding，无文档教程
- **始终显示当前步骤** — 用中文描述当前操作，禁止显示 "…thinking"

## 任务依赖图（20 个 task，5 波）

```
W1 (命名体系 + 数据模型重构 — 2 并行 (T44 T46 并行 → T47 T48 → T45)):
  T44 数据模型重构（5 核心表 + 7 关联表）
  T45 前后端命名体系更新（Instance→ComputeNode, AgentLooper→Agent, 路由/DTO 重命名）
  T46 Opencode 配置发现服务（MCP + Skill 自动发现）
  T47 计算节点 + 智能体容器自动发现增强
  T48 技能 + MCP 同步服务（opencode.json ↔ DB 双向同步）

W2 (前端资源页重构 — 3 并行 (T49 → T50 T51 T52)):
  T49 资源页全新 UI（5 层导航 + 统计大盘 + 自动发现入口）
  T50 计算节点 + 容器详情页
  T51 智能体详情页（升级版 Agent Looper 详情）
  T52 技能 + MCP 详情页（显示来自 opencode 的配置 + 手动管理）

W3 (Agent Loop SOP 引擎 — 2 并行 (T53 → T54 T55 → T56)):
  T53 Agent Loop 状态机引擎（eval hooks + 迭代 + checkpoint）
  T54 SOP 编辑器（可视化 DAG / 自然语言 SOP / 模板库）
  T55 长任务 Job 管理（ETL 风格仪表盘 + 状态机）
  T56 智能体嵌入框架（<AgentEmbedRunner> + postMessage 协议）

W4 (UX 创新 — 4 并行 (T57 T58 T59 T60)):
  T57 Cmd+K 全能搜索栏（全局快捷键 + 三模式 + 上下文感知）
  T58 Zen/God 双模式切换 + 渐进式披露
  T59 Agent 交互面板升级（流式 tool parts + 审批流）
  T60 模板库 + 零学习曲线 onboarding

W5 (集成 + E2E — 串行 (T61 → T62 → T63)):
  T61 int-full-w10 集成 + 全套回归
  T62 Playwright E2E（20+ spec）
  T63 最终合并到 main
```

> 实际依赖图见各 task 的 depends_on 字段

团队成员：1 人（全栈开发）
预估时间：W1 2天 / W2 2天 / W3 3天 / W4 2天 / W5 1天 = 总计约 10 个工作日

## 非目标
- 不引入 Temporal（MySQL 8.0 状态机足矣，跑在 <1h 的任务不需要 Temporal 的复杂度）
- 不引入 AI SDK / assistant-ui（自己实现轻量级 postMessage 协议）
- 不重构 5 层架构的其他页面（只改 `/resources`）
- 不实现跨域 iframe 嵌入（只做同源嵌入）

## 设计中使用的参考来源
- Anthropic "Building Effective Agents" — 5 种 workflow 模式 + Evaluator-Optimizer (eval hook 原型)
- Anthropic "Harness Design for Long-Running Apps" — GAN 式 generator/evaluator 分离
- LangGraph 状态机 + 条件边 + 检查点 — checkpointer 模式
- CrewAI Sequential/Hierarchical Process — SOP 原语
- Temporal 任务生命周期 + 确定性 replay — 长任务耐久性
- Opencode 原生配置格式 — MCP command/json + SKILL.md frontmatter
- ACP Agent Run Lifecycle — 状态机转换表
- Omics-OS OmniBar — Cmd+K 三模式
- Vercel AI SDK useChat parts — tool 流式渲染
- 渐进式披露 PLG 手册 — 触发式进阶
