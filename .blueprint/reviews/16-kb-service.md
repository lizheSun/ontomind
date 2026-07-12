# Task 16 — KbService review

## Verdict
APPROVE

## Reasoning
- All 13 acceptance criteria pass end-to-end:
  1. `__init__` instantiates all 6 repos (lib/asset/repo/doc/exp/tag) — lines 62-68.
  2. `list_libraries` uses `list_ordered()`; `get_library_by_code` returns Read schema or raises `KB_LIB_NOT_FOUND`.
  3. All four sub-libs expose `list_/create_/update_/delete_` with owner-only ACL via `_require_owned_*` returning `KB_*_NOT_FOUND` (opaque 404, no info leak).
  4. `_ensure_library_id_matches` (lines 377-397) raises `KB_LIB_MISMATCH` (400) on code mismatch, `KB_LIB_INVALID` on missing id.
  5. `_register_tags` filters non-string / whitespace names, no-ops on empty, delegates to `tag_repo.upsert_names` — idempotent.
  6. `upload_document` awaits `file.read()`, raises `KB_DOC_EMPTY` (400) on empty, calls `doc_repo.create_with_file(...)` inside `_tx()`.
  7. `get_document_bytes` raises `KB_DOC_FILE_MISSING` when `absolute_path(row).is_file()` is False.
  8. `search_all` returns `KbSearchGrouped`; empty/whitespace q returns empty groups (early return); `library_code` filter narrows via `{code} ∩ _SUB_LIB_CODES`; snippets are per-lib correct (asset=description slice, repo=repo_url, document=filename, experience=scenario|content_md slice).
  9. `_tx()` correctly uses `db.begin_nested()` when `in_transaction()` else `db.begin()` — matches task spec, sibling of T13's `_reset_autobegin()` (both accepted).
  10. Every write path is wrapped in `with self._tx():`; no bare `db.commit()` in service.
  11. Evidence file shows `11 passed in 0.23s`.
  12. `conftest.py` has: MEDIUMTEXT→TEXT compile shim (line 19-21), FULLTEXT index strip (line 24-32), in-memory sqlite engine per test, `expire_on_commit=False` (line 46), 4-lib seeder returning `code→id` dict (lines 82-104).
  13. Diff stats confirm only 4 new files under `backend/app/services/` and `backend/tests/knowledge_base/`; no models/repos/schemas/routers/other services touched.

- Owner ACL uses `NotFoundException` for both "missing" and "wrong owner" (avoids leaking existence) — consistent with typical Least-Privilege pattern.
- Search filter set-intersection with `_SUB_LIB_CODES` gracefully handles unknown `library_code` values (returns empty groups without exception).
- `search_all` respects the per-lib snippet strategy in the task spec, including experience's `scenario` fallback to `content_md` slice.
- Async upload test exercises the `create_with_file` path with tmp UPLOAD_DIR and validates readback — real physical write round-trip.

## Required changes (if any)
None.

## Nice-to-haves (non-blocking)
- Consider adding `owner_only=True` implicit for non-superuser callers at the router layer later (out of scope here).
- `_ensure_library_id_matches` could be cached per-request since the 4 libs are seed data — micro-opt only.
