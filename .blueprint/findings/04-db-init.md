# 04 — DB 初始化路径

## 结论
Source-of-truth = `Base.metadata.create_all()`（`backend/app/main.py:11-19`），不是 alembic，也不是 schema.sql。

## 候选对比
- `schema.sql`（12 表 DDL，无 seed）→ 过时，缺 MetaTable/Meta*/Ontology* 8 张，且 DROP。别跑。
- `alembic upgrade head` → versions/ 为空 no-op；env.py:8 导老 `app.models`，autogenerate 会拿错 schema。别跑。
- `Base.metadata.create_all()` → main.py:19 lifespan 里，起 app 就建 20 张表。正确。

## Models（20 个）
User, LLMConfig, DataSource, MetaTable, MetaColumn, MetaProfile, OntologyVersion, OntologyClass, OntologyProperty, OntologyRelationship, OntologyConstraint, Instance, Agent, Skill, MCPConfig, AgentRun, Project, Requirement, Plan, Task

## 冷启动
1. 空 DB
2. uvicorn 起 → 自动建 20 表
3. POST /api/v1/auth/register 建首用户
