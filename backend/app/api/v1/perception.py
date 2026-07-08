"""感知层 API - 数据源连接器 & 文档管理."""
import json
import re
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.data_source_schema import (
    DataSourceCreate, DataSourceUpdate, AutoConfigureRequest,
)
from app.services.data_source_service import DataSourceService

router = APIRouter()


def get_ds_service(db: Session = Depends(get_db)) -> DataSourceService:
    return DataSourceService(db)


# LLM 字段别名映射
_FIELD_ALIASES = {
    "type": "source_type",
    "db_type": "source_type",
    "dbtype": "source_type",
    "sourceType": "source_type",
    "user": "username",
    "passwd": "password",
    "pwd": "password",
    "db": "database",
    "db_name": "database",
    "dbname": "database",
    "schema": "database",
    "encoding": "charset",
    "server": "host",
    "addr": "host",
    "url": "host",
}


def _normalize_parsed(parsed: dict) -> dict:
    """标准化 LLM 返回的字段名，确保使用统一字段名。"""
    # 1. 映射别名
    for alias, target in _FIELD_ALIASES.items():
        if alias in parsed and alias != target:
            if not parsed.get(target):
                parsed[target] = parsed[alias]

    # 2. 确保必要字段存在
    parsed.setdefault("name", "未命名数据源")
    parsed.setdefault("source_type", "unknown")
    parsed.setdefault("host", None)
    parsed.setdefault("port", None)
    parsed.setdefault("username", None)
    parsed.setdefault("password", None)
    parsed.setdefault("database", None)
    parsed.setdefault("charset", "utf8mb4")
    parsed.setdefault("description", "")

    return parsed


# ========== 数据源 CRUD ==========

@router.get("/datasources")
async def list_data_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    svc: DataSourceService = Depends(get_ds_service),
):
    """获取数据源列表."""
    data = svc.list(skip, limit)
    return {"code": "SUCCESS", "message": "查询成功", "data": data, "total": len(data)}


@router.post("/datasources")
async def create_data_source(
    payload: DataSourceCreate,
    svc: DataSourceService = Depends(get_ds_service),
):
    """注册新的数据源连接."""
    data = svc.create(payload)
    return {"code": "SUCCESS", "message": "创建成功", "data": data}


@router.get("/datasources/{source_id}")
async def get_data_source(
    source_id: int,
    svc: DataSourceService = Depends(get_ds_service),
):
    """获取数据源详情."""
    data = svc.get(source_id)
    return {"code": "SUCCESS", "message": "查询成功", "data": data}


@router.put("/datasources/{source_id}")
async def update_data_source(
    source_id: int,
    payload: DataSourceUpdate,
    svc: DataSourceService = Depends(get_ds_service),
):
    """更新数据源."""
    data = svc.update(source_id, payload)
    return {"code": "SUCCESS", "message": "更新成功", "data": data}


@router.delete("/datasources/{source_id}")
async def delete_data_source(
    source_id: int,
    svc: DataSourceService = Depends(get_ds_service),
):
    """删除数据源."""
    svc.delete(source_id)
    return {"code": "SUCCESS", "message": "删除成功"}


# ========== LLM 智能解析 ==========

@router.post("/datasources/parse-config")
async def parse_config(
    payload: AutoConfigureRequest,
    db: Session = Depends(get_db),
):
    """使用 LLM 解析原始配置文本，返回结构化配置（不保存）."""
    from app.services.llm_config_service import LLMConfigService

    llm_svc = LLMConfigService(db)

    system_prompt = """你是一个数据源配置解析器。用户会提供原始配置文本（如环境变量、连接串等），你需要解析并返回结构化 JSON。

规则：
1. 自动识别数据源类型，映射关系：
   - DORIS_/doris -> "doris"
   - MYSQL_/mysql/DB_ -> "mysql"
   - PG_/POSTGRES_/postgresql -> "postgresql"
   - CLICKHOUSE_/clickhouse -> "clickhouse"
   - KAFKA_/kafka/broker/bootstrap -> "kafka"
   - MONGO_/mongodb -> "mongodb"
   - REDIS_/redis -> "redis"
   - API/HTTP/endpoint/url -> "api"
   - JDBC URL 中的 jdbc:mysql -> "mysql", jdbc:postgresql -> "postgresql"
2. 提取字段映射（大小写不敏感）：
   - HOST/server/endpoint/url/addr/broker/boostrap_servers -> host
   - PORT -> port（转为整数）
   - USER/username/user_name/UID -> username
   - PASSWORD/PWD/passwd/secret -> password
   - DATABASE/DB/db_name/schema/SCHEMA -> database
   - CHARSET/encoding/CHARACTER_SET -> charset
3. name: 生成一个简短有意义的名称（如 "Doris 数据仓库"、"MySQL 业务库"）
4. description: 简要描述用途
5. 只返回纯 JSON，不要 markdown 代码块，不要额外文字。
6. 如果无法识别类型，source_type 用 "unknown"，其他字段尽量提取。

返回格式示例：
{"name":"Doris 数据源","source_type":"doris","host":"10.18.1.249","port":9031,"username":"root","password":"DORIS#zx20240620","database":"tmp","charset":"utf8mb4","description":"Apache Doris 数据仓库"}"""

    try:
        result = await llm_svc.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.raw_text},
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        content = result["content"].strip()

        # 处理可能的 markdown 代码块包裹或推理过程前缀
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}', content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        parsed = json.loads(content)

        # 字段别名映射（LLM 可能返回不标准的字段名）
        _normalize_parsed(parsed)

        # 转换 port 为整数
        if parsed.get("port") and isinstance(parsed["port"], str):
            try:
                parsed["port"] = int(parsed["port"])
            except ValueError:
                parsed["port"] = None

        return {
            "code": "SUCCESS",
            "message": "解析成功",
            "data": {
                "parsed": parsed,
                "raw_text": payload.raw_text,
                "model_used": result.get("model"),
            },
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail=f"LLM 返回格式异常，无法解析为 JSON: {content[:300]}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 一键测试连接 ==========

@router.post("/datasources/{source_id}/test")
async def test_connection(
    source_id: int,
    db: Session = Depends(get_db),
    svc: DataSourceService = Depends(get_ds_service),
):
    """测试数据源连接，失败时调用 LLM 诊断."""
    try:
        result = svc.test_connection(source_id)

        if result["success"]:
            svc.update_status(source_id, "active")
        else:
            # 连接失败，尝试用 LLM 诊断
            try:
                from app.services.llm_config_service import LLMConfigService
                llm_svc = LLMConfigService(db)
                ds = svc.get(source_id)
                diagnosis = await llm_svc.chat_completion(
                    messages=[
                        {"role": "system", "content": "你是数据库连接诊断专家。根据错误信息和配置，用中文给出简短的诊断建议（2-3句话）。"},
                        {"role": "user", "content": f"数据源类型: {ds['source_type']}\n主机: {ds['host']}:{ds['port']}\n数据库: {ds['database']}\n用户名: {ds['username']}\n错误: {result['message']}\n\n请给出诊断建议。"},
                    ],
                    temperature=0.3,
                    max_tokens=512,
                )
                result["diagnosis"] = diagnosis["content"].strip()
            except Exception:
                result["diagnosis"] = "请检查网络连通性、防火墙规则、用户名密码是否正确。"

            svc.update_status(source_id, "error")

        return {"code": "SUCCESS", "message": "测试完成", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


# ========== 一键智能添加（解析 + 保存 + 测试） ==========

@router.post("/datasources/auto-configure")
async def auto_configure(
    payload: AutoConfigureRequest,
    db: Session = Depends(get_db),
    svc: DataSourceService = Depends(get_ds_service),
):
    """智能添加数据源: LLM 解析 -> 保存 -> 测试连接."""
    from app.services.llm_config_service import LLMConfigService
    from app.schemas.data_source_schema import DataSourceCreate

    llm_svc = LLMConfigService(db)

    # Step 1: LLM 解析
    system_prompt = """你是一个数据源配置解析器。用户会提供原始配置文本（如环境变量、连接串等），你需要解析并返回结构化 JSON。

规则：
1. 自动识别数据源类型，映射关系：
   - DORIS_/doris -> "doris"
   - MYSQL_/mysql/DB_ -> "mysql"
   - PG_/POSTGRES_/postgresql -> "postgresql"
   - CLICKHOUSE_/clickhouse -> "clickhouse"
   - KAFKA_/kafka/broker/bootstrap -> "kafka"
   - MONGO_/mongodb -> "mongodb"
   - REDIS_/redis -> "redis"
   - API/HTTP/endpoint/url -> "api"
   - JDBC URL 中的 jdbc:mysql -> "mysql", jdbc:postgresql -> "postgresql"
2. 提取字段映射（大小写不敏感）：
   - HOST/server/endpoint/url/addr/broker/boostrap_servers -> host
   - PORT -> port（转为整数）
   - USER/username/user_name/UID -> username
   - PASSWORD/PWD/passwd/secret -> password
   - DATABASE/DB/db_name/schema/SCHEMA -> database
   - CHARSET/encoding/CHARACTER_SET -> charset
3. name: 生成一个简短有意义的名称
4. description: 简要描述用途
5. 只返回纯 JSON，不要 markdown 代码块，不要额外文字。"""

    try:
        llm_result = await llm_svc.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.raw_text},
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        content = llm_result["content"].strip()
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}', content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        parsed = json.loads(content)
        parsed.setdefault("name", "未命名数据源")
        # 字段别名映射
        _normalize_parsed(parsed)

        if parsed.get("port") and isinstance(parsed["port"], str):
            try:
                parsed["port"] = int(parsed["port"])
            except ValueError:
                parsed["port"] = None

    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail=f"LLM 返回格式异常，无法解析为 JSON: {content[:300]}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 2: 保存到数据库
    try:
        create_data = DataSourceCreate(**parsed)
        ds_data = svc.create(create_data)
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"保存失败: {str(e)}")

    # Step 3: 测试连接
    test_result = svc.test_connection(ds_data["id"])

    if test_result["success"]:
        svc.update_status(ds_data["id"], "active")
    else:
        # LLM 诊断
        try:
            diagnosis_result = await llm_svc.chat_completion(
                messages=[
                    {"role": "system", "content": "你是数据库连接诊断专家。根据错误信息和配置，用中文给出简短诊断建议（2-3句话）。"},
                    {"role": "user", "content": f"数据源类型: {parsed['source_type']}\n主机: {parsed['host']}:{parsed['port']}\n数据库: {parsed['database']}\n用户名: {parsed['username']}\n错误: {test_result['message']}\n\n请给出诊断建议。"},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            test_result["diagnosis"] = diagnosis_result["content"].strip()
        except Exception:
            test_result["diagnosis"] = "请检查网络连通性、防火墙规则、用户名密码是否正确。"

        svc.update_status(ds_data["id"], "error")

    ds_data["status"] = "active" if test_result["success"] else "error"

    return {
        "code": "SUCCESS",
        "message": "智能添加完成",
        "data": {
            "datasource": ds_data,
            "parsed_config": parsed,
            "test_result": test_result,
        },
    }


# ========== 元数据提取与管理 ==========

@router.post("/datasources/{source_id}/sync")
async def sync_data_source(source_id: int, payload: dict = None, db: Session = Depends(get_db)):
    """同步数据源元数据 — 提取表结构、字段信息、注释到 MySQL.

    请求体: { "database": "指定库", "sync_all": false }
    - database: 指定库名，不传则用数据源默认库
    - sync_all: true 则同步所有用户库（跳过系统库）
    """
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    database = payload.get("database") if payload else None
    sync_all = (payload or {}).get("sync_all", False)
    result = svc.extract_metadata(source_id, database, sync_all=sync_all)
    return {"code": "SUCCESS", "message": f"同步完成: {result['tables_synced']} 张表, {result['columns_synced']} 个字段, {len(result.get('databases', []))} 个库", "data": result}


@router.get("/datasources/{source_id}/databases")
async def list_databases(source_id: int, db: Session = Depends(get_db)):
    """列出数据源上所有可用的数据库."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    dbs = svc.list_databases(source_id)
    return {"code": "SUCCESS", "data": dbs}


@router.get("/datasources/{source_id}/tables")
async def list_meta_tables(source_id: int, database: str = Query(None), db: Session = Depends(get_db)):
    """获取数据源的表元数据列表."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    tables = svc.list_tables(source_id, database)
    return {"code": "SUCCESS", "data": tables, "total": len(tables)}


@router.get("/meta/tables/{table_id}")
async def get_meta_table_detail(table_id: int, db: Session = Depends(get_db)):
    """获取表元数据详情（含字段列表）."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    data = svc.get_table_detail(table_id)
    return {"code": "SUCCESS", "data": data}


@router.put("/meta/tables/{table_id}")
async def update_meta_table(table_id: int, payload: dict, db: Session = Depends(get_db)):
    """更新表业务元数据（人工编辑）."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    data = svc.update_table_meta(table_id, payload)
    return {"code": "SUCCESS", "message": "更新成功", "data": data}


@router.post("/meta/tables/{table_id}/profile")
async def profile_table(table_id: int, payload: dict = None, db: Session = Depends(get_db)):
    """对表中每个字段抽样画像（空值率/枚举/格式/最值），落库供约束抽取使用.

    请求体: { "force": false }
    """
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    force = (payload or {}).get("force", False)
    result = svc.profile_data(table_id, force)
    return {"code": "SUCCESS", "message": result["message"], "data": result}


@router.get("/meta/tables/{table_id}/profile")
async def get_table_profile(table_id: int, db: Session = Depends(get_db)):
    """获取某表的字段画像结果列表."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    data = svc.get_profile(table_id)
    return {"code": "SUCCESS", "data": data}


@router.put("/meta/columns/{column_id}")
async def update_meta_column(column_id: int, payload: dict, db: Session = Depends(get_db)):
    """更新字段业务元数据（人工编辑）."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    data = svc.update_column_meta(column_id, payload)
    return {"code": "SUCCESS", "message": "更新成功", "data": data}


@router.post("/meta/tables/{table_id}/preview")
async def preview_table_data(table_id: int, payload: dict = None, db: Session = Depends(get_db)):
    """实时连接数据源，预览表数据."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    limit = (payload or {}).get("limit", 100)
    offset = (payload or {}).get("offset", 0)
    data = svc.preview_data(table_id, limit, offset)
    return {"code": "SUCCESS", "data": data}


@router.post("/meta/tables/{table_id}/annotate")
async def auto_annotate_table(table_id: int, payload: dict = None, db: Session = Depends(get_db)):
    """使用 LLM 或指定 Agent 自动生成表和字段的注释/描述.

    请求体: { "force": false, "agent_id": null }
    - force: 是否强制重新生成所有注释
    - agent_id: 指定资源管理里的 Agent ID，None 则用平台 LLM
    """
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    force = (payload or {}).get("force", False)
    agent_id = (payload or {}).get("agent_id")
    result = await svc.auto_annotate(table_id, force, agent_id=agent_id)
    return {"code": "SUCCESS", "message": result["message"], "data": result}


@router.websocket("/meta/tables/{table_id}/annotate/stream")
async def stream_annotate(websocket: WebSocket, table_id: int):
    """
    WebSocket 流式标注 — 类似 Cursor/CodeBuddy 的交互体验。

    前端发送: {"prompt": "自定义 prompt", "agent_id": 1, "force": false}
    后端实时推送:
      {"type":"status","content":"正在准备元数据..."}
      {"type":"context","content":"表名: xxx, 字段: ..."}  (发送上下文给前端展示)
      {"type":"prompt","content":"发送给 Agent 的完整 prompt"}
      {"type":"thinking","content":"Agent 思考过程..."}  (CLI 流式输出)
      {"type":"text","content":"Agent 回复..."}
      {"type":"tool_use","tool":"...","input":{...}}
      {"type":"error","content":"错误信息"}
      {"type":"applied","content":"已应用 N 条注释"}
      {"type":"done"}
    """
    import os
    import re
    import subprocess
    import asyncio
    from app.db.session import SessionLocal
    from app.services.metadata_service import MetadataService
    from app.db.models.metadata_model import MetaTable, MetaColumn
    from app.db.models.agent_model import Agent
    from app.services.agent_discovery import KNOWN_AGENTS

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            custom_prompt = payload.get("prompt", "").strip()
            agent_id = payload.get("agent_id")
            force = payload.get("force", False)

            db = SessionLocal()
            svc = MetadataService(db)

            table = db.query(MetaTable).filter(MetaTable.id == table_id).first()
            if not table:
                await websocket.send_text(json.dumps({"type": "error", "content": "元数据表不存在"}))
                db.close()
                break

            columns = svc.col_repo.get_by_table(table_id)

            await websocket.send_text(json.dumps({"type": "status", "content": f"📋 加载表元数据: {table.database_name}.{table.table_name}"}))

            # 构建上下文展示
            col_info = "\n".join(
                f"  - {c.column_name} ({c.data_type_full or c.data_type}) PK={c.is_primary_key} 注释={c.column_comment or '无'}"
                for c in columns
            )
            context_text = f"表名: {table.table_name}\n表注释: {table.table_comment or '无'}\n字段数: {len(columns)}\n字段列表:\n{col_info}"
            await websocket.send_text(json.dumps({"type": "context", "content": context_text}))

            # 构建 prompt（用户可自定义）
            default_prompt = f"""请分析以下数据库表的元数据，为表和字段生成中文业务描述。

表名: {table.table_name}
表注释: {table.table_comment or '无'}
字段列表:
{col_info}

请返回 JSON 格式（不要 markdown 代码块），结构如下：
{{
  "table_description": "这张表的业务用途描述（1-2句话）",
  "purpose": "用途标签，从以下选一个: dim/fact/ods/dwd/dws/tmp/config/log/other",
  "domain": "业务域，如: 用户/订单/商品/支付/营销/库存/财务/通用",
  "columns": [
    {{
      "name": "字段名",
      "comment": "字段的中文业务描述",
      "semantic_type": "语义类型，从以下选一个: id/name/amount/time/status/category/description/count/ratio/flag/url/email/phone/code/other"
    }}
  ]
}}"""

            final_prompt = custom_prompt if custom_prompt else default_prompt
            system_prompt = "你是数据治理专家，擅长理解数据库表结构并生成业务描述。只返回纯 JSON。"

            await websocket.send_text(json.dumps({"type": "prompt", "content": final_prompt[:500] + ("..." if len(final_prompt) > 500 else "")}))

            # 执行标注
            if agent_id:
                # ===== Agent CLI 流式模式 =====
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    await websocket.send_text(json.dumps({"type": "error", "content": f"Agent 不存在: {agent_id}"}))
                    db.close()
                    break

                entrypoint = (agent.entrypoint or "").strip()
                if not entrypoint:
                    await websocket.send_text(json.dumps({"type": "error", "content": "Agent 未配置 entrypoint"}))
                    db.close()
                    break

                if entrypoint.startswith("http"):
                    await websocket.send_text(json.dumps({"type": "error", "content": "HTTP 模式 Agent 暂不支持流式，请用平台 LLM 或 CLI Agent"}))
                    db.close()
                    break

                cli_path = entrypoint.split()[0]
                extra_args = entrypoint.split()[1:] if len(entrypoint.split()) > 1 else []
                agent_info = KNOWN_AGENTS.get(agent.agent_type, {})
                cli_chat_args = agent_info.get("cli_chat_args", ["{msg}"])

                agent_name = ""
                if agent.env_template and isinstance(agent.env_template, dict):
                    agent_name = agent.env_template.get("agent_name", "")
                if not agent_name and agent_info.get("cli_list_agents_args"):
                    from app.services.agent_discovery import _get_first_agent_name
                    agent_name = _get_first_agent_name(cli_path, agent_info["cli_list_agents_args"]) or ""

                full_prompt = f"{system_prompt}\n\n{final_prompt}"
                args = [arg.replace("{msg}", full_prompt).replace("{agent_name}", agent_name) for arg in cli_chat_args]

                env = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
                cli_env = agent_info.get("cli_env", {})
                env.update(cli_env)

                await websocket.send_text(json.dumps({"type": "status", "content": f"⚡ 执行 Agent: {agent.name}..."}))

                try:
                    proc = await asyncio.create_subprocess_exec(
                        *([cli_path] + extra_args + args),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                    )
                except FileNotFoundError:
                    await websocket.send_text(json.dumps({"type": "error", "content": f"CLI 命令不存在: {cli_path}"}))
                    db.close()
                    break

                ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
                stdout_buffer = []

                async for raw_line in proc.stdout:
                    line = raw_line.decode(errors="ignore").rstrip("\n\r")
                    line_clean = ansi_escape.sub("", line).strip()
                    if not line_clean:
                        continue
                    stdout_buffer.append(line_clean)

                    try:
                        evt = json.loads(line_clean)
                        evt_type = evt.get("type", "")
                        if evt_type in ("text", "message"):
                            await websocket.send_text(json.dumps({"type": "text", "content": evt.get("content", "")}))
                        elif evt_type in ("thinking", "reasoning"):
                            await websocket.send_text(json.dumps({"type": "thinking", "content": evt.get("content", "")}))
                        elif evt_type == "tool_use":
                            await websocket.send_text(json.dumps({"type": "tool_use", "tool": evt.get("tool", ""), "input": evt.get("input", {})}))
                        elif evt_type == "tool_result":
                            await websocket.send_text(json.dumps({"type": "tool_result", "tool": evt.get("tool", ""), "output": str(evt.get("output", ""))[:500]}))
                        elif evt_type == "error":
                            err_data = evt.get("error", {})
                            err_msg = err_data.get("data", {}).get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
                            await websocket.send_text(json.dumps({"type": "error", "content": err_msg}))
                        elif evt_type == "status":
                            await websocket.send_text(json.dumps({"type": "status", "content": evt.get("content", "")}))
                        else:
                            await websocket.send_text(json.dumps({"type": "log", "content": line_clean[:500]}))
                    except (json.JSONDecodeError, ValueError):
                        if not any(s in line_clean.lower() for s in ["%", "downloading"]):
                            await websocket.send_text(json.dumps({"type": "log", "content": line_clean[:500]}))

                exit_code = await proc.wait()
                stderr_data = b""
                if proc.stderr:
                    stderr_data = await proc.stderr.read()
                stderr_text = ansi_escape.sub("", stderr_data.decode(errors="ignore")).strip()

                # 解析 Agent 输出
                full_stdout = "\n".join(stdout_buffer)
                response_text = None

                # 尝试整体 JSON (OpenClaw)
                try:
                    data = json.loads(full_stdout)
                    result_obj = data.get("result", {})
                    payloads = result_obj.get("payloads", [])
                    if payloads:
                        texts = [p.get("text", "") for p in payloads if p.get("text")]
                        if texts:
                            response_text = "\n".join(texts)
                    if data.get("status") == "error" and not response_text:
                        await websocket.send_text(json.dumps({"type": "error", "content": f"Agent 错误: {data.get('summary', 'unknown')}"}))
                except (json.JSONDecodeError, ValueError):
                    pass

                # JSONL (OpenCode)
                if not response_text:
                    text_parts = []
                    for line in stdout_buffer:
                        try:
                            evt = json.loads(line)
                            if evt.get("type") in ("text", "message") and evt.get("content"):
                                text_parts.append(evt["content"])
                        except:
                            continue
                    if text_parts:
                        response_text = "\n".join(text_parts)

                if not response_text:
                    response_text = full_stdout[:3000]

            else:
                # ===== 平台 LLM 模式 =====
                from app.services.llm_config_service import LLMConfigService

                await websocket.send_text(json.dumps({"type": "status", "content": "🤖 调用平台 LLM..."}))

                llm_svc = LLMConfigService(db)
                try:
                    result = await llm_svc.chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": final_prompt},
                        ],
                        temperature=0.1,
                        max_tokens=4096,
                    )
                    response_text = result["content"].strip()
                    await websocket.send_text(json.dumps({"type": "text", "content": response_text[:1000] + ("..." if len(response_text) > 1000 else "")}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "content": f"LLM 调用失败: {e}"}))
                    response_text = None

            # ===== 解析 JSON 结果并应用注释 =====
            if response_text:
                await websocket.send_text(json.dumps({"type": "status", "content": "📝 解析注释结果并应用..."}))

                try:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)

                    data = json.loads(response_text)
                    annotated = 0

                    need_table = force or not table.table_comment_llm
                    if need_table:
                        table.table_comment_llm = data.get("table_description")
                        table.purpose = data.get("purpose")
                        table.domain = data.get("domain")
                        annotated += 1

                    col_annotations = {c["name"]: c for c in data.get("columns", [])}
                    for c in columns:
                        if c.column_name in col_annotations:
                            ann = col_annotations[c.column_name]
                            if force or not c.column_comment_llm:
                                c.column_comment_llm = ann.get("comment")
                                c.semantic_type = ann.get("semantic_type")
                                annotated += 1

                    db.commit()
                    await websocket.send_text(json.dumps({"type": "applied", "content": f"✅ 已应用 {annotated} 条注释"}))
                except (json.JSONDecodeError, ValueError) as e:
                    await websocket.send_text(json.dumps({"type": "error", "content": f"JSON 解析失败: {e}"}))

            await websocket.send_text(json.dumps({"type": "done"}))
            db.close()
            break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": f"服务器异常: {e}"}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/datasources/{source_id}/ontology-candidates")
async def get_ontology_candidates(source_id: int, db: Session = Depends(get_db)):
    """获取本体提取候选 — 筛选实体和关系候选."""
    from app.services.metadata_service import MetadataService
    svc = MetadataService(db)
    data = svc.get_ontology_candidates(source_id)
    return {"code": "SUCCESS", "data": data}


# ========== 文档管理 ==========

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档 (PDF/Word/Markdown 等)."""
    return {"filename": file.filename, "size": file.size, "status": "uploaded"}


@router.get("/documents")
async def list_documents():
    """获取文档列表."""
    return {"documents": [], "total": 0}
