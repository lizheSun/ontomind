# T25 — backend pytest coverage completion

## Goal
Consolidate + extend backend tests: unit (services/repos) + integration (httpx `TestClient` against FastAPI app w/ transactional rollback).

## Files touched
- `backend/tests/conftest.py`  (NEW or extend — fixtures: `client`, `auth_token`, `test_source`, `test_user`)
- `backend/tests/data_platform/test_dp_routers_integration.py`  (NEW)
- `backend/tests/knowledge_base/test_kb_routers_integration.py`  (NEW)
- `backend/tests/security/test_endpoints_require_auth.py`  (NEW)

## Depends on
- T17, T18

## Implementation notes
- `conftest.py`: `TestClient(app)`; `auth_token` mints JWT for a seeded test user; `test_source` creates a `dp_data_sources` row backed by an in-memory sqlite (with `dialect=sqlite`) so tests run offline.
- Integration tests cover: create+list+get+update+delete each surface, upload+download, chat happy path (mocked LLM), guard rejects DDL end-to-end.
- Auth test: every endpoint returns 401 without token.

## Acceptance
- `pytest backend/tests -q` — all green.
- Coverage `pytest --cov=app --cov-report=term-missing` ≥80% on `dp_*` and `kb_*` service+router modules.

## Verify
```bash
cd backend && pytest tests -q --cov=app.services --cov=app.api.v1.data_platform --cov=app.api.v1.knowledge_base --cov-report=term-missing | tee ../.blueprint/qa/T25/coverage.txt
```

## Commit
`tests: backend pytest coverage (unit + integration + auth gate)`
