# T14 — dp query service (execute sync + SSE stream + history + saved)

## Goal
`DpQueryService` executes shaped SQL, records history rows, supports SSE streaming of large result sets, and manages saved queries.

## Files touched
- `backend/app/services/dp_query_service.py`  (NEW)
- `backend/tests/data_platform/test_dp_query_service.py`  (NEW — TDD)

## Depends on
- T05, T09, T10, T13

## Implementation notes
- `execute_sync(source_id, sql, max_rows, user_id) -> SqlExecuteResponse`:
  1. `history = repo.create_running(...)`.
  2. `allowed = describe_schema(source_id).flatten_table_names()`.
  3. `shaped = sql_guard.validate_and_shape(sql, dialect, max_rows, allowed)`.
  4. `engine = data_source_service.get_engine(source_id)`.
  5. Wrap in `try` block; on success `mark_success`, on exception `mark_error` and raise `BusinessException`.
  6. Return columns + rows + row_count + elapsed_ms.
- `execute_stream(source_id, sql, ..., user_id) -> AsyncIterator[dict]`:
  - Emits `{"event":"columns","data":[...]}`, then `{"event":"rows","data":[[...],...]}` in batches of 500 up to `EXPORT_MAX=100000`, then `{"event":"done","data":{"row_count":...,"elapsed_ms":...}}` — pushes to caller which wraps in `sse-starlette EventSourceResponse`.
- `list_history(user_id, source_id?, limit=50)`.
- `create/list/update/delete_saved_query(...)` — owner-scoped.

> **Thread-pool wrap (required)**: wrap every synchronous `engine.execute()` / `.execute()` call inside `dp_query_service.execute_sync` with `starlette.concurrency.run_in_threadpool` so long-running pymysql queries don't block the FastAPI event loop. Do the same inside the SSE `execute_stream` yield loop.

## Acceptance
- Tests cover: DDL rejected → BusinessException, LIMIT injected on unbounded query, timeout path → status=timeout in history, stream emits ≥ 2 batches for 1000-row query.

## Verify
```bash
cd backend && pytest tests/data_platform/test_dp_query_service.py -q --tb=short | tee ../.blueprint/qa/T14/pytest.txt
```

## Commit
`dp: query service (guard-shaped execute + SSE stream + history + saved)`
