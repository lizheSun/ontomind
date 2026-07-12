# 01 — Backend Runtime 调研

## TL;DR
- venv 已就绪 (Python 3.12.13)，依赖齐全，无需 pip install。
- backend 强依赖 MySQL（`main.py:19` 启动会 `Base.metadata.create_all()`）；Redis 是 requirements.txt 里声明但代码从未 import 的"未使用依赖"，本地起服务不用跑 Redis。
- alembic/versions 为空，`schema.sql` 已过时（比 ORM 少 8 张表）。冷启动只需空 DB → 起 app 自动建 20 张表。
- `.env` 已备好 dev 值，`DATABASE_URL` 支持覆盖。
- 无 seed 无默认账号。

## 关键 file:line
- 入口: `backend/app/main.py:24-32`, `:16-19`(lifespan create_all), `:35-41`(CORS), `:47`(/api/v1 前缀)
- 配置: `backend/app/core/config.py:20-51`, `:26-35`(db_url), `:57`(env_file)
- Session: `backend/app/db/session.py:8`
- 依赖: `backend/requirements.txt`；venv Python 3.12.13
- Alembic: 空 versions/；`env.py:9-12` 读 settings.db_url
- Dockerfile: `backend/Dockerfile:19` --reload
- 无 tests、无 scripts

## 双套 model 坑
`app/models/*.py`（老，扁平）与 `app/db/models/*_model.py`（新）都挂 Base，users/data_sources 重名声明。启动会 warn "Table already defined" 但不阻塞。
