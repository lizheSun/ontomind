# T58 · Zen/God 双模式 + 渐进式披露

## Goal
全局 toggle（右上角眼睛图标）。Zen 模式：简洁卡片，隐藏 JSON / 日志 / 技术细节。God 模式：显示所有原始数据。每个卡片可独立翻转。persist 到 localStorage。渐进式披露：高级功能默认折叠，触发条件才展示。

## Files touched
- `frontend/src/stores/uiModeStore.ts` (NEW — Zen/God 全局状态)
- `frontend/src/components/ZenGodToggle.tsx` (NEW — 眼睛图标 toggle)
- `frontend/src/components/FlipCard.tsx` (NEW — 卡片翻转组件)
- `frontend/src/components/ProgressiveDisclosure.tsx` (NEW — 触发式披露)
- `frontend/src/hooks/useUIMode.ts` (NEW)
- `frontend/src/pages/resources/**` (改造关键卡片使用 FlipCard)
- `frontend/src/pages/agent-jobs/**` (改造 JobDetail)
- `frontend/src/layouts/HeaderBar.tsx` (挂载 ZenGodToggle)
- `frontend/src/components/__tests__/FlipCard.test.tsx`
- `frontend/src/components/__tests__/ZenGodToggle.test.tsx`
- `.blueprint/qa/T58/vitest.txt`

## Depends on
- T49, T50, T51, T52, T55

## UX 规格
1. 顶部导航栏眼睛图标：Zen=闭眼，God=睁眼
2. 全局切换：所有 FlipCard 同步翻转
3. 单卡翻转：点击卡片右上角小按钮，仅当前卡切换
4. 渐进式披露：`useCount >= threshold` 时才显示高级面板
5. 状态持久化：`localStorage.uiMode = 'zen'|'god'` + 卡片级 override

## Acceptance
- 全局切换正常
- 单卡翻转独立于全局
- localStorage 读写正确
- 渐进式披露基于 usage 计数

## Verify
```bash
cd frontend
npm run test -- FlipCard ZenGodToggle
```

## Commit
`feat(ux): zen/god dual mode with flip cards and progressive disclosure`
