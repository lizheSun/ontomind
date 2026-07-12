# T48 · 技能 + MCP 同步服务

## Goal
双向同步：`opencode.json` ↔ DB。实现从 DB 发布到 opencode 配置文件，以及从 opencode 配置文件导入到 DB。提供 `POST /api/v1/resources/skills/sync` 与 `POST /api/v1/resources/mcps/sync` 端点。

## Files touched
- `backend/app/services/skill_sync_service.py` (NEW)
- `backend/app/services/mcp_sync_service.py` (NEW)
- `backend/app/api/v1/resources.py` (新增 2 个 sync 端点)
- `backend/app/schemas/sync.py` (NEW — SyncDirection / SyncResult)
- `backend/app/utils/opencode_writer.py` (NEW — atomic 写 opencode.json、写 SKILL.md)
- `backend/tests/data_platform/test_skill_sync.py`
- `backend/tests/data_platform/test_mcp_sync.py`
- `.blueprint/qa/T48/pytest.txt`

## Depends on
- T44, T46

## 功能规格
1. 方向枚举：`db_to_file` / `file_to_db` / `bidirectional`
2. bidirectional 使用 `updated_at` 时间戳做冲突解决，冲突时保留最新
3. 写文件使用临时文件 + rename 原子写，写前先备份 `opencode.json.bak.<ts>`
4. dry-run 模式：返回 diff patches
5. 支持单个资源同步（`skill_id` / `mcp_id`）与全量同步

## Acceptance
- Skill sync：DB 编辑的 body_markdown 能写回 SKILL.md
- MCP sync：DB 新增的 MCP 能写入 opencode.json
- 冲突场景 test：文件较新时不会覆盖文件
- dry-run 返回 unified diff
- 备份文件生成成功

## Verify
```bash
cd backend
pytest tests/data_platform/test_skill_sync.py tests/data_platform/test_mcp_sync.py -v
curl -X POST http://localhost:8000/api/v1/resources/mcps/sync -d '{"direction":"db_to_file","dry_run":true}' -H "Authorization: Bearer $TOKEN" | jq
```

## Commit
`feat(resources): skills & mcps bidirectional sync with opencode config`
