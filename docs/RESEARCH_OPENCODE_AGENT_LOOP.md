# OpenCode Agent Loop 深度调研报告

> 调研时间：2026-07-09
> 调研方式：豆包联网搜索 + 官方文档交叉验证
> 目标：搞清如何配置 OpenCode 使其具备可持续、可控、可自恢复的 Agent Loop 能力

---

## 0. TL;DR

- **OpenCode**（`anomalyco/opencode`，前 SST 团队维护，MIT，151k+ Stars）本身是一个**可脚本化的 CLI/TUI Agent runtime**，天然具备"主 Agent + 子 Agent + 工具调用 + 会话隔离"的能力，属于"每一步都要人确认"的**同步反应式循环**。
- OpenCode 自身**并不内置无限 loop**，若要实现 Claude Code 官方 `/ralph-loop` 那种"设完目标就走开"的自动闭环，需要靠 **Plugin + `session.idle` 事件钩子**主动重新 `promptAsync` 续跑。
- 主流做法有 3 类：
  1. **官方原生**：Primary Agent（build/plan）+ Subagent（general/explore/scout）编排，配 AGENTS.md 做长期记忆。
  2. **插件式 Loop**：`@felipejesus/openloop`、`opencode-goal-plugin`、`@heimoshuiyu/opencode-goal-plugin` 等，监听 `session.idle` 自动 continue，直到检测到 `DONE` / `COMPLETE` 标记。
  3. **外挂 Ralph Loop**：用 `tmux + ralphy-cli` 或裸 shell `while` 循环反复起干净会话（原生 Ralph 范式）。
- **推荐组合（生产落地）**：
  `opencode.json` 定义 primary/subagent 权限矩阵 + `AGENTS.md` 长期规则 + Skills 可复用工作流 + `openloop` 插件做 `session.idle` 续跑 + 明确 "COMPLETE promise" 退出条件 + max iterations 熔断。

---

## 1. 背景与概念对齐

### 1.1 什么是 OpenCode

- 开源终端 AI 编程 Agent，由 anomalyco（原 SST 团队）2025 年 4 月发布，MIT 协议，截至 2026 年中 Star 已破 170k。
- 特点：
  - **Provider-agnostic**：75+ 模型提供商（Anthropic / OpenAI / Gemini / GLM / Kimi / DeepSeek / Qwen / Ollama…）都能通过 `opencode.json` 或 OpenAI-compatible endpoint 接入。
  - **原生 LSP 集成**：Agent 借助语言服务器直接理解符号表。
  - **Plan / Build 双主 Agent 模式**：Tab 切换只读规划 / 全权限执行。
  - **可脚本化 CLI + TUI + Web/Server + GitHub Actions + ACP server**，可作为 embeddable runtime。

### 1.2 什么是 Agent Loop

在 Coding Agent 语境里，"Agent Loop" 有三层含义：

| 层次 | 含义 | 代表 |
|---|---|---|
| **单轮循环** | 一次 prompt → 模型思考 → 调工具 → 观察结果 → 继续思考，直到本次任务结束 | ReAct 循环、OpenCode 单条消息内的默认行为 |
| **会话内自动续跑** | 模型自认为"完成"想停下，但外层判定"没做完"，强制它继续 | Claude Code `/ralph-loop`、OpenCode `openloop` 插件 |
| **多会话跨迭代** | 每次迭代都开一个**干净上下文**的新会话，从磁盘（PROMPT.md / AGENTS.md / IMPLEMENTATION_PLAN.md）读取进度 | Ralph Wiggum / Ralph Loop 原始范式（Geoffrey Huntley 提出） |

OpenCode 原生只支持第 1 层；第 2、3 层需要 Plugin 或外挂脚本实现。

---

## 2. OpenCode 核心概念速查

### 2.1 Agent 分类

| 类型 | 内置项 | 作用 | 默认权限 |
|---|---|---|---|
| **Primary Agent** | `build`（默认） | 全工具开放的开发主 Agent | 全部 allow |
| **Primary Agent** | `plan` | 只读分析 / 规划模式 | edit/bash 均 `ask` |
| **Subagent** | `general` | 多步任务通用型，可修改文件（除 todo 外全工具） | 完整 |
| **Subagent** | `explore` | 只读代码库探索，快速找文件/搜关键字 | 只读 |
| **Subagent** | `scout` | 只读外部文档/依赖研究，把依赖仓库 clone 进托管缓存 | 只读 |
| 隐藏系统 Agent | `compaction` / `title` / `summary` | 上下文压缩、标题、摘要 | 系统内部 |

**关键价值**：Subagent 在**独立子会话**里跑，不污染主对话，是**省 Token + 结果精炼**的核心手段。

### 2.2 会话导航

- `Tab`（或自定义 `switch_agent`）：主 Agent 间循环
- `<Leader>+Right` / `session_child_cycle`：父 → 子1 → 子2 → 父
- `<Leader>+Left` / `session_child_cycle_reverse`：反向
- CLI 子会话管理：`/agents list` | `/agents kill <id>` | `/agents save <id> <name>`

### 2.3 记忆体系（Context Engineering）

| 类型 | 存放位置 | 作用 |
|---|---|---|
| **短期上下文** | 当前会话 | 任务现场、对话历史、工具输出 |
| **长期规则** | `AGENTS.md`（项目根） / `~/.config/opencode/AGENTS.md`（全局） | 项目/团队约定、构建命令、代码风格；每次会话开始自动加载 |
| **项目知识** | Skills / MCP / 外部索引 | 按需检索，不塞进上下文 |

加载优先级：
1. 项目根 `AGENTS.md`（最高，也兼容 `CLAUDE.md`）
2. 全局 `~/.config/opencode/AGENTS.md`
3. `opencode.json` 中 `instructions` 数组显式追加

**首次进入项目**：`/init 用中文生成` → OpenCode 扫描目录、识别框架/包管理器 → 自动写入 `AGENTS.md`（已有则追加）。

---

## 3. 配置文件详解

### 3.1 `opencode.json` 骨架

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "small_model": "anthropic/claude-haiku-4-5",

  "instructions": ["AGENTS.md", "~/.mempalace/identity.txt"],

  "agent": {
    "build": {
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/build.txt}",
      "permission": { "edit": "allow", "bash": "allow" }
    },
    "plan": {
      "mode": "primary",
      "model": "anthropic/claude-haiku-4-20250514",
      "permission": { "edit": "deny", "bash": "deny" }
    },
    "code-reviewer": {
      "mode": "subagent",
      "description": "Reviews code for best practices and potential issues",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "You are a code reviewer. Focus on security, performance, maintainability.",
      "permission": { "edit": "deny" }
    }
  },

  "mcp": {
    "context7": { "type": "remote", "url": "https://mcp.context7.com/mcp", "enabled": true }
  },

  "lsp": {
    "typescript": {
      "command": ["typescript-language-server", "--stdio"],
      "extensions": [".ts", ".tsx", ".js", ".jsx"]
    }
  },

  "plugin": ["@felipejesus/openloop"]
}
```

### 3.2 Markdown Agent（推荐团队协作）

放在：
- 项目：`.opencode/agents/<name>.md`
- 全局：`~/.config/opencode/agents/<name>.md`

示例 `~/.config/opencode/agents/review.md`：
```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
tools:
  write: false
  edit: false
permission:
  edit: deny
---

You are in code review mode. Focus on:
- Code quality
- Potential issues
- Security concerns
```

### 3.3 CLI 无交互创建 Agent

```bash
opencode agent create \
  --path ./.opencode/agent \
  --description "Security auditor" \
  --mode subagent \
  --permissions bash,read,grep,glob,lsp \
  --model anthropic/claude-sonnet-4-20250514
```

可用 permissions：`bash, read, edit, glob, grep, webfetch, task, todowrite, websearch, lsp, skill`。**不写就是拒绝**。同时指定 `--path --description --mode --permissions` 时命令非交互执行。

---

## 4. 让 OpenCode 跑起来 Agent Loop 的三种范式

### 4.1 范式 A：原生主/子 Agent 编排（最稳）

**思想**：不追求"无限 loop"，而是把大任务拆成"主 Agent 决策 + 多子 Agent 并行做事"，一次交互内闭环。

- 主 Agent 用 `build` 或自定义 primary，**只负责路由，不直接写代码**。
- 规划 Agent（`plan` 或自定义只读 subagent）**只读拆方案**。
- 执行 Agent（`general` 或自定义写权限 subagent）改代码 + 跑验证命令。
- 审查 Agent（`code-reviewer`，独立上下文、只读 subagent）看 diff。
- 探索 Agent（`explore`）只读检索，把"读"的 Token 消耗隔离在子会话。

**手动调用**：`@explore 找 JWT 鉴权相关代码`、`@code-reviewer 审这个 PR`。
**自动委派**：主 Agent 根据每个 subagent 的 `description` 自动路由。

**代表插件**：`@zcy2nn/agent-forge`、`oh-my-opencode`（内置 Sisyphus 主智能体 + oracle/librarian/explore/frontend/document-writer/multimodal-looker 等）。

### 4.2 范式 B：Plugin + `session.idle` 续跑（推荐）

**思想**：会话空闲即视为"这一轮 AI 觉得做完了"；插件读取"目标"，判定是否真的完成，没完成就 `client.promptAsync(继续)`。

#### 4.2.1 `@felipejesus/openloop`

```jsonc
{ "$schema": "https://opencode.ai/config.json", "plugin": ["@felipejesus/openloop"] }
```

行为：
- `/ralph-loop <目标>` 开启自动续跑
- `/cancel-ralph` 停止
- `/ralph-help` 快查
- 状态存于 `.opencode/ralph-loop.local.md`
- 监听 `session.idle`，检查最后一条 assistant 回复，未完成就续跑

用法示例：
```
/ralph-loop 请完整地完成阶段 6 的所有任务：安全、管理后端、用户手册、源码阅读指南。全部完成后输出 DONE。
```

#### 4.2.2 `@heimoshuiyu/opencode-goal-plugin`

结构化目标流水线：
```
用户 /goal <目标>
  ↓
plugin.tool.create(objective, completion_criterion)
  ↓
监听 session.status → idle
  ↓
读 Session.metadata.goal → 若 active，client.promptAsync(continuationPrompt)
  ↓
直到 Agent 自己调 goal.complete 或达到 max iterations
```

支持 `create / get / update / complete / cancel` 五种 tool 操作，可挂完成条件（如 "所有测试通过 + coverage>80%"）。

#### 4.2.3 Plugin 生态一览

| 插件 | 作用 |
|---|---|
| `@felipejesus/openloop` | 最小可用的 ralph-loop 端口 |
| `@heimoshuiyu/opencode-goal-plugin` | 结构化 goal 对象 + 完成条件裁判 |
| `opencode-cc-hooks` | 兼容 Claude Code 的 hooks（PreToolUse / PostToolUse / UserPromptSubmit / Stop / PreCompact） |
| `opencode-yaml-hooks` | 用 `hooks.yaml` 定义 tool/session 生命周期的 shell/lint/test 联动 |
| `opencode-mempalace-persistence` | 每轮结束把对话切分入向量库，跨会话长期记忆 |
| `opencode-cmem` | 与 Claude Code 的 claude-mem worker 共享长期记忆 DB |
| `opencode-vibe-webhook` | 会话事件转 Slack / 自定义 Webhook |

### 4.3 范式 C：外挂 Ralph Loop（多会话 + 干净上下文）

**核心洞察**（Geoffrey Huntley, 2025-07 提出）：
> 长时会话必然被冗余 diff/日志/reasoning 污染，与其让 Agent 一次 session 内挣扎 8 小时，不如**每次迭代都开新会话**，把状态落地到磁盘（`PROMPT.md / AGENTS.md / IMPLEMENTATION_PLAN.md / specs/*.md`）。

极简 shell 版：
```bash
#!/bin/bash
MAX_ITERATIONS=${1:-10}
for ((i=1;i<=MAX_ITERATIONS;i++)); do
  echo "=== Iter $i ==="
  opencode run --model anthropic/claude-sonnet-4-5 "$(cat PROMPT.md)"
  grep -q '<promise>COMPLETE</promise>' .ralph/last_output && break
done
```

进阶版（`ralphy-cli` + tmux 常驻）：
```bash
tmux -S ~/.tmux/sock new -d -s my-task \
  "cd /path/to/repo && ralphy --opencode 'Fix the authentication bug'; \
   EXIT_CODE=$?; echo EXITED: $EXIT_CODE; sleep 9999"
```
`ralphy-cli` 自动做 tmux 会话恢复、退出通知（可选接 openclaw system event 推 Slack）。

**关键要素**：
- 明确任务定义（PRD 级 `PROMPT.md`）+ 可验证完成条件（如 `<promise>COMPLETE</promise>` 承诺字符串）
- Stop hook：拦截 Agent 的\"我做完了"退出信号
- max-iterations 熔断：防止 Token 无底洞
- 上下文隔离：每轮新 session，只从磁盘读进度

---

## 5. Plugin 开发：让 Loop 逻辑 100% 自主可控

### 5.1 Plugin 加载顺序

1. 全局配置：`~/.config/opencode/opencode.json`
2. 项目配置：`opencode.json`
3. 全局插件目录：`~/.config/opencode/plugins/`
4. 项目插件目录：`.opencode/plugins/`

同名同版本 npm 包只加载一次；同名的本地 + npm 插件会分别加载。

### 5.2 Plugin 骨架

```ts
// .opencode/plugins/my-loop.ts
export const MyLoopPlugin = async ({ project, client, $, directory, worktree }) => {
  let iterations = 0
  const MAX = 30

  return {
    event: async ({ event }) => {
      if (event.type !== "session.idle") return
      if (iterations++ >= MAX) return
      const last = await client.session.lastMessage(event.sessionId)
      if (/<promise>COMPLETE<\/promise>/.test(last?.text ?? "")) return
      await client.session.promptAsync(event.sessionId, {
        text: "继续。若真的完成请输出 <promise>COMPLETE</promise>。",
      })
    },
  }
}
```

### 5.3 可订阅事件（部分）

- **命令**：`command.executed`
- **文件**：`file.edited`、`file.watcher.updated`
- **安装**：`install.*`
- **权限**：`permission.asked`、`permission.replied`
- **服务器**：`server.connected`
- **会话**：`session.created`、`session.compacted`、`session.deleted`、`session.diff`、`session.error`、**`session.idle`**、`session.status`、`session.updated`
- **待办**：`todo.updated`
- **Shell**：`shell.env`
- **工具**：`tool.execute.before`（可拦截修改参数）、`tool.execute.after`
- **TUI**：`tui.prompt.append`、`tui.command.execute`、`tui.toast.show`
- **实验**：`experimental.session.compacting`

### 5.4 依赖管理

在 `.opencode/package.json` 声明依赖，OpenCode 启动时自动 `bun install`：
```json
{ "dependencies": { "shescape": "^2.1.0" } }
```

---

## 6. Skills：可复用的\"工作流即代码"

- 全局：`~/.config/opencode/skills/<name>/SKILL.md`
- 项目：`.opencode/skills/<name>/SKILL.md`
- 兼容路径：`.claude/skills/*`、`.agents/skills/*`

SKILL.md frontmatter 支持 `description / triggers / tools` 等字段，主 Agent 通过内置 `skill` 工具**按需加载**，不预塞入上下文。跨 Agent 复用最省 Token。

推荐迁移方式：`npx skills update` 统一管理（The Agent Skills Directory）。

---

## 7. 常用 Slash Commands

| 命令 | 功能 | 快捷键 |
|---|---|---|
| `/init` | 分析项目，创建/追加 `AGENTS.md` | `Ctrl+X i` |
| `/connect` / `opencode auth login` | 配置 LLM Provider | - |
| `/models` | 查看/切换模型 | `Ctrl+X m` |
| `/compact` | 压缩当前会话上下文 | `Ctrl+X c` |
| `/new` | 开启新会话 | `Ctrl+X n` |
| `/undo` / `/redo` | 撤销/恢复 Agent 变更 | `Ctrl+X u` / `r` |
| `/share` | 分享对话 | - |
| `/export` | 导出会话为 Markdown | `Ctrl+X x` |
| `/thinking` | 切换思考块显示 | - |
| `Tab` | 切换 Plan/Build 主 Agent | - |
| `@agentName …` | 手动调 subagent | - |
| `@src/index.ts` | 引入文件到上下文 | - |
| `!git status` | 执行 shell（结果作为工具输出） | - |

---

## 8. 生产级参考架构

```
┌──────────────────────────────────────────────────────────────┐
│                    opencode.json (根配置)                     │
│  model / small_model / instructions / mcp / lsp / plugin     │
└───────────────────┬──────────────────────────────────────────┘
                    │
     ┌──────────────┼───────────────┬────────────────┐
     ▼              ▼               ▼                ▼
 AGENTS.md      .opencode/       .opencode/      .opencode/
 (长期规则)      agents/         skills/         plugins/
                (角色定义)       (工作流)         (loop/hooks)
                    │               │                │
                    ▼               ▼                ▼
        ┌──────────────────────────────────────────────┐
        │                Primary Agents                │
        │      build (全权)   |   plan (只读)          │
        └──────────────┬───────────────────────────────┘
                       │ Task tool / @ mention
     ┌─────────────────┼──────────────────┐
     ▼                 ▼                  ▼
 explore(只读)   general(可写)     code-reviewer(只读)
 (调研/找文件)   (执行/验证)       (审 diff)
                       │
                       ▼
              openloop plugin
        监听 session.idle → 未 COMPLETE → 继续 prompt
                       │
                       ▼
              opencode-yaml-hooks
     tool.execute.after → 自动 lint/test/git commit
```

### 8.1 落地清单（Checklist）

1. **装 & 认证**
   ```bash
   curl -fsSL https://opencode.ai/install | bash    # 或 brew install anomalyco/tap/opencode
   opencode auth login                              # 选 provider 填 key
   opencode models --refresh
   ```

2. **项目初始化**
   ```
   cd your-project
   opencode
   /init 用中文生成
   ```
   审阅 `AGENTS.md`，补上项目铁律（构建命令、测试命令、必守规范）。

3. **写 `opencode.json`**（见 §3.1）：至少定义 build/plan/code-reviewer 三个 agent + 常用 MCP + LSP。

4. **装 loop 插件**：
   ```jsonc
   { "plugin": ["@felipejesus/openloop"] }
   ```

5. **写\"完成条件"**：在提示词末尾强制 `<promise>COMPLETE</promise>` 输出承诺 + 客观校验（测试通过 / lint 通过）。

6. **加熔断**：插件里 `MAX_ITERATIONS`（默认 20~50）+ token 预算监控。

7. **加通知**：`opencode-vibe-webhook` 或 macOS `osascript` 通知，避免\"AI 在跑但你不知道"。

### 8.2 团队场景权限矩阵建议

| Agent | mode | edit | bash | webfetch | 备注 |
|---|---|---|---|---|---|
| build | primary | allow | ask | allow | 默认主 Agent |
| plan | primary | deny | deny | allow | 只读规划 |
| general | subagent | ask | ask | allow | 通用兜底 |
| explore | subagent | deny | deny | allow | 只读检索 |
| scout | subagent | deny | deny | allow | 外部依赖研究 |
| code-reviewer | subagent | deny | deny | deny | 独立上下文只看 diff |
| batch-mechanical | subagent | ask | ask | deny | 低风险机械修改 |

---

## 9. Loop 相关最佳实践与坑

### 9.1 最佳实践

- **任务定义具体到 PRD 级**：Ralph Loop 原始作者 Geoffrey Huntley 强调：\"AI 循环失败 90% 是需求写得不够精确"。
- **完成条件二元化**：让\"是否完成"变成一段可 grep 的字符串 / 一个测试命令的 exit code，不要让 AI 自我判断。
- **上下文隔离**：能用 subagent / 新 session 就别塞进主对话，尤其是探索性 Read。
- **Token 预算前置**：跑 loop 前先 `npx @cobusgreyling/loop-cost` 或粗算，L1（只报告不改）先试跑一夜。
- **分级验证**：常规 Review → 自动验证 + 代码审查；风险等级 → 自动验证 + 人工重点审查 + 灰度。
- **审查 Agent 独立上下文**：只喂 diff + 验证结果，绝不复用执行 Agent 的会话。

### 9.2 常见坑

- **无限循环烧 Token**：必设 `max_iterations`；配额告警接 Webhook。
- **上下文污染导致\"越跑越蠢"**：长任务第 5 轮后单会话准确率下降 ~37%（社区实测），务必 `/compact` 或换 Ralph 多会话模式。
- **`AGENTS.md` 变成\"垃圾场"**：只放**项目铁律**，团队约定，用 Git 版本化；项目知识走 Skills / MCP 检索。
- **主 Agent 直接写代码**：路由与执行不分离，等于放弃了 Agent 分工的所有价值。
- **迁移工具 subagent 报错**：从 iFlow / Claude Code 迁 subagent md 到 `~/.config/opencode/agents/` 时，注意：
  - `model:` 字段不能空
  - `color:` 需改成 16 进制并加引号（`"#3366ff"`）

---

## 10. 与其它 Coding Agent 的对比

| 特性 | OpenCode | Claude Code | Codex CLI | Gemini CLI |
|---|---|---|---|---|
| 完全开源 | ✅ | ❌ | ❌ | ❌ |
| 多模型支持（75+） | ✅ | ❌ | ❌ | ❌ |
| Plan/Build 模式 | ✅ | ✅ | ❌ | ❌ |
| LSP 原生集成 | ✅ | ❌ | ❌ | ❌ |
| MCP 支持 | ✅ | ✅ | ❌ | ✅ |
| GitHub Actions 集成 | ✅ | ❌ | ❌ | ❌ |
| 远程 attach / Web UI | ✅ | ❌ | ❌ | ❌ |
| 原生 `/ralph-loop` | ❌ (需插件) | ✅ (官方 plugin) | ✅ (`/goal`) | ❌ |
| Hook 生命周期 | ✅ (Plugin) | ✅ | 部分 | ❌ |

**结论**：OpenCode 是目前**可定制化最强、可嵌入 runtime 最完整**的开源方案，Loop 能力靠社区插件补齐，但换来的是模型/上下文/权限的完全自主。

---

## 11. 关键参考资料

### 官方
- OpenCode 中文文档 - Agents：https://opencode.doczh.com/docs/agents/
- OpenCode 官方 Agents：https://opencode.ai/docs/en/agents/
- OpenCode 中文 CLI：https://open-code.ai/zh/docs/cli
- OpenCode 中文 Plugins：https://open-code.ai/zh/docs/plugins
- OpenCode Rules：https://opencode.ai/docs/zh-cn/rules/

### 插件
- `@felipejesus/openloop`：https://www.npmjs.com/package/@felipejesus/openloop
- `@heimoshuiyu/opencode-goal-plugin`：https://www.npmjs.com/package/@heimoshuiyu/opencode-goal-plugin
- `opencode-cc-hooks`：https://www.npmjs.com/package/opencode-cc-hooks
- `opencode-yaml-hooks`：https://www.npmjs.com/package/opencode-yaml-hooks
- `opencode-cmem`：https://www.npmjs.com/package/opencode-cmem
- `opencode-vibe-webhook`：https://www.npmjs.com/package/opencode-vibe-webhook
- `@zcy2nn/agent-forge`：https://www.npmjs.com/package/@zcy2nn/agent-forge

### Ralph Loop 范式
- Thoughtworks Tech Radar - Ralph loop：https://www.thoughtworks.com/en-es/radar/techniques/ralph-loop
- Coding Agent Loops (ralphy-cli)：https://m.php.cn/ai/2942
- 从 ReAct 到 Ralph Loop：https://www.toutiao.com/group/7599589996558828084/
- 拉爆官方 ralph loop：https://www.aitntnews.com/newDetail.html?newId=21877

### 实战文章
- 阿里云开发者社区 - OpenCode 完整配置指南：https://developer.aliyun.com/article/1742729
- 阿里云开发者社区 - 14 个社区插件 + 6 个实战案例：https://developer.aliyun.com/article/1744780
- SegmentFault - 151k Stars 的终端编程 Agent：https://segmentfault.com/a/1190000047737134
- 掘金 - 多模型路由与工程化治理：https://juejin.cn/post/7654899838613913615
- 掘金 - OpenCode 源码解析 Step 3：https://juejin.cn/post/7617796378902790159
- 博客园 - 第六章 Agent 与子代理自定义：https://www.cnblogs.com/znlgis/p/20298812
- 夜雨聆风 - Subagents 生态与工具版图：https://www.yeyulingfeng.com/413569.html

---

## 12. 给 ontomind 项目的落地建议（可选）

结合当前仓库结构（`backend/` + `frontend/` + `docs/` + docker-compose），建议：

1. **在项目根**新增 `opencode.json`：定义 `plan / build / db-migrator / api-tester / frontend-ui / doc-writer` 六个 agent，`db-migrator` 独占 `sql/migration/**` 写权限。
2. **`AGENTS.md`** 已存在 `AGENT_LOG.md`，可迁移/合并为标准 `AGENTS.md`（放构建命令 + 数据库迁移路径 + 前后端联调命令 + 硬约束）。
3. **`.opencode/plugins/ontomind-loop.ts`**：自定义 `session.idle` 插件，检测本仓库特有的完成条件（如 `pytest && vitest && docker compose config` 全通过）。
4. **CI 侧**：用 `opencode run` 无头执行 subagent，做每日巡检（daily-triage L1 只读）。
5. **通知**：结合团队现有 Slack/飞书 Webhook，用 `opencode-vibe-webhook` 或裸插件推送 `session.idle` / `session.error`。

以上落地方案能在**不改现有代码**的前提下，为 ontomind 提供\"日常 Agent 编程 + 夜间无人值守 Ralph 循环推进"的双通道能力。
