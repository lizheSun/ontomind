# OntoMind 本体构建全流程 — 开发交付 Prompt

> **性质**：可直接交给 opencode / 其它编码 Agent 执行的完整任务书。
> **范围**：Wiki 知识库 + 元数据自动标注 + 本体建模，共 4 个 Phase、17 张新表、3 个新路由域。
> **生成日期**：2026-08-14
> **相关**：[本体产品愿景](../ONTOLOGY_AIBI_DATA_AGENT.md) · [DataOps PRD](./dataops.md) · [AGENT_LOG](../../AGENT_LOG.md)

---

## 调研结论摘要（方案依据）

### 本体应该长什么样

业界共识（Meckler 2024 *Procedure Model for Building Knowledge Graphs*、Palantir Foundry Ontology、FIBO）：
**不要一期上 OWL 重推理**，采用轻量四元组 + 两个治理一等公民。

| 元素 | 作用 | 类比 |
|---|---|---|
| **ObjectType**（类） | 业务实体，可有层级 | 数据库表 / 业务对象 |
| **Property**（数据属性） | 类的字段 | 列 |
| **LinkType**（对象属性） | 类之间的关系，带 domain/range/基数 | 外键 / join 契约 |
| **ActionType**（动作，本期不做） | 写回业务系统 | Foundry Action |
| **Mapping**（映射） | 类/属性 → 物理库表字段 | **本体能否落地的关键** |
| **Metric**（指标口径） | 语义层，如「逾期」定义 | dbt semantic model / metric |

三层关系：本体规定「能有什么」，知识图谱记录「实际有什么」，语义层约定「业务怎么说指标」。

验收靠 **Competency Questions（CQ）** —— 贯穿全开发周期，是 NeOn / OntoScope 等方法论的标准做法。

### LLM 如何建本体

**不是「一次生成整张 OWL」，而是 delta 迭代管道**（RIGOR / NeOn-GPT / Burr benchmark 均为此范式）：

```
Schema + Docs + 领域片段 → Retrieve(相关上下文) → Gen-LLM(delta 本体)
    → Judge-LLM + 规则 Judge → 版本化 merge 进核心 → 回流下一批
```

关键风险控制：LLM 幻觉率 21–50%（JMIR 2025 实测），**必须置信度双阈值 + 人审关卡**。

### Wiki 快速转存

`Readability.js` 正文提取 → `Turndown + GFM` 转 Markdown → 预览二次编辑 → 保存带 front matter 元数据。
企业微信文档 / PPT / Word 走**粘贴 `text/html`** 路径最快，不需要写文件解析器。

### 自动标注

多信号融合：字段名 + 注释 + 类型 + 数据画像 + 血缘 + Wiki 术语命中 → 规则/字典先跑 → LLM 补语义 → 置信度双阈值 → 人机协同确认 → 沉淀为规则复用。

---

## 数据模型设计（新增 17 张表）

### Wiki 组（3 张）

| 表 | 关键字段 |
|---|---|
| `wiki_spaces` | name, slug(uq), description, icon, sort_order |
| `wiki_documents` | space_id, parent_id(树), title, slug, content_md, source_type(paste/markdown/url/manual), source_url, source_meta_json, tags_json, status(draft/published), current_version, word_count, author_user_id |
| `wiki_document_versions` | document_id, version, content_md, title, change_note, author_user_id；UQ(document_id, version) |

### 元数据 + 标注组（5 张）

| 表 | 关键字段 |
|---|---|
| `meta_scan_jobs` | source_id→data_sources, database, job_kind(scan/annotate), scope_json, status, progress, stats_json, error_detail, duration_ms |
| `meta_tables` | source_id, database, table_name, table_type, table_comment, row_count_est, column_count, profile_json, biz_name, biz_description, domain, last_scanned_at；UQ(source_id,database,table_name) |
| `meta_columns` | meta_table_id, column_name, ordinal, data_type, nullable, column_key, column_default, column_comment, profile_json, biz_name, biz_description；UQ(meta_table_id,column_name) |
| `glossary_terms` | name(uq), aliases_json, definition, domain, source_doc_id→wiki_documents, source_type(wiki/manual/llm), status |
| `annotations` | target_type(meta_table/meta_column), target_id, label_kind, label_value, confidence, source(rule/llm/human/glossary_match), evidence_json, status(suggested/accepted/rejected/superseded), reviewed_by_user_id, reviewed_at, job_id |

### 本体组（9 张）

| 表 | 关键字段 |
|---|---|
| `ontologies` | name(uq), display_name, domain, description, status(draft/reviewing/published), current_version |
| `ontology_versions` | ontology_id, version, snapshot_json, change_note, diff_json |
| `ontology_object_types` | ontology_id, key, display_name, parent_key, definition, is_abstract, icon, confidence, source, status |
| `ontology_properties` | object_type_id, key, display_name, data_type, is_primary_key, is_required, unit, definition, confidence, source, status |
| `ontology_link_types` | ontology_id, key, display_name, from_object_type_id, to_object_type_id, cardinality, inverse_key, definition, confidence, source, status |
| `ontology_mappings` | ontology_id, target_type, target_id, source_id, database, table_name, column_name, join_expr, filter_expr, confidence, status |
| `ontology_metrics` | ontology_id, key, display_name, definition_text, sql_expr, grain, object_type_id, unit, owner, status |
| `ontology_cqs` | ontology_id, question, expected_answer_shape, bound_object_keys_json, bound_metric_keys_json, verify_status, verify_note |
| `ontology_build_jobs` | ontology_id, mode, scope_json, status, phase, delta_json, judge_json, accepted_count, rejected_count, error_detail |

---

## 关键技术决策

| 项 | 决策 | 理由 |
|---|---|---|
| 本体存储 | **关系表 + JSON 列**（轻量本体） | 零新依赖，复用现有 Repository 模式；JSON-LD/Turtle 作为导出能力 |
| LLM 调用 | 后端 `app/services/llm_client.py`，用**已有的 httpx** 打 OpenAI 兼容端点 | 批量长任务需落库/重试/审计，前端直连不适合；零新后端依赖 |
| 异步任务 | `threading.Thread(daemon=True)` + job 表轮询 + `get_session_factory()` | 无 celery/redis；`BackgroundTasks` 绑 request 生命周期会截断长任务 |
| 列注释抽取 | `list_columns` 改走 `information_schema.COLUMNS`（`COLUMN_COMMENT`） | **`DESCRIBE` 拿不到注释**，而注释是本体语义的头号来源 |
| 关系推断 | 三路信号投票：命名约定(0.4) + 数据重叠度(0.4) + LLM 语义(0.2) | Doris 无真外键 |
| 置信度阈值 | `≥0.85` 自动 accepted；`0.65~0.85` suggested 待人审；`<0.65` 丢弃 | LLM 幻觉率 21–50% |
| 图可视化 | `@xyflow/react` | `@antv/g6` 已卸载；xyflow 对 React 19 兼容好 |
| Wiki 编辑器 | 复用**已有的 monaco** + `react-markdown`/`remark-gfm` | 不引 CodeMirror |
| HTML→MD | `turndown` + `turndown-plugin-gfm` + `@mozilla/readability` + `dompurify` | 纯前端，隐私友好 |
| 响应格式 | 跟随 DataOps：裸 Pydantic + `response_model=` | 保持域内一致 |

---
---

# 以下为交付给 Agent 的 Prompt 正文

````markdown
# 任务：OntoMind 新增「Wiki 知识库 + 元数据自动标注 + 本体建模」完整链路

你是这个仓库的资深全栈工程师。按下面 4 个 Phase **顺序**实施，每个 Phase 结束必须自检通过再进入下一个。

---

## 0. 先读这些（必须，不要跳）

```
AGENTS.md                                  # 但注意它已过时，见下方「事实纠正」
backend/STANDARDS.md                       # 分层/命名/事务
backend/DESIGN_STANDARDS.md                # API/错误码/DB 命名
frontend/STANDARDS.md
docs/ONTOLOGY_AIBI_DATA_AGENT.md           # ★ 本体产品愿景，第 3/4 章是本任务的语义蓝本
AGENT_LOG.md                               # 只读最后 3 条
backend/app/services/dataops_connector.py  # ★ 要改
backend/app/services/dataops_service.py    # ★ Service 层可信范本
backend/app/db/repositories/data_source_repo.py  # ★ Repository 标准范本（只 flush）
backend/app/api/v1/dataops.py              # ★ API 层范本
backend/app/db/models/data_source_model.py
backend/app/db/models/agent_template_model.py    # ★ 版本快照模式范本
backend/app/db/models/__init__.py
backend/app/api/v1/router.py
backend/app/core/exceptions.py
backend/app/db/session.py
backend/tests/conftest.py
frontend/src/App.tsx
frontend/src/components/layout/AppLayout.tsx
frontend/src/pages/dataops/WarehousePage.tsx      # ★ 三段式 UI 骨架范本
frontend/src/services/dataops.service.ts
frontend/src/styles/global.css              # 设计 token
```

### ⚠️ 事实纠正（AGENTS.md / HANDOFF.md 已过时，以此为准）

- 后端实际 **7 个路由域**（auth/users/opencode/compute/agent-factory/skill-platform/dataops），**104 个端点**，**23 张表**
- 前端已有 6 个业务域壳层（CodeOps/DataOps/ModelOps/AgentOps/GovOps/Infra），落地页是 `/overview`
- 主题已换成 **Apple Design**（SF Pro + `#0071e3` + `#F5F5F7`），不是 Editorial Light
- `monaco-editor` / `@xterm/*` **已装回来**（SmartDevPage 需要），可直接用
- alembic 已删，建表靠 `main.py` 的 `Base.metadata.create_all`

### 🔒 铁律（违反即返工）

1. **Service 层禁用 `with self.db.begin()`** —— 与 FastAPI `get_db` 默认事务冲突，会抛 `InvalidRequestError`。事务边界写法：Repository `self.db.flush()`，Service `self.db.commit()`。`app/services/base_service.py` 是不可用的历史遗留，**不要参考它**。
2. **新增 Model 必须在 `app/db/models/__init__.py` import + 加 `__all__`**，否则 `create_all` 不建表。
3. **新增路由必须在 `app/api/v1/router.py` `include_router`**，否则全部 404。
4. API 层禁止直接查 DB、禁止写业务逻辑、禁止 try/except 业务异常（抛 `BusinessException`/`NotFoundException`/`ConflictException` 让全局 handler 处理）。
5. 响应格式跟随 DataOps 风格：**裸 Pydantic + `response_model=`**，Response schema 加 `model_config = {"from_attributes": True}`。
6. 鉴权统一用 `from app.api.v1.auth import get_current_user_id`，每个端点挂 `_user_id: int = Depends(get_current_user_id)`。
7. **不要引入 celery / redis / rdflib / pandas / langchain / sqlglot**。LLM 调用用**已有的 httpx**。异步任务用独立线程 + job 表轮询。
8. 前端 lint 是 `oxlint`（`npm run lint`），不是 eslint。
9. **antd 是 v6**：`destroyOnClose`→`destroyOnHidden`、`maskClosable`→`mask.closable`、`Drawer width`→`size`、`Space direction`→`orientation`、`<Spin tip>` 独立用不生效。
10. **不要打乱 `AppLayout` 里 `<AideHost />` 的位置** —— 它必须保持跟 `<Outlet/>` 同级、在路由外。
11. 命名严格：`XxxService` / `XxxRepository` / `Xxx`(Model) / `XxxCreate|Update|Response`(Schema)，文件 `xxx_service.py` / `xxx_repo.py` / `xxx_model.py` / `xxx_schema.py`。
12. 前端页面根节点加 `className="page-enter"`，颜色优先用 `var(--*)` CSS 变量。用 `AntApp.useApp()` 拿 `message`/`modal`。
13. **不写任何代码注释**除非解释非直觉的坑。

---

## Phase 0 — 修地基（先做，不做完不许往下）

### 0.1 修 3 个现存 bug

- `backend/tests/test_smoke.py:42` 的域白名单缺 `"dataops"` → 补上（现在这个 test 是 FAIL 的）
- `backend/tests/test_smoke.py:160` 附近的表白名单缺 `"data_sources"` → 补上（现在也 FAIL）
- `frontend/src/services/dataops.service.ts:26` 模板字符串被污染成了字面量 `` `${B}/sources/$569278272835_AWS_us-west-2` ``，应为 `` `${B}/sources/${id}` ``。同类污染检查 `backend/app/services/base_service.py:23,44,51`（错误消息里的占位符），一并修。

跑 `cd backend && pytest`，必须 **0 failed**。

### 0.2 扩展 `dataops_connector.py`（本体的语义原料全靠这里）

在 `DataSourceConnector` 上新增/改造：

```python
def list_tables_meta(self, database) -> list[dict]
    # 走 information_schema.TABLES：
    #   TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, TABLE_ROWS, ENGINE, CREATE_TIME
    # Doris/MySQL 均支持。参数化查询（%s）传 database，不要字符串拼接

def list_columns(self, database, table) -> list[dict]   # ★ 改造现有方法
    # 从 DESCRIBE 改为 information_schema.COLUMNS：
    #   COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE,
    #   IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
    # ⚠️ 必须新增返回字段 comment；保持原有 name/type/nullable/key/default/extra
    #    键名不变，向后兼容 WarehousePage 和 types/dataops.ts

def batch_columns(self, database, tables: list[str]) -> dict[str, list[dict]]
    # 一次连接查 N 张表的列（information_schema.COLUMNS WHERE TABLE_NAME IN (...)）
    # 用途：扫描 33 张表时避免开 33 个连接。参数化 IN 占位符

def profile_column(self, database, table, column, *, sample_rows=10000) -> dict
    # 单列数据画像，全部走一条 SQL 的子查询采样避免全表扫：
    #   SELECT COUNT(*) total, COUNT(`c`) non_null, COUNT(DISTINCT `c`) distinct_count,
    #          MIN(`c`) min_v, MAX(`c`) max_v
    #   FROM (SELECT `c` FROM `db`.`t` LIMIT {sample_rows}) s
    # 返回 {total, null_rate, distinct_count, distinct_ratio, min, max, sampled}
    # 数值/日期类才取 min/max；字符串类额外取 top_k（GROUP BY ORDER BY cnt DESC LIMIT 10）
    # 所有标识符走已有的 _ident() 白名单校验

def overlap_ratio(self, database, left_table, left_col, right_table, right_col, *, limit=10000) -> float
    # 关系候选验证：left 列的值有多少比例能在 right 列里找到
    # SELECT COUNT(*) FROM (SELECT DISTINCT lc FROM lt LIMIT n) l
    #   WHERE lc IN (SELECT DISTINCT rc FROM rt LIMIT n)  → 除以左侧 distinct 数
    # 失败/超时返回 0.0，不要抛异常打断扫描
```

同时：`_connect` 保持不变，但给上面的批量方法**复用同一个连接**（方法内只 connect 一次）。

同步更新 `frontend/src/types/dataops.ts` 的 `ColumnInfo` 加 `comment?: string`，`TableInfo` 加 `comment?: string; row_count?: number`，并让 `WarehousePage` 的元数据表格多展示「注释」列。

### 0.3 新增 LLM Client

新建 `backend/app/services/llm_client.py`：

```python
class LLMClient:
    """OpenAI 兼容 /chat/completions 客户端。只用 httpx，不引 openai SDK。"""
    def __init__(self, *, base_url=None, api_key=None, model=None, timeout=None)
        # 默认从 settings 读

    def chat(self, messages: list[dict], *, temperature=0.2, max_tokens=4096) -> str

    def chat_json(self, messages: list[dict], *, schema_hint: str, temperature=0.1,
                  max_retries=2) -> dict
        # ★ 核心方法。要求：
        #   1. 在 system 里注入 schema_hint，并强制「只输出 JSON，不要 markdown 代码块」
        #   2. 优先带 response_format={"type":"json_object"}；如果端点返回
        #      400/422（不支持该参数），自动降级去掉该参数重试一次
        #   3. 解析时先剥离 ```json fence，再 json.loads
        #   4. 解析失败把原始输出回灌给模型让它修正，最多 max_retries 次
        #   5. 最终失败抛 BusinessException(code="LLM_INVALID_JSON")

    def is_configured(self) -> bool     # LLM_API_KEY 是否非空
```

`backend/app/core/config.py` 新增（放在 DORIS_* 那段后面，保持注释风格一致）：

```python
# === LLM（元数据标注 / 本体生成，OpenAI 兼容端点）===
LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
LLM_API_KEY: str = ""          # 空则标注/本体的 llm 模式直接返回 LLM_NOT_CONFIGURED
LLM_MODEL: str = ""
LLM_TIMEOUT: int = 120
LLM_MAX_CONCURRENCY: int = 4
```

同步补 `backend/.env.example`（若不存在则创建，**不要**把真实 key 写进去）。

未配置 key 时：所有 llm 模式的接口抛 `BusinessException("未配置 LLM，请在 .env 设置 LLM_API_KEY", code="LLM_NOT_CONFIGURED")`，但 **rules 模式必须仍可独立跑通**。

### 0.4 新增后台任务工具

新建 `backend/app/services/job_runner.py`：

```python
def run_in_background(fn, *args, **kwargs) -> None
    # 用 threading.Thread(daemon=True) 启动
    # 内部用 get_session_factory() 开独立 Session，try/except/finally 保证 close
    # 异常时把 error_detail 写回对应 job 行（fn 自己负责，这里只兜底 log）

def guard_job(db, job, fn)  # 可选辅助：统一 status/duration_ms/error_detail 写入
```

> 不要用 `BackgroundTasks` 的 request 生命周期绑定，长任务会被截断。用独立线程 + 独立 Session。

### Phase 0 自检

```bash
cd backend && pytest                 # 0 failed
cd frontend && npm run build         # 0 error
cd frontend && npm run lint
```

手工验证（如果 `.env` 里 Doris 可达）：调 `GET /api/v1/dataops/sources/{id}/columns?database=tmp&table=<任一表>`，返回里**必须有 comment 字段**。

---

## Phase 1 — Wiki 知识库（人工快速转存企微文档/PPT/Word/HTML）

### 目标

用户从企业微信文档 / PPT / Word / 网页 复制内容 → 粘贴进 OntoMind → 自动转 Markdown → 预览校正 → 保存归档。保存动作由人触发。

### 1.1 后端

**Model** `backend/app/db/models/wiki_model.py`：`WikiSpace` / `WikiDocument` / `WikiDocumentVersion`，字段按下表；枚举用 `SAEnum` + `str, enum.Enum` 风格（照抄 `data_source_model.py`）。

| 表 | 字段 |
|---|---|
| `wiki_spaces` | name(128), slug(64,uq,idx), description(512), icon(32), sort_order(int) |
| `wiki_documents` | space_id(FK,idx), parent_id(FK self,nullable,idx), title(256), slug(128,idx), content_md(Text), source_type(SAEnum: paste/markdown/url/manual), source_url(1024), source_meta_json(JSON), tags_json(JSON), status(SAEnum: draft/published), current_version(int,default=1), word_count(int), author_user_id(FK users) |
| `wiki_document_versions` | document_id(FK,idx), version(int), content_md(Text), title(256), change_note(512), author_user_id；UQ(document_id, version) |

**Repository** `wiki_repo.py`：`WikiSpaceRepository` + `WikiDocumentRepository`。方法含 `list_spaces` / `get_space` / `get_space_by_slug` / `add_space` / `delete_space` / `list_documents(space_id=None, keyword=None, tag=None, status=None)` / `get_document` / `add_document` / `delete_document` / `list_versions(doc_id)` / `add_version` / `get_version`。**只 flush**。

关键词搜索：用 `content_md LIKE :kw OR title LIKE :kw`（不要用 FULLTEXT，SQLite 测试环境不支持）。

**Schema** `wiki_schema.py`：`WikiSpaceCreate/Update/Response`、`WikiDocumentCreate/Update/Response`、`WikiDocumentListItem`（不含 content_md，列表用）、`WikiDocumentVersionResponse`、`WikiImportRequest`（`{source_type, title?, content_md, source_url?, source_meta?}`）。

**Service** `wiki_service.py`：
- `create_document` 同时写 v1 到 `wiki_document_versions`
- `update_document` 若 `content_md` 有变化 → `current_version += 1` 并写新版本行
- `rollback_document(doc_id, version)` → 读旧版本写成新版本（不删历史）
- `word_count` 用 `len(content_md)` 粗算（中文按字符）
- `list_documents` 返回轻量 `WikiDocumentListItem`
- **事务：Repository flush → Service `self.db.commit()`**

**API** `backend/app/api/v1/wiki.py`，`router = APIRouter(prefix="/wiki", tags=["Wiki 知识库"])`：

| 方法 | 路径 |
|---|---|
| GET/POST | `/wiki/spaces` |
| GET/PUT/DELETE | `/wiki/spaces/{space_id}` |
| GET | `/wiki/documents`（query: space_id, keyword, tag, status, limit, offset） |
| POST | `/wiki/documents` |
| GET/PUT/DELETE | `/wiki/documents/{doc_id}` |
| GET | `/wiki/documents/{doc_id}/versions` |
| POST | `/wiki/documents/{doc_id}/rollback`（body: `{version}`） |
| POST | `/wiki/import`（统一导入入口，body `WikiImportRequest`） |
| POST | `/wiki/fetch-url`（body `{url}` → 后端 httpx GET 抓 HTML 原文返回，绕过前端 CORS。**必须校验 scheme 只允许 http/https，拒绝内网地址（127./10./172.16-31./192.168./169.254./localhost），超时 10s，响应体上限 5MB**） |

注册进 `router.py`。启动时播种一个默认 space（`slug="default"`, name="默认空间"），幂等，参考 `ensure_seed_doris` 挂在 `main.py`。

### 1.2 前端

新增依赖：
```bash
cd frontend && npm i turndown turndown-plugin-gfm @mozilla/readability dompurify react-markdown remark-gfm
npm i -D @types/turndown @types/dompurify
```

**`frontend/src/utils/htmlToMarkdown.ts`**（核心转换器）：
```ts
export interface ConvertResult { markdown: string; title?: string; warnings: string[] }

export function htmlToMarkdown(html: string, opts?: { extractArticle?: boolean }): ConvertResult
// 流程：
// 1. DOMPurify.sanitize(html, { FORBID_TAGS:['script','style','iframe','object','embed'],
//                               FORBID_ATTR:[/^on/ 全部事件属性] })
// 2. opts.extractArticle（URL 剪藏时为 true）→ 用 @mozilla/readability 提取正文
//    粘贴场景为 false（用户已经选中了要的内容，别再裁剪）
// 3. Turndown（headingStyle:'atx', codeBlockStyle:'fenced', bulletListMarker:'-'）
//    + gfm 插件（表格/删除线/任务列表）
// 4. 自定义 rule：
//    - 企业微信/Word 特有的 <o:p>、mso-* 样式、<span> 无语义包裹 → 剥掉
//    - 合并单元格表格（rowspan/colspan）→ 展开为普通表格，并 push warning
//    - <img src="data:...">（粘贴 Word/PPT 常见）→ 保留 base64 但 push warning
//      「检测到 N 张内嵌图片，体积 X KB」
//    - <pre><code class="language-xx"> → 保留语言标记
//    - MathML / <img class="Wiris"> 公式 → 尝试取 alt 里的 LaTeX，失败则 push warning
// 5. 清理：连续 3+ 空行压成 2 行，行尾空格
export function markdownFromPlainText(text: string): string   // 纯文本兜底
```

**`frontend/src/pages/dataops/knowledge/KnowledgeBasePage.tsx`** — 三栏布局（照 `WarehousePage` 的视觉语言）：
- 左（240px）：空间列表 + 文档树（`wiki_documents.parent_id`），顶部搜索框
- 中：文档阅读态 `react-markdown` + `remark-gfm` 渲染；编辑态用 **monaco**（`language="markdown"`，已有依赖）左右分屏预览
- 右（可折叠）：元信息面板（来源类型 / source_url / 标签 / 版本历史列表 + 回滚按钮）
- 顶部工具条按钮：`新建文档` `粘贴导入` `从 URL 剪藏` `编辑/保存` `版本历史`

**`components/dataops/PasteImportModal.tsx`** — 粘贴导入弹窗（本 Phase 的体验核心）：
```
① 一个大的 contentEditable 落区，提示「Ctrl/Cmd+V 粘贴企业微信文档 / Word / PPT / 网页内容」
② onPaste 处理器：
   e.clipboardData.getData('text/html')  → 有则走 htmlToMarkdown(html, {extractArticle:false})
   否则 getData('text/plain')            → 走 markdownFromPlainText
   ⚠️ 必须 e.preventDefault()，不要让浏览器塞原生 HTML 进 DOM
③ 转换后进入两栏预览：左 monaco 可编辑 Markdown / 右 react-markdown 实时渲染
④ warnings 用 antd Alert（type="warning"）列出来（图片 base64 / 合并单元格 / 公式丢失）
⑤ 表单：标题（自动从第一个 h1 或 <title> 猜）、空间、父文档、标签、来源 URL（可选）
⑥ 「保存」→ POST /wiki/import
⚠️ antd v6：Modal 用 destroyOnHidden，不是 destroyOnClose
```

**`components/dataops/UrlClipModal.tsx`** — 输入 URL → `POST /wiki/fetch-url` 拿 HTML → `htmlToMarkdown(html, {extractArticle:true})` → 同样进预览编辑 → 保存。

**`services/wiki.service.ts`** + **`types/wiki.ts`**：覆盖全部端点，命名函数导出（照 `dataops.service.ts`）。

**路由 & 菜单**：`App.tsx` 把 `dataops/catalog/knowledge` 从 `PlaceholderPage` 换成 `<KnowledgeBasePage />`（菜单项 `/dataops/catalog/knowledge` 已存在，label「知识库」，不用改 AppLayout）。

### Phase 1 自检

- `cd backend && pytest`（新增 `backend/tests/test_wiki.py`：空间 CRUD、文档 CRUD、导入、版本递增、回滚、内网 URL 被拒）
- `cd frontend && npm run build && npm run lint`
- 手工：从任意网页复制一段带标题/列表/表格/代码的内容，粘贴 → 确认 Markdown 结构正确、能保存、能再打开、能编辑产生 v2、能回滚

---

## Phase 2 — 元数据快照 + 自动标注

### 目标

把数仓表结构落库成可标注的快照，然后融合 **规则 + Wiki 术语 + 数据画像 + LLM** 自动产出标注，人工审核确认。

### 2.1 Model `backend/app/db/models/meta_model.py`

`MetaScanJob` / `MetaTable` / `MetaColumn` / `GlossaryTerm` / `Annotation`，字段见方案表。枚举：`ScanStatus`、`JobKind`、`AnnotationTargetType`、`AnnotationLabelKind`、`AnnotationSource`、`AnnotationStatus`、`GlossarySource`。

### 2.2 扫描服务 `meta_scan_service.py`

```python
class MetaScanService:
    def create_scan(self, req) -> MetaScanJob
        # req: {source_id, database, tables?: list[str]|None, with_profile: bool}
        # 建 job(status=pending) → commit → run_in_background(self._run_scan, job.id)
    def get_scan(self, job_id)
    def list_scans(self, source_id=None)
    def _run_scan(self, job_id)
        # 独立 Session。流程：
        # 1. status=running
        # 2. connector.list_tables_meta(database) → upsert meta_tables
        #    （按 UQ(source_id,database,table_name) upsert，保留人工填的 biz_name/biz_description）
        # 3. connector.batch_columns(database, 本批表名) 分批（每批 20 张表）→ upsert meta_columns
        # 4. with_profile 时逐列 connector.profile_column(...) 写 profile_json
        #    ⚠️ 单列失败只记 warning 不中断；每完成一张表更新 job.progress 并 commit
        #    ⚠️ 跳过明显的大宽表画像（column_count > 200 时只画像前 50 列）
        # 5. status=succeeded + stats_json{table_count, column_count, profiled_count, warnings[]}
        # 异常 → status=failed + error_detail
```

### 2.3 术语抽取 `glossary_service.py`

```python
def extract_from_wiki(self, doc_ids: list[int] | None, mode: Literal["rules","llm"]) -> list[GlossaryTerm]
    # rules 模式：正则从 Markdown 抽结构化术语
    #   - 定义列表：`- **术语**：定义` / `| 术语 | 定义 |` 表格 / `### 术语` 后接段落
    # llm 模式：分块（每块 ~4000 字符）喂 LLMClient.chat_json，
    #   schema: {"terms":[{"name","aliases":[],"definition","domain","confidence"}]}
    # 都要写 source_doc_id + source_type，按 name 去重（已存在则合并 aliases）
def list_terms / get_term / create_term / update_term / delete_term
```

### 2.4 标注服务 `annotation_service.py`（本 Phase 核心）

```python
CONF_AUTO_ACCEPT = 0.85
CONF_SUGGEST_MIN = 0.65

class AnnotationService:
    def create_annotate_job(self, req) -> MetaScanJob   # 复用 meta_scan_jobs，用 job_kind 区分
        # req: {source_id, database, tables?, mode: "rules"|"llm"|"hybrid", label_kinds: [...]}

    def _run_annotate(self, job_id)
        # ===== 第一轮：规则 + 术语匹配（无 LLM 也能跑）=====
        # a) 命名规则 → biz_name 候选：
        #    - 拆下划线/驼峰 → 查内置缩写词典（id/no/amt/bal/dt/ts/cnt/flg/pct/ovd/
        #      cust/acct/txn/prod/chnl/apply/loan/repay/… 消金常用，写在
        #      backend/app/services/annotation_rules.py 里当模块常量）
        #    - 表名前缀识别分层：ods_/dwd_/dws_/dim_/fact_/ads_/tmp_ → domain 标注
        # b) glossary 匹配 → label_kind=glossary：
        #    列注释 / 列名 / 表注释 里命中 GlossaryTerm.name 或 aliases（
        #    大小写不敏感 + 中文直接子串）→ confidence 0.9(注释精确命中) /
        #    0.75(列名命中) / 0.7(别名命中)
        # c) PII 识别 → label_kind=pii_level：
        #    正则匹配列名（phone/mobile/tel/idcard/id_no/身份证/email/addr/name/
        #    bank_card/card_no）+ profile_json 的样例值形态校验（手机号 11 位数字、
        #    身份证 18 位）→ L1/L2/L3 分级
        # d) 主键/连接键 → label_kind=join_key：
        #    column_key=='PRI' → 0.95
        #    名字以 _id/_no/_code 结尾 且 profile.distinct_ratio > 0.9 → 0.8
        # e) 实体候选 → label_kind=entity_candidate：
        #    表有单一主键 + row_count 较大 + 表名不含 log/detail/tmp/his → 该表是实体表

        # ===== 第二轮：LLM 补语义（mode 含 llm）=====
        # 按表分批调 LLMClient.chat_json，每次一张表（含全部列），prompt 见 2.5
        # 输入上下文（★ 严格控制预算，别塞整库）：
        #   - 表名 + 表注释 + row_count
        #   - 每列：列名 + 类型 + 注释 + nullable + key + profile 摘要
        #     （null_rate / distinct_ratio / top_k 前 5 个值，敏感列的样例值要脱敏）
        #   - 命中的 glossary 术语定义（最多 20 条）
        #   - 同库其它表名清单（只名字，帮它理解命名体系）
        # 输出 → 写 annotations，source="llm"

        # ===== 第三轮：融合与落库 =====
        # 同一 (target_type,target_id,label_kind) 多来源冲突时：
        #   - 已有 status=accepted 的人工标注 → 新的一律 status=suggested，不覆盖
        #   - 规则与 LLM 一致 → confidence = min(1.0, max(a,b) + 0.1)
        #   - 不一致 → 各自留一条 suggested，evidence_json 记录冲突对方
        # confidence >= 0.85 且无人工冲突 → status=accepted，并把值回写到
        #   meta_tables/meta_columns 的 biz_name/biz_description/domain
        # 0.65 <= c < 0.85 → status=suggested
        # c < 0.65 → 不落库（只计数进 stats_json）
        # 旧的同 key suggested 标注 → status=superseded

    def list_annotations(self, filters)          # target_type/label_kind/status/source/confidence 区间
    def review_annotation(self, ann_id, action: "accept"|"reject", value_override=None,
                          user_id=...)
        # accept → status=accepted, 记 reviewed_by/reviewed_at，回写 meta_* 的业务字段
        # reject → status=rejected
    def batch_review(self, ann_ids, action, user_id)
    def annotate_stats(self, source_id, database) -> dict
        # 覆盖率指标：表/列的 biz_name 覆盖率、注释覆盖率、accepted/suggested/rejected 计数、
        # PII 分级分布、平均 confidence
```

### 2.5 Prompt 模板 `backend/app/services/annotation_prompts.py`

写成模块常量，**不要硬编码在 service 里**。

```
TABLE_ANNOTATE_SYSTEM = """你是资深数据仓库建模专家，精通消费金融业务。
你的任务：为给定的数仓表和字段推断准确的业务语义。

严格规则：
1. 只输出 JSON，不要 markdown 代码块，不要任何解释文字。
2. 每个推断必须给 confidence（0~1）和 evidence（你依据了什么：列名/注释/数据分布/术语表）。
3. 不确定就给低 confidence，禁止编造。宁可 confidence 0.3 也不要瞎猜高分。
4. biz_name 用简洁中文业务名（≤12字），biz_description 说明业务含义与口径（≤80字）。
5. 只能引用「已提供的术语表」里的术语，禁止发明新术语。
6. semantic_type 从固定枚举里选：identifier / person_name / phone / id_card / email /
   address / amount / rate / count / date / timestamp / status_code / category /
   boolean_flag / free_text / json / unknown
7. pii_level：L3(直接身份标识:身份证/手机/银行卡) / L2(可间接识别:姓名/地址/邮箱) /
   L1(敏感业务:金额/额度/评分) / L0(非敏感)
"""

TABLE_ANNOTATE_SCHEMA_HINT = """{
  "table": {"biz_name": str, "biz_description": str, "domain": str,
            "is_entity_table": bool, "confidence": float, "evidence": str},
  "columns": [{"column_name": str, "biz_name": str, "biz_description": str,
               "semantic_type": str, "pii_level": "L0"|"L1"|"L2"|"L3",
               "glossary_term": str|null, "is_join_key": bool,
               "confidence": float, "evidence": str}]
}"""

TABLE_ANNOTATE_USER_TMPL = """..."""   # 填入表/列/画像/术语/同库表名
```

同时准备 `RELATION_INFER_*`（Phase 3 用）。

### 2.6 API `backend/app/api/v1/metadata.py`，`prefix="/metadata"`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/metadata/scans` | 发起扫描 |
| GET | `/metadata/scans` / `/metadata/scans/{job_id}` | 进度轮询 |
| GET | `/metadata/tables` | query: source_id, database, keyword, domain, annotated(bool) |
| GET | `/metadata/tables/{table_id}` | 含 columns |
| PUT | `/metadata/tables/{table_id}` | 人工改 biz_name/biz_description/domain |
| PUT | `/metadata/columns/{column_id}` | 人工改 |
| POST | `/metadata/columns/{column_id}/profile` | 单列重新画像 |
| GET/POST | `/metadata/glossary` | 术语列表/新建 |
| PUT/DELETE | `/metadata/glossary/{term_id}` | |
| POST | `/metadata/glossary/extract` | 从 Wiki 抽术语（body: `{doc_ids?, mode}`） |
| POST | `/metadata/annotate-jobs` | 发起自动标注 |
| GET | `/metadata/annotate-jobs/{job_id}` | |
| GET | `/metadata/annotations` | 待审列表 |
| POST | `/metadata/annotations/{ann_id}/review` | 单条审核 |
| POST | `/metadata/annotations/batch-review` | 批量审核 |
| GET | `/metadata/stats` | 覆盖率看板数据 |

### 2.7 前端

- **`pages/dataops/metadata/MetadataPage.tsx`** 挂到 `/dataops/catalog/biz-systems`（当前是 Placeholder）。左：数据源→库→表树 + 覆盖率进度条；右上：扫描/标注工具条（选库、勾表、mode 选择 rules/llm/hybrid、是否画像）+ job 进度（`Progress` + 2s 轮询）；右下 Tabs：`字段清单`（可内联编辑 biz_name/biz_description，展示 confidence 彩色 Tag + profile 迷你图）/ `数据画像` / `待审标注`
- **`components/dataops/AnnotationReviewPanel.tsx`**：待审标注列表，每行显示 目标 / 标注类型 / 建议值 / confidence / 来源 / evidence（Tooltip 展开）+ `✓采纳` `✗驳回` `改一下再采纳`；顶部支持全选 + 批量采纳（按 confidence 阈值筛选，如「采纳全部 ≥0.8」）
- **`pages/dataops/metadata/GlossaryPage.tsx`** 或 MetadataPage 里一个 Tab：术语表 CRUD + 「从知识库抽取」按钮（选 Wiki 文档 → 抽取 → 预览确认入库）
- `services/metadata.service.ts` + `types/metadata.ts`
- 菜单：`/dataops/catalog/biz-systems` 的 label 从「业务系统」改为「元数据与标注」（改 `AppLayout.tsx:57` 附近）

### Phase 2 自检

- `backend/tests/test_metadata.py`：扫描 job 状态机、upsert 幂等（同一表扫两次不重复且保留人工字段）、规则标注（造假数据验证缩写词典/PII/join_key）、置信度三档分流、review 回写、glossary 规则抽取
- 全部测试用 **mock 的 connector**（`unittest.mock.patch`），不依赖真实 Doris
- 手工（Doris 可达时）：扫 `tmp` 库 33 张表 → 确认 `meta_tables` 33 行、列注释入库 → 跑 rules 标注 → 跑 hybrid 标注 → 审核几条 → 看覆盖率上升

---

## Phase 3 — 本体生成 + 图可视化 + CQ 验收

### 目标

基于「元数据快照 + 已确认标注 + Wiki 术语」，用 **delta 迭代管道** 生成轻量本体（ObjectType/Property/LinkType/Mapping/Metric），人审后版本化发布，用 Competency Questions 验收。

### 3.1 Model `backend/app/db/models/ontology_model.py`

9 张表，字段见方案表。所有 `*_object_types` / `*_properties` / `*_link_types` / `*_mappings` 都带 `confidence` + `source(rule/llm/human)` + `status(draft/accepted/rejected)`，这是人机协同的基础。

`ontology_versions.snapshot_json` 存全量本体 JSON（照 `agent_template_versions.snapshot_json` 模式）：
```json
{"object_types":[...], "properties":[...], "link_types":[...],
 "mappings":[...], "metrics":[...], "cqs":[...]}
```

### 3.2 本体构建服务 `ontology_build_service.py`（核心，delta 迭代管道）

```python
class OntologyBuildService:
    def create_build_job(self, req) -> OntologyBuildJob
        # req: {ontology_id, mode: "rules"|"llm"|"hybrid",
        #       scope: {source_id, database, tables: [...]},
        #       batch_size: int = 8,          # 每个 delta 批次处理几张表
        #       reuse_domain_fragment: str|None}  # 如 "consumer_finance"

    def _run_build(self, job_id)
        """★ 不要一次性喂全库让 LLM 生成整张本体。必须按批 delta 迭代：

        phase=extract:
          把 scope 内的表按「实体表优先、维表次之、事实表最后」排序
          （用 Phase 2 的 entity_candidate 标注 + row_count 判断），
          分成 batch_size 一批。对每批：
            context = Select(
              本批表的 meta_tables/meta_columns + accepted 的 annotations,
              相关 glossary_terms（命中的，上限 30 条）,
              ★ 当前核心本体的「类级摘要」（不是全量！只给
                object_type.key + display_name + 一句 definition + 已有 link 的 key），
              可选的领域片段（消金主干，见 docs/ONTOLOGY_AIBI_DATA_AGENT.md 第 4 章）
            )
            → LLMClient.chat_json 产出 delta：
              {"new_object_types":[], "new_properties":[], "new_link_types":[],
               "mappings":[], "aligned_to_existing":[{"proposed","existing","reason"}],
               "conflicts":[]}

        phase=align:
          delta 与核心本体对齐：
          - key 归一化（snake_case）
          - 同义类合并：display_name/aliases 相似（先字符串归一 + glossary 别名，
            必要时再问一次 LLM 判「这两个类是同一概念吗」）
          - 层级挂载：parent_key 必须已存在，否则降级为顶层类并降 confidence

        phase=judge:
          ★ Judge-LLM 独立校验（换一个 system prompt，扮演审稿人），检查：
          - 类是否真的是业务实体（不是把字段当类、不是把表当类）
          - 关系的 domain/range 是否合理、基数是否正确
          - 是否有循环继承、是否有 OOPS! 常见 pitfall
            （P04 无极性关系 / P07 兄弟类语义重叠 / P11 缺少 domain 或 range /
              P19 多继承误用 / P21 用类当实例）
          - mapping 的列类型与 property 的 data_type 是否兼容
          输出 {"verdicts":[{"target","verdict":"pass"|"warn"|"fail","reason",
                            "confidence_adjust": float}]}
          ★ 同时用「规则 Judge」做机械校验（不花 token）：
            - link_type 的 from/to 必须存在
            - property 必须挂在存在的 object_type 上
            - mapping 引用的 source_id/database/table/column 必须在 meta_* 里存在
            - key 唯一性
          规则 Judge fail 的直接 rejected，不进人审队列。

        phase=merge:
          confidence >= 0.85 且 judge pass → status=accepted 落库
          0.65~0.85 或 judge warn → status=draft 待人审
          judge fail 或 < 0.65 → rejected（记进 delta_json 供排查）
          ★ merge 完成后回流：更新「核心本体类级摘要」，供下一批的 context 使用
          循环下一批，直到 scope 处理完
        """

    def infer_relations(self, ontology_id, scope) -> list[dict]
        """★ Doris 无外键，三路信号投票产出 link_type 候选：
        1) 命名约定：A.x_id 且存在表 X 有主键 id → 候选 A→X，权重 0.4
           （同名列 A.cust_id 与 B.cust_id 都指向 customer → 共享维度）
        2) 数据验证：connector.overlap_ratio(A.x_id → X.id)
           overlap > 0.95 → 权重 0.4；0.8~0.95 → 0.25；< 0.5 → 直接否决
        3) LLM 语义：给两表的业务描述问「它们之间是什么业务关系、基数是多少」→ 权重 0.2
        三者加权求和为 confidence；基数由 A.x_id 的 distinct_ratio 判断
        （接近 1.0 → 1-1，远小于 1 → n-1）
        """

    def publish_version(self, ontology_id, change_note, user_id) -> OntologyVersion
        # 只把 status=accepted 的元素打进 snapshot_json；current_version += 1
        # 生成 diff_json（与上一版对比：added/removed/changed）
    def rollback_version(self, ontology_id, version, user_id)
    def export_ontology(self, ontology_id, fmt: "json"|"jsonld"|"turtle") -> str
        # ★ 手写序列化，不引 rdflib：
        #   json    → snapshot_json 原样
        #   jsonld  → @context 用 rdfs/owl 词表，类→@type rdfs:Class，
        #             property→owl:DatatypeProperty，link→owl:ObjectProperty
        #   turtle  → 字符串模板拼 @prefix + 三元组（转义 " 和 \）
    def graph_data(self, ontology_id, *, focus_key=None, depth=2) -> dict
        # 给前端图用：{nodes:[{id,key,label,parent,confidence,status,table_count}],
        #             edges:[{id,source,target,label,cardinality,confidence,status}]}
        # focus_key 给定时只返回 depth 跳邻域（★ 也是未来 AIBI Context Select 的接口）
```

### 3.3 CQ 服务 `ontology_cq_service.py`

```python
def generate_cqs(self, ontology_id, mode="llm") -> list[OntologyCQ]
    # 让 LLM 基于当前本体生成 10~20 个业务问题（"某客户的逾期合约有哪些？"）
    # 参考 Keet & Khan 2024 的 CQ 分类：存在性/计数/关系遍历/聚合/时间/条件
def verify_cq(self, cq_id) -> dict
    # 校验这个 CQ 能否被本体回答：
    # 1. 抽问题里的业务概念 → 匹配 object_type / metric（LLM 或关键词）
    # 2. 检查涉及的类之间是否有 link_type 路径可达（BFS，depth<=3）
    # 3. 检查涉及的类/属性是否都有 mapping（能落到物理表）
    # → verify_status = pass / fail + verify_note 说明缺什么
    #   （"缺少 LoanContract→RiskEvent 的关系" / "Customer.income 无物理映射"）
def verify_all(self, ontology_id) -> dict   # 返回通过率，这是本体质量的核心指标
```

### 3.4 Metric（语义层口径）

`ontology_metric_service.py`：CRUD + `suggest_metrics(ontology_id)`（从 Wiki 术语里含「率/额/数/占比/逾期/不良」的术语 + 数值列画像，让 LLM 提候选指标及 `sql_expr` 草稿）。**`sql_expr` 只存不执行**（这一期不做指标查询，避免安全面）。

### 3.5 API `backend/app/api/v1/ontology.py`，`prefix="/ontology"`

| 方法 | 路径 |
|---|---|
| GET/POST | `/ontology/ontologies` |
| GET/PUT/DELETE | `/ontology/ontologies/{oid}` |
| POST | `/ontology/ontologies/{oid}/build-jobs`（发起构建） |
| GET | `/ontology/build-jobs/{job_id}`（含 phase + delta 预览） |
| GET/POST | `/ontology/ontologies/{oid}/object-types` |
| PUT/DELETE | `/ontology/object-types/{id}` |
| GET/POST | `/ontology/object-types/{id}/properties` |
| PUT/DELETE | `/ontology/properties/{id}` |
| GET/POST | `/ontology/ontologies/{oid}/link-types` |
| PUT/DELETE | `/ontology/link-types/{id}` |
| POST | `/ontology/ontologies/{oid}/infer-relations` |
| GET/POST | `/ontology/ontologies/{oid}/mappings` |
| PUT/DELETE | `/ontology/mappings/{id}` |
| GET/POST | `/ontology/ontologies/{oid}/metrics` + `/suggest` |
| GET/POST | `/ontology/ontologies/{oid}/cqs` + `/generate` |
| POST | `/ontology/cqs/{id}/verify`、`/ontology/ontologies/{oid}/cqs/verify-all` |
| POST | `/ontology/ontologies/{oid}/review`（批量 accept/reject draft 元素） |
| GET | `/ontology/ontologies/{oid}/graph`（query: focus_key, depth） |
| POST | `/ontology/ontologies/{oid}/publish` |
| GET | `/ontology/ontologies/{oid}/versions` + `/versions/{v}` |
| POST | `/ontology/ontologies/{oid}/rollback` |
| GET | `/ontology/ontologies/{oid}/export?fmt=json\|jsonld\|turtle` |

### 3.6 前端

新增依赖：`cd frontend && npm i @xyflow/react`

**`pages/dataops/ontology/OntologyPage.tsx`** 挂新路由 `/dataops/catalog/ontology`：
- 顶部：本体选择器 + `构建` `发布` `导出` `CQ 验收` 按钮 + 版本号 Tag + CQ 通过率徽标
- 主区 Tabs：
  1. **图视图**（默认）：`@xyflow/react` 渲染类图。节点按 domain 着色，`confidence` 低的用虚线边框，`status=draft` 的半透明；边标注 `cardinality`；点击节点侧滑详情（属性列表 + 映射的物理表 + 相关 CQ）；支持 `focus + depth` 聚焦
  2. **类/属性表**：可编辑表格，confidence 彩色 Tag，批量采纳/驳回
  3. **关系表**：同上，含 `推断关系` 按钮（跑 `infer-relations`，结果展示三路信号明细：命名匹配✓ / 数据重叠 0.97 / LLM 判定 n-1）
  4. **映射视图**：左本体元素 → 右物理表列，两栏连线，未映射的高亮红色（"能不能落地"的核心视图）
  5. **指标（语义层）**：Metric CRUD + suggest
  6. **CQ 验收**：CQ 列表 + pass/fail + `verify_note`（缺什么一目了然）+ 通过率大数字
  7. **版本历史**：版本列表 + `diff_json` 可视化 + 回滚
- 构建任务：抽屉展示 job 的 `phase`（extract→align→judge→merge 步骤条）+ 每批 delta 预览 + judge verdicts，2s 轮询

**`components/dataops/OntologyGraph.tsx`**：封装 xyflow。布局用**分层算法**（按 `parent_key` 继承深度分层 + 同层水平铺开，简单 BFS 即可，不要引 dagre/elk）。

`services/ontology.service.ts` + `types/ontology.ts`。

**路由 & 菜单**：`App.tsx` 加 `<Route path="dataops/catalog/ontology" element={<OntologyPage />} />`；`AppLayout.tsx` 的 `/dataops/catalog` children 数组里，在「数据仓库」之后插入 `{ key: '/dataops/catalog/ontology', label: '本体建模' }`。

### 3.7 内置消金领域片段

`backend/app/services/ontology_fragments.py`：把 `docs/ONTOLOGY_AIBI_DATA_AGENT.md` 第 4 章的主干（Party/Person/Organization/LoanApplication/LoanContract/CreditProduct/LoanAccount/Transaction/RepaymentBehavior/RiskEvent/Collateral/AcquisitionChannel/ScorecardModel/RiskFeature + 第 4.1 节的类簇属性/关系）写成 Python 字典常量 `CONSUMER_FINANCE_FRAGMENT`。构建时作为对齐目标喂给 LLM —— 这让生成结果直接落在业务主干上，而不是随机造类。

### Phase 3 自检

- `backend/tests/test_ontology.py`：CRUD、规则 Judge 的每条校验、confidence 三档分流、`infer_relations` 三路投票（mock connector 的 overlap_ratio）、publish 版本递增 + snapshot 只含 accepted、rollback、export 三种格式非空且 turtle 可被字符串校验（`@prefix` 存在、括号配对）、`graph_data` 的 focus+depth、CQ verify 的可达性 BFS
- `cd backend && pytest` 0 failed；`cd frontend && npm run build && npm run lint`
- 手工端到端：Doris `tmp` 库 → 扫描 → hybrid 标注 → 审核 → 新建本体 → hybrid 构建（batch_size=8）→ 看 delta 分批产出 → 审核 draft → 推断关系 → 补映射 → 生成 CQ → verify-all → 发布 v1 → 导出 turtle

---

## 全局收尾（必做）

1. **更新 `backend/tests/test_smoke.py`**：域白名单加 `"wiki"` `"metadata"` `"ontology"`；表白名单加全部 17 张新表 + 补 `"data_sources"`。
2. **更新 `backend/app/db/models/__init__.py` 的文件头表格**（当前写着 22 张，要改成 40 张并列出新表）。
3. **重生成 `backend/schema.sql`**（文件末尾有再生成命令；当前已落后 18 张表）。
4. **追加 `AGENT_LOG.md`**，照抄已有格式，写：目标 / 决策 / 新增文件 / 修改文件 / 删除文件 / API 端点 / 数据库 / 验证。
5. **重写 `AGENTS.md` 的过时段落**：路由域数量、表数量、模块列表、主题、monaco/xterm 依赖状态、常见坑里补「LLM 未配置时 rules 模式仍须可用」「元数据扫描要走 information_schema 才有注释」。
6. **同步 `HANDOFF.md`** 的 §0 TL;DR / §4.1 表数量 / §9 冒烟预期。
7. 更新本文档（`docs/prd/ontology-build-prompt.md`）为实施后的实际状态，或另建 `docs/prd/ontology.md` 记录最终数据模型。

## 最终验收命令

```bash
cd backend  && pytest                # 必须 0 failed
cd frontend && npm run build         # 必须 0 error
cd frontend && npm run lint          # 必须 0 error
```

## 遇到以下情况必须停下来问，不要自己猜

- 需要引入未列出的新依赖
- Doris 的 `information_schema` 某个字段不存在导致扫描拿不到注释
- 某张表的字段设计你认为有更好方案
- LLM 输出结构反复不稳定，需要改 prompt 策略
- 任何需要改动 `AideHost` / `AppLayout` 的 iframe 常驻逻辑的情况
````

---

## 使用建议

1. **先单独跑 Phase 0**（对 Agent 说「只做 Phase 0」）—— 修好 2 个失败测试和 1 个前端 bug，并把 `information_schema` 改造做掉。这是后面一切的前提，也是最快能验证的部分。
2. `.env` 里先配好 `LLM_API_KEY`（可用 `arkcli auth apikey` 生成，`LLM_BASE_URL` 用默认 Ark 端点）。
3. Phase 2/3 建议先在 Doris `tmp` 库里**只选 3~5 张表**试跑，确认标注和本体质量再放开到全库。

## 参考文献

- Meckler, S. (2024). *Procedure Model for Building Knowledge Graphs for Industry Applications*. arXiv:2409.13425
- Zhong, L. et al. (2023). *A comprehensive survey on automatic knowledge graph construction*. arXiv:2302.05019（582 引用）
- Laskowski, L. et al. (2025). *Burr: A Benchmark for Ontology Learning from Relational Databases*. ACM
- Keet, C.M. & Khan, Z.C. (2024). *Discerning and characterising types of competency questions for ontologies*. arXiv:2412.13688
- Lee, K.H. et al. (2025). *LLM hallucination patterns in SQL generation*. JMIR Medical Informatics 13:e71252（幻觉率 21–50% 实测）
- Zhao, Y., Meroño Peñuela, A., Simperl, E. (2026). *OntoScope: divergent-convergent framework for LLM-based ontology scoping*. ACM
- Palantir Foundry Ontology（Object/Link/Action Type 模型）· dbt Semantic Layer / MetricFlow · FIBO (EDM Council)
