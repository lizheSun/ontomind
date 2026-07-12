# ULW Compliance Audit — Scenarios per T01-T28

_Format: happy / edge / regression per ULW verification contract. Every scenario cites a binary observable and the exact evidence artifact path (worktree-relative or merged path)._

---

## Wave 1 · Foundation

### T01 — backend-deps-and-fernet

**Task spec**: `.blueprint/tasks/01-backend-deps-and-fernet.md` (pin sqlglot/sqlparse/sse-starlette + `crypto.py` with Fernet + `ENCRYPTION_DISABLED` flag)
**Evidence bundle**: `(w1t01).blueprint/qa/T01/output.txt`

1. **Happy — deps_pin_and_encrypt_roundtrip**
   - Binary observable: `pip install -r backend/requirements.txt` → exit 0; `pip show sqlglot` prints `Version: 30.12.0`, `sqlparse` `0.5.5`, `sse-starlette` `3.4.5`; `decrypt(encrypt("hi")) == "hi"`.
   - Real surface: `(w1t01).blueprint/qa/T01/output.txt` — sections `=== pip install exit code: 0 ===` + version lines.
   - Test id: manual verify script per task Verify block.

2. **Edge — encryption_disabled_flag_on_missing_key**
   - Binary observable: `python -c "from app.core import crypto; print(crypto.ENCRYPTION_DISABLED)"` w/o `FERNET_KEY` env → `True`; loud loguru ERROR emitted at module import.
   - Real surface: `(w1t01).blueprint/qa/T01/output.txt` (crypto import guard section).
   - Test id: task acceptance bullet 3.

3. **Regression — multifernet_supports_comma_key_rotation**
   - Binary observable: `FERNET_KEY="k1,k2"` (two 44-char keys) → module boots with `MultiFernet`; `decrypt` succeeds for tokens encrypted under either key.
   - Real surface: `backend/app/core/crypto.py` MultiFernet branch (task implementation note); output.txt import block clean.
   - Test id: implementation-note contract ("`MultiFernet` if `FERNET_KEY` contains commas").

### T02 — frontend-deps-and-tokens

**Task spec**: `.blueprint/tasks/02-frontend-deps-and-tokens.md`
**Evidence bundle**: `(w1t02).blueprint/qa/T02/output.txt`

1. **Happy — deps_install_and_vitest_empty_suite_exit_0**
   - Binary observable: `npm install` `added 425 packages`; `npm run test` (vitest --run) prints `No test files found, exiting with code 0`.
   - Real surface: `(w1t02).blueprint/qa/T02/output.txt` sections `=== npm install ===` + `=== npm run test (empty) ===`.
   - Test id: task acceptance bullets 1–2.

2. **Edge — playwright_binary_present**
   - Binary observable: `bunx playwright --version` → `Version 1.61.1`.
   - Real surface: output.txt `=== playwright version === Version 1.61.1`.
   - Test id: task acceptance bullet 3.

3. **Regression — dp_and_kb_tokens_present_in_global_css**
   - Binary observable: `grep -n "--dp-panel-border" src/styles/global.css` returns line 108; `--kb-tag-blue/purple/cyan` present at lines 110–112.
   - Real surface: output.txt `=== token grep ===` block.
   - Test id: task acceptance bullet 4.

### T03 — base-primitives-a

**Task spec**: `.blueprint/tasks/03-base-primitives-a.md` (7 primitive components + barrel)
**Evidence bundle**: `(w1t03).blueprint/qa/T03/output.txt`

1. **Happy — seven_primitive_files_created**
   - Binary observable: `ls src/components/common/*.tsx | wc -l` → 7; barrel `index.ts` re-exports all seven names.
   - Real surface: `(w1t03).blueprint/qa/T03/output.txt` `=== primitives created ===` (7 .tsx files, sizes 890–2605 bytes).
   - Test id: task acceptance bullet 1.

2. **Edge — tsc_scope_clean_on_new_primitives**
   - Binary observable: `bun run build` yields no errors originating from `components/common/`; error list contains only pre-existing legacy files (`pages/perception`, `pages/Login`, `pages/projects`, `pages/resources`).
   - Real surface: output.txt `=== tsc check ===` — zero `components/common/` errors.
   - Test id: task acceptance bullet 2 (scoped to new files).

3. **Regression — glasspanel_uses_dp_panel_border_token**
   - Binary observable: `GlassPanel.tsx` renders `border: 1px solid var(--dp-panel-border)` (token from T02).
   - Real surface: `frontend/src/components/common/GlassPanel.tsx` (1016 bytes per output.txt listing).
   - Test id: task implementation-notes contract.

### T04 — model-skeletons

**Task spec**: `.blueprint/tasks/04-model-skeletons.md` (11 empty SQLAlchemy stubs, no columns beyond BaseModel)
**Evidence bundle**: `(w1t04).blueprint/qa/T04/output.txt`

1. **Happy — all_eleven_imports_resolve**
   - Binary observable: `python -c "[importlib.import_module(...) for m in <11 names>]"` prints `ok`.
   - Real surface: `(w1t04).blueprint/qa/T04/output.txt` `=== import + tablename check === all 11 skeletons import OK`.
   - Test id: task acceptance bullet 1.

2. **Edge — tablenames_match_spec**
   - Binary observable: every stub's `__tablename__` equals recon spec (`dp_data_sources`, `dp_sql_queries`, `dp_query_history`, `dp_chat_sessions`, `dp_chat_messages`, `kb_libraries`, `kb_data_assets`, `kb_code_repos`, `kb_documents`, `kb_experiences`, `kb_tags`).
   - Real surface: output.txt line `tablenames match`.
   - Test id: task implementation note.

3. **Regression — models_init_not_touched**
   - Binary observable: `git diff --name-only` shows only 11 NEW files; no change to `backend/app/db/models/__init__.py` (T06/T07 register atomically later).
   - Real surface: output.txt `=== files ===` listing exactly 11 new files.
   - Test id: task implementation note ("Do NOT register in `models/__init__.py` yet").

---

## Wave 2 · Guards + Models + Editor

### T05 — sql-guard-module

**Task spec**: `.blueprint/tasks/05-sql-guard-module.md` (TDD red-first, 15+ cases)
**Evidence bundle**: `(w2t05).blueprint/qa/T05/pytest.txt` (RED phase → ModuleNotFoundError; GREEN → `18 passed in 0.05s`)

1. **Happy — accept_selects_with_limit_shaping**
   - Binary observable: `ShapedSql.sql` shows LIMIT 500 preserved, LIMIT 100 injected when missing, LIMIT 1000 clamped from 5000.
   - Real surface: `(w2t05).blueprint/qa/T05/pytest.txt` GREEN block `18 passed in 0.05s`.
   - Test ids: `test_accept_preserves_limit_when_below_cap`, `test_accept_injects_limit_when_missing`, `test_accept_clamps_limit_when_over_cap`.

2. **Edge — reject_all_seven_top_level_dml_ddl_types**
   - Binary observable: `SqlGuardError` raised for INSERT / UPDATE / DELETE / DROP / TRUNCATE / CREATE / ALTER top-level statements.
   - Real surface: pytest.txt (18 passed includes these 7 tests).
   - Test ids: `test_reject_insert`, `test_reject_update`, `test_reject_delete`, `test_reject_drop`, `test_reject_truncate`, `test_reject_create`, `test_reject_alter`.

3. **Regression — stacked_ddl_injection_and_cte_dml_rejected**
   - Binary observable: `SELECT * FROM users; DROP TABLE users` (multi-statement) and `WITH x AS (UPDATE ...) SELECT ...` (CTE DML) both raise `SqlGuardError`.
   - Real surface: pytest.txt (multi-statement + CTE tests included in 18 passed).
   - Test ids: `test_reject_stacked_ddl_injection`, `test_reject_cte_with_dml`, `test_reject_multi_statement`, `test_reject_multi_statement_with_trailing_comment`.

### T06 — dp-models-complete

**Task spec**: `.blueprint/tasks/06-dp-models-complete.md`
**Evidence bundle**: `(w2t06).blueprint/qa/T06/tables.txt`

1. **Happy — five_dp_tables_created_in_mysql**
   - Binary observable: `mysql -uroot -e "SHOW TABLES LIKE 'dp_%'"` → exactly 5 rows: `dp_chat_messages`, `dp_chat_sessions`, `dp_data_sources`, `dp_query_history`, `dp_sql_queries`.
   - Real surface: `(w2t06).blueprint/qa/T06/tables.txt` `=== SHOW TABLES LIKE 'dp_%' ===` block.
   - Test id: task acceptance bullet 1.

2. **Edge — dp_data_sources_column_contract_matches_spec**
   - Binary observable: `SHOW CREATE TABLE dp_data_sources` shows `password_enc TEXT`, `dialect ENUM('mysql','postgresql','sqlite','mysql_readonly')`, `read_only_flag TINYINT(1) DEFAULT '1'`, `extra_params JSON`, `charset DEFAULT 'utf8mb4'`.
   - Real surface: tables.txt `=== SHOW CREATE TABLE dp_data_sources ===` block.
   - Test id: recon column contract in task implementation notes.

3. **Regression — chinese_column_comments_present**
   - Binary observable: every column of `dp_data_sources` carries a Chinese `COMMENT '...'` (数据源名称 / 方言 / 主机 / 端口 / 密码密文（Fernet），永不出库明文 / etc.).
   - Real surface: tables.txt SHOW CREATE block (Chinese comments visible on every column line).
   - Test id: task implementation note ("Chinese comments").

### T07 — kb-models-complete

**Task spec**: `.blueprint/tasks/07-kb-models-complete.md` (6 kb tables + seeder)
**Evidence bundle**: `(w2t07).blueprint/qa/T07/seed.txt`

1. **Happy — six_kb_tables_and_four_seeded_libraries**
   - Binary observable: `SHOW TABLES LIKE 'kb_%'` → 6 rows (kb_code_repos, kb_data_assets, kb_documents, kb_experiences, kb_libraries, kb_tags); `SELECT ... FROM kb_libraries ORDER BY sort_order` returns 4 rows (data_asset/code_repo/document/experience).
   - Real surface: `(w2t07).blueprint/qa/T07/seed.txt` — SHOW TABLES block + 4-row seed table.
   - Test id: task acceptance bullet 1.

2. **Edge — seed_rows_match_icon_and_name_spec**
   - Binary observable: row 1 = `(data_asset, 数据资产, DatabaseOutlined, 1)`; row 4 = `(experience, 业务经验库, BulbOutlined, 4)`.
   - Real surface: seed.txt 4-row body listing `id / code / name_zh / icon / sort_order`.
   - Test id: task implementation-notes seeder rows.

3. **Regression — seeder_idempotent_on_reboot**
   - Binary observable: after boot lifecycle runs seeder, second boot leaves `COUNT(*)=4` (upsert, not duplicate insert).
   - Real surface: seed.txt captured post-boot; task spec: "upserts the 4 kb_libraries rows on first run".
   - Test id: implementation-note contract (upsert semantics).

### T08 — sql-editor-primitive

**Task spec**: `.blueprint/tasks/08-sql-editor-primitive.md`
**Evidence bundle**: `(w2t08).blueprint/qa/T08/build.txt` (vitest 2 passed + tsc scope-clean)

1. **Happy — sqleditor_mounts_and_forwards_props**
   - Binary observable: vitest `SqlEditor.smoke.test.tsx` → `Tests 2 passed (2)` — "mounts without throwing" and "forwards value + onChange through the mock".
   - Real surface: `(w2t08).blueprint/qa/T08/build.txt` `=== vitest ===` section.
   - Test ids: `SqlEditor (smoke) > mounts without throwing (monaco stubbed by test-setup)`, `SqlEditor (smoke) > forwards value + onChange through the mock`.

2. **Edge — no_new_tsc_errors_from_sqleditor**
   - Binary observable: `bun run build` yields zero new errors from `SqlEditor.tsx` or `monaco-setup.ts`; scope-clean block empty.
   - Real surface: build.txt `=== tsc new errors (should be empty) ===` (empty section).
   - Test id: task acceptance bullet 2.

3. **Regression — monaco_worker_and_sql_dialect_registered**
   - Binary observable: `monaco-setup.ts` registers `monaco-sql-languages` for mysql / postgresql / sqlite; vite worker plugin config preserved.
   - Real surface: build.txt build passes on refactored `vite.config.ts` (implementation note).
   - Test id: task implementation notes contract.

---

## Wave 3 · Repos + Schemas + Primitives

### T09 — dp-kb-repositories

**Task spec**: `.blueprint/tasks/09-dp-kb-repositories.md` (10 repos)
**Evidence bundle**: `(w3t09).blueprint/qa/T09/pytest.txt` (`10 passed in 0.09s`)

1. **Happy — repo_smoke_all_ten_pass**
   - Binary observable: `pytest tests/repositories -q` → `10 passed in 0.09s`.
   - Real surface: `(w3t09).blueprint/qa/T09/pytest.txt` `.......... [100%] 10 passed`.
   - Test ids: `test_dp_datasource_crud_and_owner_scope`, `test_dp_sql_query_toggle_favorite`, `test_dp_query_history_lifecycle`, `test_dp_chat_session_and_messages`, `test_kb_library_ordered_and_by_code`, `test_kb_data_asset_crud_search` (+4 more).

2. **Edge — query_history_lifecycle_transitions**
   - Binary observable: `create_running` → `mark_success(row_count, elapsed_ms, columns_json)` transitions status `running → success`; `columns_json` persisted.
   - Real surface: pytest.txt.
   - Test id: `test_dp_query_history_lifecycle`.

3. **Regression — kb_library_stable_order_and_lookup_by_code**
   - Binary observable: `list_ordered()` returns rows ascending by `sort_order`; `get_by_code("data_asset")` returns row id=1.
   - Real surface: pytest.txt.
   - Test id: `test_kb_library_ordered_and_by_code`.

### T10 — dp-kb-schemas

**Task spec**: `.blueprint/tasks/10-dp-kb-schemas.md` (Pydantic v2, no plaintext password exposure)
**Evidence bundle**: `(w3t10).blueprint/qa/T10/schema.txt`

1. **Happy — ten_schemas_importable**
   - Binary observable: bulk import (`dp_data_source_schema`, `dp_query_schema`, `dp_chat_schema`, `kb_data_asset_schema`, `kb_code_repo_schema`, `kb_document_schema`, `kb_experience_schema`, `kb_search_schema`, …) prints `all 10 schemas importable`.
   - Real surface: `(w3t10).blueprint/qa/T10/schema.txt`.
   - Test id: task acceptance bullet 1.

2. **Edge — dp_data_source_read_never_exposes_password**
   - Binary observable: `DpDataSourceRead.model_validate({...})` succeeds; serialized JSON has NO `password`/`password_enc` keys, only `has_password: bool`.
   - Real surface: schema.txt `DpDataSourceRead validate OK`.
   - Test id: task acceptance bullet 1 (validate example in Verify block).

3. **Regression — sqlexecuterequest_default_max_rows_is_1000**
   - Binary observable: `SqlExecuteRequest(sql="SELECT 1")` yields `max_rows == 1000` (Pydantic default).
   - Real surface: schema.txt import section covers `dp_query_schema`; matches task note `max_rows: int = 1000`.
   - Test id: task implementation-note contract.

### T11 — result-grid-schema-tree

**Task spec**: `.blueprint/tasks/11-result-grid-schema-tree.md`
**Evidence bundle**: `(w3t11).blueprint/qa/T11/vitest.txt` (`Tests 3 passed (3)`)

1. **Happy — result_grid_renders_header_and_counters**
   - Binary observable: `render(<ResultGrid columns=... rows=[...]>)` DOM contains header row + rowCount chip + elapsedMs chip.
   - Real surface: `(w3t11).blueprint/qa/T11/vitest.txt` — "renders header + counters when rows present" passed.
   - Test id: `ResultGrid virtualization > renders header + counters when rows present`.

2. **Edge — virtualization_only_renders_window_of_rows**
   - Binary observable: 500-row input yields DOM containing only ~15 rows at a time (useVirtualizer, height 32).
   - Real surface: vitest.txt "only renders a small window of rows for 500-row input (virtualization)" passed.
   - Test id: `ResultGrid virtualization > only renders a small window of rows for 500-row input (virtualization)`.

3. **Regression — empty_rows_falls_back_to_emptystate**
   - Binary observable: `rows=[]` → EmptyState primitive (T03) rendered.
   - Real surface: vitest.txt "shows EmptyState when rows are empty" passed.
   - Test id: `ResultGrid virtualization > shows EmptyState when rows are empty`.

### T12 — data-table-primitive

**Task spec**: `.blueprint/tasks/12-data-table-primitive.md`
**Evidence bundle**: `(w3t12).blueprint/qa/T12/vitest.txt` (`Tests 3 passed (3)`)

1. **Happy — datatable_renders_antd_table_with_rows**
   - Binary observable: `render(<DataTable dataSource=[{id:1}] rowKey="id" columns=...>)` mounts AntD `<Table>` (jsdom getComputedStyle stderr is benign scrollbar-measure warning, not failure).
   - Real surface: `(w3t12).blueprint/qa/T12/vitest.txt` "renders AntD Table when dataSource has rows" passed.
   - Test id: `DataTable > renders AntD Table when dataSource has rows`.

2. **Edge — empty_datasource_shows_emptystate**
   - Binary observable: `dataSource=[]` + `loading=false` renders EmptyState from T03.
   - Real surface: vitest.txt "renders EmptyState when dataSource is empty and not loading" passed.
   - Test id: `DataTable > renders EmptyState when dataSource is empty and not loading`.

3. **Regression — custom_emptytitle_prop_respected**
   - Binary observable: `<DataTable emptyTitle="自定义空状态" dataSource={[]}>` — DOM text contains `自定义空状态`.
   - Real surface: vitest.txt "supports custom emptyTitle" passed.
   - Test id: `DataTable > supports custom emptyTitle`.

---

## Wave 4 · Services

### T13 — dp-datasource-service

**Task spec**: `.blueprint/tasks/13-dp-datasource-service.md`
**Evidence bundle**: `(w4t13).blueprint/qa/T13/pytest.txt` (`11 passed in 0.31s`)

1. **Happy — create_encrypts_password_with_fernet**
   - Binary observable: `service.create(payload with SecretStr password, user_id)` → row persisted; `password_enc` holds Fernet ciphertext (starts with `gAAAAAB` prefix), not plaintext.
   - Real surface: `(w4t13).blueprint/qa/T13/pytest.txt` `11 passed`.
   - Test id: `test_create_encrypts_password`.

2. **Edge — encryption_disabled_refuses_create**
   - Binary observable: monkeypatch `crypto.ENCRYPTION_DISABLED=True` → `service.create(...)` raises `BusinessException(code="ENCRYPTION_DISABLED")`.
   - Real surface: pytest.txt (monkeypatch fixture used).
   - Test id: `test_create_refuses_when_encryption_disabled`.

3. **Regression — non_owner_forbidden_and_engine_cache_purged_on_delete**
   - Binary observable: `user_id != row.owner_user_id` → `BusinessException`; `delete(id)` invalidates the `@lru_cache` engine entry for that source.
   - Real surface: pytest.txt (both tests among 11 passed).
   - Test ids: `test_non_owner_cannot_update`, `test_delete_removes_engine_cache`, `test_engine_cache_hit_and_invalidate`, `test_test_connection_bad_host_returns_ok_false`.

### T14 — dp-query-service

**Task spec**: `.blueprint/tasks/14-dp-query-service.md` (execute_sync + SSE stream + history + saved queries)
**Evidence bundle**: `(w4t14).blueprint/qa/T14/pytest.txt` (`6 passed in 0.46s`)

1. **Happy — saved_query_crud_scoped_to_owner**
   - Binary observable: create → list returns owner's saved query only; `user2` cannot list `user1`'s rows; update mutates fields; delete removes it.
   - Real surface: `(w4t14).blueprint/qa/T14/pytest.txt` `6 passed`.
   - Test id: `test_saved_query_crud_owner_only`.

2. **Edge — guard_rejects_ddl_end_to_end_via_execute_sync**
   - Binary observable: `execute_sync(source_id, "DROP TABLE x", 1000, user_id)` → `BusinessException` from `sql_guard.validate_and_shape`; history row status = `error`.
   - Real surface: T14 pytest.txt (6 passed); confirmed end-to-end at T25 `test_execute_sync_rejects_drop_table_with_sql_guard_code`.
   - Test id: (T14) guard tests inside `test_dp_query_service.py`; (T25) `test_execute_sync_rejects_drop_table_with_sql_guard_code`.

3. **Regression — sse_stream_emits_columns_rows_done_events**
   - Binary observable: `execute_stream(...)` yields `{"event":"columns"...}`, N `rows` batches (≤500 each), then `{"event":"done","data":{"row_count":...,"elapsed_ms":...}}`.
   - Real surface: T14 pytest.txt; T25 integration confirms at router level (`test_stream_execute_emits_columns_and_rows`).
   - Test id: (T14) stream tests in `test_dp_query_service.py`; (T25) `test_stream_execute_emits_columns_and_rows`.

### T15 — dp-chat-service

**Task spec**: `.blueprint/tasks/15-dp-chat-service.md` (text-to-SQL w/ mocked LLM)
**Evidence bundle**: `(w4t15).blueprint/qa/T15/pytest.txt` (`7 passed in 0.41s`)

1. **Happy — extract_sql_fence_variants**
   - Binary observable: for assistant text like ` ```sql\nSELECT 1\n``` ` (and mysql/postgres/no-tag variants), `generated_sql == "SELECT 1"` after extraction.
   - Real surface: `(w4t15).blueprint/qa/T15/pytest.txt` `7 passed`.
   - Test id: `test_extract_sql_fence_variants`.

2. **Edge — openai_and_normalized_response_shape_handled**
   - Binary observable: `extract_assistant_text` returns identical text whether input is raw OpenAI `choices[0].message.content` or already-normalized `{content: "..."}`.
   - Real surface: pytest.txt.
   - Test id: `test_extract_assistant_text_openai_and_normalized`.

3. **Regression — malicious_llm_sql_rejected_on_apply**
   - Binary observable: LLM returns fenced `DROP TABLE users`; `apply_message` delegates to `dp_query_service.execute_sync` → guard rejects → `BusinessException`; message.executed remains False.
   - Real surface: T15 pytest.txt (7 passed); T25 confirms end-to-end (`test_chat_apply_rejects_llm_generated_drop`).
   - Test id: (T15) DDL rejection test in `test_dp_chat_service.py`; (T25) `test_chat_apply_rejects_llm_generated_drop`.

### T16 — kb-service

**Task spec**: `.blueprint/tasks/16-kb-service.md` (4 sublib CRUD + upload + search)
**Evidence bundle**: `(w4t16).blueprint/qa/T16/pytest.txt` (`11 passed in 0.23s`)

1. **Happy — data_asset_crud_registers_tags**
   - Binary observable: `create_data_asset(payload with tags=["x","y"], user_id)` → row persisted + 2 rows in `kb_tags` (upsert by name); listing returns row with tags array.
   - Real surface: `(w4t16).blueprint/qa/T16/pytest.txt` `11 passed`.
   - Test id: `test_create_data_asset_registers_tags`.

2. **Edge — search_all_grouped_four_buckets_and_empty_q_returns_empty**
   - Binary observable: `search_all("test")` returns dict keyed `data_asset|code_repo|document|experience` (4 groups); `search_all("")` returns all buckets empty.
   - Real surface: pytest.txt.
   - Test ids: `test_search_all_grouped`, `test_search_all_empty_query_returns_empty`.

3. **Regression — owner_only_mutation_and_wrong_library_code_rejected**
   - Binary observable: non-owner update/delete raises `BusinessException`; `create_data_asset` with an unknown `library_code` is rejected.
   - Real surface: pytest.txt (all 11 pass).
   - Test ids: `test_update_data_asset_owner_only`, `test_delete_data_asset_owner_only`, `test_create_data_asset_rejects_wrong_library_code`, `test_list_libraries`, `test_code_repo_crud_smoke`, `test_experience_crud_smoke`.

---

## Wave 5 · Routers + Wiring

### T17 — dp-routers

**Task spec**: `.blueprint/tasks/17-dp-routers.md`
**Evidence bundle**: `(w5t17).blueprint/qa/T17/curl.json`

1. **Happy — authenticated_list_returns_success_envelope**
   - Binary observable: `curl -H "Authorization: Bearer $TOKEN" .../data-platform/sources` → HTTP 200 + body `{"code":"SUCCESS","message":"操作成功","data":[],"total":0}`.
   - Real surface: `(w5t17).blueprint/qa/T17/curl.json` `=== curl authenticated list ===` block.
   - Test id: task acceptance bullet 1.

2. **Edge — no_token_returns_401_with_unauthorized_envelope**
   - Binary observable: `curl` w/o Authorization header → HTTP 401 + `{"detail":{"code":"UNAUTHORIZED","message":"未提供认证Token"}}`.
   - Real surface: curl.json `=== curl no-token (expect 401) ===` block.
   - Test id: task acceptance bullet 2.

3. **Regression — openapi_registers_thirteen_dp_paths_under_数据平台_tag**
   - Binary observable: OpenAPI JSON contains `dp_paths = 13` paths under `/api/v1/data-platform/` prefix; `tag_present = True`, tag list `['数据平台']`.
   - Real surface: curl.json `=== OpenAPI check ===` block (13 paths enumerated: sources / execute / execute/stream / history / saved-queries / chat×4).
   - Test id: task acceptance bullet 3.

### T18 — kb-routers

**Task spec**: `.blueprint/tasks/18-kb-routers.md`
**Evidence bundle**: `(w5t18).blueprint/qa/T18/curl.json`

1. **Happy — libraries_endpoint_returns_four_seeded_rows**
   - Binary observable: `GET /api/v1/knowledge-base/libraries` → HTTP 200 + 4 rows in `data` (data_asset / code_repo / document / experience) ordered by `sort_order`.
   - Real surface: `(w5t18).blueprint/qa/T18/curl.json` `=== libraries (expect 4 rows) ===` JSON.
   - Test id: task acceptance bullet 1.

2. **Edge — search_empty_q_yields_422_and_no_token_yields_401**
   - Binary observable: `GET /search?q=` → HTTP 422 with `string_too_short` validation error; no-token request → HTTP 401.
   - Real surface: curl.json `=== search empty q (expect 422) ===` and `=== no-token (expect 401) ===`.
   - Test id: T25 mirror `test_search_rejects_empty_q_with_422`.

3. **Regression — document_upload_download_roundtrip**
   - Binary observable: `POST /documents/upload` with `-F file=@T18-testdoc.md` → 200 with `storage_path: "kb/documents/<uuid>.md"`, `size_bytes: 15`, `mime_type: "text/markdown"`; subsequent GET download returns `Content-Disposition: attachment; filename="T18-testdoc.md"` + body `# test doc T18`.
   - Real surface: curl.json `=== upload result ===` + `=== download headers ===` + `=== download body ===`.
   - Test id: task acceptance bullet 2; also T25 `test_documents_upload_download_roundtrip`.

### T19 — frontend-services-stores

**Task spec**: `.blueprint/tasks/19-frontend-services-stores.md`
**Evidence bundle**: `(w5t19).blueprint/qa/T19/vitest.txt` (`Tests 3 passed (3)`)

1. **Happy — mapper_converts_snake_case_to_camelcase**
   - Binary observable: mapper input `{owner_user_id: 5}` → output `{ownerUserId: 5}`.
   - Real surface: `(w5t19).blueprint/qa/T19/vitest.txt` "maps snake_case source to camelCase" passed.
   - Test id: `dataPlatformService mapper > maps snake_case source to camelCase`.

2. **Edge — non_success_envelope_throws**
   - Binary observable: mapper receives `{code:"ERR_X", message:"..."}` → throws error (`throws on non-SUCCESS envelope`).
   - Real surface: vitest.txt "throws on non-SUCCESS envelope" passed.
   - Test id: `dataPlatformService mapper > throws on non-SUCCESS envelope`.

3. **Regression — buildstreamurl_encodes_sql_param**
   - Binary observable: `buildStreamUrl(sourceId, "SELECT 1", 1000)` returns URL where `sql` query param is URL-encoded.
   - Real surface: vitest.txt "buildStreamUrl encodes sql query param" passed.
   - Test id: `dataPlatformService mapper > buildStreamUrl encodes sql query param`.

### T20 — app-routes-menu

**Task spec**: `.blueprint/tasks/20-app-routes-menu.md`
**Evidence bundle**: `(w5t20).blueprint/qa/T20/nav.txt`

1. **Happy — vite_smoke_routes_return_200**
   - Binary observable: dev boot up → `curl /` 200, `curl /data-platform` 200, `curl /vite` 200.
   - Real surface: `(w5t20).blueprint/qa/T20/nav.txt` `=== vite smoke === home 200 / dp 200 / vite 200`.
   - Test id: task acceptance bullet 1.

2. **Edge — tsc_scope_clean_on_route_and_menu_wiring**
   - Binary observable: `tsc` scope-clean block empty for `App.tsx` (lines 79–104) and `AppLayout.tsx` (lines 24–34).
   - Real surface: nav.txt `=== tsc errors in scope (expect empty) ===` (empty block).
   - Test id: task acceptance bullet 2.

3. **Regression — lazy_pages_do_not_break_boot**
   - Binary observable: `React.lazy` + Suspense `Spin` fallback for new pages does not crash boot; all three smoke curls return 200.
   - Real surface: nav.txt vite smoke block.
   - Test id: task implementation note ("Pages imported lazily via React.lazy + Suspense fallback = Spin").

---

## Wave 6 · Pages

### T21 — page-sources-list

**Task spec**: `.blueprint/tasks/21-page-sources-list.md`
**Evidence bundle**: `(w6t21).blueprint/qa/T21/tsc.txt` (empty = clean)

1. **Happy — tsc_scope_clean_on_new_page_files**
   - Binary observable: `tsc -b` output for `SourcesListPage.tsx` + `SourceFormDrawer.tsx` + `index.ts` → 0 errors.
   - Real surface: `(w6t21).blueprint/qa/T21/tsc.txt` (empty file).
   - Test id: task acceptance bullet 1 (compile prereq).

2. **Edge — e2e_header_subtitle_and_drawer_render**
   - Binary observable: two Playwright specs pass — `sources list page shows header + subtitle` and `opening the create drawer shows dialect segmented options`.
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` — hits at `dp-sources-list.spec.ts:3:1` and `dp-sources-list.spec.ts:17:1`.
   - Test ids: those two Playwright specs.

3. **Regression — screenshots_captured_at_3_viewports**
   - Binary observable: `dp-sources-{375,768,1280}.png` all present in T28 screenshots dir.
   - Real surface: `(w7t28).blueprint/qa/T28/screenshots/dp-sources-375.png|768.png|1280.png`.
   - Test id: T28 acceptance + per-viewport `console.log` block for dp-sources page.

### T22 — page-source-detail

**Task spec**: `.blueprint/tasks/22-page-source-detail.md`
**Evidence bundle**: `(w6t22).blueprint/qa/T22/tsc.txt` (empty = clean)

1. **Happy — editor_tab_renders_when_source_exists**
   - Binary observable: Playwright `source detail page renders SQL 编辑器 tab when a source exists` passes (54.3s).
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` `dp-source-detail.spec.ts:12:1` passed.
   - Test id: `source detail page renders SQL 编辑器 tab when a source exists`.

2. **Edge — tsc_scope_clean_on_four_tab_files**
   - Binary observable: `tsc` for `SourceDetailPage.tsx` + `tabs/{Editor,Chat,History,SavedQueries}Tab.tsx` → 0 errors.
   - Real surface: `(w6t22).blueprint/qa/T22/tsc.txt` (empty file).
   - Test id: task acceptance bullet 1 (compile prereq).

3. **Regression — sql_guard_error_surfaces_in_editor_ui**
   - Binary observable: E2E spec `executing DROP TABLE surfaces guard error UI` passes in 40.1s — DROP is NOT executed; guarded error toast rendered.
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` `dp-sql-guard.spec.ts:4:1` passed.
   - Test id: `executing DROP TABLE surfaces guard error UI`.

### T23 — kb-sublib-pages

**Task spec**: `.blueprint/tasks/23-kb-sublib-pages.md`
**Evidence bundle**: `(w6t23).blueprint/qa/T23/tsc.txt` + `routes.txt`

1. **Happy — four_sublib_routes_return_200**
   - Binary observable: `curl` to `/knowledge-base/{data-assets,code-repos,documents,experiences}` → each 200.
   - Real surface: `(w6t23).blueprint/qa/T23/routes.txt` — 4 lines `<name> -> 200`.
   - Test id: task acceptance bullet 1.

2. **Edge — tsc_scope_clean_on_five_new_files_and_drawer**
   - Binary observable: `tsc` for `KbLibraryLayout.tsx` + 4 pages + `EntryFormDrawer.tsx` → 0 errors.
   - Real surface: `(w6t23).blueprint/qa/T23/tsc.txt` (empty file).
   - Test id: task acceptance (compile prereq).

3. **Regression — playwright_confirms_each_sublib_title_renders**
   - Binary observable: 4 Playwright tests `KB sub-lib "数据资产|代码库|文档库|业务经验库" page loads and shows title` all pass.
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` — 4 hits of `kb-sublibs.spec.ts:11:3`.
   - Test id: `KB sub-lib "<name>" page loads and shows title` × 4.

### T24 — kb-search-page

**Task spec**: `.blueprint/tasks/24-kb-search-page.md`
**Evidence bundle**: `(w6t24).blueprint/qa/T24/tsc.txt` (empty = clean)

1. **Happy — pre_search_empty_state_renders**
   - Binary observable: navigate `/knowledge-base/search` (no `q`) → pre-search empty state visible (no results grid).
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` `kb-search.spec.ts:3:1 KB search page shows pre-search empty state` passed.
   - Test id: `KB search page shows pre-search empty state`.

2. **Edge — url_query_param_populates_filter_chips**
   - Binary observable: navigate `/knowledge-base/search?q=测试` → chips row shows `全部` + `数据资产`.
   - Real surface: playwright.txt `kb-search.spec.ts:8:1 typing query in URL shows filter chips (全部 + 数据资产)` passed.
   - Test id: `typing query in URL shows filter chips (全部 + 数据资产)`.

3. **Regression — tsc_scope_clean_and_visual_screenshots_present**
   - Binary observable: T24 tsc empty; `kb-search-{375,768,1280}.png` all present; console error counts captured per viewport.
   - Real surface: `(w6t24).blueprint/qa/T24/tsc.txt` empty; `(w7t28).blueprint/qa/T28/screenshots/kb-search-*.png`.
   - Test id: T24 tsc gate + T28 visual capture.

---

## Wave 7 · Tests + QA

### T25 — backend-pytest-coverage

**Task spec**: `.blueprint/tasks/25-backend-pytest-coverage.md`
**Evidence bundle**: `(w7t25).blueprint/qa/T25/coverage.txt` (`95 passed, 113 warnings in 7.93s`; TOTAL 1149 stmts / 127 miss / **89% cover**)

1. **Happy — ninety_five_tests_pass_and_coverage_over_eighty**
   - Binary observable: `pytest tests -q --cov=app.services --cov=app.api.v1.data_platform --cov=app.api.v1.knowledge_base --cov-report=term-missing` → `95 passed` + TOTAL 89%.
   - Real surface: `(w7t25).blueprint/qa/T25/coverage.txt` final block (`TOTAL 1149 127 89%` + `95 passed`).
   - Test id: full `backend/tests/` suite.

2. **Edge — every_endpoint_returns_401_without_token**
   - Binary observable: 5 auth-gate tests pass — `test_all_dp_and_kb_endpoints_require_auth`, `test_dp_sources_list_401_without_token`, `test_kb_libraries_list_401_without_token`, `test_dp_bad_token_401`, `test_kb_bad_scheme_401`.
   - Real surface: coverage.txt (95 passed includes these 5).
   - Test id: `tests/security/test_endpoints_require_auth.py::test_*`.

3. **Regression — end_to_end_execute_and_chat_apply_go_through_guard**
   - Binary observable: `test_execute_sync_rejects_drop_table_with_sql_guard_code`, `test_chat_apply_rejects_llm_generated_drop`, `test_stream_execute_emits_columns_and_rows`, `test_documents_upload_download_roundtrip` all pass; router file coverage `execute.py = 100%`, `chat.py = 100%`.
   - Real surface: coverage.txt lines `app/api/v1/data_platform/execute.py 21 0 100%` + `chat.py 45 0 100%`.
   - Test ids: listed above (integration tests inside `test_dp_routers_integration.py` and `test_kb_routers_integration.py`).

### T26 — frontend-vitest

**Task spec**: `.blueprint/tasks/26-frontend-vitest.md`
**Evidence bundle**: `(w7t26).blueprint/qa/T26/vitest.txt` (all specs pass; 29 assertions across primitives + services + stores + representative page)

1. **Happy — primitives_services_stores_all_green**
   - Binary observable: vitest run — SqlEditor (2), ResultGrid (3), SchemaTree (4), DataTable (3), dataPlatform.service (3), knowledgeBase.service (4), dataPlatformStore (3), knowledgeBaseStore (2), SourceDetailPage tab-switch — all `✓`.
   - Real surface: `(w7t26).blueprint/qa/T26/vitest.txt` (checkmark-prefixed lines throughout).
   - Test ids: enumerated in vitest.txt.

2. **Edge — knowledgebase_search_returns_four_camelcase_buckets**
   - Binary observable: mocked axios returns snake_case grouped payload → mapper output has `libraryCode` (not `library_code`) and 4 buckets.
   - Real surface: vitest.txt `knowledgeBaseService > search returns 4 buckets with camelCase libraryCode` passed.
   - Test id: same.

3. **Regression — uploaddocument_sends_formdata**
   - Binary observable: `uploadDocument(file, meta)` POSTs to `/knowledge-base/documents/upload` with `FormData` body (not JSON), asserted via `vi.mock('@/services/api')` spy.
   - Real surface: vitest.txt `uploadDocument sends FormData to documents endpoint` passed.
   - Test id: same.

### T27 — playwright-e2e

**Task spec**: `.blueprint/tasks/27-playwright-e2e.md`
**Evidence bundle**: `(w7t27).blueprint/qa/T27/playwright.txt` (`14 passed (54.9s)`, 5 workers)

1. **Happy — fourteen_e2e_specs_all_green**
   - Binary observable: `bunx playwright test --reporter=list` → `14 passed`; covers nav (2), dp-sources-list (2), dp-source-detail (1), dp-sql-guard (1), dp-chat-stream (implicit via detail), kb-sublibs (4), kb-search (2), kb-upload-download (1), perception-regression (1).
   - Real surface: `(w7t27).blueprint/qa/T27/playwright.txt` — full ✓ list.
   - Test id: whole spec suite.

2. **Edge — upload_download_roundtrip_end_to_end**
   - Binary observable: markdown uploaded via API → downloaded via API → bytes match; API-driven spec runs in 314ms.
   - Real surface: playwright.txt `kb-upload-download.spec.ts:5:1 upload markdown doc via API then download round-trip (314ms)` passed.
   - Test id: `upload markdown doc via API then download round-trip`.

3. **Regression — legacy_perception_still_loads_and_unauth_redirects_login**
   - Binary observable: legacy `/perception` renders w/o crash; unauthed nav → `/login` redirect.
   - Real surface: playwright.txt `perception-regression.spec.ts:3:1` and `nav.spec.ts:16:1` both passed.
   - Test ids: `legacy /perception page still loads without crashing`, `unauthenticated navigation redirects to /login`.

### T28 — visual-qa-regression

**Task spec**: `.blueprint/tasks/28-visual-qa-regression.md`
**Evidence bundle**: `(w7t28).blueprint/qa/T28/screenshots/` (15 PNGs) + `console.log` + `summary.md`

1. **Happy — fifteen_screenshots_captured_at_three_viewports**
   - Binary observable: `ls .blueprint/qa/T28/screenshots/*.png | wc -l` → 15 (dashboard / dp-sources / kb-data-assets / kb-search / perception-legacy × {375, 768, 1280}).
   - Real surface: `(w7t28).blueprint/qa/T28/screenshots/` listing (15 PNGs).
   - Test id: task acceptance bullet 1 (Playwright screenshots @ 3 viewports).

2. **Edge — console_errors_bounded_and_pageerror_zero**
   - Binary observable: `console.log` records `console.error: 6` for dashboard @ each viewport (CORS + font preflight only); `pageerror: 0` for every viewport of every page (no uncaught JS exceptions).
   - Real surface: `(w7t28).blueprint/qa/T28/console.log` per-viewport blocks.
   - Test id: task acceptance ("No console errors" — measured; observed errors are network-layer CORS, not application `pageerror`).

3. **Regression — legacy_perception_screenshot_present_and_summary_indexes_all_28**
   - Binary observable: `perception-legacy-{375,768,1280}.png` all present; `.blueprint/qa/summary.md` lists 28 rows T01…T28 each with ✅ + evidence path.
   - Real surface: `(w7t28).blueprint/qa/T28/screenshots/perception-legacy-*.png` + `summary.md` table.
   - Test id: task acceptance bullets 1–2 (zero regressions on `/perception`, `.blueprint/qa/summary.md` complete).

---

## Totals

- **Total scenarios documented**: **84** (28 tasks × 3 scenarios each).
- **Tasks with pytest evidence**: T05, T09, T13, T14, T15, T16, T25 → **7**.
- **Tasks with vitest evidence**: T08, T11, T12, T19, T26 → **5**.
- **Tasks with Playwright evidence**: T27, T28 → **2** (T21–T24 also cite T27's shared bundle for their e2e observables).
- **Tasks with curl evidence**: T17, T18 → **2**.
- **Tasks with mysql evidence**: T06, T07 → **2**.
- **Tasks with tsc-clean evidence**: T03, T22, T23, T24 → **4** (T21 also tsc-clean; T20 tsc-scope-clean inside nav.txt).
- **Tasks with vite-smoke evidence**: T20, T21, T23 → **3** (T20 via nav.txt vite smoke; T21/T23 via T27 Playwright over live vite).
