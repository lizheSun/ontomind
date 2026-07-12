# T32 · Frontend smart-add UI (SourceFormDrawer integration)

## Goal
Add "智能添加" button to SourcesListPage. Opens Modal → user pastes natural language → calls parse-config → opens SourceFormDrawer pre-populated → user reviews (especially password) → clicks Save → hits existing `POST /sources` endpoint (Fernet-encrypts).

## Files touched
- `frontend/src/pages/data-platform/SourcesListPage.tsx` (add "智能添加" button + Modal)
- `frontend/src/pages/data-platform/components/SmartAddModal.tsx` (NEW)
- `frontend/src/pages/data-platform/components/SourceFormDrawer.tsx` (extend props to accept `initialValues`)
- `frontend/src/services/dataPlatform.service.ts` (add `parseConfig(rawText)` method)
- `frontend/src/pages/data-platform/__tests__/SmartAddModal.test.tsx` (NEW)
- `.blueprint/qa/T32/vitest.txt`

## Depends on
- T31 (needs parse-config endpoint)

## Contract

```tsx
// dataPlatform.service.ts
async parseConfig(rawText: string): Promise<{parsed: DpDataSourceCreate; modelUsed: string; warnings: string[]}> { ... }

// SmartAddModal.tsx
<Modal title="智能添加数据源" open onOk={handleParse} onCancel={close}>
  <Alert message="⚠️ 密码字段会自动留空，请在下一步手动输入" type="warning" />
  <Input.TextArea rows={12} placeholder={PLACEHOLDER_MYSQL_EXAMPLE} 
                  value={rawText} onChange={...} />
  {loading && <Spin tip="正在调用 LLM 解析..." />}
</Modal>

// SourcesListPage.tsx
<Button icon={<ThunderboltOutlined />} onClick={() => setSmartAddOpen(true)}>
  智能添加
</Button>
{smartAddOpen && <SmartAddModal open onParsed={(dpDataSourceCreate) => {
  setDrawerInitial(dpDataSourceCreate);
  setDrawerOpen(true);
  setSmartAddOpen(false);
}} onCancel={() => setSmartAddOpen(false)} />}
```

## Vitest smoke

- `test_smart_add_modal_calls_parse_config` — mock service, assert Modal calls parseConfig
- `test_smart_add_result_prefills_drawer` — after parse success, drawer's initialValues populate
- `test_password_field_stays_empty_on_prefill` — ensures Fernet-safe behavior

## Acceptance
- Click "智能添加" → Modal opens with textarea + warning banner
- Paste raw text + click "解析" → sees Spin, then drawer opens with fields pre-filled (name/host/port/username/database/dialect/read_only_flag/description all populated)
- Password field is empty (blank) — user must type
- Click Save → hits existing `POST /sources` → row appears

## Verify
```
cd frontend
npx vitest run src/pages/data-platform/__tests__/SmartAddModal.test.tsx | tee /tmp/T32-vitest.txt
```

## Commit
`ui: smart-add data source (parse-config + SourceFormDrawer prefill)`
