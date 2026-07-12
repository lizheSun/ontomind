# T07 — kb_* models complete + seed kb_libraries + register

## Goal
Flesh out all six `kb_*` models per recon; register in models init; add a boot-time seeder that upserts the 4 kb_libraries rows on first run.

## Files touched
- `backend/app/db/models/kb_library_model.py`
- `backend/app/db/models/kb_data_asset_model.py`
- `backend/app/db/models/kb_code_repo_model.py`
- `backend/app/db/models/kb_document_model.py`
- `backend/app/db/models/kb_experience_model.py`
- `backend/app/db/models/kb_tag_model.py`
- `backend/app/db/models/__init__.py`  (append kb imports)
- `backend/app/db/seed_kb.py`  (NEW)
- `backend/app/main.py`  (lifespan call to seed)

## Depends on
- T01, T04

## Implementation notes
- **kb_libraries** columns: code (Enum "data_asset"|"code_repo"|"document"|"experience" unique), name_zh(String(64)), icon(String(64)), description(Text), order(Integer).
- **kb_data_assets**: library_id(FK), title_zh(String(255)), title_en(String(255) nullable), domain(String(64) nullable), owner_user_id(FK), description_md(MEDIUMTEXT), ref_meta_table_id(FK meta_tables.id nullable), ref_data_source_id(FK data_sources.id nullable), tags(JSON), created_by_user_id(FK). `FULLTEXT(title_zh, description_md)` if MySQL 5.7+.
- **kb_code_repos**: title_zh, repo_url(String(512)), branch(String(128) default "main"), language(String(32)), description_md, tags(JSON), owner_user_id, created_by.
- **kb_documents**: title_zh, filename(String(255)), storage_path(String(512)), mime_type(String(128)), size_bytes(BigInteger), description_md, tags(JSON), owner_user_id, created_by.
- **kb_experiences**: title_zh, scenario(String(255)), content_md, outcome(String(255) nullable), tags(JSON), owner_user_id, created_by.
- **kb_tags**: name(String(64) unique), color(String(32) default "blue").
- Seeder inserts rows: `(1,"data_asset","数据资产","DatabaseOutlined","按业务域整理的数据资产目录",1)`, `(2,"code_repo","代码库","GithubOutlined","内外部代码仓库索引",2)`, `(3,"document","文档库","FileTextOutlined","制度、SOP、方案与手册",3)`, `(4,"experience","业务经验库","BulbOutlined","一线业务经验沉淀",4)`.

## Acceptance
- Boot backend; `SELECT * FROM kb_libraries` returns 4 rows in stable order.
- FULLTEXT index present on kb_data_assets (MySQL only).

## Verify
```bash
cd backend && uvicorn app.main:app --port 8000 &
sleep 3
mysql -uroot -e "USE ontomind; SELECT code, name_zh FROM kb_libraries ORDER BY \`order\`;" | tee ../.blueprint/qa/T07/seed.txt
kill %1
```

## Commit
`kb: complete SQLAlchemy models (6 tables) + seed libraries`
