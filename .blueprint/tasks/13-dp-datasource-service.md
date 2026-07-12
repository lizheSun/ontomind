# T13 — dp data-source service

## Goal
`DpDataSourceService` — CRUD with Fernet password encryption on write / never on read; engine cache (`@lru_cache` keyed by `(id, updated_at_epoch)`); connection test; schema introspection (databases → tables → columns).

## Files touched
- `backend/app/services/dp_data_source_service.py`  (NEW)
- `backend/tests/data_platform/test_dp_data_source_service.py`  (NEW — TDD)

## Depends on
- T05, T09, T10

## Implementation notes
- `create(payload, user_id)`: if `password` given, call `crypto.encrypt`; if `ENCRYPTION_DISABLED`, raise `BusinessException(code="ENCRYPTION_DISABLED", message="加密未配置，请先设置 FERNET_KEY")`.
- `update`: empty password preserves existing.
- `get_engine(source_id) -> Engine`: lru_cache, per-dialect pool tuning: MySQL `connect_timeout=30, read_timeout=30`; PG `connect_args={"options":"-c statement_timeout=30000","connect_timeout":30}`; SQLite noop.
- `test_connection(source_id) -> {"ok": bool, "server_version": str, "elapsed_ms": int}`.
- `describe_schema(source_id) -> {"databases":[{"name":..., "tables":[{"name":..., "columns":[{"name":..., "type":...}]}]}]}` — uses `sqlalchemy.inspect(engine)`.

## Acceptance
- `pytest backend/tests/data_platform/test_dp_data_source_service.py -q` passes 8+ cases (create-with-password, update-blank-preserves, encryption-disabled-refuses-create, engine-cache-hit, test-connection-happy, test-connection-bad-host, describe-schema, delete).

## Verify
```bash
cd backend && pytest tests/data_platform/test_dp_data_source_service.py -q --tb=short | tee ../.blueprint/qa/T13/pytest.txt
```

## Commit
`dp: data-source service (Fernet + engine cache + schema introspect)`
