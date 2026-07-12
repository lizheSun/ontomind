# Review: T25 backend pytest coverage

## Verdict
APPROVE

## Reasoning
- Root `conftest.py` cleanly exports the full fixture set (`isolated_engine`, `db_session`, `override_db`, `client`, `anon_client`, `test_user`, `test_user2`, `auth_headers`, `auth_headers2`, `kb_libraries`); all share one StaticPool in-memory sqlite engine per test, with a `@compiles(MEDIUMTEXT, "sqlite")` shim + FULLTEXT-index stripping so `Base.metadata.create_all` succeeds. FERNET_KEY autouse session fixture is set before `app.core.crypto` import.
- `client` fixture uses raw `TestClient(app)` (no `with:` context) — lifespan seeder never fires against real MySQL. `kb_libraries` fixture manually seeds the 4 rows the tests need. Correct as spec'd.
- DP integration (16 tests): full sources CRUD + owner-scoping + 404, test/connection, schema describe, execute happy + SQL_GUARD_* DROP-reject, `/execute/stream` SSE emits `columns`/`rows`/`done` events, saved-queries CRUD cycle, history-lists-after-execute, chat send+apply (with LLM monkeypatched via `LLMConfigService.chat_completion`), chat apply-rejects-DROP, chat session list/get/delete + list_messages. All required branches hit.
- KB integration (11 tests): libraries=4, data_assets CRUD, code_repos CRUD, experiences CRUD, documents upload/download roundtrip via monkeypatched `settings.UPLOAD_DIR`, grouped search 4 buckets, 422 on empty q, owner scoping, tags listing, get-by-id + 404 for all 3 sub-libs w/ correct error codes, delete-doc→404.
- Auth-gate (5 tests): dynamically enumerates all `/api/v1/data-platform` + `/api/v1/knowledge-base` routes from `app.routes`, requires ≥20 routes, asserts 401 for every method (skipping HEAD/OPTIONS), plus 3 explicit assertions covering INVALID_TOKEN (Bearer-garbage) and non-Bearer scheme (Basic). Fully spec-compliant.
- Coverage evidence: `coverage.txt` shows **95 passed** with **89% total** on dp_*/kb_* service+router modules; every DP router file ≥98%, every KB router file ≥84%, service files 85–90%. Well above the ≥80% bar.
- No modifications to `app/services/`, `app/db/models/`, `app/api/v1/**` routers, repos, or schemas — diff limited to `backend/tests/**`, `backend/requirements.txt` (added pytest-cov==7.1.0), `.blueprint/qa/T25/coverage.txt`.
- LLM path fully mocked via `monkeypatch.setattr(LLMConfigService, "chat_completion", _fake)` — zero real network calls.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- `datetime.utcnow()` deprecation warnings surface in `app/core/security.py:26` and jose — not this task's scope; consider a follow-up to switch to `datetime.now(datetime.UTC)`.
- Existing sub-directory conftests (`tests/data_platform/conftest.py`, `tests/knowledge_base/conftest.py`) still define their own `db` fixture for service tests. Docstring calls this out explicitly — good, but a future consolidation could deduplicate.
