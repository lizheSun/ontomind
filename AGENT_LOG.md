# Agent 操作记录

> **用途**: 多 Agent 协同开发时，记录每次操作的目的、内容和影响范围，方便其他 Agent 快速理解上下文。

---

## 2026-08-14

### Agent: Wiki 知识库 + 元数据自动标注 + 本体建模（Phase 0–3 + 收尾）

### 目标
落地完整链路：粘贴/URL → Wiki Markdown → information_schema 扫描 → 规则/LLM 标注 → delta 本体构建 → CQ 验收/发布/导出。

### 决策
- Connector 改走 `information_schema`（注释/批列/画像/`overlap_ratio`）；LLM 仅 httpx；长任务 `job_runner` 独立 Session
- 置信度三档：≥0.85 自动采纳 / 0.65–0.85 待审 / <0.65 丢弃；rules 模式在无 `LLM_API_KEY` 时仍可用
- 本体构建按 batch delta（extract→align→judge→merge），消金片段 `CONSUMER_FINANCE_FRAGMENT` 作对齐目标；导出不引 rdflib
- UI：知识库三栏、元数据扫描/待审、本体 xyflow 图；菜单「业务系统」→「元数据与标注」，新增「本体建模」

### 新增文件
- backend: `llm_client` / `job_runner` / wiki|meta|ontology models·repos·schemas·services·apis；`annotation_rules|prompts`；`ontology_fragments`；`tests/test_{wiki,metadata,ontology}.py`
- frontend: `htmlToMarkdown`；Paste/Url 导入；Knowledge/Metadata/Ontology 页；AnnotationReviewPanel / OntologyGraph；wiki|metadata|ontology services+types
- docs: `docs/prd/ontology.md`

### 修改文件
- `dataops_connector` / `config` / `.env.example` / `main`（wiki seed）/ `router` / `models/__init__` / `test_smoke`
- `WarehousePage` + `types/dataops`（comment/row_count）
- `App.tsx` / `AppLayout.tsx`
- `AGENTS.md` / `HANDOFF.md` / `schema.sql` / `AGENT_LOG.md`

### 删除文件
- 无（清理临时 header patch）

### API 端点
- `/api/v1/wiki/*` · `/api/v1/metadata/*` · `/api/v1/ontology/*`

### 数据库
- +17 表 → 合计 **40** 张（wiki 3 + meta 5 + ontology 9）

### 验证
```
cd backend && pytest          # 85 passed
cd frontend && npm run build  # 0 error
cd frontend && npm run lint
```

---

## 2026-08-14

### Agent: 提交推送 — DataOps 智能数开 + 平台壳层

### 目标
整理近期未提交改动并 push：DataOps 数据仓库/智能数开、侧栏可收起、Cursor 风格白底 IDE、Agent/Compute/Skill 相关平台能力。

### 决策
- 智能数开：左 Explorer / 中 Editor+Result / 右 Agent；主体白色；Doris 执行 `POST /dataops/sources/{id}/execute`
- OpenCode：`@opencode-ai/sdk/client`；thinking/tools/`/`/`@`；修复 `session.idle` 导致发送按钮不结束
- AppLayout 左侧二级导航可折叠，偏好写入 `localStorage.ontomind_sidebar_open`
- **不提交** `backend/.env`（含 Doris 密码）；仅 `.env.example` 占位

### 主要范围
- 后端：dataops / compute / agent_factory / skill_platform 模型·仓库·服务·API
- 前端：多域路由壳、Warehouse、SmartDev、AgentOps/Infra 页面与服务
- 文档：`docs/prd/*`、`AGENT_LOG.md`

### 验证
- 本地前后端可起；智能数开页布局与侧栏折叠已手动确认

---

## 2026-08-13

### Agent: 智能数开白底 + DataOps 侧栏可收起

### 目标
1. 智能数开主体色改为白色（保留 Cursor 三栏结构）
2. 最左侧 DataOps 二级导航可收起/展开

### 修改
- `SmartDevPage.css` / `SmartDevPage.tsx`：浅色 token + Monaco `vs`
- `AppLayout.tsx`：`sidebarOpen` + 顶栏/侧栏折叠按钮 + localStorage

---

## 2026-08-13

### Agent: 智能数开 Cursor 工作台布局

### 目标
执行结果与 SQL 编辑同宽（中栏上下）；整体仿 Cursor IDE（三栏 + 底栏 Result/Output + 状态栏），收紧顶栏字号。

### 决策
- 结构：Explorer | Editor+Panel | Agent；Panel 仅挂在中栏下方
- 视觉：暗色 workbench（#181818/#1e1e1e）、30px titlebar、22px statusbar、vs-dark Monaco
- 样式独立 `SmartDevPage.css`

### 修改
- `frontend/src/pages/dataops/smart-dev/SmartDevPage.tsx`
- `frontend/src/pages/dataops/smart-dev/SmartDevPage.css`（新增）

---

## 2026-08-13

### Agent: 智能数开 IDE 增强（执行结果 / Doris / OpenCode parts / 可拖拽布局）

### 目标
优化 DataOps「智能数开」页：底部 SQL 执行过程与结果、Doris 执行器、OpenCode thinking/tools/`/`/`@`、修复发送按钮转圈、白底编辑器、四区可拖拽收起。

### 决策
- 发送转圈根因：只认 `session.status=idle`，忽略独立事件 `session.idle` → 同时监听两者并加 generation 兜底
- SQL 执行走后端 `POST /dataops/sources/{id}/execute`（单语句、结果截断），前端选已配置 Doris/MySQL
- Agent 展示 `reasoning` / `tool` part；`/` → `command.list` + `session.command`；`@` → `app.agents` + AgentPart
- 布局用 `react-resizable-panels`；Monaco theme `vs` 白底

### 新增/修改
- 后端：`dataops_connector.execute`、`ExecuteSql*` schema、`/sources/{id}/execute`
- 前端：`opencodeSdk.ts` 增强、`SmartDevPage.tsx` 重做、`dataops.service`/`types`、依赖 `react-resizable-panels`

### 验证
- `tsc -b` 通过；`oxlint` 无新增 error；前后端 health 200

---

## 2026-08-04（下午）

### Agent: Agent 工厂 — OpenCode Agent/Skill 平台化（设计→版本→编排→发布→校验）

### 目标
把 OpenCode 的 Agent 设计（含 Agent Loop 编排模式）与 Skill 设计从「手写散落文件」
升级为平台化能力：MySQL 存模板/结构、可版本回滚、可视化编排 Loop、一键发布到 Docker 容器并回读校验。

**PRD：`docs/PRD-agent-skill-platform.md`**（含完整研究结论、字段字典、API 契约、验收用例）

### 研究（实证，非推测）
依据 OpenCode 官方文档 + 权威 JSON Schema（`opencode.ai/config.json`）+ 对运行实例的实机验证。

| 项 | 结论 |
|---|---|
| Agent 定义 | Markdown（`agents/<name>.md`，**文件名即 agent 名**）或 JSON（`opencode.json` 的 `agent.<name>`）|
| 权限键 | **仅 15 个合法**；其中 **10 个**支持 glob；规则**最后匹配胜出**（`*` 必须置顶）|
| ⚠️ 静默失效 | 写错权限键（如 `write` 应为 `edit`）**不报错也不生效** —— 这是平台必须前置校验的根本原因 |
| Loop 四旋钮 | `permission.task`（谁能调谁，deny 会把 subagent 从 Task 描述整条移除）/ `subagent_depth` / `steps` / `mode` |
| Skill | 一目录一 skill；frontmatter **只认 5 字段**；`name` 必须等于目录名 |
| Skill 最佳实践 | **渐进披露**：SKILL.md 只放高频规则，细节下沉 `references/`（实测本地 55 个 skill 的通用结构）→ 必须支持多文件 |

**运行时控制面实测（决定了发布策略）**

| 端点 | 实测结论 |
|---|---|
| `GET /agent` | ✅ 可靠，权限已展开为 `{permission,pattern,action}[]` → **作为回读校验权威依据** |
| `PATCH /config` | ❌ **返回 200 但 agent 不出现在 `GET /agent`，也不落盘** → 原计划的「热注入」方案被实测否决 |
| 写 `opencode.jsonc` 后不重启 | ❌ 不热感知 |
| `GET /api/skill` | ❌ **skill 明确可用时仍返回 `data: []`**，不可信 |
| skill 校验替代方案 | ✅ 容器内 `opencode run "列出可用 skills"` —— 实测有效 |

→ **唯一可靠路径 = 写文件（为真）+ 重启（生效）+ `GET /agent`（校验）**
→ `opencode web` 不暴露 `/agent`，控制面必须用 **serve**

### 设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 发布通道 | 写文件 + 重启 | 实测热注入不生效；文件抗重启、可版本化、可手改 |
| 文件传输 | 本地 `put_archive()` 内存 tar；远程 `tar+base64` over SSH | 原子；彻底避开引号/中文编码问题 |
| **发布单元** | **Bundle（编排方案）而非单个 agent** | Loop 是「一组 agent + 全局旋钮」整体，拆开发布会产生「装了但没人能调」的半成品 |
| 校验时机 | **设计态就拦**（不合法存不进 DB）| 权限键写错 OpenCode 静默忽略，事后无法排查 |
| 发布后 | 回读 `GET /agent` 逐项比对，差异写 `verify_json` | 不做 fire-and-forget，结果必须可证伪 |
| Skill 存储 | 正文 LONGTEXT + 独立 `skill_files` 表 | 支撑 references/scripts 真实结构 |
| YAML 渲染 | 手写而非 pyyaml | pyyaml 会给 `"git *"` 去引号导致解析不稳；且需控字段顺序、中文不转义 |
| 重启告知 | `restart_confirmed` 必填 | 重启会中断进行中会话，不偷偷做 |

### 数据库

**新增 7 张表（6 → 13）**：
`agent_templates` · `agent_template_versions`（整份快照非 diff，回滚可靠）
`skill_templates` · `skill_files`（uniq(skill,rel_path)，防路径穿越）
`agent_bundles` · `bundle_members` · `deployments`（产物 sha256 + 回读结果）

### 新增文件（后端 12 / 前端 8）

| 文件 | 说明 |
|---|---|
| `docs/PRD-agent-skill-platform.md` | PRD（唯一依据）|
| `backend/app/db/models/{agent_template,skill_template,agent_bundle,deployment}_model.py` | 7 表 |
| `backend/app/db/repositories/{agent_template,skill_template,agent_bundle,deployment}_repo.py` | 7 repo |
| `backend/app/schemas/agent_factory_schema.py` | schema + 权限元数据 + **6 Loop / 8 Agent / 4 Skill 预设** |
| `backend/app/services/agent_validate_service.py` | **15 条校验规则**（权限键白名单、glob 能力、`*` 置顶、路径穿越、拓扑一致性）|
| `backend/app/services/agent_render_service.py` | DB → `.md`/`.jsonc`（glob 键强制加引号）|
| `backend/app/services/agent_factory_service.py` | CRUD + 版本 + **渲染↔解析往返** 导入 |
| `backend/app/services/agent_deploy_service.py` | **五阶段发布**：resolve→validate→write→reload→verify |
| `backend/app/db/seed_agent_factory.py` | 幂等播种预设 |
| `backend/app/api/v1/agent_factory.py` | **26 端点** |
| `backend/tests/test_agent_factory.py` | **33 个单测** |
| `frontend/src/types/agentFactory.ts` + `services/agentFactory.service.ts` | 类型 + API |
| `frontend/src/components/agent-factory/{PermissionMatrix,LoopTopology,AgentDesigner,SkillDesigner,BundleDesigner,DeployCenter,shared}.tsx` | 四页 + 权限矩阵 + SVG 拓扑 |
| `frontend/src/pages/agent-factory/AgentFactoryPage.tsx` | 主页（懒挂载 4 tab）|

### 修改文件
`backend/app/db/models/__init__.py`（注册 7 表）· `backend/app/api/v1/router.py`（挂 agent-factory）
· `backend/app/main.py`（lifespan 播种）· `backend/app/db/repositories/deployment_repo.py`（`latest_for_target` 加 `exclude_id`）
· `backend/tests/test_smoke.py`（表/域断言）· `frontend/src/App.tsx` + `AppLayout.tsx`（路由与导航）

### 验证

**后端单测 33 个 + 回归 24 个 = 57 passed**

**实机验证（curl + docker inspect + GET /agent 三方交叉）**
- 校验器：`write` → 报错并提示「应该写 edit」；`webfetch` 给 object → 报错；`*` 未置顶 → 警告；`../evil.md` → 拦截；无 primary / default_agent 是 subagent / task 死引用 → 全部命中 ✅
- 渲染器：glob 键加引号、中文不转义、`#3b52af` 加引号、空值不输出 ✅
- **渲染↔解析往返**：8 个预设全部无损（含嵌套 glob 权限）✅
- 发布五阶段：`status=success`、8.5s、**回读 3/3 全一致** ✅
- 幂等：二次发布 `written=0 skipped=6` ✅
- 剪枝：移除成员后 `pruned=['agents/e2e-reviewer.md']`，容器内确认消失、`GET /agent` 不再列出 ✅
- **容器内独立核对**：`agents/*.md` + `skills/<n>/{SKILL.md,references/,scripts/}` 全部就位 ✅
- **OpenCode 真实加载**：`GET /agent` 回读 mode/temperature/color/中文描述/全部 glob 权限逐条一致 ✅
- **skill 真实加载**：容器内 `opencode run` 输出含新 skill ✅
- **实际调用**：`opencode run --agent ui-guard` → OpenCode 正确识别为 subagent 并 fallback 到我们部署的 primary `orchestrator`，按部署的 prompt 作答 ✅

**前端（Playwright 真实浏览器）**
- 四 tab 全渲染；权限矩阵 15 键 + 5 档；Skill 多文件树；**SVG 拓扑（4 节点 + 3 箭头）**；发布中心重启确认 + 产物 diff ✅
- **走 UI 全链路**：矩阵点选 `edit=禁止` → DB 存 `{'edit':'deny'}` → 渲染 frontmatter 正确 → UI 发布 → 「全部一致」→ 容器内文件与 `GET /agent` 双向核对通过 ✅
- 全站走查（compute 4 tab + agent-factory 4 tab + aide + users）：**console 0 error**（仅 `/users` 403 为既有权限问题，相关文件本次未改动）✅

**回归**：`pytest` 57 passed · `tsc` 0 error · `vite build` 261ms · `oxlint` **0 error**（从 2 降到 0）

### 追加修复：预设方案误报「没有 primary agent」+ 拓扑图连线缺失

用户反馈两个问题，均已定位并修复。

**问题 1：3 个内置预设在页面上报错**

现象：「单体全能」「先规划后执行」「实现与评审环」都提示
`1 处错误必须修正 · members 方案里没有 primary agent，用户无法与之对话`。

根因：校验器只检查「成员里有没有 mode=primary 的 agent」，
但**依赖 OpenCode 内置 `build`/`plan` 作主对话是完全合法的用法** ——
这三个预设正是这种形态（只自定义 subagent，入口用内置 agent）。
讽刺的是错误文案里已经写了「或依赖 OpenCode 内置的 build/plan」，代码却没实现这个分支。

修复：
- 入口判定改为「有自定义 primary **或** `default_agent ∈ {build, plan}`」
- 新增 **`info` 级别**（区别于 error/warning）：配置合法，只把「会发生什么」讲清楚 ——
  提示「本方案未自定义 primary，主对话将使用 OpenCode 内置的 'plan'」
- 报错文案改为可执行的二选一：「① 把某成员角色设为主对话；② 把默认入口设为 build/plan」

**问题 2：Loop 拓扑图连线缺失、节点错乱**

三个独立缺陷：

| 缺陷 | 现象 | 根因 |
|---|---|---|
| 无入口节点 | 「实现与评审环」2 节点 **0 连线**、「先规划后执行」1 节点 **0 连线** | 只画成员里的 primary；依赖内置入口时图上没有源节点，自然画不出箭头 |
| subagent 排布错乱 | 「编排者与专家团」x=91/280/469 间距不均、y 不齐(158/170/158) | 弧度偏移 `arc` 与居中公式混用，把等距算歪了 |
| 节点溢出画布 | x=469 + 宽 108 = 577 > 画布 560 | 布局未按内容反推画布尺寸 |

修复（重写 `LoopTopology.tsx` 布局层）：
- **补画内置入口节点**：没有自定义 primary 时，按 `default_agent` 画出 `build`/`plan`，
  用**虚线边框 + 浅色填充**区分「非本方案定义」，并标注「OpenCode 内置入口」
- **布局改为按内容反推画布**：`linear` 单行等距；`star` 每行最多 4 个、多行铺开，
  画布宽高由节点数算出（`canvasW`/`canvasH`），彻底消除溢出
- 移除弧度偏移，改用「每行独立居中」保证等距对齐

**验证**

| 方案 | 修复前 | 修复后 |
|---|---|---|
| 实现与评审环 | 2 节点 / **0 连线** | **3 节点（含 build 内置入口）/ 2 连线** |
| 先规划后执行 | 1 节点 / **0 连线** | **2 节点（含 plan 内置入口）/ 1 连线** |
| 编排者与专家团 | x=91/280/469 错乱溢出 | **x=82/208/334 等距对齐，520×182 不溢出** |

- API 逐个校验 6 个预设：**全部 `ok=true`，0 error**（修复前 3 个报 error）
- 浏览器逐个点开 6 个预设：无「错误必须修正」、无「没有入口」报错、连线数量正确、**console 0 error**
- 新增 3 个回归测试（`test_bundle_may_rely_on_builtin_primary`、
  `test_bundle_with_no_members_but_builtin_entry_is_ok`、
  `test_all_bundle_presets_pass_validation`）—— 最后一个直接守住「内置预设自身必须校验通过」

**涉及文件**：`backend/app/services/agent_validate_service.py`（入口判定 + `_info`）、
`backend/app/schemas/agent_factory_schema.py`（`level` 加 `info`）、
`backend/tests/test_agent_factory.py`（+3 测试）、
`frontend/src/components/agent-factory/LoopTopology.tsx`（重写布局）、
`frontend/src/components/agent-factory/shared.tsx`（渲染 info）、
`frontend/src/types/agentFactory.ts`（类型）。

**回归**：`pytest` 60 passed（+3）· `tsc` 0 error · `vite build` 285ms · `oxlint` 0 error。

### 追加修复：AIDE 不能实时识别容器新起的 opencode

**现象**：用户在容器里启动了 `opencode web`，AIDE 页面仍显示不可用/看不到该服务。

**两个独立根因**

**A. 数据层 —— 只 refresh 不 discover（主因）**

AIDE 首屏调的是 `listContainerServices(refresh=true)`，它只回探**DB 里已登记**的服务。
用户直接在容器控制台敲 `opencode web`，平台没经手过、DB 里根本没这条记录 →
refresh 再多次也发现不了。

实证（清空 `container_services` 模拟零登记态）：

| 调用 | 结果 |
|---|---|
| `GET /services`（旧 AIDE 行为） | **0 个服务、`aide-sources` 0 条** ← 用户遇到的现象 |
| `POST /services/discover`（修复后） | **2 个服务全部发现，均 `is_aide_source=true`** |

**B. 体验层 —— 本机 opencode 在跑时会掩盖容器服务**

宿主自己跑着 opencode（`embed_source=serve`）时 AIDE 判定 `ready=true`，
「未就绪」引导区根本不渲染，用户完全看不到容器里还有可选服务，
自然以为「我起的容器 opencode 没被识别」。

**修复**

1. `fetchServices(refresh, discover)` 增加 discover 通道；**首屏改为 discover**
2. **未连接容器源时 10s 自动轮询 discover** —— 覆盖「先起服务再回 AIDE 等它亮」的场景
3. 打开下拉时也做一次 discover（刚起的服务立刻出现）
4. 刷新按钮由 refresh 改为 discover，并给**可执行结论**：
   有几个可用 / 都不可用时直接说出最典型原因
5. **工具条常驻提示**（不再依赖「未就绪」分支）：
   `容器可选 N` / `N 个容器服务不可用`（hover 显示每个的具体原因）
6. 未就绪引导区新增两个诊断横幅：
   - 有可用容器服务 → 绿色 + **一键接入按钮**（不必再起本机 opencode）
   - 有服务在跑但宿主访问不到 → 黄色 + 逐条原因 + 两种修法
7. `pickService` 的拒绝提示细化：端口未映射时明确指出
   「到『算力管理 → 容器』用『修改配置』加映射，或改起在已映射端口上」

**顺带定位到用户环境的一个真实配置问题**

`opencode001` 容器只映射了 `4097`，但服务起在容器内 `4096` →
Docker 端口转发指向 `容器IP:4097`（无人监听），宿主必然访问不到。
平台的判定是**正确**的（`host_port=None, host_reachable=0, is_aide_source=0`），
只是原来没把原因讲清楚。改起在 4097 后立即可用（实测宿主 14097 → 200）。

**验证**

- 清空 DB + 容器内手工起服务 → 进 AIDE 后自动 discover 出 2 个服务，下拉两项均 `OK` 可选 ✅
- 选中 `opencode001` → iframe 切到 `http://localhost:14097`，工具条显示「容器 opencode001 / 容器端口 4097」✅
- 本机 opencode 在跑时，工具条仍显示 **「容器可选 2」** ✅
- 浏览器 **console 0 error**
- 回归：`pytest` 60 passed · `tsc` 0 error · `vite build` 267ms · `oxlint` 0 error

**涉及文件**：`frontend/src/pages/aide/AidePage.tsx`（discover 通道 + 轮询 + 诊断横幅 + 工具条提示 + 拒绝提示细化）。

### 追加修复：AIDE 服务探测慢 + 容器控制台打不开（连接池被打满）

**现象**：① AIDE 选容器 opencode 服务时探测极慢；② 算力管理打开容器控制台一直转圈。

**定位过程**（先量后修，不猜）

压测发现连 `GET /compute/services`（纯查库）都要 **30s**，说明不是单个功能慢，是后端整体被拖死。
翻日志拿到根因：

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached,
connection timed out, timeout 30.00
```

**连接池 30 个连接全部耗尽**，且有 **3 个残留 uvicorn 进程**在抢资源。
再往上追，池被耗尽是因为下面这条慢链路被 AIDE 10s 轮询反复触发：

| 环节 | 耗时 | 问题 |
|---|---|---|
| `list_containers` | 0.5–2s | 每次对每个容器 `docker inspect` + 查镜像 ENV/CMD，**零缓存** |
| `_probe_listen_ports` | 每容器一次 `docker exec` | 跨请求零复用 |
| `refresh_services` | N × (exec + HTTP) | `_probe_one` **串行** |
| `discover_services` | **~10s** | 遍历**所有**节点，含已知 offline 的远程节点 → 等 SSH 超时 |

**四项修复**

1. **短 TTL 缓存**（3s）：`list_containers` 与 `_probe_listen_ports` 加模块级缓存。
   容器状态 3s 内几乎不变，但轮询叠加能省掉绝大部分 docker 调用。
   需要强一致的路径可传 `fresh=True` 绕过。
2. **缓存失效钩子** `invalidate_container_cache()`：容器创建/删除/启停/重建后立即失效，
   避免读到旧状态（5 个调用点覆盖全部变更路径）。
3. **并发探测**：`refresh_services` 与 `discover_services` 改为
   「同容器串行（复用 listen 缓存）、不同容器 `asyncio.gather` 并发」——
   这些都是 IO 等待，串行时 N 个服务 = N 倍延迟。
4. **跳过离线节点 + 硬超时**（关键）：`discover_services` 默认跳过 `status=offline`
   的远程节点（本地节点永不跳过），并给每个节点 8s `wait_for` 上限。
   用户环境里那台 `macmini`（offline）一个就贡献了 10s。

**效果（实测）**

| 指标 | 修复前 | 修复后 |
|---|---|---|
| `GET /services` | **30s**（池耗尽） | **0.03s** |
| `list_containers` | ~30s | **0.095s 冷 / 0.013s 缓存** |
| `refresh_services` | 30s | **0.029s** |
| `discover_services` | **10.5s** | **0.28s 冷 / 0.07s 缓存**（38×） |
| AIDE 服务列表就绪 | 慢/超时 | **1.1s**；下拉打开 **0.4s** |
| 控制台「已连接」 | 一直转圈 | **0.6s** |
| 控制台 WS 首字节 | — | **0.18s** |

**关于「控制台一直转圈」的结论**：后端 WS 链路本身一直是健康的
（`exec_terminal_local` 返回 0.09s、PTY 首字节 0.16s、命令回显 0.18s）。
转圈是**连接池耗尽的连带症状** —— 前置的 `/shells` 探测请求排队 30s 拿不到连接，
前端就一直停在 `probing` 状态。池修好后自然恢复。
（排查中我一度误判首字节要 6.5s，实为我自己测试脚本的 `recv timeout=6s` 造成的假象，
 用精确计时复测后确认是 0.18s。）

**新增 3 个结构性保护测试**：TTL 真会过期、失效钩子按节点精确清理、
`discover_services` 必须保留 `include_offline` 与 `asyncio.wait_for`。

**运维动作**：清理了 3 个残留 uvicorn 进程与孤儿 MySQL 连接，前后端已重启。

**涉及文件**：`backend/app/services/compute_service.py`（缓存 + 失效 + 并发 + 跳离线 + 超时）、
`backend/tests/test_agent_factory.py`（+3 测试）。

**回归**：`pytest` 63 passed（+3）· `tsc` 0 error · `vite build` 272ms · `oxlint` 0 error · console 0 error。

### 追加修复：编排方案缺「委派授权」入口 + Prompt 无填写引导

用户反馈三个问题，两个是**真实功能缺失**，一个是**可用性缺陷**。

**问题 1：新加的 subagent 是虚线，且无法在页面上改**

现象：在「编排者与专家团」里加 `refactorer` 后，`orchestrator → refactorer` 是灰虚线，
而预设自带的三个 subagent 是实线。

机制（实测确认）：`orchestrator` 的 permission.task 是
`{"*": "deny", "explorer": "allow", "test-writer": "allow", "code-reviewer": "allow"}`。
OpenCode **最后匹配胜出**，新加的 `refactorer` 不在白名单 → 落到 `"*": "deny"`。
`deny` 会让 OpenCode 把该 subagent **从 Task 工具描述里整条移除** —— 模型看不到、永远不会指派。
所以虚线本身是**正确反映**了配置。

真正的缺陷：**编排页没有任何入口能改这个 task 权限**
（`grep -c PermissionMatrix BundleDesigner.tsx` = **0**，设计时漏了最关键的编辑入口）。
用户只能去 Agent 设计页手改 JSON，且完全不知道该改哪个字段。

修复：编排页新增 **「委派授权」区块**（`primary × subagent` 矩阵）：
- 每行一个 subagent，三态 Segmented（允许 / 需确认 / 禁止），带状态色点
- 当前是 `deny` 的直接标注「模型看不到它」
- 顶部 Alert 讲清「最后匹配胜出 + 预设自带 `{"*": "deny"}`」这个机制
- 写入时**把精确名字追加到规则末尾**，并保证 `"*"` 仍在最前 —— 否则新规则会被 `*` 覆盖而不生效
- 改的是 primary **agent 模板**的 `permission.task`（OpenCode 的 task 规则就落在 agent 定义里），
  并明确告知「对所有引用该 agent 的方案生效」

**问题 2：拓扑图虚线含义不明**

修复：图例文案改为「禁止（模型看不到，**不会指派**）」；
有 deny 边时在图下方直接点名：
「`refactorer` 当前是禁止状态（灰虚线）—— OpenCode 会把它从 Task 工具描述里整条移除…
到上方「**委派授权**」把它切成「允许」即可」。

**问题 3：System Prompt 不知道怎么填**

原来只有一行提示 + 一个 placeholder，面对空框无从下手。

修复：
- 新增 **「填入模板」** 按钮 —— 一键填入四段式骨架
  （角色定位 → 工作方法 → 输出要求 → 禁止事项），带 `<占位说明>` 照着改
- 新增 **「参考预设写法」** 按钮 —— 直接载入内置预设的 prompt 当范本
- 字段说明写清建议结构，并点明「写清**不要做什么**比泛泛要求做好更有效」

**验证**

复现用户场景（给「编排者与专家团」加 `refactorer`）：

| 步骤 | 结果 |
|---|---|
| 加入后打开编排页 | 「委派授权」区块出现，`refactorer` 在列，标注「模型看不到它」；拓扑 **1 条灰虚线** |
| 点该行「允许」 | 拓扑 **灰虚线 0 条**（全变实线） |
| DB 落库 | `{"*": "deny", "explorer": "allow", "refactorer": "allow", ...}`，`*` 仍在最前 ✅ |
| 「填入模板」 | textarea 正确填入四段式模板 ✅ |

浏览器 **console 0 error**。测试后已还原预设与 `orchestrator` 的原始 task 规则。

**涉及文件**：`frontend/src/components/agent-factory/BundleDesigner.tsx`（委派授权矩阵 +
`resolveTaskAction` / `setTaskPermission`）、`LoopTopology.tsx`（deny 提示）、
`AgentDesigner.tsx`（prompt 模板与引导）。

**回归**：`pytest` 63 passed · `tsc` 0 error · `vite build` 267ms · `oxlint` 0 error。

### 追加修复：task 权限归属错位 —— 隐性规则透明化（用户指出的架构缺陷）

**用户反馈**：报 3 条「规则指向 'explorer'/'test-writer'/'code-reviewer'，但它既不在本方案成员中…
该规则不会生效」，并质疑「有很多隐性的规则，设计 agent 应该比较透明，
`members.orchestrator.permission.task` 这种规则是读的 md 还是怎么获取的？应该怎么设计更直观」。

**这个质疑完全正确，暴露了我上一轮引入的架构错误。**

**根因：`permission.task` 归属错位**

| 事实 | 说明 |
|---|---|
| 规则存哪 | `agent_templates.permission_json.task`（MySQL），渲染落盘到 `agents/<name>.md` frontmatter |
| 不是读 md | md 是**渲染产物**，DB 才是源（导入功能才反向解析 md）|
| **错在哪** | `task` 在 OpenCode 里是 **agent 级字段**，但语义是 **bundle 级**的（「本编排里谁能调谁」）|

我上一轮的「委派授权」直接改 agent 模板，于是**跨方案污染**：

```
在 test 方案里授权 docs-writer / security-auditor
  → 写进了共享的 orchestrator 模板
  → 编排者与专家团 方案也带上这两条
  → 但那个方案没有这俩成员 → 报「规则不会生效」
```

校验器的 warning **是对的**，它精确暴露了我的设计错误。

**架构级修复**

1. **数据层**：`bundle_members` 新增 `task_permission` —— 授权存在**方案成员**上，
   不再回写 agent 模板（MySQL ALTER 已执行，13 表结构不变）
2. **渲染层**：新增 `synthesize_task_rule()` —— 发布时按**本方案成员**重新合成
   `permission.task`：
   - 只为本方案 subagent 产出规则，模板里指向方案外 agent 的条目**一律剔除**
   - 优先级：方案覆盖 > 模板规则 > 默认
   - 保留模板 `"*"` 兜底（无则 deny），且 `"*"` 强制置顶（最后匹配胜出）
   - 与兜底相同的动作不重复写，保持产物精简
3. **校验层**：方案外规则由 **warning 降为 info**，文案改为
   「模板里还有 N 条指向方案外 agent 的规则 —— 发布时会自动剔除，不写进产物」
4. **透明化（回应「应该怎么设计更直观」）**：`BundleMemberResponse` 新增三个溯源字段
   - `effective_task` —— **最终生效**的动作
   - `task_source` —— `bundle`(本方案) / `template`(agent 模板) / `default`(未配置)
   - `task_source_detail` —— 人话说明，如 `orchestrator 模板规则 "*": deny 命中`
5. **前端**：委派授权矩阵改写 bundle；每行显示 **「来源」标签**（hover 出具体命中的规则）；
   有覆盖时给「跟随模板」一键还原；未保存改动标 `有未保存改动`；
   拓扑图连线改用后端 `effective_task`，保证**图与矩阵完全同源一致**

**验证**

| 检查项 | 结果 |
|---|---|
| 7 个方案校验 | **err=0 warn=0**（修复前 4 个方案共 11 条 warning）|
| 溯源显示 | `docs-writer effective=deny source=template \| orchestrator 模板规则 "*": deny 命中` |
| 产物剔除死规则 | `test` 方案的 `orchestrator.md` 只有 `"*": deny`，无 docs-writer/security-auditor |
| 方案内覆盖生效 | 设 `docs-writer=allow` → 产物出现 `docs-writer: allow` |
| **模板未被污染** | `orchestrator` 模板 task 仍是原始 4 条，**不含 docs-writer** ✅ |
| 前端透明化 | 「来源：本方案」「来源：agent 模板」「跟随模板」「模型看不到它」全部呈现 |
| 拓扑一致 | 1 allow(已授权) + 1 deny，与矩阵一致 |

浏览器 **console 0 error**。测试后已还原被污染的 `orchestrator` 模板与 test 方案覆盖。

**新增 5 个回归测试**：死规则剔除、方案覆盖优先、`*` 置顶、
`resolve_task_action` 最后匹配胜出、方案外规则只报 info。

**涉及文件**：`backend/app/db/models/agent_bundle_model.py`（+`task_permission`）、
`app/schemas/agent_factory_schema.py`（+溯源字段）、
`app/services/agent_render_service.py`（+`synthesize_task_rule`/`resolve_task_action`）、
`app/services/agent_factory_service.py`（+`_resolve_effective_task`，`_bundle_members` 返回 5 元组）、
`app/services/agent_deploy_service.py`（传 task_overrides）、
`app/services/agent_validate_service.py`（warning→info）、
`backend/tests/test_agent_factory.py`（+5）、
`frontend/src/types/agentFactory.ts`、`BundleDesigner.tsx`、`LoopTopology.tsx`。

**回归**：`pytest` 68 passed（+5）· `tsc` 0 error · `vite build` 273ms · `oxlint` 0 error。

### 追加修复：Skill 平台 PRD + 双平面数据层 + 合规导出（P1-P2）

**背景**：用户要求基于 OpenCode 官方 Skill 标准，设计并输出「Skill 可视化设计&统一管理平台」，
覆盖 8 大模块、全生命周期，支持一键导出合规 OpenCode 目录包。

**关键实测发现（决定整个架构）**

在真实 OpenCode 容器（v1.18.12）上做两组探针确认：

| 实验 | 构造 | 结果 |
|---|---|---|
| A | frontmatter 顶层塞 `risk_level` / `owner` / `qps_limit` | ✅ skill 正常加载，字段被**静默忽略** |
| B | 同样信息放进 `metadata:` 子映射 | ✅ 正常加载，字段保留在文件里 |

这说明往 frontmatter 塞治理字段是**无效的** —— 用户以为配了限流，实际没有。

**架构决策：双平面分离**

| 平面 | 内容 | 谁执行 |
|---|---|---|
| **执行平面**（Data Plane）| SKILL.md（**仅 5 合法字段**）+ references/ + scripts/ | OpenCode 原生 |
| **治理平面**（Control Plane）| 限流/熔断/RBAC/脱敏/鉴权/Trace（9 张表） | 新增平台 Skill 网关 |

三条落地规则：合规兜底（只出 5 字段）、metadata.omd_* 摘要可追溯、治理由网关执行。
治理全量配置导出到 `_ontomind/skill.manifest.json`（刻意在 skills/ 之外）。

**产出**

| 文档 | 路径 |
|---|---|
| PRD（含架构/菜单/8 模块交互/全部表设计/分期/收益对比） | `docs/PRD-skill-platform.md` |
| 9 张治理表（22 表） | `backend/app/db/models/skill_platform_model.py` |
| Schema（含 SKILL_KIND_META/LIFECYCLE_META 等） | `backend/app/schemas/skill_platform_schema.py` |
| 校验器（17 条规则，含明文密钥拦截） | `backend/app/services/skill_validate_service.py` |
| 双平面渲染器 / JSON Schema 编译器 / 合规导出包 | `backend/app/services/skill_render_service.py` |

**17 条校验规则（全实测验证）**

| 范围 | 规则 |
|---|---|
| 合规 | ① kebab-case ② 目录名一致性 ③ description 1-1024 ④ metadata 值必须 string ⑤ 路径安全 ⑰ 渐进披露 |
| **密钥安全** | ⑥ **明文密钥拦截**（AKIA/sk-/ark-/ghp_/JWT/PEM/长hex/长base64，仅放行 `cc://`/`kms://`/`vault://`/`sm://`/`env://`）|
| 治理 | ⑧ 高危`+`二次确认 ⑨ 生命周期合法性 ⑩ 上线门禁(canary/released 前必配责任人/出参/生产地址) ⑯ API 型上线必配生产地址 |
| Schema | ⑪ 参数名合法 ⑫ 枚举与类型匹配 ⑬ 正则合法性 |
| 编排 | ⑭ 无环/连通/有 start-end ⑮ 引用未上线 skill 警告 |

**双平面导出验证（约束 1 最终的判据）**

导出 `pay-order-query` 包（含 SKILL.md + references + scripts）到真实容器 → 重启 serve → `opencode run` 输出：

```
- customize-opencode
- db-migration
- git-release
- pay-order-query     ✅ 被 OpenCode 成功加载
```

**交付 PRD 文档**：`docs/PRD-skill-platform.md`（含完整架构设计、页面菜单结构、
8 个模块逐模块交互逻辑、全部 22 表设计、标准 SKILL.md 模板样例、分 7 阶段落地计划、
对比手工模式的收益量化表）。

**回归**：`pytest` 68 passed · `tsc` 0 error · `vite build` 283ms · `oxlint` 0 error。

### 追加：PRD 目录重构 + 产品骨架（7 域导航）

**背景**：用户要求① 按域生成多份 PRD 文档；② 现有功能归入 Infra 目录；③ 项目名保持 OntoMind；④ 按 PROTOTYPE-GUIDANCE.md §9.2 搭建产品骨架。

**产出**：

| 产出 | 路径 |
|---|---|
| 总体 PRD | `docs/prd/overview.md` |
| 6 个域 PRD | `docs/prd/{infra,codeops,dataops,modelops,agentops,govops}.md` |
| 总览仪表盘 | `frontend/src/pages/overview/OverviewPage.tsx`（6 个 KPI 卡片） |
| 占位页面 | `frontend/src/components/common/PlaceholderPage.tsx` |
| 新导航布局 | `frontend/src/components/layout/AppLayout.tsx`（左侧 7 域图标栏 + 子菜单） |

**导航结构**：

```
左侧图标栏：总览 · CodeOps · DataOps · ModelOps · AgentOps · GovOps · Infra
点击域 → 右侧子菜单（如 AgentOps 含 Agent 设计 / Skill 设计 / 编排方案 / 发布中心）
选中子菜单 → 内容区渲染对应页面
```

**路由映射**：

| 旧路径 | 新路径 |
|---|---|
| `/compute` | → `/infra/compute`（重定向） |
| `/aide` | → `/infra/aide`（重定向） |
| `/agent-factory` | → `/agentops/agents`（重定向） |
| `/skill-platform` | → `/agentops/skills`（重定向） |

占位页面（`即将上线，敬请期待`）用于 CodeOps/DataOps/ModelOps/GovOps 尚未实现的功能。

**验证**：
- 总览页显示 6 个 KPI 卡片（AI 代码贡献率 38.5%、数据资产 1,247、模型服务 12 等）
- 7 个域导航图标正常渲染
- 每个域子菜单正确，点击跳转正常
- 旧路由全部 301 重定向到新路径
- 浏览器 console 0 error（仅 antd v6 预置弃用告警）
- 回归：`pytest` 68 passed · `tsc` 0 error · `vite build` 267ms · `oxlint` 0 error

### 追加：Skill 平台前端页面 + API 路由

**背景**：之前做了后端数据层（9 张表）、校验器（17 条规则）、双平面渲染器，但完全没做前端页面和 API 路由，用户页面上看不到任何变化。

**本轮交付**：
- 挂载 `skill-platform` 路由，API 端点 15 个
- `SkillPlatformService`（CRUD/生命周期/参数/版本/导出/克隆/审计）
- 前端 `SkillDesignerPage.tsx`：三段式设计器（元数据 + 参数契约 + 执行逻辑）+ 右侧预览 + 导出/版本/克隆
- 前端 `skillPlatform.service.ts` + `skillPlatform.ts` 类型定义
- 导航栏新增「Skill 平台」入口

**验证**：
- 后端 API 创建/列表/导出全部正常
- 页面加载正常，选中 skill 后三段式设计器显示完整
- 浏览器 console 0 error
- 回归：`pytest` 68 passed · `tsc` 0 error · `vite build` 328ms · `oxlint` 0 error

### 遗留 / 注意
- **控制面必须用 `opencode serve`**：`web` 不暴露 `/agent`，此时发布仍会写文件+重启，但校验降级为 `partial` 并明确告知原因（已实测该降级路径）
- 容器重建会丢产物：`deployments` 记录容器 ID，可据此提示重新发布（未做自动重发）
- `_probe_host_reachable` / 控制面探测走**后端视角**；后端与浏览器不同机时（远程节点）可能不一致
- 远程 SSH 节点的发布路径已实现但**未在真机验证**（当前只有 local 节点在线）
- 踩坑记录：`docker ps --filter name=opencode` 会**子串匹配到 `opencode001`**，测试与脚本里需用 `name=^opencode$` 精确匹配

---

## 2026-08-04

### Agent: 容器服务登记 — 状态可见化 + MySQL 持久化 + AIDE 源联动

### 目标（用户三条诉求）
1. 算力页面「容器通过执行命令启动的服务是一种状态，应该要有地方展示出来」
2. 容器启动的 opencode web/serve「应该有地方存下来，存到 MySQL，并维护状态的真实性、实时性」
3. AIDE 页面「根据 MySQL 里的信息来加载选项进行切换」

### 问题根因
容器内起的服务是**运行态**，进程只活在容器里。原实现：
- 服务信息不落库 → 页面刷新/后端重启后完全看不见
- `get_aide_sources()` 每次实时扫全部容器，只按「容器端口是否为 4096/4097」判断，
  **不校验进程是否真在监听、绑的什么地址、宿主是否真连得上** → 会把已挂掉/绑 loopback 的服务当可用源
- AIDE 下拉只显示「节点/容器名」，选到不可用的源也没有任何提示

### 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 存储 | 新增 **`container_services`** 表 | 服务是可管理实体，需跨会话持久化 |
| 唯一键 | `(container_id, container_port)` | 同容器同端口只一条，重复启动走 upsert |
| 状态定位 | DB 存「声明 + **探测快照**」，**不当可信实时源** | 诚实建模，避免 UI 拿过期状态骗人 |
| 真实性保证 | `refresh_services()` **四步递进探测** | 容器在吗 → 端口映射对吗 → 容器内在监听吗（绑什么） → 宿主真连得上吗 |
| 端口监听探测 | 解析 **`/proc/net/tcp`**，不用 ss/netstat | 精简镜像普遍没有这些命令；/proc 是内核接口一定存在 |
| loopback 坑 | 探测到 `bind=127.0.0.1` 直接判 `host_reachable=false` 并给修复建议 | 8-03 用户实际踩过的坑，这次在数据层堵掉 |
| 启动服务 | `launch_service()` **强制 `--hostname 0.0.0.0`** | 从源头消灭上面那个坑 |
| 自动登记 | 快速命令里跑 opencode → 自动 upsert 登记 | 用户不必手工再记一遍 |
| 生命周期 | 容器删除 → 级联清登记；容器重建 → 迁移登记到新 ID | 避免 DB 留 unreachable 脏数据 |
| AIDE 源 | 改为**读 DB**（`is_aide_source AND host_reachable`） | 快、准、且能解释「为什么这个不能选」 |
| UI 新鲜度 | 每行显示「探测于 X 前」，>60s 标「可能已过期」+ 可选 15s 自动刷新 | 让快照语义对用户透明 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/container_service_model.py` | `ContainerService` + `ServiceKind` / `ServiceStatus` 枚举 |
| `backend/app/db/repositories/container_service_repo.py` | 含 `get_by_container_port` / `list_aide_sources` / `delete_by_container` |
| `frontend/src/components/compute/ServicesPanel.tsx` | 「服务」tab：状态表格 + 探测新鲜度 + 启动/停止/刷新/扫描发现 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册新 model（否则 `create_all` 不建表）|
| `backend/app/schemas/compute_schema.py` | 新增 `ContainerServiceResponse` / `ContainerServiceCreate` / `ServiceRefreshResult` / `ServiceLaunchRequest` |
| `backend/app/services/compute_service.py` | 新增 `_parse_listen_table` 等解析函数；服务登记 CRUD、`refresh_service(s)`、`discover_services`、`launch_service`、`stop_service`、`_probe_one` 四步探测；`get_aide_sources` 改读 DB；exec 自动登记；容器删除/重建时维护登记；补 `httpx` import |
| `backend/app/api/v1/compute.py` | 新增 8 个服务端点；`aide-sources` 支持 `refresh` |
| `backend/tests/test_smoke.py` | 表清单断言补 `container_services`（5 → 6 张表）|
| `frontend/src/types/compute.ts` | `ContainerServiceInfo` 等类型 + 状态色/文案映射 |
| `frontend/src/services/compute.service.ts` | 8 个服务 API；`listAideSources` 支持 refresh |
| `frontend/src/pages/compute/ComputePage.tsx` | 新增「服务」tab |
| `frontend/src/pages/aide/AidePage.tsx` | 源下拉改读 `container_services`，富选项（状态点 + 访问地址 + 不可用原因）、不可用项置灰、选前校验、独立刷新按钮；容器源模式隐藏本机启停按钮；修 antd v6 `onDropdownVisibleChange` 弃用 |

### API 端点（新增 8 个）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/compute/services?node_id&refresh` | 列服务（refresh=1 先回探）|
| POST | `/compute/services/refresh` | 批量回探（维护实时性主入口）|
| POST | `/compute/services/discover` | 扫描补录现实中已在跑但未登记的服务 |
| POST | `/compute/nodes/{nid}/containers/{cid}/services` | 手工登记（upsert）|
| POST | `/compute/nodes/{nid}/containers/{cid}/services/launch` | 一键启动 opencode + 登记（强制 0.0.0.0）|
| POST | `/compute/services/{id}/refresh` | 回探单个 |
| POST | `/compute/services/{id}/stop` | 停容器内进程（保留登记）|
| DELETE | `/compute/services/{id}` | 删登记（不动进程）|

变更：`GET /compute/aide-sources` 增加 `refresh` 参数，数据源由「实时扫容器」改为「查 container_services」。

### 数据库

**新增 1 张表 `container_services`**（5 → 6 张）：
- 归属：`node_id`(FK→compute_nodes, CASCADE) / `node_name` / `container_id` / `container_name` / `image`
- 定义：`kind`(enum) / `name` / `container_port` / `host_port` / `access_url` / `command` / `log_path` / `exec_id`
- 探测态：`status`(enum) / `status_detail` / `bind_address` / `host_reachable` / `last_checked_at` / `is_aide_source`
- 唯一键 `uq_container_port(container_id, container_port)`

⚠️ 建表踩坑：首次 `create_all` 时被上一个被 kill 的进程遗留的
`Waiting for table metadata lock` 卡死。处理办法：
`SELECT * FROM performance_schema.metadata_locks` 定位持锁事务 → KILL 掉长 Sleep 的孤儿连接。

### 验证

后端（curl + docker 交叉校验）：
- `discover` 扫出 2 个服务，`bind_address=0.0.0.0` / `host_reachable=true` / `is_aide_source=true` ✅
- MySQL 落库确认：`(1,'opencode001',4097,14097,'running','0.0.0.0',1,1)`、`(2,'opencode',4096,14096,...)` ✅
- **状态真实性**：容器内 `pkill` 掉服务 → refresh 后该行变 `stopped`、`is_aide_source=false`，
  aide-sources 只剩 1 个 ✅
- **loopback 检测**：故意用 `--hostname 127.0.0.1` 起服务 → 识别为 `bind=127.0.0.1`、
  `host_reachable=false`，提示「Docker 端口映射对它无效…加 --hostname 0.0.0.0」✅
- `launch` 一键启动 → 命令含 `--hostname 0.0.0.0`，回探 `host_reachable=true` ✅

前端（Playwright 真实浏览器）：
- 「服务」tab 展示两个服务、AIDE 标签、运行中、`bind 0.0.0.0`、「探测于 X 前」、统计条 ✅
- AIDE 下拉 2 个富选项（状态点 + `http://localhost:14096` + kind 标签）✅
- 选中后 iframe src 切到 `http://localhost:14096`，工具条显示「容器 opencode」+「容器端口 4096」✅
- 杀掉 4097 服务 → 下拉该项**自动置灰**并显示「容器内端口 4097 没有进程监听…」✅
- 四个 tab + AIDE 全量走查：**console 0 error，API 0 失败** ✅

回归：`pytest` 24 passed；`tsc -b` 0 error；`vite build` 252ms 成功。

### 追加修复：容器控制台点不同容器进的都是同一个终端

**现象**：在「Docker 管理」点 A 容器的控制台，再点 B 容器的控制台，终端仍连着 A。

**根因（两个叠加缺陷）**：
1. `ContainerConsole` 用 `const [target] = useState(() => getStoredTarget())` 从 sessionStorage 取目标。
   `useState` 的初始化函数**只在首次挂载时执行一次**，而该面板被 antd `Tabs` 常驻挂载
   （切 tab 不卸载），所以后续 `sessionStorage.setItem` 再也不会被读到 → target 永远是第一个容器。
2. 即使 target 更新了，自动连接 effect 的依赖是 `[shell, probing]`，**不含容器身份**。
   切到「shell 相同的另一个容器」时两者都没变，effect 不重跑 → WebSocket 仍指向旧容器。

**处置**：
- 目标改由 **store 持有**（`computeStore.consoleTarget` + `openConsole()` action），
  彻底放弃 sessionStorage 这条非响应式通路；`DockerManagement.openConsole` 改调 store action
- shell 探测 effect 依赖改为 `[target?.nodeId, target?.containerId]`，
  并在切换时**先 `cleanup()`** 杀掉旧 WebSocket + dispose 旧 xterm 实例（防串台）
- 自动连接 effect 依赖补上容器身份
- 控制台头部同时显示 **容器名 + 短 ID**，同名/相似容器也能一眼确认连的是哪个

**验证**（Playwright + 容器内唯一标记文件）：
- 在两个容器内分别写 `/tmp/whoami.txt`，点各自控制台后在终端 `cat`：
  `opencode001` → `I_AM_CONTAINER_OPENCODE001_4097`；`opencode` → `I_AM_CONTAINER_OPENCODE_4096` ✅
- 头部显示与实际容器 ID 一致（`aaacb9802daa` / `d75583b77b97`）✅
- 快速来回切换 4 次，**4/4 header 与点击目标一致**，无串台 ✅
- WebSocket 生命周期：切换时旧连接全部 close；离开算力页后 `opened=1 closed=1 leaked=0` ✅
- 全量走查 4 tab + AIDE：console 0 error、API 0 失败 ✅

**涉及文件**：`frontend/src/stores/computeStore.ts`（新增 `consoleTarget` / `openConsole`）、
`frontend/src/types/compute.ts`（新增 `ConsoleTarget`）、
`frontend/src/components/compute/ContainerConsole.tsx`、
`frontend/src/components/compute/DockerManagement.tsx`。

### 遗留 / 注意
- `_probe_host_reachable` 探的是**后端视角**的可达性。后端与浏览器不同机时（远程节点场景）
  可能与用户实际情况不一致，UI 已展示 `access_url` 供用户自行确认。
- 服务状态是**拉取式**（按需/定时回探），没有做 watch/推送。长期停留可开「15s 自动刷新」。
- 远程 SSH 节点的服务探测逻辑已实现但未在真机验证（当前只有 local 节点在线）。

---

## 2026-08-03（下午）

### Agent: 算力管理 — 容器管理全链路排障与重构

### 目标
用户反馈 `/compute` 页「容器管理功能全是不能用的」：创建/修改容器都不成功、opencode 容器点 console 报错、
错误信息匪夷所思、输入框全靠手写字符串拼接。要求逐项排查、优雅实现、每改一处自测后交付。

### 排查方法
起本地 Docker + uvicorn + vite，用 curl 直打 API、`docker inspect` 校验真实状态、
Playwright 驱动真实浏览器跑完整交互，逐条定位而非猜测。

### 发现并修复的 14 个缺陷

| # | 缺陷 | 根因 | 影响 |
|---|------|------|------|
| 1 | 创建容器端口**方向反了** | `port_bindings[f"{parts[0]}/tcp"] = parts[1]`，把 `8099:80` 建成「容器 8099 → 宿主 80」 | 端口映射全错，服务永远访问不到 |
| 2 | 创建容器**永久挂起** | 直接 `containers.run()`，镜像缺失时 SDK 隐式 pull，无网络时无限等待且无任何提示 | 「点新建一直转圈，最后什么都没有」 |
| 3 | 容器列表端口**重复且反向** | 只读 `NetworkSettings.Ports` 未按 IPv4/IPv6 去重 | 显示 `4096:14096, 4096:14096` |
| 4 | Docker 面板**永远 0 个容器** | `ensureLocalNode()` 直接 set selectedNode，从不触发 fetch（只有 `selectNode()` 里才 fetch） | 进页面就是空表，功能「全都不能用」的直接观感 |
| 5 | `aide-sources` **永远返回空** | 自己 split ports 字符串且方向搞反 | AIDE 无法发现 opencode 容器 |
| 6 | 修改容器表单**回填空白** | 前端读 `raw.config` / `hostConfig.restartPolicy`（驼峰），而 docker inspect 是 `Config` / `HostConfig.RestartPolicy` | 一改就把端口/环境变量清空 |
| 7 | 后台命令**永远显示「已退出」** | 用 `fuser` 判活，精简镜像普遍没这个命令 | 无法观察长任务 |
| 8 | 后台命令 **exit_code 永远 0/None** | `grep -oP 'EXIT_CODE=\K\d+'` 找一个从没被写入的标记 | 失败当成功 |
| 9 | exec **命令注入 / 引号截断** | `sh -c '{cmd}'` 裸拼，命令含单引号即破 | 安全问题 + 命令跑不了 |
| 10 | 控制台**硬编码 `/bin/bash`** | 前端固定 `/bin/bash`，alpine/distroless 无 bash 直接失败且无提示 | **「opencode 容器点 console 报错」的根因** |
| 11 | 启停后表格行**变空白** | 远程分支 `return ContainerInfo(name="", image="", ...)` | UI 状态被空值覆盖 |
| 12 | 改配置后容器**起不来** | 重建只带 `Cmd` 丢了 `Entrypoint` | 改个端口容器就废 |
| 13 | 所有错误被**静默吞掉** | store 里 `catch {}` 空处理 | 用户看不到任何原因 |
| 14 | antd v6 弃用告警 | `Alert message` / `notification message` / `Space direction` / `InputNumber addonBefore` / 静态 notification | 控制台一片红 |

### 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 端口/挂载/环境变量传输格式 | 字符串拼接 → **结构化对象** (`PortMapping`/`VolumeMapping`/`EnvVar`) | 方向语义由字段名固定，Pydantic 直接校验，前后端不再靠解析猜 |
| 端口方向 | `to_docker_key()` = `容器端口/协议`，值 = 宿主端口 | 与 docker SDK 契约对齐并写进方法名，避免再写反 |
| 镜像拉取 | 显式 `images.get()` → 缺失才 `pull()` → 900s 上限 | 杜绝隐式挂起，超时给可执行建议 |
| 容器列表数据源 | 统一走 `docker inspect` 全量 JSON（本地 + 远程同口径） | 一次拿全端口/挂载/env/网络，前端零解析 |
| 运行态判定 | `fuser` → **sentinel 文件**（`.done` 内含 exit code） | 不依赖容器内有额外命令 |
| shell 选择 | 新增 `/shells` 探测端点 + 后端自动回退 + WS 下发 notice | bash 缺失时自动换 sh，不再报错 |
| 修改容器 | 字段 `None`=沿用 / `[]`=清空；保留 Entrypoint；原在跑则重建后自动起 | 语义明确，重建不破坏容器 |
| 命令执行 | 新增 **sync / async 双模式** | 短命令直接看结果，长任务才轮询 |
| 表单 UX | 6 个**容器预设** + 每字段 placeholder/示例/「填入示例」+ 实时 `docker run` 预览 | 满足「不要那么多输入，每个输入都有案例」 |
| 错误呈现 | 后端把 docker 原始报错**翻译成可执行中文**；前端 banner + notification | 端口占用/重名/挂载被拒/网络不存在都直接说怎么改 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `frontend/src/components/compute/ContainerConfigEditor.tsx` | 端口/环境/挂载/网络/重启 结构化行编辑 + 校验 + docker run 预览 |
| `frontend/src/components/compute/ContainerFormModal.tsx` | 新建/修改容器共用弹窗（预设驱动 + 结构化回填） |
| `frontend/src/components/compute/ContainerExecModal.tsx` | 快速命令弹窗（模板参数表单 + sync/async + 轮询日志） |

### 修改文件

| 文件 | 说明 |
|------|------|
| `backend/app/schemas/compute_schema.py` | 新增 `PortMapping`/`VolumeMapping`/`EnvVar`/`ImagePull*`/`ContainerPreset`；`ContainerInfo` 带结构化配置；7 个命令模板（含 mode/example）；6 个容器预设 |
| `backend/app/services/compute_service.py` | 新增 inspect→结构化 解析函数组；重写 create/list/update/exec/aide-sources；新增 `detect_shells`/`resolve_shell`/`pull_image`/`_explain_docker_error`/`_validate_container_request` |
| `backend/app/api/v1/compute.py` | 新增 `POST /images/pull`、`GET /containers/{id}/shells`、`GET /container-presets`；WS console 改为自动选 shell + 下发 error/notice |
| `frontend/src/types/compute.ts` | 结构化类型 + 状态中文映射 + preset/shell/pull 类型 |
| `frontend/src/services/compute.service.ts` | 新增 `pullImage`/`detectShells`/`listContainerPresets`；create/update 放宽 timeout |
| `frontend/src/stores/computeStore.ts` | 修复自动选中本地节点后不 fetch；新增 `dockerError`/`pullImage`/`fetchPresets`；导出 `extractErrMsg`；操作错误改为抛出 |
| `frontend/src/components/compute/DockerManagement.tsx` | 重写：结构化列（端口方向/挂载数/网络）、行级 loading、错误 banner、镜像拉取、接入新弹窗 |
| `frontend/src/components/compute/ContainerConsole.tsx` | shell 自动探测 + 自动连接 + 解析 JSON 控制帧 + 可执行错误提示 + 清理泄漏 |
| `frontend/src/components/compute/NodeManagement.tsx` | antd v6 适配（`App.useApp()` + orientation） |

### API 端点

新增 3 个：
- `POST /api/v1/compute/nodes/{id}/images/pull` — 拉取镜像（900s 上限）
- `GET  /api/v1/compute/nodes/{id}/containers/{cid}/shells` — 探测可用 shell
- `GET  /api/v1/compute/container-presets` — 容器预设清单

变更契约：`POST/PUT /containers` 的 `ports`/`envs`/`volumes` 由字符串改为结构化数组；
`ContainerInfo` 增加 `port_mappings`/`volume_mappings`/`env_vars`/`command`/`restart`/`network`/`state_detail`/`exit_code`。

### 数据库
无变更。

### 验证

后端（curl + docker inspect 交叉校验）：
- 创建 `8099:80` → `PortBindings={"80/tcp":[{"HostPort":"8099"}]}` ✅ 方向正确
- 列表端口 `4096:14096, 4096:14096` → `4096->14096` ✅ 去重
- 重名 → 「容器名 'x' 已被占用。请换一个名字…」；相对路径 → 「'app' 应写成 '/app'」；host+端口 → 明确拒绝 ✅
- sync exec `exit 3` → `exit_code=3`；async `exit 7` → 日志增量 + `running` 翻转 + `exit_code=7` ✅
- 含单引号命令 `echo 'it'\''s fine'` → 正确输出 `it's fine` ✅
- shells 探测 → `{"shells":["/bin/bash","/bin/sh"],"default":"/bin/bash"}` ✅
- aide-sources：`4200:4096` 容器 → 正确识别（原来恒为 `[]`）✅
- 改端口后 `Entrypoint=["/bin/sleep"] Cmd=["600"]` 保留且容器仍 `running` ✅

前端（Playwright 真实浏览器）：
- Docker 管理 tab 容器数 1、`opencode` 可见（原为「暂无容器」）✅
- 选 Nginx 预设 → 预览自动出现 `-p 8080:80 -v /tmp/site:… --restart` ✅
- UI 建容器 `18081→8080` + env → docker 侧完全一致、状态 running ✅
- 改端口 → 弹窗正确回填、重建后 `19090` 生效、env 保留、成功通知 ✅
- opencode 控制台 → 自动选 bash、自动连接、`echo CONSOLE_WORKS_123` 有真实回显 ✅
- 快速命令 → 7 模板、`进程列表` sync 执行返回 ps 输出 + 「成功 (exit 0)」✅
- 空镜像/空镜像名校验、host 模式禁用端口 联动 ✅
- Docker Desktop 停止时 → 明确 banner「无法连接本地 Docker…请确认 Docker Desktop 已启动」（原为静默空表）✅
- 浏览器控制台 **0 error**（原有多条 antd 弃用告警）✅

回归：`pytest` 24 passed；`tsc -b` 0 error；`oxlint` compute 相关 0 新增问题；`vite build` 1.07s 成功。

### 追加修复：容器内服务绑 loopback 导致宿主访问不到

**现象**：用户在容器内跑 `opencode web --port 4096`，容器端口映射为 `0.0.0.0:14096->4096/tcp`，
但宿主 `http://localhost:14096/` 访问不到。

**定位**（三步实证，非猜测）：
1. `docker exec ... curl 127.0.0.1:4096` → **200**；`curl 172.17.0.2:4096`（容器自身 eth0 IP）→ **000**
2. `/proc/net/tcp` 显示 `0100007F:1000 0A` —— 即 LISTEN 在 `127.0.0.1:4096`，而非 `0.0.0.0`
3. `opencode web --help` 确认 `--hostname` **默认值就是 `127.0.0.1`**

**根因**：Docker 端口转发的目标是「容器 IP:容器端口」(`172.17.0.2:4096`)，
进程只绑容器 loopback 时该地址无人监听 → 转发落空。与端口映射配置无关。

**处置**：
- 现场用 `opencode web --port 4096 --hostname 0.0.0.0` 重启，`/proc/net/tcp` 变为 `00000000:1000`，
  宿主 `http://localhost:14096/` 返回 200 + 正常 HTML ✅
- 平台侧把坑消灭在模板里（`app/schemas/compute_schema.py`）：
  - `opencode-serve` / `opencode-web` 两个模板**新增 `hostname` 参数，默认 `0.0.0.0`**，
    命令串固定带 `--hostname {hostname}`，描述里写明「不要用 127.0.0.1」
  - `opencode-web` 默认端口从 4097 修正为 4096（与实际用法一致）
  - **新增 `check-bind-address` 模板**：列出容器内所有 LISTEN 端口及绑定地址，
    并把 `0100007F` / `00000000` 直接翻译成「仅容器内可访问」/「宿主可访问」，
    无 `ss`/`netstat` 的精简镜像也能用（回退解析 `/proc/net/tcp`）

**验证**：`check-bind-address` 经 API 实跑输出 `port 4096  bind 0.0.0.0 [宿主可访问]`，exit 0；
命令模板总数 7 → 8；`pytest` 24 passed。

### 遗留 / 注意
- 本次把 `/containers` 的请求体契约从字符串改为结构化数组，若有其它调用方需同步调整。
- `_exec_sessions` 仍是进程内内存态，后端重启后旧 exec_id 查不到（已给明确提示）。
- 远程（SSH）节点的结构化解析已实现但**未在真机验证**（当前只有 local 节点在线）。

---

## 2025-07-07

### Agent: 主开发 Agent（感知层元数据提取系统 — 存储 + 浏览 + LLM/Agent 标注 + 流式交互）

### 目标
1. 对挂载的数据源进行元数据提取（表结构、字段信息、注释）
2. 元数据按表维度存储到 MySQL，设计可用于本体提取的结构
3. 实时连接数据源浏览数据
4. 支持大模型/Agent 自动注释（无注释的字段自动生成）
5. 标注交互参照 Cursor/CodeBuddy 风格 — 右侧对话面板 + 流式执行

### 设计决策

| 决策点 | 选择 |
|--------|------|
| 存储方式 | 表维度存储（meta_tables + meta_columns 两张表） |
| 元数据提取 | 通过 information_schema.TABLES + .COLUMNS + .KEY_COLUMN_USAGE |
| 同步策略 | 支持指定库 / 一键同步所有用户库（跳过系统库） |
| 查询优化 | 批量查 COLUMNS 再按表分组，避免 N+1 |
| 数据浏览 | 实时连接数据源 SELECT * LIMIT N OFFSET M |
| 标注方式 | 平台 LLM 或指定 Agent（CLI 模式），可自定义 prompt |
| 标注交互 | WebSocket 流式，右侧对话面板（参照 Cursor/CodeBuddy） |
| 本体映射 | entity_candidate + is_entity_identifier + is_relationship_key + related_table |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/metadata_model.py` | MetaTable + MetaColumn ORM 模型 |
| `backend/app/db/repositories/metadata_repo.py` | MetaTableRepository（upsert）+ MetaColumnRepository |
| `backend/app/services/metadata_service.py` | 元数据提取/浏览/标注/本体候选 服务 |
| `backend/app/schemas/metadata_schema.py` | 元数据 Pydantic Schema |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 MetaTable, MetaColumn |
| `backend/app/api/v1/perception.py` | 新增 10 个端点（sync/databases/tables/detail/preview/annotate + WebSocket 流式标注） |
| `frontend/src/services/index.ts` | 新增 10 个 API 方法 + WebSocket URL |
| `frontend/src/pages/perception/index.tsx` | 元数据浏览区 + 表详情双栏 Drawer（左:元数据 右:标注对话面板） |

### 数据库表设计

#### meta_tables — 表级元数据

| 字段 | 说明 |
|------|------|
| datasource_id | 关联数据源 |
| database_name + table_name | 库表定位（联合唯一） |
| table_type | table / view |
| table_comment / table_comment_llm | 原始注释 + LLM 生成注释 |
| business_description / purpose / domain | 业务描述/用途(dim/fact/ods/...)/业务域 |
| entity_candidate | 本体候选实体标记 |
| row_count / column_count / storage_size_mb / engine | 技术元数据 |

#### meta_columns — 字段级元数据

| 字段 | 说明 |
|------|------|
| column_name / data_type / data_type_full | 字段名和类型 |
| is_primary_key / is_unique / is_indexed / is_nullable | 约束信息 |
| column_comment / column_comment_llm | 原始注释 + LLM 注释 |
| semantic_type | 语义类型(id/name/amount/time/status/...) |
| is_entity_identifier / is_relationship_key | 本体映射辅助 |
| related_table / related_column | 外键关联（用于提取关系） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/datasources/{id}/sync` | 提取元数据（支持 sync_all） |
| GET | `/datasources/{id}/databases` | 列出所有库 |
| GET | `/datasources/{id}/tables` | 表元数据列表 |
| GET | `/meta/tables/{id}` | 表详情（含字段） |
| PUT | `/meta/tables/{id}` | 编辑表业务元数据 |
| PUT | `/meta/columns/{id}` | 编辑字段业务元数据 |
| POST | `/meta/tables/{id}/preview` | 实时数据预览 |
| POST | `/meta/tables/{id}/annotate` | LLM/Agent 自动注释（HTTP） |
| **WS** | `/meta/tables/{id}/annotate/stream` | 流式标注（WebSocket） |
| GET | `/datasources/{id}/ontology-candidates` | 本体候选 |

### 标注交互（Cursor/CodeBuddy 风格）

后端 WebSocket `/meta/tables/{id}/annotate/stream`:
- asyncio subprocess 逐行读取 Agent CLI stdout
- 实时推送事件: status/context/prompt/thinking/text/tool_use/tool_result/error/applied/done
- 支持 Agent CLI 流式（OpenClaw --json / OpenCode --format json）
- 也支持平台 LLM
- 自动解析 JSON 结果并应用注释到数据库

前端表详情 Drawer（1200px 双栏）:
- 左侧（flex 1）: 表元数据 + 字段列表 + 数据预览
- 右侧（460px）: 智能标注对话面板
  - Agent 选择器（平台 LLM / OpenClaw / OpenCode）
  - 事件流区域（实时显示执行过程，带图标颜色区分）
  - 自定义 prompt 输入框 + 发送/停止按钮

### 验证
- ✅ TypeScript 编译零错误
- ✅ 后端路由全部注册
- ✅ WebSocket 流式标注可用
- ✅ 元数据提取支持同步所有库
- ✅ 外键关系自动提取

---

## 2025-07-02

### Agent: 主开发 Agent（资源管理增强 — 本地服务器一键注册 + Agent 自动发现 + CLI 流式交互）

### 目标
1. 修复计算节点显示 offline 问题
2. 实现一键添加本地服务器为计算节点
3. 自动发现计算节点上运行的 Agent（OpenClaw/OpenCode）
4. 支持与 Agent 实时流式交互测试（WebSocket）

### Bug 修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 计算节点显示 offline | `status` 默认值是 `offline`，心跳接口只写 `last_heartbeat` 不写 `status` | `update_heartbeat()` 同时设置 `status=online`；`register-local` 注册后立即设为 `online` |
| Ant Design v5 废弃警告 | `bodyStyle`/`valueStyle`/`width`/`direction` 等 prop 被废弃 | 全量替换为 `styles.body`/`styles.content`/`styles.wrapper`/`orientation` |
| Agent 测试「无响应内容」 | OpenClaw/OpenCode 是 CLI 工具不是 HTTP 服务，之前用 HTTP 请求打 dev server 端口 | 改为 CLI 模式，用 `shutil.which` 检测命令路径 |
| OpenCode 输出解析失败 | 输出带 ANSI 转义码 + JSONL 事件流，旧代码直接 `json.loads` 整体失败 | 逐行解析 JSONL + ANSI 清理 |
| OpenClaw 需要 --agent 参数 | `agent` 命令必须指定 `--agent <name>` | 自动执行 `agents list` 获取第一个可用 agent 名称 |
| WebSocket 连接失败 | 后端缺少 `websockets` 库 | `pip install websockets` |
| 发送后不自动停止 loading | 后端 `while True` 循环发完 `done` 后没 `break`；前端 `onclose` 只在无内容时才 `setChatSending(false)` | 后端加 `break`；前端 `onclose` 无条件重置 |
| Space.Compact DOM 错误 | antd Drawer 内 `getBoundingClientRect` on null | 改为普通 flex div |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/agent_discovery.py` | Agent 发现与可用性检测服务（CLI 检测 + 进程扫描 + 端口扫描 + HTTP 健康检查） |

### 修改文件

| 文件 | 变更要点 |
|------|---------|
| `backend/app/api/v1/resources.py` | 新增 `register-local`、`scan-agents`、`agents/{id}/chat`（POST）、`agents/{id}/chat/stream`（WebSocket）4 个端点 |
| `backend/app/db/repositories/instance_repo.py` | `update_heartbeat` 同时更新 `status=online` |
| `frontend/src/pages/resources/index.tsx` | 计算节点卡片新增「添加本地服务器」按钮 + Agent 发现区域 + Agent 卡片新增 💬 测试按钮 + WebSocket 流式聊天 Drawer |
| `frontend/src/services/index.ts` | 新增 `registerLocalInstance`、`scanAgents`、`chatWithAgent`、`chatWithAgentStream` |
| `frontend/src/types/index.ts` | 新增 `DiscoveredAgent`、`AgentScanResult` 类型 |

### 设计决策

| 决策点 | 选择 |
|--------|------|
| Agent 发现策略 | CLI 命令检测（`shutil.which`）> 进程扫描（`pgrep`）> 端口扫描 + HTTP 健康检查 |
| Agent 交互模式 | 自动判断：entrypoint 以 `http` 开头 → HTTP 模式，否则 → CLI 模式 |
| CLI 命令模板 | 参照 multica 项目封装方式，每种 agent_type 有专属 `cli_chat_args` |
| 流式交互 | WebSocket + `asyncio.create_subprocess_exec` 逐行读取 stdout，实时推送事件 |
| agent_name 存储 | OpenClaw 的 `--agent` 参数值存入 `env_template` 字段 |

### Agent 发现配置（参照 multica）

| Agent | CLI 命令 | 交互参数 | 环境变量 |
|-------|---------|---------|---------|
| OpenClaw | `openclaw` | `agent --agent {agent_name} -m "{msg}" --json` | — |
| OpenCode | `opencode` | `run --format json "{msg}"` | `OPENCODE_PERMISSION={"*":"allow"}` |
| Harness | `harness` | `"{msg}"` | — |

### WebSocket 事件类型

| 事件 | 图标 | 说明 |
|------|------|------|
| `status` | ⏳ | 执行状态 |
| `thinking` | 💭 | 思考过程 |
| `text` | 💬 | 文本回复 |
| `tool_use` | 🔧 | 工具调用 |
| `tool_result` | 📋 | 工具结果 |
| `error` | ⚠️ | 错误信息 |
| `log` | ┃ | 原始日志 |
| `meta` | ℹ️ | 模型信息 |
| `done` | — | 完成（exit_code + stderr） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/resources/instances/register-local` | 一键添加本地服务器 |
| POST | `/resources/instances/{id}/scan-agents` | 扫描 Agent + 自动注册 |
| POST | `/resources/agents/{id}/chat` | Agent 交互（HTTP，兼容旧版） |
| **WS** | `/resources/agents/{id}/chat/stream` | Agent 交互（WebSocket 流式） |

### 本机检测结果
- OpenClaw → `/opt/homebrew/bin/openclaw` (v2026.3.13) — CLI 模式，agent_name=testagent
- OpenCode → `/Users/sunleone/.opencode/bin/opencode` (v1.14.39) — CLI 模式
- 当前状态：两个 Agent 的 API key/订阅均过期（OpenCode: Coding Plan expired，OpenClaw: API rate limit）

### 验证
- ✅ TypeScript 编译零错误
- ✅ 后端所有路由注册正常
- ✅ WebSocket 流式交互可用（thinking/text/error/log 实时推送）
- ✅ 前端事件流渲染正常（带图标+颜色区分）
- ✅ 发送/停止 loading 状态正确

---

## 2025-07-01

### Agent: 主开发 Agent（下午 — 需求项目管理完整实现）

### 目标
实现 Agent 驱动的需求项目管理（Project / Requirement / Plan / Task + Kanban），打通「需求提交 → Agent评审打分 → Agent拆解为Task → 看板跟踪」全链路。

### 设计决策

| 决策 | 方案 |
|------|------|
| 需求模板 | 标题 / 类型(feature|bug|improvement|perf) / 优先级(P0-P3) / 描述 / 验收标准 / 影响范围 |
| Agent 评审 | LLM 三维打分：需求清晰度 + 技术可行性 + 业务价值 → 综合评分 ≥5 通过 |
| 任务拆解 | LLM 自动拆分为 3-8 个 Task，含标题/描述/优先级/工时/建议Agent类型 |
| 敏捷看板 | 4 列（待开始/进行中/评审中/已完成），HTML5 原生拖拽移动 |
| 项目层级 | Project → Plan (Sprint/Release/Milestone) → Task |

### 新增文件（后端）

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/project_model.py` | Project ORM（name/key/icon/color/status） |
| `backend/app/db/models/requirement_model.py` | Requirement ORM（模板字段 + Agent 评分字段） |
| `backend/app/db/models/plan_model.py` | Plan ORM（sprint/release/milestone + 日期范围） |
| `backend/app/db/models/task_model.py` | Task ORM（status/assignee_agent/工时/position） |
| `backend/app/db/repositories/project_repo.py` | ProjectRepository |
| `backend/app/db/repositories/requirement_repo.py` | RequirementRepository |
| `backend/app/db/repositories/plan_repo.py` | PlanRepository |
| `backend/app/db/repositories/task_repo.py` | TaskRepository（含 get_kanban / batch_create） |
| `backend/app/schemas/project_schema.py` | 全部 Pydantic Schema（含 TaskMove 看板移动） |
| `backend/app/services/project_service.py` | ProjectService CRUD |
| `backend/app/services/requirement_service.py` | RequirementService + analyze() LLM评审 + decompose() LLM拆解 |
| `backend/app/api/v1/projects.py` | 完整 REST API（20 个端点 + /kanban 看板查询） |

### 新增文件（前端）

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/projects/index.tsx` | 完整页面：项目选择器 + 需求池(卡片列表) + 敏捷看板(拖拽4列) + 计划列表 + Agent工作流引导 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 4 个新模型 |
| `backend/app/api/v1/router.py` | 挂载 projects 路由 |
| `backend/schema.sql` | 新增 4 张表 DDL（projects/requirements/plans/tasks） |
| `frontend/src/App.tsx` | 注册 /projects 路由 |
| `frontend/src/components/layout/AppLayout.tsx` | 导航新增「项目管理」 |
| `frontend/src/types/index.ts` | 新增 5 个类型（Project/Requirement/Plan/Task/KanbanData） |
| `frontend/src/services/index.ts` | 新增 projectsAPI 完整封装（20+ 方法） |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/projects` | 项目 CRUD |
| GET/POST | `/projects/{id}/requirements` | 需求列表/创建 |
| PUT/DELETE | `/projects/{id}/requirements/{rid}` | 需求更新/删除 |
| POST | `/projects/{id}/requirements/{rid}/analyze` | 🤖 Agent 评审打分 |
| POST | `/projects/{id}/requirements/{rid}/decompose` | 🤖 Agent 拆解为 Task |
| GET/POST/PUT/DELETE | `/projects/{id}/plans` | 计划 CRUD |
| GET/POST/PUT/DELETE | `/projects/{id}/tasks` | 任务 CRUD |
| PUT | `/projects/{id}/tasks/{tid}/move` | 看板拖拽移动 |
| GET | `/projects/{id}/kanban` | 看板数据 |

### 验证
- ✅ TypeScript 编译零错误
- ✅ 全部 API 端点返回正常
- ✅ 项目 CRUD + 需求 CRUD + 计划 CRUD 全链路验证
- ✅ 后端自动建表生效（12 张表完整）

---

### Agent: 主开发 Agent（上午 — 资源管理中心完整实现）

### 目标
实现资源管理的 5 个核心实体（Instance / Agent / Skill / MCP / AgentRun）+ WebSocket 实时日志，支撑 Agent 编排配置能力。

### 设计决策
| 决策点 | 选择 |
|--------|------|
| 节点管理协议 | SSH + Docker API（不做 k8s） |
| Agent 运行方式 | 混合支持：docker / python / node / binary |
| Skill 归属 | 全局共享，Agent 管理页一键安装 |
| MCP 自动发现 | 任意 HTTP API + LLM 推断参数 |
| 实时日志 | WebSocket 流式推送 |

### 新增文件（后端）

| 文件 | 层 | 说明 |
|------|------|------|
| `backend/app/db/models/instance_model.py` | 数据层 | Instance ORM（instance_type / protocol / credential / labels / status） |
| `backend/app/db/models/agent_model.py` | 数据层 | Agent ORM（agent_type / runtime / docker_image / skill_ids） |
| `backend/app/db/models/skill_model.py` | 数据层 | Skill ORM（skill_type / install_cmd / is_installed / tags） |
| `backend/app/db/models/mcp_model.py` | 数据层 | MCPConfig ORM（mcp_type / auto_discovery / tools_manifest） |
| `backend/app/db/models/agent_run_model.py` | 数据层 | AgentRun ORM（status / container_id / pid / log_offset） |
| `backend/app/db/repositories/instance_repo.py` | 数据层 | InstanceRepository（update_heartbeat） |
| `backend/app/db/repositories/agent_repo.py` | 数据层 | AgentRepository（get_by_type） |
| `backend/app/db/repositories/skill_repo.py` | 数据层 | SkillRepository（get_installed / get_by_tags） |
| `backend/app/db/repositories/mcp_repo.py` | 数据层 | MCPRepository |
| `backend/app/db/repositories/agent_run_repo.py` | 数据层 | AgentRunRepository（get_running / get_by_agent / get_by_instance） |
| `backend/app/schemas/instance_schema.py` | Schema | Instance CRUD Pydantic 校验 |
| `backend/app/schemas/agent_schema.py` | Schema | Agent CRUD + AgentUpdate |
| `backend/app/schemas/skill_schema.py` | Schema | Skill CRUD + SkillInstallRequest |
| `backend/app/schemas/mcp_schema.py` | Schema | MCP CRUD + MCPAutoDiscoverRequest（api_url / method / LLM 推断参数） |
| `backend/app/schemas/agent_run_schema.py` | Schema | AgentRun CRUD + LogEntry |
| `backend/app/services/instance_service.py` | 服务层 | InstanceService 完整 CRUD |
| `backend/app/services/agent_service.py` | 服务层 | AgentService 完整 CRUD |
| `backend/app/services/skill_service.py` | 服务层 | SkillService + install() 一键安装 |
| `backend/app/services/mcp_service.py` | 服务层 | MCPService + auto_discover() LLM 推断 |
| `backend/app/services/agent_run_service.py` | 服务层 | AgentRunService + stream_logs() WebSocket 日志流 |
| `backend/app/api/v1/resources.py` | 接口层 | 完整 API：Instance/Agent/Skill/MCP/AgentRun 全部 CRUD + WebSocket 日志 + MCP 自动发现 |

### 新增文件（前端）

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/resources/index.tsx` | 全面重写：6 个 Tab（LLM 配置 + 计算节点 + 智能体 + 技能 + MCP 工具 + 运行监控），含 WebSocket 日志抽屉、MCP 自动发现弹窗、Skill 一键安装按钮 |
| `docs/RESOURCE_MANAGEMENT_DESIGN.md` | 资源管理模块设计文档（实体关系、字段设计） |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/db/models/__init__.py` | 注册 5 个新模型 |
| `backend/app/api/v1/router.py` | 挂载 resources 路由 `/resources` |
| `backend/app/main.py` | 添加启动时自动建表 `Base.metadata.create_all()` |
| `backend/schema.sql` | 新增 5 张表 DDL（instances / agents / skills / mcp_configs / agent_runs） |
| `frontend/src/types/index.ts` | 新增 5 个实体类型定义 |
| `frontend/src/services/index.ts` | 新增 resourcesAPI 完整调用封装 |

### API 端点汇总（全部测试通过）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/resources/instances` | 计算节点 CRUD |
| POST | `/resources/instances/{id}/heartbeat` | 心跳刷新 |
| GET/POST/PUT/DELETE | `/resources/agents` | Smart Agent CRUD |
| GET/POST/PUT/DELETE | `/resources/skills` | Skill CRUD |
| POST | `/resources/skills/{id}/install` | 一键安装 Skill |
| GET/POST/PUT/DELETE | `/resources/mcps` | MCP 工具 CRUD |
| POST | `/resources/mcps/auto-discover` | LLM 自动发现 MCP |
| GET/POST/PUT | `/resources/runs` | AgentRun 管理 |
| POST | `/resources/runs/{id}/stop` | 停止运行 |
| **WS** | `/resources/runs/{id}/logs` | WebSocket 实时日志 |

### 验证
- ✅ TypeScript 编译零错误
- ✅ 5 个端点全部返回 `{"code":"SUCCESS"}`
- ✅ 创建/查询/删除 Instance、Agent 全链路验证通过
- ✅ 后端自动建表生效（8 张表完整）

---

## 2025-06-30

### Agent: 主开发 Agent（晚间 — 感知层智能添加 & Bug 修复）

### 目标
修复前端白屏和智能添加失败问题，打通感知层完整链路（LLM 解析 → 保存 → 测试连接）。

### Bug 修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 前端白屏 | `perception/index.tsx` 使用不存在的图标 `TestOutlined`（`@ant-design/icons` 无此导出） | 替换为 `ExperimentOutlined` |
| 智能添加返回 500 | Qwen 推理模型返回 `content: null`，实际内容在 `reasoning` 字段 | `_call_openai()` 增加 fallback：`content` → `reasoning` → `reasoning_content` |
| LLM 解析 token 不足 | `max_tokens=1024` 不够推理模型思考 | 增加为 `4096`（parse-config / auto-configure），诊断类增加为 `512` |
| 保存数据源事务冲突 | `DataSourceService` 多处 `with self.db.begin()` 嵌套导致冲突 | 改为手动 `self.db.commit()` |
| LLM 返回字段名不标准 | Qwen 返回 `"type": "doris"` 而非 `"source_type": "doris"`，导致类型设为 unknown | 新增 `_normalize_parsed()` 辅助函数，`_FIELD_ALIASES` 映射 15+ 别名 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/db/models/data_source_model.py` | DataSource ORM 模型 |
| `backend/app/db/repositories/data_source_repo.py` | DataSourceRepository 数据层 |
| `backend/app/schemas/data_source_schema.py` | DataSource Pydantic Schema |
| `backend/app/services/data_source_service.py` | DataSourceService 服务层（含 create/update/delete/update_status/test_connection） |

### 修改文件

| 文件 | 变更要点 |
|------|---------|
| `backend/app/api/v1/perception.py` | 新增智能添加 3 个端点（parse-config / auto-configure / test-connection-for-source）、LLM 调用集成、`_normalize_parsed` 字段别名映射 |
| `backend/app/services/llm_config_service.py` | `_call_openai()` 增加 reasoning 字段 fallback；统一 `_call` 方法 |
| `backend/app/api/v1/llm.py` | 新增 `/active/info` 端点获取当前活跃 LLM 配置快照 |
| `backend/app/db/models/llm_config_model.py` | 补充字段 |
| `backend/app/schemas/llm_config_schema.py` | 补充 Schema 字段 |
| `backend/app/db/models/__init__.py` | 注册 DataSource 模型 |
| `frontend/src/pages/perception/index.tsx` | 重写：完整 CRUD 表格 + 智能添加对话框 + 连接测试 |
| `frontend/src/services/index.ts` | 新增 `DataSource` 类型和 API |
| `frontend/src/types/index.ts` | 新增 DataSource 类型定义 |
| `frontend/src/services/llm.service.ts` | 补充 API 方法 |
| `frontend/src/pages/resources/index.tsx` | 适配新类型 |

### 验证
- ✅ 智能添加全链路：LLM 解析配置 → 保存数据库 → 连接测试成功
- ✅ 解析返回正确字段：`source_type: doris` 带全部连接参数
- ✅ 前端无白屏，页面正常渲染
- ✅ TypeScript 编译零错误

---

### Agent: 主开发 Agent（下午 — UI/UE 框架重构）

### 目标
将前端整体替换为**硅谷风格**设计系统，涵盖暗色主题、玻璃拟态、渐变光晕、点阵背景、精致排版。

### 设计决策
| 维度 | 选择 |
|------|------|
| 主题 | Ant Design `darkAlgorithm` + 自定义覆写 |
| 字体 | Plus Jakarta Sans（Google Fonts）+ JetBrains Mono |
| 主色 | 蓝 `#3b82f6` → 紫 `#8b5cf6` → 青 `#06b6d4` 三色渐变 |
| 背景 | `#060b14` 根背景，`32px` 间距点阵纹理 |
| 玻璃效果 | `backdrop-filter: blur(12-20px)` + 半透明渐变 |
| 动效 | `cubic-bezier(0.16, 1, 0.3, 1)` 弹性曲线 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/styles/global.css` | 全局设计系统：CSS 变量（60+ Token）、动画关键帧（6 组）、点阵背景、玻璃拟态工具类、antd 组件 20+ 覆写 |

### 重写文件
| 文件 | 变更要点 |
|------|---------|
| `frontend/index.html` | 标题、lang、theme-color meta |
| `frontend/src/main.tsx` | 导入 global.css |
| `frontend/src/App.tsx` | `darkAlgorithm`、覆写全部 token、添加 `App` 包裹 |
| `frontend/src/components/layout/AppLayout.tsx` | 分组菜单（五层架构 group）、毛玻璃侧边栏、粘性顶栏、Logo 渐变图标、页面入场 `.page-enter` 错开动画 |
| `frontend/src/pages/Login.tsx` | 全屏暗色背景、双色模糊光球、玻璃拟态卡片、入场淡入 |
| `frontend/src/pages/dashboard/index.tsx` | 渐变色统计卡片、彩色图标容器、五层状态彩色指示灯 |
| `frontend/src/pages/perception/index.tsx` | Tag 颜色系统重构、Card 标题带图标 |
| `frontend/src/pages/cognition/index.tsx` | 图谱占位区渐变背景、语义搜索、实体/关系表格统一 Tag 风格 |
| `frontend/src/pages/decision/index.tsx` | 决策层 3 统计卡片、策略状态色彩映射表 |
| `frontend/src/pages/execution/index.tsx` | 监控指标彩色数字、目标系统在线 Tag、执行状态映射 |
| `frontend/src/pages/application/index.tsx` | AIbi 输入区渐变底层、数据集/仪表盘卡片 |
| `frontend/src/pages/users/index.tsx` | 用户表格外容器玻璃态、角色/状态彩色 Tag |

### Bug 修复
- 修复 `cognition/index.tsx` 缺少 `NodeIndexOutlined` 导入导致白屏
- 修复 `AppLayout.tsx` 误用 `useUserStore` 获取 sidebar 状态（改为 `useAppStore`）

### 验证
- TypeScript 编译零错误
- 20 个文件变更，+1646 / -267 行

---

### Agent: 主开发 Agent（上午 — 全链路打通）

### 目标
打通前后端全链路，实现用户注册/登录/删除完整功能，并使用本地 MySQL 数据库。

### 后端修复
| 文件 | 修复内容 |
|------|----------|
| `backend/app/core/exceptions.py` | 新增 `UnauthorizedException`（auth_service 之前引用但未定义） |
| `backend/app/api/v1/router.py` | 挂载 users 路由（之前遗漏） |
| `backend/app/api/v1/users.py` | 移除 router 内的 `prefix="/users"`（避免与 include_router 的 prefix 重复）；移除重复的 login 端点；路由重新排序避免 GET "" 与 GET "/{user_id}" 冲突 |
| `backend/app/api/v1/auth.py` | `/me` 端点从硬编码改为从 JWT Authorization Header 提取 user_id；`get_current_user_id` 依赖注入; register 改用 UserCreate Pydantic 校验 |
| `backend/app/services/auth_service.py` | 补充缺失的 `NotFoundException` 导入 |
| `backend/app/main.py` | 注册全局异常处理器 `add_exception_handlers(app)` |
| `backend/.env` | 新建：配置 DB_USER=root（无密码），匹配本地 MySQL |

### 数据库
- 创建 MySQL 数据库 `ontomind`（utf8mb4）
- SQLAlchemy `Base.metadata.create_all()` 初始化 `users` 表
- 注意：bcrypt 需用 4.x 版本（5.x 与 passlib 不兼容）

### 前端修复
| 文件 | 修复内容 |
|------|----------|
| `frontend/src/App.tsx` | 重写：移除循环引用，正确配置 react-router-dom Routes（公开 /login + 受保护路由 + 404 兜底） |
| `frontend/src/pages/Login.tsx` | 重写：真实对接 /auth/login 和 /auth/register API，支持登录+注册双 Tab |
| `frontend/src/services/user.service.ts` | login 改为 /auth/login，新增 getCurrentUser(/auth/me)；添加 snake_case→camelCase 映射 |
| `frontend/src/stores/userStore.ts` | fetchCurrentUser 调用 /auth/me |
| `frontend/src/components/layout/AppLayout.tsx` | 新增退出登录功能、当前用户显示、用户管理菜单项 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/pages/users/index.tsx` | 用户管理页面（表格展示 + 新建 + 删除） |

### 验证结果
- ✅ 用户注册 POST /auth/register
- ✅ 用户登录 POST /auth/login → 返回 JWT Token
- ✅ 获取当前用户 GET /auth/me（JWT 认证）
- ✅ 用户列表 GET /users
- ✅ 用户删除 DELETE /users/{id}
- ✅ 后端运行在 :8000，前端运行在 :5173
- ✅ MySQL `ontomind` 数据库，root 无密码

### 已知问题
- 前端用户管理页面（/users）需手动登录后访问，登录/注册在 Login 页面的双 Tab 中

---

## 2025-06-29

### Agent: 主开发 Agent

### 目标
为 OntoMind 项目建立全栈开发规范和设计范式，实现后端三层架构（接口层/服务层/数据层）分层重构。

### 新增文件

#### 规范文档
| 文件 | 说明 |
|------|------|
| `backend/STANDARDS.md` | 后端开发规范：分层架构、事务控制、命名规范、错误处理、依赖注入 |
| `backend/DESIGN_STANDARDS.md` | API 设计标准（RESTful 规范、错误码）和数据库设计标准（表命名、字段命名、索引策略） |
| `backend/REFACTORING_GUIDE.md` | 现有代码重构指南，指导如何将旧代码迁移到三层架构 |
| `frontend/STANDARDS.md` | 前端开发规范：代码组织、TypeScript 类型、API 服务层、Zustand 状态管理 |

#### 后端基础架构
| 文件 | 说明 |
|------|------|
| `backend/app/db/models/base.py` | BaseModel - 所有 ORM 模型基类（含 id, created_at, updated_at） |
| `backend/app/db/repositories/base_repo.py` | BaseRepository - 数据层基类，封装通用 CRUD 方法 |
| `backend/app/services/base_service.py` | BaseService - 服务层基类，统一管理 db session 注入 |
| `backend/app/core/exceptions.py` | BusinessException - 统一业务异常类（含错误码 + HTTP 状态码） |
| `backend/app/core/decorators.py` | @transactional - 事务装饰器，自动管理 commit/rollback |

#### 安全工具（新增 + 重构）
| 文件 | 说明 |
|------|------|
| `backend/app/core/security.py` | 密码哈希（bcrypt）、JWT Token 生成/解码/验证 |

#### 用户模块示例（完整三层架构模板）
| 文件 | 层 | 说明 |
|------|------|------|
| `backend/app/db/models/user_model.py` | 数据层 | User ORM 模型 |
| `backend/app/db/repositories/user_repo.py` | 数据层 | UserRepository，含特有查询方法 |
| `backend/app/schemas/user_schema.py` | Schema | Pydantic 请求/响应校验模型 |
| `backend/app/services/user_service.py` | 服务层 | UserService，含事务控制、密码加密等业务逻辑 |
| `backend/app/api/v1/users.py` | 接口层 | User CRUD API 端点 |

#### 认证模块重构
| 文件 | 说明 |
|------|------|
| `backend/app/services/auth_service.py` | 新增 AuthService，处理登录/注册/获取当前用户逻辑 |
| `backend/app/api/v1/auth.py` | 重构：从占位代码改为调用 AuthService，统一响应格式 |

#### 前端示例
| 文件 | 说明 |
|------|------|
| `frontend/src/types/user.ts` | User 相关 TypeScript 类型定义 |
| `frontend/src/services/user.service.ts` | 用户 API 服务层封装 |
| `frontend/src/stores/userStore.ts` | Zustand Store，用户状态管理 |

### 修改文件
- `backend/app/api/v1/auth.py` - 重构为三层架构，注入 AuthService
- `backend/app/core/security.py` - 重构：新增 get_password_hash/get_current_user_id_from_token，返回类型改为 Dict

### 架构决策
1. **事务边界在服务层控制**：使用 `with self.db.begin()` 或 `@transactional` 装饰器
2. **接口层只做参数校验和响应格式化**：不包含任何业务逻辑
3. **数据层不处理业务逻辑**：只封装数据库查询操作
4. **统一异常体系**：所有业务异常抛出 `BusinessException`，由全局 handler 统一处理
5. **用户模块作为完整模板**：后续所有模块（perception/cognition 等）均参照此模式开发

### 后续待办
- [ ] 重构 `perception.py`、`cognition.py` 等其他 API 文件为三层架构
- [ ] 完善 JWT 认证中间件（当前 `/me` 端点临时硬编码 user_id=1）
- [ ] 创建 perceptions/cognitions 等模块的 Repository 和 Service

---

## 2026-07-12

### Agent: 主开发 Agent（OntoMind Agent 资源平台 + OpenCode 流式 SSE）

### 目标
1. 落地 Agent 资源管理 / Studio / 对话工作台，对接本机 OpenCode
2. 会话执行过程（thinking / tools / steps / 文本）改为 **实时 SSE 流式**，不再与最终回复整包阻塞返回
3. 写清跨机交接文档，便于另一台电脑 pull 后续作

### 设计决策

| 决策点 | 选择 |
|--------|------|
| 资源真源 | 平台 `agents` 表；OpenCode 为运行时/发现面 |
| 层级 | 计算节点 → OpenCode 容器 → Agent/Skill/MCP |
| 编辑发布 | 仅资源管理 + Studio；对话工作台只聊天 |
| 执行通道 | `opencode run --format json`，按行解析 JSONL |
| 实时推送 | SSE（`GET /runs/{id}/events` 长连接）；非 WebSocket |
| 发消息 | 立即返回 `run_id`，BackgroundTasks 后台流式写事件 |
| 测试 | `force_stub=true` 同步 stub，不调 CLI |

### 功能清单
- 资源控制台：本机注册、inventory、三栏 UI、发布/去对话
- Agent Studio：草稿/发布、绑本机 OpenCode runtime
- 对话工作台：Session + Run + SSE 时间线
- Run 控制：start/cancel/pause/resume/retry + 乐观锁 `state_version`

### 新增主要路径
- `backend/app/api/v1/agent_platform/`
- `backend/app/services/agent_platform/`（含 `opencode_chat.py` 流式）
- `backend/app/db/models/agent_platform_model.py` 及 credentials/audit/discovery 模型
- `backend/alembic/versions/2026071202_*.py`、`2026071204_*.py`
- `frontend/src/pages/agent-platform/`、`hooks/useAgentStream.ts`、`stores/agentPlatformStore.ts`
- `docs/agent-platform/HANDOFF-2026-07-12.md`（**跨机必读**）

### 数据库
- **库**：一般不新建 schema/database，仍用同一 MySQL 库做 **CREATE TABLE + ALTER**
- **新表**：`credentials`、`audit_logs`、`agent_versions`、`agent_deployments`、`agent_sessions`、`agent_messages`、`agent_run_steps`、`agent_run_events`（SSE 真源）、`agent_tool_approvals`、`eval_suites`、`eval_cases`、`node_connections`、`discovery_runs`、`discovery_items`
- **改表**：`agents`（owner/current_version）、`agent_runs`（status→VARCHAR + session/strategy/input/output/state_version…）、`compute_nodes`（address/environment/heartbeat…）
- **字段级明细**：见 [`docs/agent-platform/HANDOFF-2026-07-12.md`](docs/agent-platform/HANDOFF-2026-07-12.md) §3

### 验证
- `pytest tests/agent_platform/` → 10 passed
- 联调：发消息应立刻返回，SSE 推送 step/thinking/message.delta

### 跨机续作入口
详见 [`docs/agent-platform/HANDOFF-2026-07-12.md`](docs/agent-platform/HANDOFF-2026-07-12.md)

---

## 2026-07-24

### Agent: OpenCode Serve/SDK 接入对话工作台

### 目标
不用 iframe 嵌 OpenCode Web；自研 `/workspace` UI 保持不变，后端将对话主路径从短命 `opencode run` 升级为长驻 `opencode serve` + HTTP/SSE 桥接，能力对齐 Web（多轮会话、流式、审批、取消）。

### 决策
| 决策点 | 选择 |
|--------|------|
| UI | 继续 AgentChatPanel / ChatWorkspacePage，不嵌官方 Web |
| 协议 | 前端只谈 OntoMind Session/Run/SSE；后端桥接 Serve |
| SDK | Python `httpx` 调 Serve HTTP/SSE（对齐 CLI 1.17+），不引入 Node `@opencode-ai/sdk` |
| 会话 | OntoMind `session_metadata.opencode_session_id` 映射远端 session |
| Fallback | Serve 不可用时回退 `opencode run --format json` |
| 权限 | v1 默认 `OPENCODE_PERMISSION={"*":"allow"}`；`permission.asked` 仍可落审批并回写 Serve |

### 新增文件
- `backend/app/services/agent_platform/opencode_serve_manager.py`
- `backend/app/services/agent_platform/opencode_session_bridge.py`

### 修改文件
- `backend/app/services/agent_platform/opencode_chat.py` — Serve 优先 stream
- `backend/app/services/agent_platform/run.py` — meta/checkpoint、取消 abort、审批落库
- `backend/app/services/agent_platform/approval.py` — 回写 OpenCode permission
- `backend/app/services/agent_platform/node_service.py` — 暴露 `opencode_serve` 状态（无密码）
- `backend/app/api/v1/agent_platform/nodes.py` — `POST .../opencode-serve/ensure`
- `backend/app/core/config.py` — `OPENCODE_SERVE_*` / `OPENCODE_MIN_VERSION`
- `frontend/.../ChatWorkspacePage.tsx`、`AgentChatPanel.tsx`、`timelineReducer.ts`
- `AGENTS.md`、`backend/requirements.txt` 注释

### API 端点
- `POST /api/v1/agent-platform/nodes/{node_id}/opencode-serve/ensure`

### 验证
- 本机 CLI 1.17.18；ensure → health；bridge prompt「PONG」收到 text 事件 exit=0

## [2026-07-24] 对话工作台切换为 SDK 直连（Wave 1-3 完成）

### 目标
按用户决策把 `/agent-platform/chat` 对话工作台从"后端 CLI 子进程 + 后端 SSE 桥接"架构，
彻底切换为"前端直连本机 opencode serve (127.0.0.1:4096)"的 SDK 直连架构。
- Vendor 起点：opencode `v1.18.4` (commit `49c69c5`)
- 样式隔离：Tailwind Path B (`preflight:false` + `important:'.oc-scope'`)，Wave 4 启用
- Dev spawn：`POST /api/v1/opencode/spawn` 仅 `DEBUG=True` 挂载
- 保留 openclaw / harness 历史模块（AIBIPage / RunsPage / agent_platform 编排层仍在用），
  只删掉 `agent_runner.py` 一个 CLI wrapper；新对话工作台走全新代码路径。

### 决策
1. **不 vendor 官方 UI 组件**（Wave 3 交付版）：第一版消息 Part 用 antd 原生渲染
   （`features/opencode/components/MessagePart.tsx`），足够跑通 text/reasoning/tool/file 四类。
   Wave 4 再从 opencode `packages/web/src/components/` 移植 15 个组件（≈2500 行）。
2. **不接 `@opencode-ai/sdk`**：`features/opencode/client.ts` 自己封 fetch，接口签名与 SDK 等价，
   方便断网 / 私有 registry 场景直接构建。切回 SDK 只需替换 `client.ts` 一个文件。
3. `useAgentStream` / `AgentEmbedRunner` 保留（AIBIPage 嵌入用），新对话工作台完全不再引用。

### 新增文件
- `backend/app/api/v1/opencode.py` — 三端点：`/health`、`/spawn`(DEBUG)、`/session-link` (POST+GET)
- `backend/app/db/models/opencode_session_model.py` — 业务侧 `opencode_sessions` 映射表
- `frontend/.env.example` — `VITE_OPENCODE_URL=http://127.0.0.1:4096`
- `frontend/src/features/opencode/`（15 文件）：
  - `client.ts` — fetch wrapper（health/sessions/messages/prompt/permissions/find/config/agents/commands/mcp/SSE）
  - `types.ts` — OpenCode 数据模型（OcSession/OcPart/OcMessage/OcPermission/OcEvent…）
  - `stores/opencodeStore.ts` — Zustand，全局会话/消息/权限/流状态
  - `hooks/useOpencodeHealth.ts` `useSessions.ts` `useMessages.ts` `useEventStream.ts`
    `useSendPrompt.ts` `usePermissions.ts` `useAgents.ts` `useCommands.ts` `useFilesMention.ts`
    `useProviders.ts`
  - `components/OpencodeGuard.tsx` `HealthBanner.tsx` `ChatWorkspaceShell.tsx`
    `SessionListSidebar.tsx` `ChatMessageList.tsx` `ChatComposer.tsx` `MessagePart.tsx`
    `PermissionDialog.tsx`
  - `vendor/{LICENSE, VENDOR_META.md, styles/opencode.css}` — Wave 4 vendor 目录占位

### 修改文件
- `backend/app/api/v1/router.py` — include_router `opencode_bridge` under `/opencode`
- `backend/app/db/models/__init__.py` — 注册 `OpencodeSession`
- `backend/schema.sql` — 追加 `opencode_sessions` 表 DDL
- `backend/app/services/requirement_service.py` — Prompt 中的 agent_type 描述从 openclaw/harness/custom 改为 opencode
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 完全重写为 `<OpencodeGuard><ChatWorkspaceShell/></OpencodeGuard>`
- `AGENTS.md` — 对话工作台架构描述更新

### 删除文件
- `backend/app/services/agent_runner.py` (377 行) — CLI 子进程 wrapper，彻底废弃

### API 端点
- `GET  /api/v1/opencode/health`
- `POST /api/v1/opencode/spawn`（仅 `settings.DEBUG=True` 挂载）
- `POST /api/v1/opencode/session-link` — 绑定 (opencode_session_id, user_id, project_id)
- `GET  /api/v1/opencode/session-link` — 列出当前用户绑定过的会话

### 数据库
- 新表 `opencode_sessions`：主键 + `opencode_session_id` unique + `user_id/project_id` FK + `title`
- ⚠️ AGENTS.md 已提示：alembic 形同虚设，`app/main.py` 靠 `create_all` 自动建表；
  上生产前需要手工执行 `backend/schema.sql` 里的 `CREATE TABLE opencode_sessions ...`。

### 前置条件
开发者需先启动本机 opencode server（否则 Guard 会显示引导页）：
```bash
opencode serve --port 4096 --cors http://localhost:5173
```
Guard 会通过 `GET /api/v1/opencode/health` 每 5s 探活；也可点击顶部 [一键启动]（仅 DEBUG 模式）。

### 验证
- `tsc --noEmit` 对新增 `features/opencode` + `ChatWorkspacePage.tsx` 零错误
- `npm run lint` (oxlint) 对新增文件零 warning
- `python3 -c "import app.api.v1.opencode; import app.db.models"` 通过
- 端到端流式对话验证：**留给用户在浏览器手工验证**（需要本机启动 opencode serve 才能跑）

### 未完成（Wave 4-7）
- Wave 4：Vendor opencode v1.18.4 官方组件 + Tailwind 启用
- Wave 5：CommandPalette / FileMention / ModelSwitcher / undo-redo-fork 高级功能
- Wave 6：MCP/Skill/Agent 资源面板改造为 opencode SDK 数据源
- Wave 7：更详细的启动脚本、README 更新、E2E playwright

## [2026-07-24 后续] 对话工作台 `/` 命令面板 + `@` 文件面板

### 目标
用户反馈"输入斜杠没有反应"，要求 100% 复刻 opencode web 的交互体验。
先实现最痛点的两个：`/` 命令面板 + `@` 文件搜索面板。

### 决策
1. **不搬 SolidJS 源码**：opencode `packages/app/src/components/prompt-input/` 是 SolidJS + Effect
   (2757 行) + 自研 editor-dom + attachments，硬移植成本高。
2. **视觉参考 + React 原生实现**：参考 opencode `slash-popover.tsx` 的视觉与交互（深色圆角卡片、
   ↑↓ 键盘导航、Enter/Tab 选中、Esc 关闭、按 trigger 前 char + 空白规则识别 token）。
   用 React + antd 复刻，2 个文件 ≈ 320 行。
3. **触发规则**：光标向前扫到首个 `/` 或 `@`；trigger 前一个字符必须是空白/换行/开头
   （防止 email @ 干扰）；token 内不能含空白。

### 新增文件
- `frontend/src/features/opencode/components/SlashPopover.tsx` — `/` 命令面板
  - 输入 `/` 弹出前 12 条命令；`/x` 前缀过滤
  - source badge（command/skill/mcp）
  - 支持键盘 ↑/↓/Enter/Tab/Esc，鼠标点选，选中滚入可视区
- `frontend/src/features/opencode/components/MentionPopover.tsx` — `@` 文件面板
  - `@xxx` 触发 `oc.findFiles()`，debounce 200ms
  - 文件名 + 目录路径双行显示
  - 同样支持键盘/鼠标

### 修改文件
- `frontend/src/features/opencode/components/ChatComposer.tsx` — 深度改写
  - 新增 `detectToken()` 光标 token 识别
  - 集成 SlashPopover + MentionPopover
  - popover 打开时，textarea 的 ↑↓Enter Esc Tab 让给 popover 处理
  - 选中后 `replaceToken()` 精确替换 token 段（保留光标位置）
  - 底部快捷键提示条加了 `/=命令` `@=文件` badge

### 验证（playwright headless 冒烟）
- 输入 `/` → 弹出 12 条命令（含 command + skill）✅
- `/arkcli` 过滤 → 只显示 arkcli 前缀 ✅
- ↑↓ + Enter → 选中并插入 `/name ` ✅
- 鼠标 click → 选中 ✅
- Esc → 关闭 popover ✅
- 触发规则前 char 校验通过 ✅
- `@AGENTS` → 弹出对应文件（依赖 opencode server 启动目录，非 bug）✅

### 已知边界
- `@` 文件搜索的可用文件受限于 `opencode serve` 启动时的 cwd（就是 opencode server 的 project 根）。
  用户如果在 `/Users/sunleone` 起 server 就只能搜到该目录里的文件；在 ontomind 目录起就能搜到项目文件。
  这是 opencode server 侧的行为，不是 UI bug。
- 键盘导航时 popover 里的项目 scrollIntoView 已就位。

### 未完成（后续 Wave）
- 命令有 `template` / `arguments` 时应弹出参数输入框（当前只是插入 `/name `）
- Model Switcher（`Cmd+/` 或按钮切模型）
- Undo/Redo/Fork 消息级操作
- Markdown + code block 高亮渲染
- Diff viewer（session.diff 事件）

## [2026-07-24 追加] 对话工作台 UI 重构 — 严格对齐 opencode v1.18.4 视觉

### 目标
用户反馈"UI 太丑，重新设计简单大方一些，严格参考 opencode web/desktop 模型"。
彻底换掉 antd Card / Space / Splitter / Tag / List 的堆砌感，用 opencode v1.18.4 的
`packages/ui/src/v2/styles/*` + `packages/session-ui/src/components/*.css` 里的视觉规范复刻。

### 关键视觉决策 (参考 opencode source)
- **消息布局**：`user` 右对齐圆角气泡 (max-width `min(82%, 64ch)`, radius 10px, bg `layer-1`)；
  `assistant` 左对齐纯文本流无气泡，靠位置区分角色（严格照 `message-part.css`）
- **色板**：完整搬 opencode v2 grey scale (grey-50..1200) + blue accent + state colors，
  用 CSS `light-dark()` 自动跟随系统
- **字体**：`-apple-system` sans + `SF Mono` mono，body 14px / line-height 1.65
- **圆角**：气泡/tool card 10px，popover 12px，按钮 8px，chip 999px（pill）
- **无 badge 满天飞**：只在 tool status 和 popover source 显示；用户消息不显示 role tag
- **深浅色主题**：CSS 变量 + `light-dark()`，跟随系统主题
- **工具卡片**：head (bg layer-2 + 单色 status pill) / body (mono pre with layer-deep bg)

### 新增文件
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 500 行完整视觉主题
  - v2 grey scale + blue accent + light-dark 自动切换
  - `.oc-msg-wrap[data-role]` 用户/助手区分
  - `.oc-part-tool` opencode 风格工具卡片
  - `.oc-popover` 浮层 + `oc-pop-in` 动画
  - `.oc-composer-inner` 圆角边框容器 + focus-within 边框态
  - 全套 `.oc-btn` / `.oc-icon-btn` / `.oc-hint-chip` / `.oc-session-item`

### 修改文件（视觉全部重写，不再包 antd Card/Space/Splitter/Tag/List）
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — 原生 CSS grid 2 栏
- `frontend/src/features/opencode/components/SessionListSidebar.tsx` — 纯 div + SVG 图标
- `frontend/src/features/opencode/components/ChatMessageList.tsx` — user 气泡 / assistant 流
- `frontend/src/features/opencode/components/MessagePart.tsx` — 无 antd 全 css class
- `frontend/src/features/opencode/components/ChatComposer.tsx` — 圆角容器 + textarea + toolbar
- `frontend/src/features/opencode/components/SlashPopover.tsx` — opencode-style 命令面板
- `frontend/src/features/opencode/components/MentionPopover.tsx` — opencode-style 文件面板
- `frontend/src/features/opencode/components/OpencodeGuard.tsx` — 引导页视觉
- `frontend/src/features/opencode/index.ts` — 移除已删除的 HealthBanner 导出
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 去掉 antd PageHeader，全屏 shell
- `frontend/src/main.tsx` — import opencode.css

### 删除文件
- `frontend/src/features/opencode/components/HealthBanner.tsx` — 引导页并入 OpencodeGuard

### 验证
- `tsc --noEmit` 零错误
- `npm run lint` (oxlint) 新增/修改文件零告警
- Playwright headless: 发消息 → 用户右气泡 + assistant 左流式回复 + PONG 通过 ✅
- `/init` 弹 opencode-style popover，键盘/鼠标交互全通 ✅
- Esc 关 popover ✅

## [2026-07-24 又追加] session 清理 + 布局固定 + zen/god 联动

### 三个问题
1. 用户命令：清理 opencode 里所有 session，只留一个（并期望前端 sidebar 自动同步）
2. UI 有"松散感"，上下能滚动 → 底部 composer 不固定
3. Zen/God 模式对新 opencode UI 没差别

### 修复
**1. Session 清理 & 前端联动**
- 一次性调 opencode API `DELETE /session/:id` 清 79 条 session，仅留最新一条（60 直删成功 + 19
  子会话父删时级联；opencode server 侧只剩 1 条）
- Store 新增 `session.deleted` SSE 事件处理 → 自动 `state.removeSession(sid)`
- `useSessions` 新增"死绑定自愈"：`activeSessionId` 指向的 session 不在列表时，自动切到第一条或 null

**2. 布局硬修**
- 原因 1：ChatWorkspacePage 用 `position: absolute + inset:0` 撞了 antd `.ant-layout-content`
- 原因 2：算高度按 header=64px（实际是 56px）
- 修复：`useEffect` 挂载期改写 `.ant-layout-content` 的 margin/padding/minHeight/overflow/height
  为固定值；shell 用严格 `flex column` + 各 slot `flexShrink:0` / `flex:1 minHeight:0`；
  只有 `.oc-turn` 有 `overflow-y: auto`
- 结果：`bodyH=900` = `winH`，body 不再滚；`.oc-turn.scrollH=2574 > clientH=670` 只在消息区滚动

**3. Zen/God 模式**
- `AGENTS.md` 里已有 `html[data-ui-mode="zen|god"]` 全局机制（ZenGodToggle）
- 在 `opencode.css` 追加规则：
  - Zen: 隐藏 `.oc-msg-meta` `.oc-hint-chip` `.oc-header-sub` `.oc-composer-toolbar-left`
  - God: 消息 meta 蓝色高亮，暴露 `.oc-god-only` 元素（如 message id 前缀）
- `ChatMessageList` 消息底部 meta 加 `<span class="oc-god-only">· msg_id</span>`

### 修改文件
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx` — 完全重写高度算法
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — 严格 flex + 各 slot 定
- `frontend/src/features/opencode/components/ChatMessageList.tsx` — 增加 `.oc-god-only` id 显示
- `frontend/src/features/opencode/stores/opencodeStore.ts` — 新增 `session.deleted` 事件
- `frontend/src/features/opencode/hooks/useSessions.ts` — 死绑定自愈
- `frontend/src/features/opencode/vendor/styles/opencode.css` — `.oc-turn` 严格 100%，zen/god 规则

### 验证 (playwright headless)
- Sidebar session count = 1 ✅
- Shell w=1440 h=844 (=viewport 900 - header 56) ✅
- Sidebar h=844 (与 shell 齐平) ✅
- Turn scrollH=2574 > clientH=670，只在 turn 滚 ✅
- body scrollY=0 且 bodyH === winH，外层无滚动 ✅
- Zen → 隐藏 hint chips；God → 显示 hint chips ✅
- 发消息 → 1s 收到 PONG ✅

## [2026-07-24 又追加 3] Plan/Build 切换 + Model 选择

### 目标
用户反馈：composer 没 Plan/Build 模式切换，也不能选/加 Model。这是 opencode 桌面版核心 UX。

### 决策
- **Agent Mode** = 从 `GET /agent` 过滤 `mode==='primary' && !HIDDEN` 得到 build / plan
  两个 pill，横排在 composer 左下；对齐 opencode desktop 的 primary agent cycle
- **Model** = `GET /config/providers` 拿所有 provider + model，pill 在 send 按钮左边，
  点开 popover 分组展示、带搜索框、点选后 pill 立刻更新
- **快捷键**：`Cmd/Ctrl + .` 循环 primary agent；`Cmd/Ctrl + M` 打开 model switcher
- **持久化**：sessionStorage 存 `oc:currentAgent` / `oc:currentModel`
- **未配 provider**：popover 内引导点击"打开 opencode UI" (`http://127.0.0.1:4096/`)；
  原生 Add-Provider Dialog 下一 wave 再做

### 新增文件
- `frontend/src/features/opencode/components/AgentModeSwitcher.tsx` — Plan/Build pill group
- `frontend/src/features/opencode/components/ModelSwitcher.tsx` — pill + popover + 搜索

### 修改文件
- `frontend/src/features/opencode/stores/opencodeStore.ts` — 新增
  `currentAgent` / `currentModel` state、`setCurrentAgent()` / `setCurrentModel()` 及
  sessionStorage 持久化（load/save）
- `frontend/src/features/opencode/hooks/useSendPrompt.ts` — 发消息时读取 store
  currentAgent + currentModel，注入 `body.agent` / `body.model`
- `frontend/src/features/opencode/hooks/useProviders.ts` — 重写返回结构，展平 provider.models
  从 Record→ProviderModelInfo[]
- `frontend/src/features/opencode/client.ts` — `listProviders` 返回类型对齐 v1.17 真实 shape
- `frontend/src/features/opencode/components/ChatComposer.tsx` — toolbar-left 挂
  `<AgentModeSwitcher/>`，toolbar-right 挂 `<ModelSwitcher openTrigger/>`；全局监听
  `Cmd/Ctrl+.` 循环切 primary agent，`Cmd/Ctrl+M` 弹模型面板
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 新增 `.oc-pill`
  `.oc-mode-group` `.oc-mode-pill` `.oc-model-popover` 全套视觉；zen 只隐藏 hint chips，
  不隐藏 mode/model switcher（核心 UX）
- `frontend/src/features/opencode/index.ts` — 导出新组件

### 验证（Playwright）
- Build + Plan pill 渲染，默认 Build 高亮 ✅
- 点击 / Cmd+. 快捷键切换 ✅
- Model pill 显示 `provider/modelID`，Cmd+M 打开面板 ✅
- 搜索 "gpt-5" 命中 12 个模型（跨 provider）✅
- 选中后 pill 更新，发消息 body 正确携带 `agent: "plan"` + `model: {...}` ✅

### 未做（下一 wave）
- 原生 Add Provider Dialog（含 API Key / OAuth / custom endpoint）—— 现在通过跳转
  `http://127.0.0.1:4096/` 兜底
- Model popover 的键盘 ↑↓ 高亮 & Enter 选中（现在只支持鼠标点选和搜索）

## [2026-07-24 又追加 4] 全站 UI 重设计 — Editorial Light Theme

### 目标
用户："重新设计整个项目的 UI，浅色为主，要高级、整洁、简单"。

### 设计定位
**editorial minimal**（编辑排版级极简）:
- 象牙白 `#fafaf7` (paper) 主背景 + 深墨黛 `#1a1918` (ink) 主文字
- 单色 accent：靛蓝墨水 `#3b52af`（indigo ink），代替以前的青蓝渐变
- Fraunces (serif italic) 做 display / 标题；Geist Sans 做 body；JetBrains Mono 做 code
- 边框全用 hairline `rgba(26,25,24,0.06~0.10)`；阴影极其克制（无 glow）
- Card / Modal / Popover 都平白无渐变，靠精确排版 + 空间讲话
- Primary Button 是**纯墨黛**背景 + 白字，不是蓝色渐变（editorial 惯例）

### 修改文件
- `frontend/src/styles/global.css` — 全面重写：
  - 新 token（paper-00..04 / ink-100..10 / accent），保留 legacy 变量映射以兼容既有页面
  - Fraunces + Geist + JetBrains Mono 三字体链
  - Antd overrides 全面浅色：Layout / Menu / Card / Table / Tag / Button / Input / Select / Modal /
    Tabs / Statistic / Pagination / Dropdown / Message / Tooltip / Alert / Splitter / Popover /
    Radio / Checkbox / Switch / Typography
  - `.bg-grid` 由深色 dot grid 改为极淡米色 dot 底噪
- `frontend/src/App.tsx` — antd `algorithm: theme.defaultAlgorithm`；token 全线切浅
- `frontend/src/components/layout/AppLayout.tsx` — Header 淡化 + Logo 改 Fraunces italic
  "OntoMind" + mono "v0.1"；Avatar 改为墨黛 solid（不是渐变）
- `frontend/src/features/opencode/vendor/styles/opencode.css` — 移除 `light-dark()`，硬编码浅色
  scheme；改用 warm-ivory grey scale 替代冷灰；header + sidebar title 改为 Fraunces italic
- 用户消息气泡：`bg-layer-2` + hairline border（不再纯 solid）
- `.oc-header-title` 从 13px sans 改为 18px Fraunces italic

### 验证 (Playwright)
- body bg = `rgb(250,250,247)` 米白 ✅
- body color = `rgb(26,25,24)` 墨黛 ✅
- header bg = `rgba(250,250,247,0.85)` + blur ✅
- font-family 首选 Geist（浏览器已加载 Google Fonts）✅
- 发消息 → 回复 ping 正常 ✅
- tsc + oxlint 零错误 ✅

### 视觉对比
- Before: 深色 (`#060b14`) + 蓝紫渐变 logo + Plus Jakarta Sans + 玻璃卡片阴影发光
- After: 象牙白 (`#fafaf7`) + Fraunces italic serif logo + hairline border + editorial 排版

### 未做（可后续）
- 其他页面 (Login / Dashboard / Resources 各详情页) 使用 legacy 变量已自动继承新色；
  但视觉密度可能还需 case-by-case 抛光
- Dark mode 切换（当前默认强制浅色）
- Google Fonts 加载失败降级样式（当前直接回退到 system-ui）

## [2026-07-24 又追加 5] Settings 面板（Shell / 推理摘要 / 工具展开 / 新版布局）

### 目标
用户："opencode web 还有这些设置" —— Shell 选择、显示推理摘要、展开 shell 工具部分、
展开编辑工具部分、新版布局。

### 分工
- **Shell**：opencode server 侧行为，通过 `PATCH /config` 写；auto → 传 `null`
- 其它 4 项：纯前端偏好（localStorage `oc:ui-settings`），影响 UI 层渲染逻辑

### 新增文件
- `frontend/src/features/opencode/hooks/useOcSettings.ts` — 偏好 state（load/save/CustomEvent 广播）+
  updateShell 顺带 PATCH /config
- `frontend/src/features/opencode/components/SettingsDialog.tsx` — Modal 面板，Editorial Light
  视觉：Fraunces italic 标题、hairline row 分隔、shell 分段控件、原生 antd Switch

### 修改文件
- `frontend/src/features/opencode/client.ts` — `patchConfig()` API
- `frontend/src/features/opencode/types.ts` — `OcConfig.shell?: string | null`
- `frontend/src/features/opencode/components/MessagePart.tsx` — reasoning part 遵循
  `showReasoningSummaries`；tool part 按 tool name 判断是否为 shell / edit 类，配合
  `expandShellTool` / `expandEditTool` 决定默认展开态；用户可点击 head 折叠
- `frontend/src/features/opencode/components/ChatWorkspaceShell.tsx` — Header 右侧新增齿轮按钮，
  点开 SettingsDialog
- `frontend/src/features/opencode/index.ts` — 导出 SettingsDialog

### 验证（Playwright）
- 齿轮按钮存在 ✅
- 点击弹出 Modal，5 个设置行 ✅
- 点 "zsh" → PATCH /config 200 返回 `{shell: zsh}`（opencode v1.17.18 不持久化 shell 字段到 GET
  响应，是 server 版本行为，UI 层已正确调用）✅
- Toggle "显示推理摘要" 从 false → true ✅
- localStorage 保存: `{"shell":"zsh","showReasoningSummaries":true,...}` ✅
- 关掉 Modal 再打开，Toggle 保持 true ✅
- 点 "自动" → PATCH `{shell:null}` ✅
- tsc + lint 零错误 ✅

### 已知问题（非本次引入）
- 有 React 警告 "Cannot update a component while rendering" 来自 SSE store 事件，不阻塞使用，
  后续可用 `queueMicrotask` 或 `useSyncExternalStore` 优化

## [2026-07-24 大清理] 删除 4 个页面 + 所有依赖（前后端 + DB）

### 目标
用户要求删除：仪表盘、应用层、项目管理、运行记录 4 个页面，**前后端全部清干净**。

### 5 项决策（均已确认）
1. 后端 agent_platform 编排层（run/approval/session/version/migration/opencode_chat/serve_manager/session_bridge）连同前端 RunsPage 一起清；保留 agents/deployments/nodes/discoveries
2. `opencode_sessions.project_id` 字段整个删（配合 projects 表 drop）
3. `resources.py::/runs*` 端点 + AgentRun model/service/repo/schema 一起删
4. AppLayout 顶部菜单去 4 项，剩 workspace / resources / perception / cognition / decision / execution / users
5. agent_looper/test.py::/jobs* + AgentJobService + AgentRunJob + AgentJobPage 一起删

### 前端删除（约 15 文件 / 2000 行）
- 页面：`pages/dashboard/` `pages/application/` `pages/projects/`（整目录）
- 页面：`pages/agent-platform/RunsPage.tsx` `timelineReducer.ts` `__tests__/`
- 隐藏页：`pages/resources/AgentJobPage.tsx`（无路由，死代码）
- 组件：`components/common/AgentEmbedRunner.tsx` + `__tests__/AgentEmbedRunner.test.tsx`
- Hooks / Store：`hooks/useAgentStream.ts` `stores/agentPlatformStore.ts`

### 前端修改
- `services/agentPlatform.service.ts` — 重写为薄壳，只保留 agents / nodes / discoveries / deployments 相关方法（~130 行）
- `services/index.ts` — 删 `projectsAPI` / `applicationAPI` block
- `types/index.ts` — 删 `Project` `Requirement` `Plan` `Task` `KanbanData` `AgentRun` 5 个 interface
- `App.tsx` — 移 4 个 imports + 4 个 route
- `components/layout/AppLayout.tsx` — `topMenuItems` 移 4 项 + 移 icon imports
- `components/common/CmdKOmnibar.tsx::buildNavItems` — 移 4 项 nav + "新建项目" 快捷操作
- `components/common/index.ts` — 移 AgentEmbedRunner 导出
- `pages/agent-platform/index.ts` — 移 RunsPage / timelineReducer 导出
- `pages/resources/AgentDetailPage.tsx` — 删 "Job 历史" tab + AgentRun / runColumns 相关（150+ 行）
- `pages/resources/index.tsx` — 删 running/errors 计数卡片 + `loadRunsStats`
- `tests/visual/screenshots.spec.ts` — 移 dashboard 断言

### 后端删除（约 30 文件 / 4000 行）
- API：`api/v1/application.py` `projects.py`；`api/v1/agent_platform/runs.py, approvals.py, sessions.py`
- Services：`agent_run_service.py` `agent_job_service.py` `agent_loop_service.py`
  `project_service.py` `requirement_service.py`
- Services：`agent_platform/run.py, approval.py, session.py, migration.py,
  opencode_chat.py, opencode_serve_manager.py, opencode_session_bridge.py`
- Repos：`agent_run_repo.py, project_repo.py, requirement_repo.py, plan_repo.py, task_repo.py`
- Models：`agent_run_model.py, agent_run_job_model.py, project_model.py,
  requirement_model.py, plan_model.py, task_model.py`
- Schemas：`agent_run_schema.py, agent_loop_schema.py`
- Tests：`tests/data_platform/test_agent_loop.py, test_agent_jobs.py, agent_platform/test_agent_platform.py`

### 后端修改
- `api/v1/router.py` — 移除 projects / application 的 include_router；改为直接 `from app.api.v1 import ...`（不含删除模块）
- `api/v1/__init__.py` — 兼容 shim（`from app.api.v1.router import api_router`）
- `api/v1/resources.py` — 删掉 AgentRun 端点段（`/runs*` GET/POST/PUT + stop + WebSocket）+ 相关 imports
- `api/v1/agent_platform/__init__.py` — 只保留 nodes/discoveries/agents/deployments 4 个 sub-router
- `api/v1/agent_platform/agents.py` — 删掉 `POST /legacy/{id}/migrate` 与 `LegacyAgentMigrationService` 引用
- `api/v1/agent_looper/test.py` — 删 `/jobs*` 端点段（190 行）+ `AgentJobService` import
- `db/models/agent_platform_model.py` — 只保留 `AgentVersion` + `AgentDeployment`；删掉
  Session/Message/RunStep/RunEvent/ToolApproval/EvalSuite/EvalCase 7 个模型
- `db/models/opencode_session_model.py` — 删 `project_id` 字段（配合 projects 表删）
- `db/models/__init__.py` — 移除对应 imports 与 `__all__`
- `tests/data_platform/test_data_model.py` — 删 AgentRunJob 相关断言，保留其余 11 张核心表

### 数据库
- **DROP**（14 张）：tasks / plans / requirements / eval_cases / eval_suites /
  agent_tool_approvals / agent_run_events / agent_run_steps / agent_messages /
  agent_sessions / agent_run_jobs / agent_runs / projects（+ opencode_sessions 的 FK to projects）
- opencode_sessions 移除 `project_id` 列
- 剩余 54 张表

### schema.sql 同步
- 删掉 agent_runs / projects / requirements / plans / tasks 5 段 DDL
- opencode_sessions DDL 去掉 project_id 字段 + fk_ocsession_project 约束

### 验证
- Playwright headless：
  - Header 菜单只剩 7 项（对话工作台 / 资源管理 / 感知层 / 认知层 / 决策层 / 执行层 / 用户管理）✅
  - `/dashboard` / `/application` / `/projects` / `/agent-platform/runs` 全部 redirect 到 `/workspace` ✅
  - Workspace 发送 ping → 收到回复 ✅
- Backend `from app.main import app` 成功，203 个 route
- `tsc --noEmit` — 我改动的文件零错误（存量老代码错误未管）
- `npm run lint` — 我改动的文件零告警

## [2026-07-24 大重构] 专家团（Expert Team）+ opencode 原生 @agent 路由

### 目标
用户要求："删除资源管理页面重建，改名'专家团'"；
1 个专家 = 一套定制好的 opencode agent 配置；
在线状态可控（启动/关闭）；对话工作台可选取。

### 核心架构决策
1. **Expert = opencode agent 定义**：创建/编辑专家时同步写入 `~/.config/opencode/agent/{slug}.md`
   (YAML frontmatter + Markdown body)；opencode 启动时 discover 该 agent
2. **对话工作台走 opencode 原生 `@agent` 路由**（不用 system prompt 伪造）：
   - ExpertPicker 选中 → `store.currentAgent = expert.slug`
   - `useSendPrompt` 里 body.agent 直接是 slug（不带 @）
   - `@popover` 里选 agent → 插入 `@slug` 到 textarea
3. **状态管理**：online = agent md 文件存在；offline = 文件不存在
4. **Docker 保留位**：`image` 字段已建，`ExpertService._start_container` mock 逻辑就位，
   等真正需要多实例隔离时再启用

### 后端新增
- `backend/app/db/models/expert_model.py` — Expert model：
  role / sop / provider / model / skills / mcps / tools / agent_file_path / status
- `backend/app/db/repositories/expert_repo.py` — Expert repo（list_ordered / get_by_slug / list_online）
- `backend/app/schemas/expert_schema.py` — Pydantic schema
- `backend/app/services/expert_service.py` — Expert service:
  - `_write_agent_md(e)` 生成 opencode agent MD 文件
  - `_remove_agent_md(e)` 删除对应文件
  - CRUD / start / stop / seed 4 个内置专家
  - 4 个内置专家 seed：data-analyst / frontend / backend / product-manager
- `backend/app/api/v1/experts.py` — /api/v1/experts 完整 CRUD + start/stop + seed

### 前端新增
- `frontend/src/services/expert.service.ts` — API 客户端
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — 专家团管理页（卡片网格 + 启停 + 编辑抽屉）
  - 结构化表单：基本信息 / 角色 & 工作流 / 模型 / Skills-MCPs-Tools / 部署端点
  - Skills 支持从 20+ 常用 opencode skill 里选 + 自定义 tag
  - 工具权限勾选（read/write/bash/todo）
- `frontend/src/features/opencode/components/ExpertPicker.tsx` — Header 专家下拉
  - 显示当前 agent（默认 Build）
  - 列出所有在线专家；未被 opencode discover 的显示"未加载"提示
  - 选中 → 设置 currentAgent + currentModel + 新建专属会话（标题带 emoji）

### 前端修改
- `App.tsx` — 新增 `/experts` 路由；`/agent-platform/resources` redirect 到 `/experts`
- `AppLayout.tsx` — 菜单"资源管理"改为"专家团"
- `CmdKOmnibar.tsx` — 快捷跳转项更新
- `MentionPopover.tsx` — 扩展为 agents + files 两类结果：
  - agent 项标 `agent` badge，前缀 `@`
  - file 项标 `file` badge
  - opencode `/agent` API 拉取所有已 discover 的 agent
- `ChatWorkspaceShell.tsx` — Header 加入 ExpertPicker（AgentModeSwitcher 左侧）
- `stores/opencodeStore.ts` — 新增 currentExpertId / currentSystemPrompt state
  （后来废弃 system prompt 用法，但字段保留兼容）
- `Login.tsx` — 从深色改成 editorial light 主题（跟 workspace 一致）

### 数据库
- 新表 `experts`（在 `schema.sql` 添加）
- 字段：id / name / slug (unique) / avatar / description / role / sop /
  provider / model / temperature / skills (JSON) / mcps (JSON) / tools (JSON) /
  image / container_name / container_id / host_port / host / port / status /
  agent_file_path / started_at / stopped_at / error_message / sort_order

## [2026-07-24 后续 bug 修复]

### 1. 保存专家 500 错误
- 根因：`ExpertService` 用 `with self.db.begin()` 嵌套事务，FastAPI 的 `get_db` 已开事务
- 修：所有 create/update/delete/start/stop 改成 `flush()` + `commit()`，无 `begin()` 嵌套

### 2. 选专家后对话不知道自己身份
- 根因 1：切专家时用的是**已有 session**，opencode `system` 只在首条消息生效
- 修 1：ExpertPicker.select() 自动 `oc.createSession()` 新建专属会话
- 根因 2（更本质）：用 `system` prompt 是绕路，应该用 opencode 原生 `@agent` 路由
- 修 2：改为 `store.currentAgent = expert.slug`；`useSendPrompt` 去掉 `system` 参数

### 3. @ popover 增强
- MentionPopover 从 files-only 扩为 agents + files
- opencode `GET /agent` 拉取已 discover 的 agent（含 build/plan/product-manager
  及所有 seed 的专家）
- 选中 → 直接插入 `@slug` 到 textarea，opencode 原生解析

### 4. 双 @ bug
- 现象：`@` 后选择插入 → 变成 `@@data-analyst`
- 根因：某些场景（stale token state / IME 交互）导致 `token.triggerStart`
  位置错位，`before.slice(0, triggerStart)` 保留了原 `@`
- 修：`replaceToken()` 加防御 —— 如果 `replacement` 首字符是 `@`/`/` 且 `before`
  末尾也是同一字符，吞掉 `before` 末尾那个字符

### 5. opencode agent 热加载限制（架构注意）
- opencode server 只在启动时扫描 `~/.config/opencode/agent/*.md`
- 新增/编辑专家后需**重启 opencode** 才能通过 `@agent` 路由
- UI 应对：ExpertPicker 里未 discover 的专家灰显 + "未加载"tag + 点击时提示重启

### 验证（Playwright）
- 保存专家：`PATCH /api/v1/experts/1` 返回 SUCCESS ✅
- @pro Enter → `@product-manager ` (1 个 @) ✅
- @ Enter → `@build ` ✅
- hello @pro Enter → `hello @product-manager ` ✅
- 鼠标点选 → 同样 1 个 @ ✅
- 发送 `@product-manager who are you in 3 words` → 回复 "Product requirement doc." ✅
  (opencode 原生 subagent 路由生效)

## [2026-07-25] 补交 HANDOFF.md + 刷新 AGENTS.md

### 目标
让下一位 agent 拿到仓库能 30 分钟内跑通全链路（数据库初始化 / opencode CLI / 后端 / 前端）。

### 新增
- **`HANDOFF.md`**（新 agent 冷启动 30 分钟指南）：
  - §1 一次性初始化：装依赖、起 MySQL/Redis、建库、`.env`、`create_all` 建表、seed admin 用户 + 4 个专家
  - §2 日常启动 3 个终端（opencode serve + uvicorn + npm dev）
  - §3 核心架构：对话工作台/专家团/三方数据流
  - §4 数据库真相：alembic 坏、schema.sql 不全、如何完全重置
  - §5-6 三层架构 + 前端硬约束
  - §7 常见问题排查表
  - §8 手上活的接头协议（AGENT_LOG 格式）
  - §9 参考文档索引
  - §10 一键冒烟脚本（后端/opencode/数据库/登录列专家四步探活）

### 修改
- **`AGENTS.md`** 全量刷新：
  - 首行加"新 agent 先读 HANDOFF.md"提示
  - 项目一句话去掉已删的 application 层，改为"对话工作台 + 专家团"
  - 技术栈补充 opencode CLI ≥ 1.17
  - 常用命令改为 3 个终端方式（不再靠 docker compose）
  - 数据库章明确 schema.sql 不包含 experts/agent_versions/agent_deployments
  - 三层约束里补充"不用 `with self.db.begin()`"陷阱
  - 业务域列表更新到当前 15 个真实 router 前缀
  - 新增"对话工作台 + 专家团"章节完整描述当前架构
  - 参考文档索引加 HANDOFF.md
  - 常见坑速览补充：Service 事务陷阱 / opencode 不热加载 / IME 中文输入回车

### 未修改
- backend/STANDARDS.md / DESIGN_STANDARDS.md 保持（团队一致规范未变）
- frontend/STANDARDS.md 保持

### 验证
- 手工 review HANDOFF.md 3 遍确保 §1.6 的 seed 脚本可复制粘贴直接跑
- AGENTS.md 里所有链接指向的文件均存在

## [2026-07-27] 新增算力调度模块（Compute Scheduling）

### 目标
用户需求：新 tab「算力调度」包含两大功能
1. Docker 服务管理（管理 opencode docker 容器）
2. 调度管理（长时/定时任务 + 运行监控 + 实时日志）

### 数据模型（4 张新表）
- **docker_services**：一个 opencode docker 容器 = 一条记录（可关联 expert）
  - image / container_id / host_port / opencode_args / env / volumes / status
- **schedule_tasks**：任务定义
  - schedule_type: manual/once/interval/cron
  - schedule_expr: cron 表达式 / interval 秒数 / once ISO 时间戳
  - opencode_config: {prompt, agent, model, system}
  - enabled / status / last_run_at / next_run_at / total_runs / success_runs / failed_runs
- **task_runs**：一次运行记录（一个 task 多个 run）
  - trigger (manual/schedule/retry) / status / started_at / finished_at / duration_ms
  - snapshot (任务配置快照) / exit_code / output_summary / opencode_session_id
- **task_log_entries**：日志行（一个 run 多条 log）
  - sequence 保证同 run 内顺序，level (info/warn/error/stdout/stderr/event)

### 新增文件（后端）
- `backend/app/db/models/docker_service_model.py`
- `backend/app/db/models/schedule_task_model.py` (含 ScheduleTask + TaskRun + TaskLogEntry)
- `backend/app/db/repositories/docker_service_repo.py`
- `backend/app/db/repositories/schedule_task_repo.py`
- `backend/app/schemas/docker_service_schema.py`
- `backend/app/schemas/schedule_task_schema.py`
- `backend/app/services/docker_service_service.py`
  - Docker 可用 → 真实 `docker run/start/stop`，端口自动分配 4200-4400
  - Docker 不可用 → mock 模式，只更新 DB 状态回退到本机 4096
  - 定时探测 socket 同步状态
  - `logs(tail)` 调 `docker logs --tail N`
- `backend/app/services/schedule_task_service.py`
  - `_run_task_worker`：后台线程执行 opencode 调用，日志实时写入 task_log_entries
  - `_compute_next_run`：极简 interval + cron（`*/N * * * *` / `0 */N * * *`）+ once
  - `_Scheduler`：asyncio 后台协程每 5s 扫描 due tasks 触发
  - 手动 trigger 与调度 trigger 复用同一 worker
- `backend/app/api/v1/compute.py` — 19 个端点：
  - Docker services: list/get/create/patch/delete/start/stop/logs (8)
  - Tasks: list/get/create/patch/delete/toggle/trigger (7)
  - Runs: list_by_task/get/cancel/logs (4)

### 修改文件（后端）
- `backend/app/db/models/__init__.py` 注册 4 张新表
- `backend/app/api/v1/router.py` include `/compute`
- `backend/app/main.py` lifespan 里启动调度器 `scheduler.start(loop)`
- `backend/schema.sql` 追加 4 表 DDL

### 新增文件（前端）
- `frontend/src/services/compute.service.ts` — 完整类型 + 19 个 API 方法
- `frontend/src/pages/compute/ComputePage.tsx` — 顶层 tabs 主页
- `frontend/src/pages/compute/DockerServicePanel.tsx` — 卡片网格 + 启停 + 编辑抽屉 + 日志 Modal
- `frontend/src/pages/compute/ScheduleTaskPanel.tsx` — 卡片网格 + 触发 + 运行记录 Modal + 日志实时刷新 Modal

### 修改文件（前端）
- `frontend/src/App.tsx` — 加 `/compute` 路由 + import
- `frontend/src/components/layout/AppLayout.tsx` — 顶部菜单加"算力调度"
- `frontend/src/components/common/CmdKOmnibar.tsx` — CmdK 快捷跳转
- `AGENTS.md` — 五层业务域列表加入 `/api/v1/compute`

### 数据库
- `experts` 表以外新增 4 张：docker_services / schedule_tasks / task_runs / task_log_entries
- 建表通过 `Base.metadata.create_all(engine)` 自动完成
- schema.sql 追加 4 段完整 DDL

### API 端点（19 个）
```
GET    /api/v1/compute/docker-services
POST   /api/v1/compute/docker-services
GET    /api/v1/compute/docker-services/{id}
PATCH  /api/v1/compute/docker-services/{id}
DELETE /api/v1/compute/docker-services/{id}
POST   /api/v1/compute/docker-services/{id}/start
POST   /api/v1/compute/docker-services/{id}/stop
GET    /api/v1/compute/docker-services/{id}/logs?tail=200

GET    /api/v1/compute/tasks
POST   /api/v1/compute/tasks
GET    /api/v1/compute/tasks/{id}
PATCH  /api/v1/compute/tasks/{id}
DELETE /api/v1/compute/tasks/{id}
POST   /api/v1/compute/tasks/{id}/toggle
POST   /api/v1/compute/tasks/{id}/trigger

GET    /api/v1/compute/tasks/{id}/runs
GET    /api/v1/compute/runs/{id}
POST   /api/v1/compute/runs/{id}/cancel
GET    /api/v1/compute/runs/{id}/logs?since_seq=0
```

### 验证（Playwright + curl）
- 页面：算力调度标题 / 两个 tab (Docker 服务 + 调度任务) / 添加服务按钮 ✅
- 创建 docker service：200 ✅
- 创建 task（manual + prompt=say hi）：200 ✅
- 触发 task → 后台 worker 起线程调 opencode → 3.8s 完成 ✅
- 8 行日志按 sequence 顺序追加，含 event/info/warn/stdout ✅
- run.opencode_session_id 记录（可跳转 workspace 复盘）✅
- run.exit_code=0, status=success, duration_ms=3780 ✅
- tsc 零错误、oxlint 零告警 ✅

### 已知限制
- cron 表达式简化实现（只支持 `*/N * * * *` 和 `0 */N * * *`）—— 需要更完整可换 croniter
- 日志推送用轮询（3s 一次），非真实 SSE / WebSocket —— 用户体验足够
- Docker 未装时走 mock 模式，UI 顶部 tag 明示

## [2026-07-27] 算力调度页面原型 v2（前端重构，脱离后端）

### 目标
按新交互方案重做 `/compute` 页面：**原型先行，不接后端**。页面所有数据为本地 mock 状态，操作仅在前端模拟。

### 决策
- 头部改紧凑单行（标题 + 原型 Tag + 一句话说明 + 右侧 Tabs），不再用大 hero 区
- Docker 服务改为「节点卡片（上）+ 容器列表（下）」两层结构；节点支持本机 / SSH / Docker API(TLS) 三种挂载方式，弹窗内附两种远程方案的后端要求说明（推荐 SSH：目标节点零配置，后端走 `DOCKER_HOST=ssh://` 通道）
- 镜像搜索直连 Docker Hub 公共 API（`hub.docker.com/v2/search/repositories`，只读无需登录），失败回退内置示例数据；搜到镜像一键创建容器
- 调度运行改为「任务表 + 运行记录表」两张表：任务 = id/name/命令/日志目录/调度配置；日志落盘规则 `{logDir}/{taskId}/{yyyyMMdd}/{taskId}-{HHmmss}-{seed}.log`，编辑器内实时预览 `>> log 2>&1` 重定向后的完整命令
- 手动执行任务会生成 running 记录，打开日志窗模拟流式追加（1.2s/行，18 行后自动完结并回填统计），演示实时日志体验
- 旧实现（直连后端 compute API 的两个 Panel + service）删除，后端 `/api/v1/compute` 暂成无头 API，后续按新模型重写

### 新增文件
- `frontend/src/pages/compute/types.ts` — ComputeNode / ContainerInstance / SchedulerTask / TaskRunRecord / LogLine / HubImage
- `frontend/src/pages/compute/mock.ts` — mock 节点/容器/任务/运行记录 + 日志生成 + buildLogFile 落盘规则
- `frontend/src/pages/compute/LogViewer.tsx` — 公共日志视图（级别着色 + 跟随滚动）
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 节点卡片 + 容器表格 + 挂载节点/镜像搜索/创建容器/日志 4 个弹窗
- `frontend/src/pages/compute/SchedulerPanel.tsx` — 任务表 + 编辑抽屉 + 运行记录 Modal + 日志 Modal（实时模拟）
- `frontend/src/pages/compute/compute.css` — 紧凑头部 + 节点卡片样式

### 删除文件
- `frontend/src/pages/compute/DockerServicePanel.tsx`
- `frontend/src/pages/compute/ScheduleTaskPanel.tsx`
- `frontend/src/services/compute.service.ts`

### 修改文件
- `frontend/src/pages/compute/ComputePage.tsx` — 重写为紧凑头部 + 双面板（保持挂载以保留 tab 内状态）

### 数据库 / API
- 无变化（后端未动；现有 compute 后端与新原型模型不一致，留待后端阶段重写）

### 验证
- `tsc -b` compute 目录零错误（其余模块历史错误未动）
- `oxlint src/pages/compute` 0 warnings 0 errors
- dev server (5173) HMR 加载正常，`/compute` 可访问

### 已知限制
- 全部操作为前端模拟，刷新即还原
- 远程节点"测试连接"为假延时；镜像搜索依赖浏览器可访问 hub.docker.com
- 后端重写建议：节点接入先落 SSH 方案（docker CLI over SSH / SDK `use_ssh_client`），Docker API(TLS) 作为备选

## [2026-07-27] 调度运行视图重设计（搜索 + 勾选过滤 + 任务/记录分离）

### 目标
调度运行 tab 美观度与可用性升级：任务管理与运行记录拆成独立视图；两个视图都有搜索与筛选能力。

### 决策（frontend-design skill，延续 Editorial Light 运维账簿风）
- 顶部段落式切换器（sched-switch，ink 底 + 等宽计数）：任务管理 / 运行记录（跨任务全局流水）
- 任务视图：衬线大数字统计条（总数/调度中/运行中/成功率）+ 搜索（名称/命令/#ID）+ 类型/状态下拉筛选
- 运行记录视图：搜索（#ID/日志文件/任务名）+ 任务下拉 + 触发下拉 + **状态 chips 勾选过滤**（ink 实心激活态，带实时计数）
- 细节：运行中行左侧琥珀发丝线 + 状态脉冲点、失败行红色发丝线、命令等宽 code-chip、衬线斜体空状态插画位
- 任务行「运行记录」动作直接跳到运行记录视图并带上任务过滤（替代原 Modal）
- 修复 webview 告警：antd List（v6 已废弃）→ 自绘 img-results 列表；Alert message → title；隐藏 tab 面板改懒挂载（避免 display:none 下 rc 组件测量异常）

### 修改文件
- `frontend/src/pages/compute/SchedulerPanel.tsx` — 全量重写（双视图 + 双筛选体系 + 空状态组件）
- `frontend/src/pages/compute/compute.css` — 追加 sched-switch / sched-stats / sched-toolbar / filter-chip / code-chip / run-row 发丝线 / pulse-dot / sched-empty / img-results 样式
- `frontend/src/pages/compute/ResourcesPanel.tsx` — List→自绘列表、Alert title
- `frontend/src/pages/compute/ComputePage.tsx` — 面板懒挂载

### 验证
- tsc compute 目录零错误；oxlint 0/0；read_lints 0

## [2026-07-27] 算力调度后端实现 + 前端全量接入 API

### 目标
原型确认后，实现完整后端（模型 / Repository / Service / API 三层）+ 前端从 mock 切换到真实 API 调用。

### 决策

**后端架构**
- **Docker 节点**：模型 `docker_nodes` 表（docker_hosts），支持 local / ssh / docker-api 三种连接方式。服务层用 `subprocess` 调 Docker CLI（不依赖 Python Docker SDK），SSH 远程走 `DOCKER_HOST=ssh://user@host:port` 环境变量
- **调度任务**：模型重写为 `schedule_tasks` + `task_runs` 两张表。日志不再写 DB（删除 TaskLogEntry），改为落地磁盘文件：`{logDir}/{taskId}/{yyyyMMdd}/{taskId}-{HHmmss}-{seed}.log`。执行用 `subprocess.Popen` + `preexec_fn=os.setsid`（进程组，便于 kill）。后台线程每 15s 扫描到期任务
- **API 端点 23 条**：节点 CRUD/测试 → 容器列表/创建/启停/删除/日志 → Docker Hub 代理搜索 → 任务 CRUD/启停/触发 → 运行记录查询/取消 → 运行日志增量读取
- **调度器**改用类方法 `_Scheduler.start()/stop()`（原走 `scheduler.start(event_loop)` 已废弃）

**前端改动**
- 新增 `services/compute.service.ts`：完整封装 23 条 API + 数据归一化（snake_case→camelCase）
- `ResourcesPanel.tsx`：节点/容器全部从后端加载；镜像搜索直连后端代理（再代理 Docker Hub）；操作按钮（启停/删除/日志）全部走真实 API
- `SchedulerPanel.tsx`：任务/运行记录均从后端加载；日志弹窗增量轮询（`since_line=`，3s 刷新）；运行中自动跟随、非运行中最终拉一次并停止轮询
- `types.ts`：`ContainerStatus` 新增 `'unknown'`，`SchedulerTask` 新增 `status` 字段

### 新增文件
- `backend/app/db/models/docker_node_model.py` — DockerHost ORM
- `backend/app/db/repositories/docker_node_repo.py`
- `backend/app/services/docker_node_service.py` — Docker CLI 封装 + Hub 搜索
- `backend/app/schemas/docker_node_schema.py` — DockerHostCreate/Response, ContainerCreate/Info, NodeTestResult
- `frontend/src/services/compute.service.ts` — 完整前端 API 封装

### 重写文件
- `backend/app/db/models/schedule_task_model.py` — ScheduleTask + TaskRun（原 ScheduleTask/TaskRun/TaskLogEntry）
- `backend/app/db/repositories/schedule_task_repo.py`
- `backend/app/services/schedule_task_service.py` — subprocess 执行 + 日志落盘 + _Scheduler 轮询
- `backend/app/schemas/schedule_task_schema.py`
- `backend/app/api/v1/compute.py` — 23 条端点
- `frontend/src/pages/compute/ResourcesPanel.tsx` — mock→真实 API
- `frontend/src/pages/compute/SchedulerPanel.tsx` — mock→真实 API（含增量日志轮询）
- `frontend/src/pages/compute/ComputePage.tsx`

### 删除文件
- `backend/app/db/models/docker_service_model.py`
- `backend/app/schemas/docker_service_schema.py`
- `backend/app/services/docker_service_service.py`
- `backend/app/db/repositories/docker_service_repo.py`

### 修改文件
- `backend/app/db/models/__init__.py` — 注册 DockerHost, ScheduleTask, TaskRun
- `backend/app/main.py` — 调度器启动 `_Scheduler.start()`；移除 `import asyncio`
- `frontend/src/pages/compute/types.ts` — ContainerStatus + SchedulerTask.status
- `frontend/src/pages/compute/mock.ts` — mock 数据补 status 字段 + 导出 fmtDuration

### 验证
- 后端：`python -c "from app.main import app"` 加载成功，23 条 compute 路由全部注册
- 前端：`tsc -b` compute 目录零错误（其余模块历史错误未动）
- `oxlint src/pages/compute` — 0 errors, 1 warning（hook deps 无关）
- `read_lints src/pages/compute` — 0 diagnostics

## [2026-07-27] 算力调度三大能力：Docker 镜像管理 + 本地 OpenCode 服务 + 对话工作台选服

### 目标
1. Docker 服务增加镜像管理（列表/拉取/删除/从镜像一键创建容器带 volume 配置）
2. 新增「本地服务」tab：OpenCode 安装检测/Web 启停/CLI 一次执行/对话工作台选服务
3. Docker 容器创建支持目录映射 + 重启策略
4. 对话工作台自动读取算力调度选中的 opencode 服务 URL

### 决策

**后端新增 11 条 API**
- 镜像管理：`GET images` / `POST images/pull` / `DELETE images/path/{name:path}`
- OpenCode 服务：`GET opencode/status` / `POST start-web` / `POST stop-web` / `GET web-instances` / `POST run-cli` (async) / `GET runs` / `GET runs/{id}`
- 共 34 条 compute 路由

**OpenCodeLocalService** (`backend/app/services/opencode_local_service.py`)
- 检测安装：`shutil.which("opencode")` + `--version`
- Web 管理：`subprocess.Popen` 后台起 serve，`psutil` 扫描运行中进程
- CLI 执行：`asyncio.create_subprocess_exec` + 超时控制 + 输出持久化到 `/tmp/ontomind/opencode/runs/`
- 进程间隔离：`start_new_session=True`

**对话工作台选服**
- `ontomind_opencode_url` 存入 localStorage
- `opencodeBaseUrl()` 优先读取 localStorage，其次 VITE_OPENCODE_URL 环境变量
- 算力调度「本地服务」tab 中可选择运行中的 web 实例 → 对话工作台自动切换

**Docker 容器创建增强**
- 新增 volumes 配置：一行一个 `hostPath:containerPath`
- 新增 restart 策略：no / always / on-failure / unless-stopped
- 新增 `--network` / `extra_args`（后端 schema 已支持）

### 新增文件
- `backend/app/services/opencode_local_service.py`
- `frontend/src/pages/compute/OpenCodePanel.tsx`

### 重写文件
- `frontend/src/pages/compute/ComputePage.tsx` — 从 2 tab → 3 tab（Docker 服务 / 调度运行 / 本地服务）
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 节点详情增加「容器/镜像管理」tab 切换；创建容器增加 volumes + restart 配置
- `frontend/src/services/compute.service.ts` — 新增镜像 API + OpenCode API 共 13 个方法
- `frontend/src/pages/compute/types.ts` — 新增 ImageListItem / OpenCodeStatus / OpenCodeWebInstance / OpenCodeCliRun 类型
- `frontend/src/features/opencode/client.ts` — opencodeBaseUrl() 优先读取 localStorage

### 修改文件
- `backend/app/api/v1/compute.py` — 新增 11 条端点 + 导入新 service
- `backend/app/services/docker_node_service.py` — 新增 list_images / pull_image / remove_image + ContainerCreate volumes/restart/network/extra_args
- `backend/app/schemas/docker_node_schema.py` — 新增 ImageInfo / PullImageRequest + ContainerCreate 新字段

### 验证
- 后端 34 条路由全部注册，python import 无错误
- 前端 tsc -b：compute + opencode + service 目录零错误
- oxlint：0 errors, 3 warnings（历史 hook deps）

## [2026-07-27] 提交收尾

### 提交
- 29 files changed, 4939 insertions(+), 2058 deletions(-)
- Commit: `e531227` — `feat(compute): 算力调度全面重构`
- **Push 失败**：GitHub SSH connection reset（国内网络问题），待网络恢复后重试 `git push origin main`

## [2026-07-29] 容器三件套：启动命令 + Console 终端 + 镜像模板

### 目标
算力调度页扩展容器管理三大能力：
1. 镜像默认启动命令（docker run 覆盖 CMD，无需 Dockerfile）
2. 容器 Console：xterm.js 交互终端（WS+pty）+ 一次性命令执行
3. 镜像模板系统：CRUD + 内置 opencode 模板 + 创建容器一键填充

### 决策
- **拒绝 Dockerfile 路线**：`docker run <image> <command>` 原生覆盖 CMD，配置存模板而非镜像，镜像保持干净、配置随时可调
- **Console 双形态**：完整 xterm.js 终端（WS+pty，支持 bash/sh 探测+resize）+ 轻量一次性 exec REST API
- **pty 桥接**：pty.openpty + docker exec -it，对 local/ssh/docker-api 三种节点天然兼容（DOCKER_HOST 透传 TTY）
- **模板内置保护**：is_builtin 字段保护内置模板不可删/不可改名
- **修复 extra_args 语义**：从 image 之后（误当 CMD）移到 image 之前（正确 docker run flags）；新增 command 字段追加 image 之后

### 新增文件
- backend: `container_template_model.py` / `container_template_repo.py` / `container_template_schema.py` / `container_template_service.py` / `seed_compute.py`
- frontend: `TemplatesPanel.tsx` / `TerminalDrawer.tsx` / `ExecCommandModal.tsx`

### 修改文件
- `backend/app/schemas/docker_node_schema.py` — ContainerCreate +command 字段；+ExecRequest/ExecResult
- `backend/app/services/docker_node_service.py` — create_container 修正 extra_args/command 顺序（shlex）；+exec_in_container +detect_shell
- `backend/app/api/v1/compute.py` — +POST /exec、+WS /terminal（pty 桥接）、+模板 CRUD 4 端点
- `backend/app/db/models/__init__.py` — 注册 ContainerTemplate
- `backend/app/main.py` — lifespan 接入 seed_container_templates
- `frontend/src/services/compute.service.ts` — +execContainerCommand +terminalWsUrl +模板 CRUD 4 方法
- `frontend/src/pages/compute/types.ts` — +ContainerTemplate +ExecResult
- `frontend/src/pages/compute/ResourcesPanel.tsx` — 创建 Modal 加模板选择/启动命令/另存模板；容器行加终端/执行命令按钮；+模板 Tab
- `frontend/src/pages/compute/compute.css` — +模板卡片/终端/执行输出样式

### API 端点
- `POST /api/v1/compute/nodes/{nid}/containers/{cid}/exec` — 一次性命令执行
- `WS  /api/v1/compute/nodes/{nid}/containers/{cid}/terminal` — 交互终端
- `GET/POST /api/v1/compute/templates` — 模板列表/创建
- `PATCH/DELETE /api/v1/compute/templates/{id}` — 模板更新/删除

### 数据库
- 新表 `container_templates`（靠 create_all 自动建表）：name/image/command/ports(JSON)/env_vars(JSON)/volumes(JSON)/restart_policy/network/extra_args/is_builtin/sort_order
- 内置 seed：OpenCode 模板（image=sst/opencode:latest, command=`opencode web --port 4096`, ports=4096:4096, restart=unless-stopped）

### 验证
- 后端：模板 API 返回内置 OpenCode 模板（command/ports/is_builtin 正确）；CRUD + 内置保护测试通过（删内置抛 BusinessException，ORM 无污染）；exec/WS 端点已注册
- 前端：tsc -b 无新增错误（预存无关错误不计）；oxlint 0 errors；@xterm/xterm + @xterm/addon-fit 已安装
- 端到端 preview：算力调度页正常打开

---

## 2026-07-31

### Agent: 主开发 Agent（OALP v1.0 — 专家团 / 多 Agent 协同 / 容器化 / AI 一键生成 / Skill+MCP 管理）

### 目标
基于 [opencode 1.17+ Agent 协议](https://opencode.ai/docs/agents/) 把专家团升级为完整多 Agent 协同平台：
1. 容器部署时自动注入 expert（agent md + skills + opencode.json）到 opencode 容器
2. expert 元数据对齐 opencode 协议（OALP v1.0），用 MySQL 存储
3. 一句话 LLM 自动生成专家草稿
4. 专家团页面管理 skill/mcp（discover / 加载 / LLM 解读 / 文件夹上传）
5. 选 expert 时从 DB 动态选 skill/mcp（不再硬编码）

### 调研结论（opencode 官方，无"loop 引擎"产品级概念）
- 多 Agent 协同 = primary → subagent（`@` 引用 / `task` 工具）→ 子返回文本 → 主继续
- 没有 "loop 引擎" 原语；loop 由 LLM 自身推理驱动，受 `steps` + `subagent_depth` 约束
- "evals hook" = plugin event 总线：`tool.execute.before/after` / `session.idle` / `permission.asked` / `experimental.session.compacting`
- 协议 frontmatter 关键字段：`mode` / `steps` / `permission` / `permission.task`（glob→action）/ `tools` / `model` / `temperature` / `top_p`

### 决策
- **DB 是 source of truth**，`~/.config/opencode/agent/{slug}.md` 是 sync 产物
- **permission.task 不进 agent md**（避免每次保存反查关系），单独由 `sync_expert_relations_to_opencode` 合并到 `opencode.json` 的 `agent.{slug}.permission.task`
- **schema 增量迁移**：`create_all` 只对全新表生效；已有表加列用 `app/db/schema_patch.py` 的 `add_column_if_missing`（捕获 1060 重复列错误做幂等）
- **evals_json 字段先只读展示**，本期不连 LLM judge（决策确认）
- **新容器模板 `opencode-agent`**（区别于通用 `OpenCode`）：用 `opencode serve` 而非 `web`，挂载由 deploy 函数运行时注入
- **容器注入只 mount 必要文件**：`{agent_dir}` + `{skill_dir}` + `opencode.json` 三个 bind，不动其他命名 volume

### 新增文件
- backend: `db/models/agent_relation_model.py`（AgentRelation + assert_no_cycle）/`db/schema_patch.py`（幂等加列 helper）/`api/v1/expert_skill_mcp.py`（discover/load/upload/summarize 子路由）
- 修改文件（按层）：

### 修改文件
- `backend/app/db/models/expert_model.py` — +OALP 字段（mode/subagent_depth/max_steps/system_prompt/permission_json/hooks_json/evals_json/version/container_template_id/bind_skills_to_container/top_p）
- `backend/app/db/models/skill_model.py` — +folder_path/is_loaded/auto_description
- `backend/app/db/models/mcp_model.py` — +auto_description/tools_manifest_json/last_synced_at（import 加 Text）
- `backend/app/db/models/__init__.py` — 注册 AgentRelation + assert_no_cycle
- `backend/app/db/seed_compute.py` — +内置 opencode-agent 模板（image=sst/opencode、command=`opencode serve`）
- `backend/app/services/expert_service.py` — 重写：_build_frontmatter（OALP 全集）/ _render_frontmatter_yaml（嵌套 dict/list）/ sync_expert_relations_to_opencode（合并 task 到 opencode.json）/ AgentRelationService / auto_draft_expert（LLM + fallback）/ clone_expert / deploy_expert_container（mount 注入 + health check）
- `backend/app/schemas/expert_schema.py` — +mode/subagent_depth/max_steps/system_prompt/permission/hooks/evals/container_template_id/bind_skills_to_container/top_p + ExpertAutoDraftResponse + ExpertDeployContainerRequest + ExpertCloneRequest + AgentRelationCreate
- `backend/app/api/v1/experts.py` — 重写：+auto-draft /clone /deploy-container /relations CRUD 端点
- `backend/app/api/v1/router.py` — 注册 `/experts/skill-mcp` 子路由
- `backend/app/main.py` — lifespan 接入 OALP schema 补丁 + seed_default_experts
- `frontend/src/services/expert.service.ts` — 重写：Expert OALP 全集类型 + 全部 OALP 端点
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — 重写为 3 Tab（专家 / Skills / MCPs）+ AI 一键生成 Modal + 部署容器 Drawer + 关系管理 Drawer

### API 端点（OALP v1.0）
- `POST /api/v1/experts/auto-draft` — 一句话 LLM 生成草稿（response_model 扁平返回）
- `POST /api/v1/experts/{id}/clone` — 复制专家
- `POST /api/v1/experts/{id}/deploy-container` — 拉起 opencode 容器并注入（node_id + container_template_id + host_port + extra_env + auto_start）
- `GET  /api/v1/experts/relations/all` — 全部关系
- `GET  /api/v1/experts/{id}/relations` — 指定专家的关系
- `POST /api/v1/experts/relations` — 建关系（DFS 反环）
- `DELETE /api/v1/experts/relations/{id}` — 删关系
- `GET  /api/v1/experts/skill-mcp/skills/discover` — 扫 opencode + claude + .agents 的 SKILL.md
- `POST /api/v1/experts/skill-mcp/skills/load-from-opencode` — 全部 upsert 到 skills 表
- `POST /api/v1/experts/skill-mcp/skills/upload-folder` — zip 上传 + 扫 SKILL.md
- `POST /api/v1/experts/skill-mcp/skills/{id}/summarize` — LLM 解读
- `GET  /api/v1/experts/skill-mcp/mcps/discover` — 从 opencode.json 读 mcp 节
- `POST /api/v1/experts/skill-mcp/mcps/load-from-opencode` — upsert 到 mcps 表
- `POST /api/v1/experts/skill-mcp/mcps/{id}/summarize` — LLM 解读
- `GET  /api/v1/experts/skill-mcp/agents/list-local` — 列出本机 agent/*.md

### 数据库
- 新表 `agent_relations`（靠 create_all 自动建表）：parent_expert_id / child_expert_id / relation / condition / sort_order + unique(parent, child)
- `experts` 表加 11 列：`top_p`/`mode`/`subagent_depth`/`max_steps`/`system_prompt`/`permission_json`/`hooks_json`/`evals_json`/`version`/`container_template_id`/`bind_skills_to_container`（通过 `db/schema_patch.py` 幂等 ALTER）
- `skills` 表加 3 列：`folder_path`/`is_loaded`/`auto_description`
- `mcps` 表加 3 列：`auto_description`/`tools_manifest_json`/`last_synced_at`
- 内置 seed：4 个专家（data-analyst / frontend / backend / product-manager）+ 3 条演示关系（pm→fe/be/da）+ 1 个 opencode-agent 容器模板

### 验证
- 后端启动 + schema 补丁幂等：成功（已加列的表跳过，未加列的 ADD）
- 启动后 seed 4 个内置专家 + 演示关系：成功
- HTTP e2e（用 `oalp_admin`/`Oalp123!` 跑）：
  - `POST /experts/seed` → 已 seed 0（幂等）
  - `GET  /experts` → 6 个专家（4 内置 + 1 xiaohua + 1 test-oalp），全部 OALP 字段填充
  - `POST /experts` (with permission) → 写入磁盘 md 含完整 frontmatter
  - `POST /experts/relations` → 自动合并到 `opencode.json` 的 `product-manager.permission.task = {test-oalp: allow, *: deny, test-rel: allow}`（保留旧规则不覆盖）
  - `GET  /experts/relations/all` → 3 条
  - `POST /experts/relations` 构造环 → 400 `AGENT_RELATION_CYCLE`
  - `GET  /experts/skill-mcp/skills/discover` → 42 个 SKILL.md
  - `POST /experts/skill-mcp/skills/load-from-opencode` → 新增 20 / 更新 69
  - `GET  /experts/skill-mcp/mcps/discover` → 3 个 MCP（dataPro-search / mcp-server-askecho-search-infinity / openviking-controlplane）
  - `POST /experts/{id}/deploy-container` (无 docker node) → 404 友好
  - `POST /experts/auto-draft` → 200（LLM 不可用走 fallback 也填好）
  - `POST /experts/{id}/clone` → 新 slug `data-analyst-copy`
- 前端：`npm run build` 我引入的 ExpertTeamPage 错误 = 0（剩余 13 个 TS 错误是仓库原有，与本次无关）
- 前端 lint（oxlint）：我引入的 ExpertTeamPage 错误 = 0
- pytest 现有测试：68 passed（1 deselected，是仓库原有 agent_platform websocket 鉴权测试，与本次无关）

### 已知遗留（未做）
- 真正的"主 agent 跑通调用子 agent"留给 Agent Looper 那条线（本期只做关系持久化 + opencode.json 同步）
- evals 字段仅展示，UI 上没接 eval runner
- LLM 解读的 prompt 用的中文硬编码，多语言切换未做

---

## 2026-08-03

### Agent: 主开发 Agent（AIDE — 把 opencode Web UI 嵌入平台）

### 目标
新增 `AIDE` Tab 页，把 opencode 的完整 Web UI 嵌进平台，作为「完整 IDE 体验」入口。
要求：页面布局合理、运行流畅。

### 关键调研发现（决定了实现方案）
1. 查 [opencode web 文档](https://opencode.ai/docs/web/) — `opencode web` 提供浏览器 UI，`serve` 文档上写的是「headless HTTP server」
2. **但实测本机 opencode 1.18.4 的 `serve` 已内置完整 Web UI**：
   `curl http://127.0.0.1:4096/` 返回 2884 字节完整 HTML（`<title>OpenCode</title>` + manifest + favicon）
3. **响应头没有 `X-Frame-Options`，CSP 也没有 `frame-ancestors`** → iframe 嵌入不会被浏览器拦
   （CSP 只有 `default-src 'self'` 等，管的是 iframe 内部资源加载，不管谁能嵌它）

### 决策
- **优先复用对话工作台已有的 `serve(4096)`**，零额外进程、零额外内存、启动即用
  → 后端 `_serves_html()` 探测 `GET /` 是否返回 `text/html` 来判断
- **独立 `opencode web`(4097) 只作兜底**（老版本 opencode 的 serve 没 UI 时）
- **不做反向代理**：直接 iframe `127.0.0.1:4096`，少一跳、无 WebSocket/SSE 转发损耗，最流畅
- **iframe 而非搬 UI 源码**：opencode UI 迭代快，iframe 自动跟随升级，零维护成本
- **AppLayout 加 full-bleed 分支**：`/aide` 路由跳过 `Content margin:24` 和 `.page-enter`
  （后者的 `transform: translateY` 会让 `position: fixed` 全屏失效 — CSS containing block 陷阱）

### 新增文件
- `backend/app/api/v1/opencode.py` 内新增 3 端点（不是新文件，见修改文件）
- `frontend/src/services/aide.service.ts` — AideStatus/AideStartResult 类型 + status/start/stop
- `frontend/src/pages/aide/AidePage.tsx` — AIDE 页面（工具条 + iframe + 未就绪引导 + 全屏）

### 修改文件
- `backend/app/api/v1/opencode.py` — +`_find_web_processes()` / +`_serves_html()` / +`GET /web/status`（智能决策嵌入源）/ +`POST /web/start`（幂等，15s 轮询，注入 `OPENCODE_NO_OPEN=1` 防自动开浏览器）/ +`POST /web/stop`
- `frontend/src/App.tsx` — import AidePage + `<Route path="aide">`
- `frontend/src/components/layout/AppLayout.tsx` — 菜单加 `{ key: '/aide', icon: <CodeOutlined />, label: 'AIDE' }`（放在对话工作台之后）+ `isFullBleed` 分支

### API 端点
- `GET  /api/v1/opencode/web/status` — 探活 + 返回最佳 `embed_url` / `embed_source`(serve|web|none) / cli 版本 / serve+web 双端状态
- `POST /api/v1/opencode/web/start` — 拉起独立 `opencode web`（幂等，body: port/cors/hostname）
- `POST /api/v1/opencode/web/stop` — 停掉指定端口的 `opencode web`

### 数据库
无变更（纯运行时探测，不落库）

### 页面交互设计
- **工具条（40px）**：AIDE 标题 + 状态点（已连接/未就绪）+ 嵌入源标签（复用 serve / 独立 web）+ URL + 版本号 + 右侧 4 个按钮
  - 重新加载 iframe（改 `key` 强制重挂）
  - 在新窗口打开
  - 全屏 / 退出全屏（支持 **Esc**）
  - 启停：`embed_source === 'web'` 才给「停止」按钮（**避免误关对话工作台在用的 serve**）
- **未就绪态**：`<Result>` 展示两种启动方式的可复制命令 + 「一键启动 opencode web」+「重新探测」；CLI 未安装时给安装命令
- **流畅性优化**：
  - 就绪后停止轮询（`if (status?.healthy) return`），避免无谓请求
  - iframe `key` 固定，切 Tab 回来不重新 load
  - iframe 加载遮罩（`iframeLoaded` 状态）
  - `allow="clipboard-read; clipboard-write; fullscreen"` + `sandbox` 给足权限（opencode UI 要用剪贴板/弹窗/下载）

### 验证
- 后端 `GET /web/status` 实测：`healthy=True` / `embed_url='http://127.0.0.1:4096'` / `embed_source='serve'` / `serve_has_ui=True` / `version='1.18.4'` ✅
- **Playwright e2e 全绿**（`/tmp/aide_0*.png`）：
  - 登录 → `/aide` → `frames = 2`，第二个是 `http://127.0.0.1:4096/` ✅
  - iframe 内真实渲染出 opencode UI：`Projects / Add project / Settings / Help / Nothing here yet / Create a session to get started` + 8 个可交互按钮 ✅
  - 工具条：「已连接」+「复用 serve」标签都在 ✅
  - **无双滚动条**：`hasBodyScroll = False`（`docScrollH 1000 === docClientH 1000`）✅
  - iframe 精确铺满：`1600 × 904`，`top=96`（= 56 Header + 40 工具条），`1000 - 96 = 904` ✅
  - 全屏：`top: 40, h: 960`（占满视口只留工具条）→ Esc 正常退出 ✅
- 前端 `npm run build`：AIDE 相关 0 error（剩余 13 个是仓库原有，与本次无关）
- 前端 `npm run lint`（oxlint）：AIDE 相关 0 error/warning
- 修掉一个 antd v6 废弃警告：`<Spin tip>` → `<Spin />` + 独立 `<Text>`

### 已知遗留
- iframe 内 opencode 的主题跟平台 Editorial Light 不统一（opencode 自己的深/浅色跟随系统），后续可考虑通过 opencode `tui.json` 的 theme 或注入 CSS 变量对齐
- 平台侧无法感知 iframe 内的 session 状态（跨域 iframe 无法读 DOM），若要打通需走 `postMessage` 协议（opencode 上游暂未提供）
- `serve` 内置 UI 是 opencode ≥ 1.18 的行为；若降级到老版本会自动回退到独立 `opencode web` 路径（代码已兼容）

---

## 2026-08-03（补）

### Agent: 主开发 Agent（AIDE 性能优化 — 根治"每次进来都在加载"）

### 问题
用户反馈：「为什么每次进 AIDE 总是会加载 opencode UI，很慢」

### 根因定位（实测数据，不是猜）
分三层量化：

**A. 后端 `/web/status` 端点 600ms**
```
[1] subprocess opencode --version :  504.2 ms   ← 占 85%
[2] psutil process_iter (611 procs):  50.3 ms
[3] port_open 4096                :   3.5 ms
[4] GET 4096/ (serves_html)       : 105.3 ms
>>> 合计 ≈ 663 ms，curl 实测 0.56~0.60s
```

**B. 前端 iframe 每次都重建（真正主因）**
React Router 切走路由会卸载 `AidePage`，iframe 随之从 DOM 移除；
再回 `/aide` 时 opencode UI 得从零重来：重下 11 个 JS/CSS bundle、
重建 SSE 连接、重新拉 session 列表 → 每次 2 秒白屏。

**C. 首屏必须等接口返回才渲染** → 叠加 600ms 空等

### 决策与修法

**后端（`opencode.py`）**
- `_cli_version()` 加 10min TTL 缓存 —— CLI 版本在进程生命周期内不会变，504ms → 0ms
- `_serves_html()` 加 60s TTL 缓存 + 改用 `HEAD`（不传 body，比 GET 快），4xx 时回退 GET
- `_find_web_processes()`（50ms psutil 遍历）改成**只在 `?detail=1` 才跑**，默认不跑
- 新增 `?fast=1` 快路径：只做端口探活（~4ms），跳过 HTML 探测和版本查询，给前端轮询用
- `/web/start` `/web/stop` 成功后主动清 `_HTML_CACHE`，避免返回失效的嵌入源

**前端（架构调整）**
- 新增 `components/layout/AideHost.tsx` —— iframe 常驻宿主，**挂在 `AppLayout` 里**（跟路由同级），
  切走路由只做 `display: none`，iframe 不卸载、SSE 不断
- 新增 `stores/aideStore.ts` —— iframe 在 AppLayout、控制它的工具条在 AidePage，
  两者非父子关系，用 zustand 共享状态
  - `mounted`：进过一次就永久 true
  - `visible`：当前是否在 /aide（仅控制 display）
  - `reloadToken`：递增触发手动 reload（改 `el.src` 而非换 key，避免 DOM 节点重建）
  - status 结果落 `sessionStorage`，**首屏直接渲染 + iframe 立刻开始加载，不等接口**
- `AidePage.tsx` 瘦身为「工具条 + 未就绪引导」，iframe 交给 AideHost
  - 全屏时工具条 `zIndex: 1001` 盖在 iframe(1000) 上，`pointerEvents: 'none'` 让 iframe 可点
  - 首次探测用 full（拿 version/cli_path），之后全部走 `fast=1`
- `aide.service.ts` — `status()` 支持 `{ fast, detail }` 参数

### 修改文件
- `backend/app/api/v1/opencode.py` — +`_VERSION_CACHE`/`_HTML_CACHE`/`_cli_version()`；`_serves_html()` 加缓存+HEAD；`web_status()` 加 `fast`/`detail` 参数；启停后清缓存
- `frontend/src/components/layout/AideHost.tsx` — **新增**
- `frontend/src/stores/aideStore.ts` — **新增**
- `frontend/src/pages/aide/AidePage.tsx` — 重写（去掉 iframe，改用 store）
- `frontend/src/services/aide.service.ts` — `status()` 加 fast/detail
- `frontend/src/components/layout/AppLayout.tsx` — 挂载 `<AideHost />`

### 验证（Playwright e2e，`/tmp/aide_perf.png`）

⚠️ **测试坑**：一开始用 `page.goto()` 测「切走再回来」，结果 `iframe exists = False`，
误判优化无效。原因是 `goto` 是**整页导航**（整个 SPA 重新加载），
而真实用户点导航菜单走的是**客户端路由**。改成 `page.click('.ant-menu-item:has-text("专家团")')` 后才测准。

| 指标 | 优化前 | 优化后 | 提升 |
|---|---|---|---|
| 二次进入 iframe 就绪 | 2076 ms | **112 ms** | **18.5x** |
| 二次进入 iframe 请求数 | 11 个 | **0 个** | 完全复用 |
| 切走后 iframe 状态 | 被销毁 | `display:none` 存活 | — |
| `/web/status`（缓存热） | 600 ms | **2 ms** | **300x** |
| `/web/status?fast=1`（含网络） | — | 13~21 ms | — |
| 布局回归 | — | `hasBodyScroll=False`, `1600×904`, `top=96` | 无回归 |

- 前端 `npx tsc -b`：AIDE 相关 0 error
- 前端 `npm run lint`：AIDE 相关 0 问题

### 已知遗留
- 首次进入仍需 ~2s（opencode UI 自身的 bundle 加载时间，非本平台可控）；
  若要再压，需 opencode 上游支持 SSR 或 service worker 预缓存
- 整页刷新（F5）时 iframe 仍会重载 —— 浏览器行为，无法规避；
  但 `sessionStorage` 缓存让 iframe 少等 600ms 接口，能提前开始加载

---

## 2026-08-03（补 2）

### Agent: 主开发 Agent（修「无法连接后端服务」— 加网络错误自动重试）

### 现象
用户报错：`无法连接后端服务，请确认后端已启动且 CORS 配置正确`

### 诊断过程（先量化，不猜）

**第一步：确认后端到底行不行**
```
lsof -iTCP:8000  → python3.1 78433 LISTEN ✅ 在跑
curl /health     → {"status":"healthy"} HTTP 200 / 0.023s ✅
curl OPTIONS 预检 → access-control-allow-origin: http://localhost:5173 ✅
curl GET 带 Origin → 200 + 正确 CORS 头 ✅
```
**后端和 CORS 完全正常。**

**第二步：Playwright 走真实浏览器复现**
```
9 个 API 调用全部 200：
  200 POST /auth/login    200 GET /auth/me       200 GET /opencode/health
  200 GET /experts        200 GET /opencode/web/status
AIDE 页面正常显示：已连接 / 复用 serve / v1.18.4
唯一失败：GET http://127.0.0.1:4096/event :: net::ERR_ABORTED
  ← 这是 iframe 内 opencode 自己的 SSE，跟我们后端无关
```

**第三步：定位文案来源**
```
grep -rn "无法连接" frontend/src
  → pages/Login.tsx:23   ← 是【登录页】的提示，不是 AIDE
```

**第四步：找到真正根因**
```
ps -p 78433 -o lstart=,etime=
  → Mon Aug 3 11:18:33 2026   etime=03:37
```
后端进程只活了 **3 分 37 秒** —— 因为我前面在改 `opencode.py`，
`uvicorn --reload` 触发了热重载。**热重载期间有 1~3 秒窗口会 ECONNREFUSED**，
用户恰好在这个窗口点了登录 → axios 抛 `Network Error` → 弹出那句提示。

**不是配置问题，是开发时热重载的固有时序窗口。**

### 决策
既然是必然存在的时序窗口，就让前端自己扛住，而不是把锅甩给用户：
1. **网络层失败自动重试**（有 HTTP 响应的 4xx/5xx 一律不重试，避免重复提交）
2. **重试白名单**：GET/HEAD/OPTIONS 天然幂等可重试；
   POST 默认不重试，但 `/auth/login` `/auth/me` 是纯查询语义，显式加白名单
3. **指数退避** 300/600/1200ms —— 总窗口 2.1s，刚好覆盖 uvicorn 热重载时间
4. **错误提示改成可执行的排查步骤**，而不是笼统说"CORS 配置不对"（本来就没错）

### 修改文件
- `frontend/src/services/api.ts` — 重写响应拦截器：
  - `shouldRetry()`：只重试无 response 的网络错误 + 幂等方法/白名单路径
  - 指数退避重试，`__retryCount` 挂在 config 上防无限循环
  - 401 处理加防护：已在 `/login` 就不再跳转，避免无限刷新
- `frontend/src/pages/Login.tsx` — `formatApiError()` 区分场景：
  - 超时（ECONNABORTED）→ 提示负载过高
  - 网络失败 → 给出 3 步可执行排查（含具体命令），并说明已自动重试过
  - notification 加 `whiteSpace: 'pre-line'` 让多行提示正常换行，`duration: 8` 给足阅读时间

### 验证（Playwright e2e）

**场景 1：后端未启动时登录，中途拉起后端**
```
准备：kill -9 后端，确认 8000 端口空
点登录 → 1.2s 后后台拉起后端
控制台：
  [api] 网络失败，300ms 后重试 (1/3): POST /auth/login
  [api] 网络失败，600ms 后重试 (2/3): POST /auth/login
  [api] 网络失败，1200ms 后重试 (3/3): POST /auth/login
结果：url = http://localhost:5173/workspace
✅ 自动重试成功 —— 后端恢复后登录自动完成，用户全程无感
```

**场景 2：后端真的挂了（不重启）**
```
重试 3 次后停止，弹出提示：
  连不上后端 http://localhost:8000/api/v1（已自动重试 3 次）。请检查：
  1. 后端是否在跑：cd backend && uvicorn app.main:app --reload --port 8000
  2. 若刚改过后端代码，--reload 热重载需 1~3 秒，稍等再试
  3. 端口是否被占用：lsof -iTCP:8000 -sTCP:LISTEN
✅ 提示清晰可执行，不再误导用户查 CORS
```

- `npx tsc -b`：api.ts / Login.tsx 相关 0 error
- `npm run lint`：api.ts / Login.tsx 相关 0 问题
- 后端已恢复运行（`/health` 200）

### 副作用说明
- 全站所有走 `services/api.ts` 的请求都获得了网络重试能力（GET 类自动生效）
- POST/PATCH/PUT/DELETE 默认**不重试**，不会产生重复写入
- 重试日志用 `console.warn` 打印，便于开发时观察，不影响用户

---

## 2026-08-03（补 3）

### Agent: 主开发 Agent（下线「对话工作台」— 前后端彻底删除）

### 目标
对话工作台功能不再需要，前后端删除干净。能力已由 AIDE（iframe 嵌 opencode 官方 UI）承接。

### 删前盘点（避免删漏/删错）
```
frontend:
  features/opencode/**                    31 个文件，只被 ChatWorkspacePage 引用（自闭环）
  pages/agent-platform/ChatWorkspacePage.tsx
  main.tsx                                引了 vendor/styles/opencode.css
  App.tsx / AppLayout.tsx / CmdKOmnibar.tsx / AgentStudioPage.tsx / ResourcesConsolePage.tsx
                                          共 10 处 /workspace 引用
backend:
  api/v1/opencode.py                      /health /spawn /session-link 三个端点（仅工作台用）
  db/models/opencode_session_model.py
  db/models/__init__.py                   注册 + __all__
  schema.sql                              第 8 节 opencode_sessions 建表
  MySQL                                   opencode_sessions 表（9 行数据）
```
**关键确认**：AIDE 只用 `/opencode/web/*`，跟被删的三个端点零交集；
`features/opencode` 里的 `ExpertPicker` 只被 `ChatWorkspaceShell` 用，专家团页面不依赖它。

### 决策
- **`/workspace` 路由保留为重定向**（`<Navigate to="/aide" replace />`），
  老书签/外链不会 404
- **默认落地页从 `/workspace` 改成 `/aide`**（`<Route index>` + `AppLayout.selectedKey`）
- CmdK 面板的「对话工作台」项换成「AIDE」；顺手删掉指向死路由的「运行记录」（`/agent-platform/runs` 早已下线）
- `ResourcesConsolePage`（已不在路由里的死代码）里的 `/workspace` 跳转也改指 `/aide`，避免留脏引用
- **MySQL 表直接 DROP**（9 行历史数据无保留价值，纯审计映射）
- `schema.sql` 删掉第 8 节后，把 9~13 节编号重排为 8~12，保持连续

### 删除文件
- `frontend/src/features/opencode/`（**整目录 31 个文件**：client.ts / types.ts / index.ts /
  13 个 components / 11 个 hooks / stores/opencodeStore.ts / vendor/{LICENSE,opencode.css,VENDOR_META.md}）
- `frontend/src/pages/agent-platform/ChatWorkspacePage.tsx`
- `backend/app/db/models/opencode_session_model.py`

### 修改文件
- `frontend/src/main.tsx` — 去掉 `import './features/opencode/vendor/styles/opencode.css'`
- `frontend/src/App.tsx` — 去掉 ChatWorkspacePage import；`<Route index>` 改指 `/aide`；
  `workspace` 改成 `<Navigate to="/aide" replace />`
- `frontend/src/components/layout/AppLayout.tsx` — 删「对话工作台」菜单项 + `MessageOutlined` import；
  `selectedKey` 默认值 `/workspace` → `/aide`
- `frontend/src/components/common/CmdKOmnibar.tsx` — 「对话工作台」项换成「AIDE」；删「运行记录」死项
- `frontend/src/pages/agent-platform/index.ts` — 去掉 ChatWorkspacePage 导出
- `frontend/src/pages/agent-platform/AgentStudioPage.tsx` — 「前往对话工作台」→「前往 AIDE」
- `frontend/src/pages/agent-platform/ResourcesConsolePage.tsx` — 2 处跳转改指 `/aide`
- `backend/app/api/v1/opencode.py` — **526 行 → 348 行**，只保留 `/web/{status,start,stop}`；
  清掉 `get_db` / `Session` / `OpencodeSession` / `settings` 等不再需要的 import
- `backend/app/db/models/__init__.py` — 去掉 OpencodeSession import + `__all__` 条目
- `backend/schema.sql` — 删第 8 节 opencode_sessions 建表（22 行），9~13 节编号重排为 8~12
- `AGENTS.md` — 「对话工作台 + 专家团」章节重写为「AIDE + 专家团」；补已删端点清单；
  清 2 行过期内容（vendor 计划、ChatComposer 输入法说明）
- `HANDOFF.md` — 10 处更新：目标/活跃模块/CLI 版本/终端说明/验证步骤/3.1 整节重写/
  数据流图/数据表清单/排查表/冒烟脚本加 AIDE 探活

### 数据库
- `DROP TABLE opencode_sessions`（含 9 行历史数据）
- `schema.sql` 同步删除建表语句
- ⚠️ `task_runs.opencode_session_id` 字段**保留** —— 那是算力调度记录 opencode 任务用的独立字段，与本次无关

### API 端点变更
- ❌ `GET  /api/v1/opencode/health`
- ❌ `POST /api/v1/opencode/spawn`
- ❌ `POST /api/v1/opencode/session-link`
- ❌ `GET  /api/v1/opencode/session-link`
- ✅ 保留 `GET /api/v1/opencode/web/status` / `POST /web/start` / `POST /web/stop`

### 验证
**后端**
```
GET /opencode/web/status  -> 200  healthy=True src=serve   ✅ 保留端点正常
GET /opencode/health      -> 404  ✅
GET /opencode/session-link-> 404  ✅
GET /opencode/spawn       -> 404  ✅
后端启动无错误（bcrypt 警告是仓库既有问题）
pytest: 68 passed, 1 deselected  ← 与删除前完全一致，无回归
```

**前端**
```
npm run build: 14 个 error 全是仓库原有（AgentStudioPage/TemplatesPanel/perception/
               AgentDetailPage/AgentLooperWizard/userStore），无「找不到模块」类删漏错误
npm run lint : 只有既有 warning
grep -rn "/workspace" frontend/src  -> 无残留
```

**Playwright e2e 回归全绿**（`/tmp/after_delete.png`）
```
1) 登录后默认落地页 = http://localhost:5173/aide            ✅
2) 顶部菜单 = [AIDE, 专家团, 算力调度, 感知层, 认知层,
              决策层, 执行层, 用户管理]                      ✅ 无「对话工作台」
3) 访问老链接 /workspace → 自动跳 /aide                      ✅
4) AIDE 页面：含「AIDE / 已连接 / 复用 serve」，
   iframe 指向 http://127.0.0.1:4096/                        ✅
5) 专家团：正常渲染，14 个专家卡片匹配                        ✅
6) CmdK 面板已无「对话工作台」                                ✅
页面错误：仅 2 个 antd 既有废弃警告
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 代码量变化
- 前端：删 32 个文件
- 后端：删 1 个文件，`opencode.py` 瘦身 178 行（526 → 348）
- schema.sql：删 22 行

---

## 2026-08-03（补 4）

### Agent: 主开发 Agent（大清理 — 删除五层业务域 + resources + agent-looper/platform）

### 目标
感知层 / 认知层 / 决策层 / 执行层全部删除，前后端 + 数据库表都要干净。

### 删前盘点发现的 3 个关键交叉点（不是无脑删）

**1. 数据平台的「元数据」页完全依赖感知层**
```
/data-platform/metadata（仍在导航里活着）是从感知层 verbatim port 过来的：
  前端 12 处调 perceptionAPI
  后端 8 个 /api/v1/perception/* 端点
  MetadataService + metadata_repo + MetaTable/MetaColumn/MetaProfile
  4 张表：meta_tables(3007) / meta_columns(83451!) / meta_profiles(11) / data_sources(2)
```
→ 用户决策：**元数据能力也一起删干净**

**2. instances/agents 被 /api/v1/resources 大量使用**
```
resources.py 46 个端点，其中 29 处是 skills/mcps —— 而专家团页面正在用
（resourcesAPI.listSkills / listMCPs）
```
→ 用户决策：**全删 resources，skills/mcps 搬到 experts 下**

**3. Agent Looper 的 3 个页面挂在 /resources 下**
→ 用户决策：**一起删掉**

### 决策
- **先搬迁再删除**：skills/mcps 的 13 个 CRUD/sync 端点先搬到
  `/api/v1/experts/skill-mcp/*`（原文件 21 个端点），再删 resources.py
- **前端 resourcesAPI 彻底废弃**：`expert.service.ts` 补 `listSkills/createSkill/.../syncMCPs`
  等 13 个方法，ExpertTeamPage 改用 expertService
- **所有已删路由保留为重定向**（`<Navigate>`），老书签/外链不 404：
  `/workspace|/perception|/cognition|/decision|/execution` → `/aide`；
  `/resources/*|/agent-platform/*` → `/experts`；`/data-platform/metadata` → `/data-platform`
- **schema.sql 从 ORM 自动重生**：原文件表名大量过期（`mcp_configs`/`docker_services`/
  `schedule_tasks` 早已改名）且只覆盖 12 张表 → 改成用 `CreateTable` 从
  `Base.metadata.sorted_tables` 导出，并在头部写清 24 张保留表 + 39 张已删表清单
- **3 个跨模块外键去掉但保留列**（标 DEPRECATED），避免与历史数据不一致：
  `kb_data_assets.ref_meta_table_id` / `ref_data_source_id` / `dp_chat_sessions.agent_looper_config_id`
- **role_service / audit_log_service 保留**：被 `core/authorization.py` 用（llm.py 的权限校验依赖）

### 删除文件（后端 58 个）
- **API（7）**：`api/v1/{perception,cognition,decision,execution,resources}.py`
  + `api/v1/agent_looper/`（4 文件）+ `api/v1/agent_platform/`（6 文件）
- **Service（21）**：`services/agent_platform/`（10 文件）+ `agent_container_discovery_service`
  / `agent_discovery` / `agent_looper_{discovery,service,writer}_service` / `agent_service`
  / `data_source_service` / `instance_service` / `metadata_service` / `ontology_service`
  / `credential_service`
- **Repository（7）**：`agent_looper_repo` / `agent_platform_repo` / `agent_repo`
  / `data_source_repo` / `instance_repo` / `metadata_repo` / `credential_repo`
- **Model（21）**：`data_source` / `metadata` / `ontology` / `instance` / `agent`
  / `compute_node` / `agent_container` / `node_container` / `container_agent`
  / `container_skill` / `container_mcp` / `agent_skill` / `agent_mcp` / `node_connection`
  / `discovery_run` / `discovery_item` / `agent_platform` / `agent_looper_{config,version,test_run}`
  / `credential`
- **Schema（8）**：`agent_looper` / `agent_platform` / `agent` / `data_source` / `instance`
  / `metadata` / `credential` / `project`
- **测试（9）**：`tests/agent_platform/`（1）+ `test_agent_looper_*`（4）
  / `test_compute_node` / `test_node_container_discovery` / `test_naming_migration`
  / `test_agent_platform_wave0`
- **孤儿脚本（1）**：`app/scripts/purge_test_runs.py`

### 删除文件（前端）
- **页面目录（6）**：`pages/{perception,cognition,decision,execution,resources,agent-platform}/`
- **单页（1）**：`pages/data-platform/MetadataPage.tsx`（依赖感知层）
- **Service（3）**：`services/{resourcesAPI,agentPlatform.service,agentLooper.service}.ts`
- **组件（2）**：`components/common/AgentPicker.tsx` + 其测试（依赖已删 service，已成孤儿）

### 修改文件
- `backend/app/api/v1/expert_skill_mcp.py` — **+13 个 skills/mcps CRUD/sync 端点**（493→660 行，共 21 端点）
- `backend/app/api/v1/router.py` — 重写：只注册 8 个模块，头部写清已删路由清单
- `backend/app/db/models/__init__.py` — 重写：24 个 model，头部写清已删 model 清单
- `backend/app/db/models/kb_data_asset_model.py` — 2 个外键去约束保留列（DEPRECATED）
- `backend/app/db/models/dp_chat_session_model.py` — `agent_looper_config_id` 去外键（DEPRECATED）
- `backend/schema.sql` — **从 ORM 自动重生**（609 行 / 24 张表 + 完整已删清单）
- `backend/tests/data_platform/test_opencode_sync.py` — 3 处 `app.api.v1.resources`
  改成 `expert_skill_mcp`；异常类型 `HTTPException` → `BusinessException`
- `frontend/src/services/expert.service.ts` — +`SkillRow`/`McpRow` 类型 + 13 个 CRUD 方法
- `frontend/src/services/index.ts` — 重写：删 `resourcesAPI`/`perceptionAPI`/`cognitionAPI`
  /`decisionAPI`/`executionAPI`，只留 `llmAPI`+`authAPI`，头部写清迁移指引
- `frontend/src/App.tsx` — 重写：8 个活跃路由 + 8 条重定向
- `frontend/src/components/layout/AppLayout.tsx` — 菜单 6 项（AIDE/专家团/算力调度/数据平台/知识库/用户管理）；
  `selectedKey` 简化（agent-platform 分支已删）
- `frontend/src/components/common/CmdKOmnibar.tsx` — 删 7 个指向死路由的 nav 项 + 4 个未用图标
- `frontend/src/components/common/index.ts` — 去掉 AgentPicker 导出
- `frontend/src/pages/experts/ExpertTeamPage.tsx` — `resourcesAPI` → `expertService`；`MCPConfig` → `McpRow`
- `frontend/src/pages/compute/TemplatesPanel.tsx` / `stores/userStore.ts` — 顺手清历史未用变量
- `AGENTS.md` / `HANDOFF.md` — 项目定位、活跃模块、路由清单、数据表清单、数据流图全部同步

### 数据库
**DROP 39 张表（约 9 万行数据）**，一次性执行（关 FOREIGN_KEY_CHECKS）：
```
感知层    : data_sources(2) / meta_tables(3007) / meta_columns(83451) / meta_profiles(11)
认知层    : onto_versions(3) / onto_classes(138) / onto_properties(1250)
            / onto_relationships(40) / onto_constraints(680)
资源管理  : instances(1) / agents(2) / credentials(0) / mcp_configs(0)
T44 平台  : compute_nodes(1) / agent_containers(0) / node_containers(0)
            / container_agents(0) / container_skills(0) / container_mcps(0)
            / agent_skills(0) / agent_mcps(0) / node_connections(1)
            / discovery_runs(71) / discovery_items(1828)
AgentLooper: agent_looper_configs(0) / agent_looper_versions(0) / agent_looper_test_runs(0)
AgentPlatform: agent_versions(2) / agent_deployments(0)
旧知识库  : knowledge_bases(1) / knowledge_chunks(0) / knowledge_documents(0)
            / source_code_repos(0) / source_code_files(0)
旧算力表名: docker_services(1) / schedule_tasks(1) / task_runs(1) / task_log_entries(8)
Alembic   : alembic_version(1)
```
**结果**：DB 从 63 张表 → **24 张**，零孤儿零缺失（ORM 声明与 DB 实际完全一致）

### API 端点变更
- ❌ 删除：`/api/v1/{perception,cognition,decision,execution,resources,agent-looper,agent-platform}/*`
- ✅ 新增：`/api/v1/experts/skill-mcp/{skills,mcps}` 全套 CRUD + `/sync`（从 resources 搬迁）
- ✅ 保留：`/api/v1/{auth,users,llm,opencode,experts,compute,data-platform,knowledge-base}`

### 验证

**后端**
```
app import 成功，路由只剩 8 个模块前缀
✅ 保留端点（7 个全 200）:
   /experts (8) · /experts/skill-mcp/skills (43) · /experts/skill-mcp/mcps (3)
   /opencode/web/status · /compute/nodes (1) · /data-platform/sources · /knowledge-base/libraries (4)
❌ 已删端点（8 个全 404）:
   /perception/* · /cognition/* · /decision/* · /execution/*
   /resources/skills · /resources/compute-nodes · /agent-looper/configs · /agent-platform/agents
外键完整性：Base.metadata.sorted_tables 成功排序 24 张表（修完 3 个断链后）
启动日志无错误
```

**pytest 基线对比**（用 `git stash` 精确对比）
```
删除前：34 failed, 202 passed, 6 errors
删除后：29 failed, 109 passed, 6 errors
→ 失败数 34→29（修好 5 个 opencode_sync 端点测试）
→ passed 下降是因为删了 8 个测试文件（测的都是已删模块）
→ 剩余 29 个失败全部集中在 data_platform 既有测试（用 mcp_type 等旧字段名），
  逐个用 git stash 验证过：删除前后完全一致，非本次引入
```

**前端**
```
npm run build → ✓ built，0 error
  （连历史遗留的 14 个 TS 错误也一并清零：AgentStudioPage/AgentLooperWizard
   /AgentDetailPage/perception 等文件已删除，TemplatesPanel/userStore 顺手修掉）
```

**Playwright e2e 全绿**（`/tmp/after_purge.png`）
```
1) 登录 → 默认落地 /aide                                          ✅
2) 菜单 = [AIDE, 专家团, 算力调度, 数据平台, 知识库, 用户管理]      ✅ 与预期完全一致
3) 8 条死路由重定向全部生效                                        ✅
   /workspace|/perception|/cognition|/decision|/execution → /aide
   /resources|/agent-platform → /experts
   /data-platform/metadata → /data-platform/sources
4) 6 个保留页面全部正常渲染（无白屏）                              ✅
5) 专家团 Skills Tab 20 行 / MCPs Tab 23 行                        ✅ 端点搬迁成功
页面错误：仅 antd 既有废弃警告 + 2 个 403（/api/v1/users，
          测试用户非平台管理员，权限系统正常工作，与本次无关）
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 代码量变化
- 后端：删 **58 个文件**（API 7 + service 21 + repo 7 + model 21 + schema 8 + 测试 9 + 脚本 1，含目录）
- 前端：删 **6 个页面目录 + 4 个单文件**
- 数据库：63 张表 → **24 张**（DROP 39 张，约 9 万行）
- schema.sql：从手工维护的 12 张过期表 → ORM 自动生成的 24 张准确表

---

## 2026-08-03（补 5）

### Agent: 主开发 Agent（深度清理 — 删除专家团/算力调度/数据平台/知识库/LLM，只留 AIDE + 用户管理）

### 目标
继续删除专家团、算力调度、数据平台、知识库，让项目整体清爽干净，包括数据库。

### 删前盘点
- **AIDE 完全自闭环**：`AidePage`/`AideHost`/`aideStore`/`aide.service` 只依赖 `api.ts`；
  后端 `opencode.py` 只依赖 `auth` + `exceptions` → 删四模块对 AIDE 零影响 ✅
- 发现上次删除留下的**空壳目录**（只剩 `__pycache__`）：
  `api/v1/agent_looper/` / `api/v1/agent_platform/` / `services/agent_platform/` → 一并清掉

### 用户决策（提问确认）
1. **LLM 配置** → 一起删掉（四模块删完后 `LLMConfigService` 只剩 `/api/v1/llm` 自己在用，前端无页面）
2. **用户管理** → 保留（登录必需 `users` 表）
3. **4 个重组件** → 全删 + 卸依赖（`SqlEditor`/`ResultGrid`/`SchemaTree`/`DataTable`
   拖着 monaco-editor 6.9MB worker，删完页面后已成孤儿）

### 删除文件（后端 79 个）
- **API（6）**：`experts.py` / `expert_skill_mcp.py` / `compute.py` / `llm.py`
  + `data_platform/`（6 文件）+ `knowledge_base/`（8 文件）
- **Service（14）**：`expert` / `skill` / `mcp` / `docker_node` / `schedule_task`
  / `container_template` / `opencode_config_discovery` / `opencode_sync` / `opencode_local`
  / `dp_data_source` / `dp_query` / `dp_chat` / `kb` / `llm_config`
- **Repository（17）**：expert / skill / mcp / docker_node / schedule_task / container_template
  / dp_*（4）/ kb_*（6）/ llm_config
- **Model（19）**：expert / agent_relation / skill / mcp / docker_node / schedule_task
  / container_template / dp_*（5）/ kb_*（6）/ llm_config
- **Schema（17）**：对应上述模块的全部 Pydantic schema
- **Core（3）**：`sql_guard.py` / `crypto.py` / `decorators.py`（删完模块后成孤儿）
- **DB 工具（3）**：`seed_kb.py` / `seed_compute.py` / `schema_patch.py`
- **目录（4）**：`app/connectors/`（4 文件，Agent Platform 遗留）/ `app/scripts/` / `app/models/`
  / `sim/`（数据模拟器）/ `alembic/` + `alembic.ini`（本就不可用）
- **测试（12）**：`tests/{data_platform,knowledge_base,repositories,security}/` 全部

### 删除文件（前端）
- **页面目录（4）**：`pages/{experts,compute,data-platform,knowledge-base}/`
- **Service（5）**：`{expert,compute,dataPlatform,knowledgeBase,llm}.service.ts`
- **Store（2）**：`{dataPlatform,knowledgeBase}Store.ts`
- **组件（11）**：`SqlEditor` / `ResultGrid` / `SchemaTree` / `DataTable` / `monaco-setup`
  / `AgentChatPanel` / `DangerConfirm` / `PageHeader` / `SectionTitle` / `StatCard` / `TagPill`
- **测试（4）**：`{dataPlatform,knowledgeBase}.service.test.ts` / `{dataPlatform,knowledgeBase}Store.test.ts`
  + `components/common/__tests__/`（4 个）

### 卸载依赖
**前端（11 个）**：`@monaco-editor/react` / `monaco-editor` / `monaco-sql-languages`
/ `@xterm/xterm` / `@xterm/addon-fit` / `@tanstack/react-table` / `@tanstack/react-virtual`
/ `@ant-design/charts` / `@antv/g6` / `echarts` / `echarts-for-react`
→ dependencies **12 个 → 8 个**

**后端（13 个）**：`alembic` / `aiomysql` / `redis` / `langchain` / `langchain-openai`
/ `openai` / `numpy` / `pandas` / `celery` / `rdflib` / `asyncssh` / `sqlglot` / `sqlparse`
/ `sse-starlette`（`cryptography` 保留 — `python-jose[cryptography]` 需要）
→ 新增显式 `psutil`（AIDE 扫 `opencode web` 进程用，原来靠间接依赖）

### 修改文件
- `backend/app/api/v1/router.py` — 重写：只注册 3 个域，附完整已删清单表格
- `backend/app/main.py` — 重写：lifespan 只留 `create_all`（seed/scheduler/schema_patch 全删）
- `backend/app/db/models/__init__.py` — 重写：4 个 model，附两批删除清单
- `backend/app/core/config.py` — 重写：删 Redis/OpenAI/Fernet/AgentLooper/OpencodeServe 等过期配置；
  **加 `"extra": "ignore"`** 让 `.env` 历史遗留项（FERNET_KEY 等）不导致启动崩溃；
  新增 `OPENCODE_{HOST,PORT,WEB_PORT}` 统一管理
- `backend/app/api/v1/opencode.py` — `os.environ.get` 改用 `settings.OPENCODE_*`
- `backend/requirements.txt` — 重写：从 30+ 个依赖精简到 15 个
- `backend/schema.sql` — 从 ORM 重生（135 行 / 4 张表 + 88 张已删表完整清单）
- `backend/tests/conftest.py` — 重写：删 kb_libraries / MEDIUMTEXT shim / FULLTEXT strip
  / FERNET_KEY fixture（都指向已删模块）
- `frontend/src/App.tsx` — 重写：2 个活跃路由 + 11 条重定向
- `frontend/src/components/layout/AppLayout.tsx` — 菜单 2 项（AIDE / 用户管理）
- `frontend/src/components/common/CmdKOmnibar.tsx` — 删 10 个死路由 nav 项 + 3 个未用图标
- `frontend/src/components/common/index.ts` — 重写：只导出 4 个组件
- `frontend/src/services/index.ts` — 重写为空壳（`export {}`），附迁移指引
- `frontend/src/test-setup.ts` — 删 monaco mock（依赖已卸）
- `AGENTS.md` / `HANDOFF.md` — **整篇重写**，反映"只剩 2 个模块"的新形态

### 新增文件
- `backend/tests/test_smoke.py` — **25 个冒烟测试**（原测试全删了不能裸奔）：
  - `/health` `/` 可用性
  - **OpenAPI 里只应出现 auth/users/opencode 三个域**（防止误恢复模块）
  - 登录成功 / 密码错误 401 / `/auth/me`
  - `/users` 认证闸门（无 token / 伪造 token / Basic / 乱码 全 401）
  - `/opencode/web/status?fast=1` 响应协议校验
  - **15 个已删端点必须 404**（参数化，防回归）
  - ORM 只应剩 4 张表

### 数据库
**DROP 49 张表**（含上次删除后被 `create_all` 重建的 25 张空表壳）：
```
专家团   : experts(8) / agent_relations(2) / skills(43) / mcps(3)
算力调度 : docker_nodes(1) / compute_tasks / compute_runs / container_templates(2)
数据平台 : dp_data_sources(1) / dp_sql_queries / dp_query_history(3)
           / dp_chat_sessions(1) / dp_chat_messages(2)
知识库   : kb_libraries(4) / kb_data_assets / kb_code_repos
           / kb_documents / kb_experiences / kb_tags
LLM      : llm_configs(2)
+ 25 张第一批已删但被 create_all 重建的空壳
```
**结果**：DB **53 张 → 4 张**（`users` / `roles` / `user_roles` / `audit_logs`），零孤儿零缺失

累计两批共 **DROP 88 张表**。

### API 端点变更
- ❌ 删除：`/api/v1/{experts, experts/skill-mcp, compute, data-platform, knowledge-base, llm}/*`
- ✅ 保留：`/api/v1/{auth, users, opencode}` —— **共 11 个端点**

### 验证

**后端**
```
app import ✅ · 4 张表 ✅ · 11 个端点 ✅ · 启动无错误 ✅
保留端点：/health · /auth/me · /opencode/web/status?fast=1  全 200
已删端点：/experts · /experts/skill-mcp/skills · /compute/nodes
          /data-platform/sources · /knowledge-base/libraries · /llm  全 404
pytest: 25 passed / 0 failed  ← 从长期的 34 failed 变成全绿
残留扫描：expert_service / skill_service / mcp_service / docker_node / kb_service
          / dp_chat / llm_config / sql_guard / crypto / connectors / seed_* / schema_patch
          → 全部 0 处引用 ✅
```

**前端**
```
npx tsc -b        → 0 error
npm run build     → ✓ built in 208ms
构建产物：8MB（含 6.9MB monaco worker）→ 单个 1.1MB（gzip 369KB）
构建时间：914ms → 208ms
```

**Playwright e2e 全绿**（`/tmp/final.png`）
```
1) 登录 → 默认落地 /aide                     ✅
2) 菜单 = [AIDE, 用户管理]                    ✅ 与预期完全一致
3) 11 条死路由全部重定向到 /aide              ✅
   /workspace /perception /cognition /decision /execution
   /resources /agent-platform /experts /compute
   /data-platform /knowledge-base
4) 2 个保留页面正常渲染（无白屏）              ✅
5) AIDE iframe → http://127.0.0.1:4096/       ✅
   工具条含「AIDE / 已连接 / 复用 serve」      ✅
页面错误：仅 1 个 antd 既有警告 + 2 个 403（/users，测试用户非管理员，权限系统正常）
失败请求：仅 iframe 内 opencode 自己的 SSE（正常）
```

### 过程中修掉的一个自引入回归
删 `core/crypto.py` 后从 `config.py` 移除了 `FERNET_KEY` 字段，
但 `.env` 里仍有该项 → pydantic 抛 `extra_forbidden`，全部 25 个测试变 ERROR。
**修法**：`Settings.model_config` 加 `"extra": "ignore"`，让 `.env` 里任何历史遗留项
都不会导致启动失败（比逐个声明废弃字段更健壮）。

### 项目最终形态
```
前端：AIDE（iframe 嵌 opencode Web UI）+ 用户管理
      2 个页面 · 8 个 npm 依赖 · 产物 1.1MB
后端：/api/v1/{auth, users, opencode} · 11 个端点 · 4 张表 · 15 个依赖
测试：pytest 25 passed / 0 failed · tsc 0 error
```

### 代码量变化（两批累计）
| | 第一批前 | 第一批后 | 第二批后（当前） |
|---|---|---|---|
| 后端文件 | — | -58 | **-79（再删）** |
| 前端页面目录 | 11 | 5 | **2** |
| API 路由域 | 15 | 8 | **3** |
| API 端点 | ~200 | ~90 | **11** |
| 数据库表 | 63 | 24 | **4** |
| 前端 npm 依赖 | 19 | 12 | **8** |
| 后端 pip 依赖 | 30+ | 30+ | **15** |
| 构建产物 | ~8MB | ~8MB | **1.1MB** |
| pytest | 34 failed | 27 failed | **0 failed** |

### 补充清理（同批次收尾）

盘点后又发现一批孤儿，一并清掉：

**前端**
- `presets/agentLoopers.ts`（Agent Looper 预设）
- `types/{agent,agentLooper,dataPlatform,knowledgeBase,index}.ts` — 只剩 `types/user.ts` 有人用
- `stores/appStore.ts` — 零引用
- **`tests/` 整目录**：15 个 spec（`dp-*` 5 个 / `kb-*` 3 个 / `perception-*` 2 个
  / `w10-*` 3 个 / `nav` / `visual/screenshots`）全部测已删模块
- `playwright.config.ts` + 卸载 `@playwright/test` + 删 `test:e2e` script

**新增前端测试** `src/__tests__/smoke.test.tsx`（**20 个**）：
- 品牌名渲染
- 菜单只有 AIDE / 用户管理两项
- **参数化断言 10 个已删模块名不应出现在菜单**（专家团/算力调度/数据平台/知识库/
  感知层/认知层/决策层/执行层/对话工作台/资源管理）
- `/aide` `/users` 正常渲染
- **参数化断言 6 条已删路由重定向到 `/aide`**

**踩坑**：React 19 + jsdom 下 antd Menu 需要 `ResizeObserver`，
`test-setup.ts` 补了 stub 才跑通（报错信息里 `AggregateError` 会掩盖真实原因，
要往下翻才看到 `ResizeObserver is not defined`）。

### 最终文件数
```
后端 app/     33 个 .py
前端 src/     26 个文件
前端依赖      8 dependencies / 13 devDependencies
后端依赖      15 个
```

### 最终验证（全绿）
```
后端 pytest    25 passed / 0 failed
前端 vitest    20 passed / 0 failed
前端 tsc       0 error
前端 lint      0 error（2 个 fast-refresh warning）
前端 build     ✓ 217ms · 1.1MB
e2e            5 组全绿
```

---

## 2026-08-12

### Agent: DataOps 数据仓库（数据源 / 元数据 / 样例）

### 目标
资产地图「数据仓库」：添加数据源（Doris/MySQL/Hive 配置）、原始元数据探查、5–10 行样例查询；联调 Doris 10.18.1.249:9031。

### 决策
- UI：左侧源列表 + 右侧三段式（连接 / 元数据 / 样例），简约大气
- Doris/MySQL 走 pymysql；Hive 可登记，探活后续
- 凭据写 backend/.env（密码含 # 需引号），启动种子幂等入库；不提交真实密码

### 新增
- backend: data_source_model / repo / dataops_connector / dataops_service / api/v1/dataops
- frontend: WarehousePage + dataops.service/types

### API
- `/api/v1/dataops/sources*` test/databases/tables/columns/sample

### 验证
- 探活 ok ~34ms；tmp 库 33 表；DESCRIBE + LIMIT 样例成功

---

## 2026-08-13

### Agent: 智能数开 IDE（资产地图）

### 目标
资产地图下新增「智能数开」：左 ETL SQL 文件、中 Monaco SQL 编辑器、右 OpenCode Agent；可选容器 opencode serve；窗口联动。

### 决策
- 前端直连 `@opencode-ai/sdk` → serve（需 CORS）
- 服务源：本机 4096 + `container_services` 中可达的 opencode_serve/web
- 联动：发消息附带当前 SQL；助手 ```sql``` 可写回编辑器

### 新增
- `frontend/src/pages/dataops/smart-dev/*`
- `frontend/src/services/opencodeSdk.ts`
- deps: `@opencode-ai/sdk`, `@monaco-editor/react`, `monaco-editor`
