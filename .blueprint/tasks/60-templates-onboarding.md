# T60 · 模板库 + 零学习曲线 onboarding

## Goal
5 个预设模板：数据分析师 / SQL 编写员 / 元数据审核员 / 通用助手 / 自定义 SOP。首次打开 `/agent-looper` 显示模板选择（非文档）。Cmd+K 里可直接搜索模板。使用 3 次后自动提示"保存为模板"。

## Files touched
- `backend/app/services/agent_template_service.py` (NEW)
- `backend/app/api/v1/agent_templates.py` (NEW — CRUD + `apply` 端点)
- `backend/app/db/models/agent_template_model.py` (NEW)
- `backend/app/seed/agent_templates_seed.py` (NEW — 5 个预设)
- `frontend/src/pages/agent-looper/TemplateGallery.tsx` (NEW — 首次打开)
- `frontend/src/pages/agent-looper/components/TemplateCard.tsx` (NEW)
- `frontend/src/pages/agent-looper/components/SaveAsTemplate.tsx` (NEW)
- `frontend/src/hooks/useOnboarding.ts` (NEW — 首次访问检测 + usage 计数)
- `frontend/src/pages/agent-looper/index.tsx` (集成模板画廊)
- `backend/tests/data_platform/test_agent_templates.py`
- `frontend/src/pages/agent-looper/__tests__/TemplateGallery.test.tsx`
- `.blueprint/qa/T60/pytest.txt`

## Depends on
- T51, T54, T57

## 模板结构
```json
{
  "name": "数据分析师",
  "description": "...",
  "icon": "📊",
  "system_prompt": "...",
  "loop_strategy": "plan_execute",
  "default_skills": ["sql-writer", "chart-builder"],
  "default_mcps": ["mysql-mcp"],
  "sop_template": { ... },
  "recommended_tools": [...]
}
```

## Acceptance
- 5 个模板 seed 成功入库
- 首次打开 `/agent-looper` 显示画廊
- 「保存为模板」在 usage_count >= 3 时提示
- Cmd+K 可搜索模板并一键应用

## Verify
```bash
cd backend && pytest tests/data_platform/test_agent_templates.py -v
cd frontend && npm run test -- TemplateGallery
```

## Commit
`feat(agent-looper): template gallery with zero-learning-curve onboarding`
