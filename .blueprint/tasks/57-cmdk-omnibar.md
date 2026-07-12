# T57 · Cmd+K 全能搜索栏

## Goal
全局热键（Cmd+K / Cmd+Space）打开 Omnibar。三模式：Search（搜索节点/容器/智能体/Skill/MCP）、Assist（自然语言 → 执行操作）、Act（快速操作：创建 agent / 运行测试 / 发现配置）。上下文感知：在资源页默认搜索资源，在数据页搜索数据源。

## Files touched
- `frontend/src/components/CmdKOmnibar/index.tsx` (NEW)
- `frontend/src/components/CmdKOmnibar/SearchMode.tsx` (NEW)
- `frontend/src/components/CmdKOmnibar/AssistMode.tsx` (NEW)
- `frontend/src/components/CmdKOmnibar/ActMode.tsx` (NEW)
- `frontend/src/components/CmdKOmnibar/hooks/useHotkey.ts` (NEW)
- `frontend/src/components/CmdKOmnibar/hooks/useContextAware.ts` (NEW)
- `frontend/src/components/CmdKOmnibar/registry.ts` (NEW — 操作注册表)
- `frontend/src/components/CmdKOmnibar/index.less` (NEW)
- `frontend/src/App.tsx` (挂载全局 Omnibar)
- `backend/app/api/v1/search.py` (NEW — 统一搜索接口 `POST /search`)
- `backend/app/services/unified_search_service.py` (NEW)
- `frontend/src/components/CmdKOmnibar/__tests__/index.test.tsx`
- `.blueprint/qa/T57/vitest.txt`

## Depends on
- T49

## UX 规格
1. Cmd+K / Cmd+Space 打开；Esc 关闭
2. 顶部 Tab 切换三模式（默认按上下文选中）
3. 键盘导航：↑↓ 选择，Enter 执行
4. 结果分组：资源类型 / 页面 / 操作
5. Act 模式带确认二次弹窗

## Acceptance
- 全局热键在任意页面生效
- 三模式切换正确
- 上下文感知：`/resources` 默认 Search，`/agent-looper` 默认 Act
- 至少 15 个可执行操作注册在 registry

## Verify
```bash
cd frontend
npm run test -- CmdKOmnibar
npm run build
```

## Commit
`feat(ux): cmd+k omnibar with search/assist/act modes`
