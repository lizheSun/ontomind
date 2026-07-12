# 03 — 启动路径选择

## 三条路径
| 路径 | 前置 | 迭代 | 坑 |
|---|---|---|---|
| A: docker compose up -d | Docker + 5-10min build | 差 | frontend 冷装慢，未验证 |
| B: MySQL in docker + 本地 backend/frontend | Docker + Py3.12 + Node 20.19+ | 最好 | — |
| C: SQLite 降级 | Py + Node，无 Docker | 好 | 需 aiosqlite + DATABASE_URL 覆盖 |

## 关键
- Redis 不需要跑（代码零 import）
- `.env` 默认 localhost 与 Path B 天然对齐
- AGENT_LOG 无 docker 记录
- **本次场景：用户本机 MySQL root 无密码，走 Path B 变种（复用本机 MySQL）**
