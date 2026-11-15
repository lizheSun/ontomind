# 贡献指南

> 本文面向**参与 OntoMind 开发的人**（含编码 Agent）。  
> 仓库技术细节与踩坑清单见 [AGENTS.md](./AGENTS.md)，当前进度快照见 [AGENT_LOG.md](./AGENT_LOG.md)。

## 1. 开始之前

新加入请按这个顺序读，能省掉大量误解：

1. [README.md](./README.md) — 产品定位：OntoMind 是 Agent 应用的「设计车间」
2. [HANDOFF.md](./HANDOFF.md) — 交接状态
3. [AGENT_LOG.md](./AGENT_LOG.md) — 先看「当前快照」，再看最近几条
4. [AGENTS.md](./AGENTS.md) — 技术栈版本、非常规约定、常用命令

> ⚠️ 历史文档里的「只有 4 张表」「只有 AIDE」等描述已过期，**以代码和上述文件为准**。

## 2. 分支模型

`main` 是唯一长期分支，始终保持可运行。所有改动走分支 + PR：

```bash
git checkout main && git pull
git checkout -b <type>/<short-slug>
```

分支名用 `<type>/<简短描述>`，与提交类型保持一致：

| 类型 | 用途 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat/ontology-graph-editor` |
| `fix` | 缺陷修复 | `fix/kanban-drag-crash` |
| `docs` | 只改文档 | `docs/contributing` |
| `refactor` | 不改行为的重构 | `refactor/agent-factory-split` |
| `chore` | 构建、依赖、脚本 | `chore/bump-fastapi` |

## 3. 提交信息

采用 Conventional Commits，可用 scope 标注所属域：

```
<type>(<scope>): <一句话说清做了什么>
```

```
feat(dataops): Wiki 知识库支持按标签过滤
fix(auth): 刷新 token 时未清除旧会话
docs: 补贡献指南
```

- 标题用祈使句，不加句号，不超过 50 字
- 一个提交只做一件事；格式化改动单独提交，不要混进功能提交
- 需要展开说明时在空行后写正文，解释**为什么**改，而不是重复改了什么

## 4. 提交前自检

后端：

```bash
cd backend
pytest                 # 当前基线：108 passed，不允许下降
```

前端：

```bash
cd frontend
npm run lint           # 用 oxlint，不是 eslint
npm run build          # 确认类型检查与构建通过
```

文档类改动（只动 `*.md`）可跳过测试，但需自查链接是否有效。

## 5. 提 PR

```bash
git push -u origin <branch>
gh pr create --base main --title "docs: 补贡献指南" --body "..."
```

PR 描述建议包含三部分：

- **做了什么** — 改动的范围
- **为什么** — 关联的 issue（写 `Closes #123` 可自动关闭）
- **怎么验证** — 跑了什么命令、看到什么结果

PR 保持小而聚焦。一个大改动拆成多个可独立评审的 PR，比一个巨型 PR 更容易通过。

## 6. 代码约定速查

| 项 | 约定 |
|---|---|
| 后端框架 | FastAPI + SQLAlchemy 2.0（DeclarativeBase）+ Pydantic v2 |
| 数据模型 | 新增表后同步更新 `app/db/models/__init__.py`（ORM 表清单的权威来源） |
| 接口路径 | `/api/v1/<域>/...`，域与后端路由保持一致 |
| 前端 lint | `oxlint`（**不是** eslint） |
| 前端框架 | React 19 + TypeScript + Vite + antd v6 + Zustand |
| 主题 | Yao Agents CUI：Outfit 字体、`#3371fc`、64px 图标轨、256px 上下文栏 |

改到数据模型、接口契约或主题规范时，请同步更新 `AGENTS.md` 对应段落，避免下一个人被旧信息误导。

## 7. 文档改动同样走 PR

`README.md` / `AGENTS.md` / `HANDOFF.md` / `AGENT_LOG.md` 是团队的共识载体，改动同样需要评审。  
`AGENT_LOG.md` 按时间倒序追加，不删除历史条目。
