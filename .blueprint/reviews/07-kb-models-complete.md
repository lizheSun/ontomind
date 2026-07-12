# Review — Task 07: kb_* models complete + seed 4 libraries

## Verdict
APPROVE

## Reasoning
- All 6 kb_* models have complete columns per spec, with Chinese `comment=` on every column and table; T04 skeleton stubs replaced cleanly.
- `kb_libraries.code` is an `Enum('data_asset','code_repo','document','experience')` with `unique=True`; sort field correctly named `sort_order` (not the reserved `order`).
- `kb_data_assets` includes all required FKs (library_id, owner_user_id, created_by_user_id, ref_meta_table_id → meta_tables.id nullable, ref_data_source_id → data_sources.id nullable), `description_md=MEDIUMTEXT`, `tags=JSON`, plus FULLTEXT composite index `ft_kb_data_assets_title_desc` on (title_zh, description_md) via `mysql_prefix="FULLTEXT"` — SQLite/PG safely ignore it.
- `kb_documents.size_bytes = BigInteger` ✅ (not Integer); `kb_experiences.content_md = MEDIUMTEXT` ✅; `kb_code_repos.branch` has `server_default='main'`; `kb_tags` has unique `name` + `color` with default `blue`.
- `seed_kb.py` is idempotent: queries `KbLibrary.code == row['code']` and only `session.add` when missing; 4 seed rows match spec exactly (data_asset/DatabaseOutlined, code_repo/GithubOutlined, document/FileTextOutlined, experience/BulbOutlined; sort_order 1–4).
- `main.py` change is surgical (8 lines inside lifespan before `yield`, lazy imports from `app.db.session` + `app.db.seed_kb`, try/finally close) — file is not rewritten.
- `__init__.py` appends 6 imports under a labeled `# --- Knowledge Base (T07) ---` section and extends `__all__`; T04/T05/T06 entries above are untouched.
- Diff stat shows only 10 files, all under `backend/app/db/models/kb_*`, `seed_kb.py`, `__init__.py`, `main.py`, plus evidence file — no dp_* file touched.
- Evidence (`.blueprint/qa/T07/seed.txt`) shows all 6 kb_ tables created and 4 kb_libraries rows with correct code/name/icon/sort_order.

## Required changes
None.

## Nice-to-haves (non-blocking)
- Evidence file only captures one seed pass; a second `SELECT COUNT(*) FROM kb_libraries;` after a re-run would explicitly demonstrate idempotency, but the code path (query-then-add on unique `code`) makes duplication impossible by design.
- `KbTag` model has no `library_id` — spec confirms tags are shared across sub-libraries, so this is intentional; worth a brief inline note if future tasks assume per-library tags.
