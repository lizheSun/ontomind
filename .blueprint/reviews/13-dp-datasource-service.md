# T13 Review — DpDataSourceService

## Verdict
APPROVE

## Reasoning
- Every one of the 14 review criteria is satisfied by the diff:
  - Ctor + repo (lines 41-43); create() encrypts via `crypto.encrypt`, refuses with `ENCRYPTION_DISABLED` code, stamps owner/created_by (lines 54-81).
  - update() correctly treats `None` and `""` as "keep", non-empty as rotate (lines 100-109); `_require_owner` returns 403 with `DP_DS_FORBIDDEN` (lines 205-215).
  - `DpDataSourceRead._to_read` sets `has_password=bool(row.password_enc)` and never exposes ciphertext (lines 217-239).
  - Engine cache keyed by `(source_id, cache_version)` with cache_version = `ts_us ^ hash((host,port,database,username,dialect))` — updated_at AND connection-identity, disposes old versions on both fresh build and `_engine_cache_invalidate` (lines 134-148, 245-299). Cross-test collision fix confirmed.
  - Per-dialect connect_args exactly match spec: PG `connect_timeout=30` + `options=-c statement_timeout=30000`; MySQL `connect_timeout/read_timeout/write_timeout=30`; SQLite `{}` (lines 328-333). SQLite path skips `pool_size/max_overflow` (lines 269-276).
  - `test_connection` uses dialect-branched version probe (`SHOW server_version` / `SELECT VERSION()` / `SELECT sqlite_version()`) and returns `DpDataSourceTestResult(ok/elapsed_ms/server_version/error)` (lines 152-181).
  - `describe_schema` uses `sqlalchemy.inspect(engine)` and returns the exact `{"databases":[{"name","tables":[{"name","columns":[{"name","type"}]}]}]}` shape (lines 185-201).
  - `_reset_autobegin()` rollback-before-begin helper is present and called at every write site (lines 45-50, 72, 111, 126). Matches note — legitimate alternative to T16's `_tx()` begin_nested fallback.
- Test file has the required 11 cases and all match the spec labels (create-encrypts, encryption-disabled, blank-preserves, new-rotates, name-conflict, engine-cache-hit+invalidate, test-connection-happy-sqlite, test-connection-bad-host, describe-schema-sqlite, delete-clears-cache, non-owner-ACL). Evidence `.blueprint/qa/T13/pytest.txt` shows `11 passed in 0.31s`.
- Diff scope is strictly additive: `git diff --stat` = 1 new service file + 3 new test artifacts. Zero touches to models/repos/schemas/routers, so criterion #14 is unambiguously met and regression risk to the pre-existing 28-test suite is nil.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- `hash((...))` for connection identity uses Python's process-scoped hash (with PYTHONHASHSEED randomization). Fine for in-process cache versioning, but if you ever persist/compare cache_versions across processes, switch to a stable digest (e.g. `zlib.crc32` of a `repr` string).
- The blackhole-IP test relies on the environment failing fast (or psycopg2 being absent). Consider `monkeypatch`ing `svc.get_engine` to raise, or using a definitely-invalid URL, to keep the test bounded on CI hosts where the 30 s `connect_timeout` would actually elapse.
- `describe_schema` currently returns only tables from the default schema; the spec allows one database entry, so this is fine, but adding a comment that multi-schema PG introspection is intentionally deferred would help future readers.
