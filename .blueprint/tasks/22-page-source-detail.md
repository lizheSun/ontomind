# T22 — /data-platform/sources/:sid detail (tabs)

## Goal
Explorer page. Left rail = SchemaTree (30% width). Right area = Tabs: SQL Editor / AI 对话 / 执行历史 / 保存的查询.

## Files touched
- `frontend/src/pages/data-platform/SourceDetailPage.tsx`  (NEW)
- `frontend/src/pages/data-platform/tabs/EditorTab.tsx`  (NEW)
- `frontend/src/pages/data-platform/tabs/ChatTab.tsx`  (NEW)
- `frontend/src/pages/data-platform/tabs/HistoryTab.tsx`  (NEW)
- `frontend/src/pages/data-platform/tabs/SavedQueriesTab.tsx`  (NEW)

## Depends on
- T08, T11, T19, T20

## Implementation notes
- EditorTab: SqlEditor (schema-aware, height=340) + ResultGrid below, Ctrl+Enter runs sync; if `row_count == max_rows` show hint "已截断至 1000 行，可切换为流式导出".
- Export button opens SSE stream to `/execute/stream` and streams into a CSV blob w/ progress bar in status bar.
- ChatTab: message list (user + assistant bubbles, code block for `generated_sql` with 复制 / 应用到编辑器 / 直接运行 buttons); input row bottom; `stream=true`; tokens append live; "应用" copies SQL into EditorTab; "直接运行" calls `apply/{message_id}`.
- HistoryTab: DataTable with 时间 / SQL 摘要 / 状态 / 行数 / 用时 / 操作 (查看 / 重跑) — 重跑 pushes SQL into EditorTab.
- SavedQueriesTab: DataTable + 收藏/取消收藏 toggle + 运行 / 编辑 / 删除.

## Acceptance
- Click table in SchemaTree → column list expands; click column → inserted into editor.
- Ctrl+Enter runs a `SELECT NOW()` and shows result.
- Chat message returns fenced SQL and populates editor.
- History tab lists the query just executed.

## Verify
```bash
cd frontend && bunx playwright test tests/e2e/dp-source-detail.spec.ts | tee ../.blueprint/qa/T22/pw.txt
```

## Commit
`ui: data source detail page (Editor/Chat/History/Saved tabs + SSE)`
