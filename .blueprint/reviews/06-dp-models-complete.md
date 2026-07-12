# Review — Task 06: dp_* models complete

## Verdict
APPROVE

## Reasoning
- All 5 dp_* model files carry the full column contract: `dp_data_sources` (name UNIQUE + dialect/status enums + Fernet `password_enc` Text + owner/created_by FK + `read_only_flag` default 1 + `extra_params` JSON), `dp_sql_queries` (source_id CASCADE + owner_user_id + is_favorite default 0), `dp_query_history` (status enum + row_count/elapsed_ms/error_message/columns_json/started_at/finished_at + composite index `ix_dp_query_history_user_started(user_id, started_at)`), `dp_chat_sessions` (source_id CASCADE, user_id, `model_config_id` FK→llm_configs.id nullable), `dp_chat_messages` (session_id CASCADE, role enum user/assistant/system, content, generated_sql nullable, executed default 0).
- Every column has a Chinese `comment=`; every model has `__table_args__` with `{"comment": "…"}` — confirmed on the live MySQL DDL: `dp_data_sources` shows `COMMENT='数据平台-数据源（Fernet 加密）'` and per-column Chinese `COMMENT` on all 16 business columns.
- `__init__.py` appends a clearly labeled `# --- Data Platform (T06) ---` block plus 5 new `__all__` entries; no existing imports/exports removed.
- Scope discipline: diff touches only `backend/app/db/models/dp_*` + `__init__.py` + `.blueprint/qa/T06/tables.txt`. No `kb_*` files, no `main.py`, no migrations.
- Evidence `.blueprint/qa/T06/tables.txt` contains real MySQL output — `SHOW TABLES LIKE 'dp_%'` returns exactly 5 rows (dp_chat_messages, dp_chat_sessions, dp_data_sources, dp_query_history, dp_sql_queries) and a full `SHOW CREATE TABLE dp_data_sources` with FKs to `users` and enum/JSON types intact.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- Evidence file only captures `SHOW CREATE` for `dp_data_sources`. Future QA passes could dump all 5 `SHOW CREATE` statements to make the composite index on `dp_query_history` and the CASCADE FK on `dp_chat_messages.session_id` audit-visible without re-running MySQL.
- `dp_data_sources.source_type` (String(32)) and `dialect` (enum) partially overlap semantically; a downstream task may want to fold `source_type` into a computed/derived view of `dialect` — not a blocker for T06.
