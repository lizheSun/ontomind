# Vendor / opencode packages/web components

## Source

- Repository: <https://github.com/anomalyco/opencode>
- Tag: **`v1.18.4`**
- Commit: **`49c69c5ed3ccf706b61b3febb43c8aaff7f8325e`** (2026-07-20)
- Original path: `packages/web/src/components/`
- License: **MIT** (see LICENSE next to this file)

## Why vendor instead of npm import

opencode 官方没把 web UI 组件发布成 npm 包（只发了 `@opencode-ai/sdk` 数据层）。
所以对话工作台想要"视觉贴 opencode web"，只能把组件源码搬过来，跟着上游 tag 手动同步。

## Scope isolation (Tailwind Path B)

Vendor 组件使用 Tailwind class。为了避免污染项目主体的 antd v6 样式：

1. `frontend/tailwind.config.ts` 里：
    - `content` 只匹配 `./src/features/opencode/vendor/**`
    - `corePlugins.preflight = false`（禁用会重置全局样式的 reset）
    - `important = '.oc-scope'`（生成的 utility 只在 `.oc-scope` 后代生效）
2. 所有 vendor 组件的最外层容器加 `className="oc-scope"`。
3. Vite 入口 `main.tsx` 增加 `import './features/opencode/vendor/styles/opencode.css'`。

## Sync policy

- 每季度手动 diff 一次 `opencode@<最新tag>:packages/web/src/components/` 与本目录。
- 只搬 `.tsx` 组件；`.astro` 页面壳不搬。
- 依赖第三方包（e.g. `lucide-react`）时先加进 `frontend/package.json`。

## Current status (Wave 3 交付)

**尚未导入任何 vendor 组件。**

对话工作台第一版走 antd 原生渲染（`features/opencode/components/MessagePart.tsx` 内置了
text / reasoning / tool / file 四种基础渲染），足够跑通端到端流式对话。

Wave 4 计划一次性 vendor：

- `message/{TextPart,ToolCallPart,ToolResultPart,FilePart,ReasoningPart,StepStart,StepFinish}.tsx`
- `markdown/MarkdownRenderer.tsx`
- `diff/DiffView.tsx`
- `command/CommandPalette.tsx`
- `mention/FileMention.tsx`
- `model/ModelSwitcher.tsx`

Wave 4 落地时会重写 `MessagePart.tsx` 内部实现为委托到 vendor 组件（对外 API 保持稳定）。
