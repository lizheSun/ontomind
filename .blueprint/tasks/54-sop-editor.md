# T54 · SOP 编辑器

## Goal
两种编辑模式：自然语言描述（输入"先分析表结构，再生成 SQL，最后验证" → 自动编译成 DAG）+ 可视化 DAG 编辑（拖拽节点 / 连线）。模板库包含 5 个预设 SOP。

## Files touched
- `frontend/src/pages/agent-looper/SOPEditor.tsx` (NEW)
- `frontend/src/pages/agent-looper/components/DAGCanvas.tsx` (NEW — 基于 reactflow)
- `frontend/src/pages/agent-looper/components/SOPNodePalette.tsx` (NEW)
- `frontend/src/pages/agent-looper/components/NLtoSOPCompiler.tsx` (NEW)
- `frontend/src/pages/agent-looper/components/SOPTemplateGallery.tsx` (NEW)
- `frontend/src/pages/agent-looper/templates/*.json` (5 个预设)
- `backend/app/services/sop_compiler_service.py` (NEW — 自然语言 → DAG JSON)
- `backend/app/schemas/sop.py` (NEW)
- `backend/app/api/v1/sop.py` (NEW — compile / validate / templates)
- `backend/tests/data_platform/test_sop_compiler.py`
- `frontend/src/pages/agent-looper/__tests__/SOPEditor.test.tsx`
- `.blueprint/qa/T54/pytest.txt`

## Depends on
- T53

## 功能规格
1. reactflow 画布：节点类型 = task / decision / eval / parallel / merge
2. NL 编译器：把自然语言拆成 task 列表 + 顺序 → DAG JSON
3. 模板：数据分析师 / SQL 编写员 / 元数据审核员 / 通用助手 / 自定义
4. 保存到 `agents.custom_tools['sop']` 字段
5. 支持 import/export SOP JSON

## Acceptance
- SOP 编辑器可创建 / 保存 / 加载 DAG
- NL 编译器至少支持 3 种模板句式
- 5 个模板可一键应用
- pytest 覆盖编译器边界（空句 / 单节点 / 多分支）

## Verify
```bash
cd backend && pytest tests/data_platform/test_sop_compiler.py -v
cd frontend && npm run test -- agent-looper/SOPEditor
```

## Commit
`feat(agent-looper): SOP editor with NL compiler and DAG canvas`
