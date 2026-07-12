## Verdict
APPROVE

## Reasoning
- All 13 endpoints across sources/execute/saved-queries/history/chat carry `Depends(get_current_user_id)`, and the T17 smoke evidence confirms 401 for no-token calls plus 200 for token'd list — criterion 1 satisfied.
- Envelope `{code,message,data}` is uniform on every handler; all list endpoints (`list_sources`, `list_saved_queries`, `list_sessions`, `list_messages`, `list_history`) also include `total` — criterion 2 satisfied.
- Endpoint inventories match the spec exactly: sources.py = 7 (POST/GET list, GET/PUT/DELETE {id}, POST /test, GET /schema); saved_queries.py = 4 (no GET/{id}); execute.py has POST sync + GET SSE with `json.dumps(..., default=str)`; chat.py exposes session CRUD, list_messages, POST /messages with an accepted-but-ignored `stream` query, and POST /apply/{message_id}; history.py accepts `source_id` + `limit`. Aggregator mounts all 5 sub-routers under `/data-platform`, and `router.py` is a clean append (import + include with `prefix="/data-platform"` and `tags=["数据平台"]`).
- Diff is confined to `backend/app/api/v1/data_platform/*`, `backend/app/api/v1/router.py` (append-only), `backend/scripts/mint_test_token.py`, and `.blueprint/qa/T17/` — no models/repos/schemas/services touched, honoring criterion 12.
- OpenAPI smoke shows `dp_paths=13`, tag "数据平台" present, `/api/docs` 200 — evidence complete.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- `router.py`'s new `from app.api.v1 import data_platform` sits at the file's bottom instead of joining the top import block; harmless but slightly odd stylistically.
- `mint_test_token.py` is 24 lines vs the spec's 22 (extra shebang-less blank + trailing newline); cosmetic only.
- Consider adding an explicit `# noqa: E402` if a linter later complains about the bottom-of-file import in `router.py`.
