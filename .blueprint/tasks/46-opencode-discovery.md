# T46 · Opencode 配置发现服务

## Goal
实现 `OpencodeConfigDiscoveryService`：扫描 `~/.config/opencode/opencode.json` 的 `mcp:` 部分，扫描 `~/.config/opencode/skills/*/SKILL.md`，解析 MCP 与 Skill 配置，写入 DB。

## Files touched
- `backend/app/services/opencode_discovery_service.py` (NEW)
- `backend/app/schemas/opencode_discovery.py` (NEW — MCP + SKILL 解析出的 DTO)
- `backend/app/api/v1/resources.py` (新增 `POST /api/v1/resources/discover-opencode` 端点)
- `backend/app/utils/frontmatter.py` (NEW — SKILL.md YAML frontmatter 解析)
- `backend/tests/data_platform/test_opencode_discovery.py` (10+ test)
- `backend/tests/fixtures/opencode_configs/*.json` (NEW — 测试 fixture)
- `backend/tests/fixtures/skills_samples/*.md` (NEW — SKILL.md fixture)
- `.blueprint/qa/T46/pytest.txt`

## Depends on
- T44

## 功能规格
1. 支持从 `OPENCODE_CONFIG_PATH` 环境变量或默认 `~/.config/opencode/` 读取
2. 解析 `opencode.json` 顶层 `mcp` 字段：`{name: {type: "local"|"remote", command?: [...], url?: "...", enabled: bool, environment?: {...}}}`
3. 递归扫描 `skills/**/SKILL.md`，读取 YAML frontmatter (`---\nname: ...\ndescription: ...\n---`) 与 markdown body
4. 幂等入库：以 `source_path` / `name` 作为去重键
5. dry-run 模式：返回将要创建/更新的列表，不真正写库

## Acceptance
- 至少 10 个 test 通过（MCP local/remote, SKILL 完整/损坏 frontmatter, dry-run, 幂等重跑, 空目录, 权限错误）
- `POST /api/v1/resources/discover-opencode` 返回 `{mcps_found: n, skills_found: m, created: k, updated: j}`
- 遇到解析错误不中断整体流程，收集到 `errors` 字段返回

## Verify
```bash
cd backend
pytest tests/data_platform/test_opencode_discovery.py -v
curl -X POST http://localhost:8000/api/v1/resources/discover-opencode -H "Authorization: Bearer $TOKEN" | jq
```

## Commit
`feat(resources): opencode config auto-discovery service`
