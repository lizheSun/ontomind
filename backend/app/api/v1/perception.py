"""感知层 API - 数据源连接器 & 文档管理."""
import json
import re
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
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


# ========== 文档管理 ==========

@router.post("/datasources/{source_id}/sync")
async def sync_data_source(source_id: int):
    """同步数据源元数据."""
    return {"message": f"syncing data source {source_id}"}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档 (PDF/Word/Markdown 等)."""
    return {"filename": file.filename, "size": file.size, "status": "uploaded"}


@router.get("/documents")
async def list_documents():
    """获取文档列表."""
    return {"documents": [], "total": 0}
