# T06 — dp_* models complete + register + create_all

## Goal
Flesh out all five `dp_*` models with columns per recon; register in `app/db/models/__init__.py`; ensure `Base.metadata.create_all()` in `main.py` picks them up on next boot.

## Files touched
- `backend/app/db/models/dp_data_source_model.py`
- `backend/app/db/models/dp_sql_query_model.py`
- `backend/app/db/models/dp_query_history_model.py`
- `backend/app/db/models/dp_chat_session_model.py`
- `backend/app/db/models/dp_chat_message_model.py`
- `backend/app/db/models/__init__.py`

## Depends on
- T01, T04

## Implementation notes
Column contracts (all snake_case, utf8mb4, InnoDB, Chinese comments):
- **dp_data_sources**: name(String(128) unique), source_type(String(32)), dialect(Enum "mysql"|"postgresql"|"sqlite"|"mysql_readonly"), host(String(255) nullable), port(Integer nullable), username(String(128) nullable), password_enc(Text nullable, Fernet ciphertext), database(String(128)), default_schema(String(128) nullable), charset(String(32) default "utf8mb4"), description(Text nullable), status(Enum "active"|"inactive"|"error" default "active"), owner_user_id(FK users.id), created_by_user_id(FK users.id), read_only_flag(Boolean default True), extra_params(JSON nullable).
- **dp_sql_queries**: name(String(128)), source_id(FK dp_data_sources.id ondelete=CASCADE), sql_text(Text), is_favorite(Boolean default False), owner_user_id(FK users.id).
- **dp_query_history**: source_id(FK), user_id(FK), sql_text(Text), status(Enum "running"|"success"|"error"|"canceled"|"timeout"), row_count(Integer nullable), elapsed_ms(Integer nullable), error_message(Text nullable), columns_json(JSON nullable), started_at(DateTime), finished_at(DateTime nullable). Index on `(user_id, started_at desc)`.
- **dp_chat_sessions**: name(String(128)), source_id(FK), user_id(FK), model_config_id(FK llm_configs.id nullable).
- **dp_chat_messages**: session_id(FK dp_chat_sessions.id ondelete=CASCADE), role(Enum "user"|"assistant"|"system"), content(Text), generated_sql(Text nullable), executed(Boolean default False).

## Acceptance
- Boot backend; `SHOW TABLES` in MySQL includes all 5 new tables with `dp_` prefix.
- Table comments in Chinese.

## Verify
```bash
cd backend && python -c "from app.main import app; from app.db.session import engine; from app.db.base import Base; Base.metadata.create_all(engine)"
mysql -uroot -e "USE ontomind; SHOW TABLES LIKE 'dp_%';" | tee ../.blueprint/qa/T06/tables.txt
# → 5 tables listed
```

## Commit
`dp: complete SQLAlchemy models (5 tables) + register`
