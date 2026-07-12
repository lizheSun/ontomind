APPROVE

## Verdict
APPROVE

## Reasoning
- App.tsx: 10 new eager imports (2 index + 8 pages) added; 9 new `<Route>` entries inserted inside the existing `ProtectedRoute><AppLayout />` block (line 111 range), directly above the `path="*"` catch-all.
- App.tsx: `<ConfigProvider theme={...}>`, existing routes (dashboard/perception/cognition/decision/execution/application/resources/projects/users), and catch-all `<Route path="*" element={<Navigate to="/" replace />} />` untouched.
- AppLayout.tsx: `DatabaseOutlined` + `BookOutlined` imported from `@ant-design/icons`; `topMenuItems` grew from 9→11; new items placed at index 2 and 3 — after `/perception`, before `/cognition`. Menu remains flat (no `children`).
- All 7 stub pages compose `PageHeader + GlassPanel` from `../../components/common` with the exact Chinese titles/subtitles from the spec table (数据平台·数据源, 数据源详情, 数据资产, 代码库, 文档库, 业务经验库, 知识库搜索).
- Both index files use `<Navigate to="..." replace />` from `react-router-dom`. No new deps. QA evidence `nav.txt` shows home/dp/vite all 200 and tsc in-scope empty.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- Consider extracting the shared stub body into a `<StubPage />` component in a future pass to remove the 7× duplicated JSX — fine to defer since these are placeholders replaced by T21–T24.
