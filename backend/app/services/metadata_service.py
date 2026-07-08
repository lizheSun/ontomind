"""元数据服务 — 从数据源提取表/字段元数据，浏览数据，LLM 自动注释，字段数据画像."""
import json
import re
import pymysql
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.db.repositories.metadata_repo import MetaTableRepository, MetaColumnRepository
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.models.metadata_model import MetaTable, MetaColumn, MetaProfile
from app.core.exceptions import NotFoundException, BusinessException


class MetadataService:
    """元数据提取、浏览、注释服务."""

    def __init__(self, db: Session):
        self.db = db
        self.table_repo = MetaTableRepository(db)
        self.col_repo = MetaColumnRepository(db)
        self.ds_repo = DataSourceRepository(db)

    # ========== 元数据提取 ==========

    # 系统库，同步时跳过
    _SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys", "__recycle_bin__"}

    def extract_metadata(self, ds_id: int, database: Optional[str] = None, sync_all: bool = False) -> dict:
        """从数据源提取表和字段元数据.

        Args:
            ds_id: 数据源 ID
            database: 指定库名，None 则提取该数据源配置的默认库
            sync_all: True 则同步所有用户库（跳过系统库）

        Returns:
            {"tables_synced": N, "columns_synced": M, "databases": [...], "errors": [...]}
        """
        ds = self.ds_repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")

        source_type = ds.source_type.lower()
        db_drivers = {"mysql", "doris", "clickhouse"}

        if source_type not in db_drivers:
            raise BusinessException(f"暂不支持 {source_type} 类型的元数据提取", code="UNSUPPORTED_TYPE")

        try:
            conn = pymysql.connect(
                host=ds.host,
                port=ds.port or 3306,
                user=ds.username or "",
                password=ds.password or "",
                database="information_schema",
                charset=ds.charset or "utf8mb4",
                connect_timeout=15,
            )
        except Exception as e:
            raise BusinessException(f"连接数据源失败: {e}", code="CONN_FAILED")

        # 确定要同步的库列表
        if sync_all:
            cursor = conn.cursor()
            cursor.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME")
            all_dbs = [row[0] for row in cursor.fetchall()]
            target_dbs = [db for db in all_dbs if db not in self._SYSTEM_DATABASES]
        else:
            target_db = database or ds.database
            if not target_db:
                raise BusinessException("未指定数据库名，无法提取元数据", code="NO_DATABASE")
            target_dbs = [target_db]

        total_tables = 0
        total_columns = 0
        all_errors = []
        synced_dbs = []

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            for target_db in target_dbs:
                try:
                    t_count, c_count, errors = self._sync_one_database(cursor, ds_id, target_db)
                    total_tables += t_count
                    total_columns += c_count
                    all_errors.extend(errors)
                    synced_dbs.append(target_db)
                except Exception as e:
                    all_errors.append(f"库 {target_db}: {str(e)}")

            self.db.commit()

        finally:
            conn.close()

        return {
            "tables_synced": total_tables,
            "columns_synced": total_columns,
            "databases": synced_dbs,
            "errors": all_errors,
        }

    def _sync_one_database(self, cursor, ds_id: int, target_db: str) -> tuple:
        """同步单个库的元数据，返回 (表数, 字段数, 错误列表)."""
        tables_synced = 0
        columns_synced = 0
        errors = []

        # 1. 提取表列表（包括表和视图）
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, ENGINE, TABLE_COLLATION,
                   TABLE_ROWS, AVG_ROW_LENGTH, DATA_LENGTH
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """, (target_db,))
        tables = cursor.fetchall()

        # 2. 批量提取该库所有字段（一次性查询，按表分组）
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE,
                   IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """, (target_db,))
        all_columns = cursor.fetchall()
        # 按表名分组
        cols_by_table = {}
        for c in all_columns:
            tbl = c["TABLE_NAME"]
            if tbl not in cols_by_table:
                cols_by_table[tbl] = []
            cols_by_table[tbl].append(c)

        # 3. 批量提取外键信息
        fk_map = {}  # {(table, column): (ref_table, ref_column)}
        try:
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (target_db,))
            for row in cursor.fetchall():
                fk_map[(row["TABLE_NAME"], row["COLUMN_NAME"])] = (
                    row["REFERENCED_TABLE_NAME"], row["REFERENCED_COLUMN_NAME"]
                )
        except Exception:
            pass  # 某些数据库不支持外键查询

        # 4. 逐表处理
        for t in tables:
            table_name = t["TABLE_NAME"]
            table_type_raw = (t.get("TABLE_TYPE") or "").upper()
            table_type = "view" if "VIEW" in table_type_raw else "table"

            try:
                meta_table = self.table_repo.upsert(
                    ds_id=ds_id,
                    database=target_db,
                    table=table_name,
                    table_type=table_type,
                    table_comment=t.get("TABLE_COMMENT") or None,
                    engine=t.get("ENGINE"),
                    collation=t.get("TABLE_COLLATION"),
                    row_count=t.get("TABLE_ROWS"),
                    storage_size_mb=round((t.get("DATA_LENGTH") or 0) / 1024 / 1024, 2) if t.get("DATA_LENGTH") else None,
                )

                # 删旧字段
                self.col_repo.delete_by_table(meta_table.id)

                # 插入新字段
                table_cols = cols_by_table.get(table_name, [])
                for c in table_cols:
                    col_key = (c.get("COLUMN_KEY") or "").upper()
                    fk_info = fk_map.get((table_name, c["COLUMN_NAME"]))

                    col = MetaColumn(
                        meta_table_id=meta_table.id,
                        column_name=c["COLUMN_NAME"],
                        ordinal_position=c.get("ORDINAL_POSITION", 0),
                        data_type=c.get("DATA_TYPE"),
                        data_type_full=c.get("COLUMN_TYPE"),
                        is_nullable=(c.get("IS_NULLABLE") == "YES"),
                        is_primary_key=(col_key == "PRI"),
                        is_unique=(col_key in ("PRI", "UNI")),
                        is_indexed=(col_key in ("PRI", "UNI", "MUL")),
                        default_value=str(c.get("COLUMN_DEFAULT")) if c.get("COLUMN_DEFAULT") is not None else None,
                        column_comment=c.get("COLUMN_COMMENT") or None,
                        is_entity_identifier=(col_key == "PRI"),
                        is_relationship_key=bool(fk_info),
                        related_table=fk_info[0] if fk_info else None,
                        related_column=fk_info[1] if fk_info else None,
                    )
                    self.db.add(col)
                    columns_synced += 1

                meta_table.column_count = len(table_cols)
                tables_synced += 1

            except Exception as e:
                errors.append(f"表 {target_db}.{table_name}: {str(e)}")
                continue

        return tables_synced, columns_synced, errors

    # ========== 元数据查询 ==========

    def list_tables(self, ds_id: int, database: Optional[str] = None) -> list[dict]:
        tables = self.table_repo.get_by_datasource(ds_id, database)
        return [t.to_response_dict() for t in tables]

    def get_table_detail(self, table_id: int) -> dict:
        table = self.table_repo.get_by_id(table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")
        result = table.to_response_dict()
        columns = self.col_repo.get_by_table(table_id)
        result["columns"] = [c.to_response_dict() for c in columns]
        return result

    def list_databases(self, ds_id: int) -> list[str]:
        """列出数据源上所有可用的数据库."""
        ds = self.ds_repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")

        source_type = ds.source_type.lower()
        if source_type not in ("mysql", "doris", "clickhouse"):
            return [ds.database] if ds.database else []

        try:
            conn = pymysql.connect(
                host=ds.host,
                port=ds.port or 3306,
                user=ds.username or "",
                password=ds.password or "",
                database="information_schema",
                charset=ds.charset or "utf8mb4",
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME")
            dbs = [row[0] for row in cursor.fetchall()]
            conn.close()
            return dbs
        except Exception as e:
            raise BusinessException(f"获取数据库列表失败: {e}", code="DB_LIST_FAILED")

    # ========== 数据浏览（实时连接） ==========

    def preview_data(self, table_id: int, limit: int = 100, offset: int = 0) -> dict:
        """实时连接数据源，预览表数据."""
        from app.db.models.metadata_model import MetaTable

        table = self.db.query(MetaTable).filter(MetaTable.id == table_id).first()
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")

        ds = self.ds_repo.get_by_id(table.datasource_id)
        if not ds:
            raise NotFoundException("数据源不存在")

        try:
            conn = pymysql.connect(
                host=ds.host,
                port=ds.port or 3306,
                user=ds.username or "",
                password=ds.password or "",
                database=table.database_name,
                charset=ds.charset or "utf8mb4",
                connect_timeout=10,
            )
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # 安全的分页查询
            cursor.execute(f"SELECT * FROM `{table.table_name}` LIMIT %s OFFSET %s", (limit, offset))
            rows = cursor.fetchall()

            # 获取总行数
            cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table.table_name}`")
            total = cursor.fetchone()["cnt"]

            conn.close()

            # 序列化（处理 Decimal/datetime 等不可 JSON 序列化的类型）
            serialized_rows = []
            for row in rows:
                serialized = {}
                for k, v in row.items():
                    if isinstance(v, (datetime,)):
                        serialized[k] = v.isoformat()
                    elif hasattr(v, "isoformat"):
                        serialized[k] = v.isoformat()
                    else:
                        serialized[k] = v
                serialized_rows.append(serialized)

            return {
                "table_name": table.table_name,
                "database_name": table.database_name,
                "columns": list(rows[0].keys()) if rows else [],
                "rows": serialized_rows,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            raise BusinessException(f"数据预览失败: {e}", code="PREVIEW_FAILED")

    # ========== 字段数据画像 ==========

    # 采样行数上限，避免对大表全量扫描
    _PROFILE_SAMPLE_LIMIT = 5000
    # 判定为枚举的最大去重值数量
    _ENUM_MAX_DISTINCT = 50
    # 判定为枚举的去重值占比上限（去重数 / 非空行数）
    _ENUM_MAX_RATIO = 0.2

    _RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _RE_PHONE = re.compile(r"^(?:\+?86)?1[3-9]\d{9}$")
    _RE_URL = re.compile(r"^https?://", re.IGNORECASE)
    _RE_DATE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T]\d{1,2}:\d{2}(:\d{2})?)?")

    def _connect_target(self, ds, database: str, timeout: int = 15):
        """连接数据源中指定库，返回 pymysql 连接（调用方负责关闭）."""
        try:
            return pymysql.connect(
                host=ds.host,
                port=ds.port or 3306,
                user=ds.username or "",
                password=ds.password or "",
                database=database,
                charset=ds.charset or "utf8mb4",
                connect_timeout=timeout,
            )
        except Exception as e:
            raise BusinessException(f"连接数据源失败: {e}", code="CONN_FAILED")

    @staticmethod
    def _is_empty(v) -> bool:
        return v is None or (isinstance(v, str) and v.strip() == "")

    def _detect_format(self, col, non_null: list) -> tuple:
        """根据字段类型与采样值识别格式，返回 (format, confidence)."""
        ctype = (col.data_type or "").lower()
        name = (col.column_name or "").lower()

        if col.is_primary_key or name.endswith("_id") or name == "id":
            return "id", 0.9

        if ctype in ("int", "bigint", "smallint", "tinyint", "mediumint",
                     "decimal", "float", "double", "numeric", "real"):
            return "number", 0.95

        if ctype in ("date", "datetime", "timestamp", "time", "year"):
            return "date", 0.95

        if not non_null:
            return "text", 0.3

        n = len(non_null)
        email_hit = sum(1 for v in non_null if isinstance(v, str) and self._RE_EMAIL.match(v))
        if email_hit / n >= 0.8:
            return "email", round(email_hit / n, 2)

        phone_hit = sum(1 for v in non_null if isinstance(v, str) and self._RE_PHONE.match(v))
        if phone_hit / n >= 0.8:
            return "phone", round(phone_hit / n, 2)

        url_hit = sum(1 for v in non_null if isinstance(v, str) and self._RE_URL.match(v))
        if url_hit / n >= 0.8:
            return "url", round(url_hit / n, 2)

        date_hit = sum(1 for v in non_null if isinstance(v, str) and self._RE_DATE.match(v))
        if date_hit / n >= 0.8:
            return "date", round(date_hit / n, 2)

        return "text", 0.5

    def profile_data(self, table_id: int, force: bool = False) -> dict:
        """对表中每个字段抽样画像：空值率、去重数、最值、格式、枚举候选.

        画像结果落库到 meta_profiles，供认知层约束抽取使用。
        """
        table = self.table_repo.get_by_id(table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")

        columns = self.col_repo.get_by_table(table_id)
        if not columns:
            return {"message": "表无字段，跳过画像", "profiled": 0}

        ds = self.ds_repo.get_by_id(table.datasource_id)
        if not ds:
            raise NotFoundException("数据源不存在")

        conn = self._connect_target(ds, table.database_name)
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                f"SELECT * FROM `{table.table_name}` LIMIT %s",
                (self._PROFILE_SAMPLE_LIMIT,),
            )
            rows = cursor.fetchall()
        except Exception as e:
            conn.close()
            raise BusinessException(f"画像采样失败: {e}", code="PROFILE_FAILED")
        finally:
            conn.close()

        total = table.row_count or len(rows)
        profiled = 0

        for col in columns:
            # 已存在且非强制则跳过
            existing = self.db.query(MetaProfile).filter(
                MetaProfile.meta_column_id == col.id
            ).first()
            if existing and not force and existing.profile_status == "done":
                continue

            col_values = [r.get(col.column_name) for r in rows]
            non_null = [v for v in col_values if not self._is_empty(v)]

            null_count = len(col_values) - len(non_null)
            distinct = len(set(non_null))
            sample = [str(v) for v in non_null[:20]]

            fmt, conf = self._detect_format(col, non_null)

            # 枚举识别：字符串类型、低基数、去重占比低
            is_enum = False
            enum_values = None
            if (fmt == "text" and distinct <= self._ENUM_MAX_DISTINCT
                    and (len(non_null) == 0 or distinct / len(non_null) <= self._ENUM_MAX_RATIO)):
                is_enum = True
                counts = {}
                for v in non_null:
                    key = str(v)
                    counts[key] = counts.get(key, 0) + 1
                top = sorted(counts.items(), key=lambda x: -x[1])[:20]
                enum_values = [{"value": k, "count": c} for k, c in top]

            # 最值：数值或日期类型
            min_v = max_v = None
            ctype = (col.data_type or "").lower()
            if ctype in ("int", "bigint", "smallint", "tinyint", "decimal", "float", "double", "numeric", "date", "datetime", "timestamp"):
                numeric = []
                for v in non_null:
                    try:
                        if isinstance(v, (int, float)):
                            numeric.append(v)
                        elif isinstance(v, str):
                            numeric.append(float(v))
                    except (ValueError, TypeError):
                        continue
                if numeric:
                    min_v = str(min(numeric))
                    max_v = str(max(numeric))

            profile = existing or MetaProfile(
                datasource_id=table.datasource_id,
                meta_table_id=table.id,
                meta_column_id=col.id,
            )
            profile.row_count = total
            profile.null_count = null_count
            profile.null_ratio = round(null_count / total, 4) if total else 0.0
            profile.distinct_count = distinct
            profile.min_value = min_v
            profile.max_value = max_v
            profile.sample_values = json.dumps(sample, ensure_ascii=False)
            profile.detected_format = fmt
            profile.format_confidence = conf
            profile.is_enum = is_enum
            profile.enum_values = json.dumps(enum_values, ensure_ascii=False) if enum_values else None
            profile.profile_status = "done"
            profile.error = None

            self.db.add(profile)
            profiled += 1

        self.db.commit()
        return {
            "message": f"已画像 {profiled} 个字段",
            "profiled": profiled,
            "table_id": table_id,
        }

    def get_profile(self, table_id: int) -> dict:
        """获取某表的字段画像结果列表."""
        table = self.table_repo.get_by_id(table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")
        profiles = self.db.query(MetaProfile).filter(
            MetaProfile.meta_table_id == table_id
        ).order_by(MetaProfile.meta_column_id).all()
        return {
            "table_id": table_id,
            "profiles": [p.to_response_dict() for p in profiles],
        }

    # ========== LLM / Agent 自动注释 ==========

    async def _call_agent_for_annotation(self, agent_id: int, system_prompt: str, user_prompt: str) -> str:
        """调用指定 Agent（CLI 模式）执行标注任务，返回响应文本."""
        import os
        import re
        import subprocess
        from app.db.models.agent_model import Agent
        from app.services.agent_discovery import KNOWN_AGENTS

        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise NotFoundException(f"Agent 不存在: {agent_id}")

        entrypoint = (agent.entrypoint or "").strip()
        if not entrypoint or entrypoint.startswith("http"):
            # HTTP 模式的 Agent，走 HTTP chat
            return await self._call_agent_http(agent, system_prompt, user_prompt)

        # CLI 模式
        cli_path = entrypoint.split()[0]
        extra_args = entrypoint.split()[1:] if len(entrypoint.split()) > 1 else []

        agent_info = KNOWN_AGENTS.get(agent.agent_type, {})
        cli_chat_args = agent_info.get("cli_chat_args", ["{msg}"])

        # 获取 agent_name（OpenClaw 需要）
        agent_name = ""
        if agent.env_template and isinstance(agent.env_template, dict):
            agent_name = agent.env_template.get("agent_name", "")
        if not agent_name and agent_info.get("cli_list_agents_args"):
            from app.services.agent_discovery import _get_first_agent_name
            agent_name = _get_first_agent_name(cli_path, agent_info["cli_list_agents_args"]) or ""

        # 合并 system + user prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        args = [arg.replace("{msg}", full_prompt).replace("{agent_name}", agent_name) for arg in cli_chat_args]

        env = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
        cli_env = agent_info.get("cli_env", {})
        env.update(cli_env)

        full_cmd = [cli_path] + extra_args + args

        result = subprocess.run(
            full_cmd,
            capture_output=True, text=True, timeout=180,
            env=env,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # 清理 ANSI
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        stdout_clean = ansi_escape.sub('', stdout).strip()

        if not stdout_clean:
            raise BusinessException(
                f"Agent CLI 无输出 (exit={result.returncode})。stderr: {stderr[:500]}",
                code="AGENT_NO_OUTPUT"
            )

        # 解析输出 — 尝试 JSON
        try:
            data = json.loads(stdout_clean)
            # OpenCode JSONL 事件流
            if isinstance(data, dict) and data.get("type"):
                text_parts = []
                # 可能是多行 JSONL
                for line in stdout_clean.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                        if evt.get("type") in ("text", "message") and evt.get("content"):
                            text_parts.append(evt["content"])
                        elif evt.get("type") == "error":
                            err = evt.get("error", {})
                            if isinstance(err, dict):
                                raise BusinessException(
                                    f"Agent 返回错误: {err.get('data', {}).get('message', str(err))}",
                                    code="AGENT_ERROR"
                                )
                    except json.JSONDecodeError:
                        continue
                if text_parts:
                    return "\n".join(text_parts)
            # OpenClaw 整体 JSON
            elif isinstance(data, dict) and data.get("result"):
                payloads = data["result"].get("payloads", [])
                texts = [p.get("text", "") for p in payloads if p.get("text")]
                if texts:
                    return "\n".join(texts)
            # 通用字段
            for key in ["response", "reply", "output", "content", "text", "result"]:
                if data.get(key):
                    return str(data[key])
            return json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            return stdout_clean[:8000]

    async def _call_agent_http(self, agent, system_prompt: str, user_prompt: str) -> str:
        """HTTP 模式 Agent 调用（兼容旧版）."""
        import json
        import urllib.request

        base_url = (agent.entrypoint or "").rstrip("/")
        chat_endpoints = ["/v1/chat/completions", "/chat", "/api/chat"]

        body = json.dumps({
            "model": agent.name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "max_tokens": 4096,
        }).encode("utf-8")

        for endpoint in chat_endpoints:
            url = f"{base_url}{endpoint}"
            try:
                req = urllib.request.Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                resp = urllib.request.urlopen(req, timeout=60)
                resp_body = resp.read().decode(errors="ignore")[:10000]
                data = json.loads(resp_body)
                if "choices" in data:
                    return data["choices"][0].get("message", {}).get("content", "")
                for key in ["response", "reply", "output", "content", "text"]:
                    if data.get(key):
                        return str(data[key])
            except Exception:
                continue

        raise BusinessException("Agent HTTP 调用失败，未找到可用端点", code="AGENT_HTTP_FAILED")

    async def auto_annotate(self, table_id: int, force: bool = False, agent_id: Optional[int] = None) -> dict:
        """使用 LLM 或指定 Agent 为表和字段自动生成注释/描述.

        Args:
            table_id: 元数据表 ID
            force: 是否强制重新生成（即使已有注释）
            agent_id: 指定 Agent ID（资源管理里的 Agent），None 则用平台 LLM
        """
        table = self.table_repo.get_by_id(table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")

        columns = self.col_repo.get_by_table(table_id)

        # 收集需要注释的字段
        cols_to_annotate = []
        for c in columns:
            if force or not c.column_comment_llm:
                cols_to_annotate.append({
                    "name": c.column_name,
                    "type": c.data_type_full or c.data_type,
                    "comment": c.column_comment or "",
                    "is_pk": c.is_primary_key,
                })

        need_table_annotate = force or not table.table_comment_llm

        if not cols_to_annotate and not need_table_annotate:
            return {"message": "所有注释已存在，无需生成", "annotated": 0}

        # 构建 prompt
        col_info = "\n".join(
            f"  - {c['name']} ({c['type']}) PK={c['is_pk']} 注释={c['comment'] or '无'}"
            for c in cols_to_annotate
        )

        prompt = f"""请分析以下数据库表的元数据，为表和字段生成中文业务描述。

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

        system_prompt = "你是数据治理专家，擅长理解数据库表结构并生成业务描述。只返回纯 JSON。"

        # 调用 LLM 或 Agent
        if agent_id:
            content = await self._call_agent_for_annotation(agent_id, system_prompt, prompt)
        else:
            from app.services.llm_config_service import LLMConfigService
            llm_svc = LLMConfigService(self.db)
            result = await llm_svc.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            content = result["content"].strip()

        try:
            # 提取 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            import json
            data = json.loads(content)

            # 更新表注释
            annotated = 0
            if need_table_annotate:
                table.table_comment_llm = data.get("table_description")
                table.purpose = data.get("purpose")
                table.domain = data.get("domain")
                annotated += 1

            # 更新字段注释
            col_annotations = {c["name"]: c for c in data.get("columns", [])}
            for c in columns:
                if c.column_name in col_annotations:
                    ann = col_annotations[c.column_name]
                    if force or not c.column_comment_llm:
                        c.column_comment_llm = ann.get("comment")
                        c.semantic_type = ann.get("semantic_type")
                        annotated += 1

            self.db.commit()

            return {
                "message": f"已生成 {annotated} 条注释",
                "annotated": annotated,
                "table_id": table_id,
            }

        except json.JSONDecodeError:
            raise BusinessException("LLM 返回格式异常，无法解析为 JSON", code="LLM_PARSE_ERROR")
        except Exception as e:
            raise BusinessException(f"LLM 注释生成失败: {e}", code="LLM_FAILED")

    # ========== 本体提取辅助 ==========

    def get_ontology_candidates(self, ds_id: int) -> dict:
        """获取本体提取候选 — 筛选有实体候选标记的表和字段."""
        from app.db.models.metadata_model import MetaTable, MetaColumn

        tables = self.db.query(MetaTable).filter(
            MetaTable.datasource_id == ds_id,
            MetaTable.sync_status == "synced",
        ).all()

        entities = []
        relationships = []

        for t in tables:
            columns = self.col_repo.get_by_table(t.id)

            # 实体候选：有主键或被标记为 entity_candidate
            pk_cols = [c for c in columns if c.is_primary_key]
            if t.entity_candidate or pk_cols:
                entities.append({
                    "table_id": t.id,
                    "table_name": t.table_name,
                    "database": t.database_name,
                    "description": t.table_comment_llm or t.table_comment or t.business_description,
                    "domain": t.domain,
                    "purpose": t.purpose,
                    "identifier": pk_cols[0].column_name if pk_cols else "id",
                    "attributes": [
                        {
                            "name": c.column_name,
                            "type": c.data_type,
                            "semantic_type": c.semantic_type,
                            "description": c.column_comment_llm or c.column_comment,
                        }
                        for c in columns if not c.is_primary_key
                    ],
                })

            # 关系候选：有外键标记的字段
            fk_cols = [c for c in columns if c.is_relationship_key and c.related_table]
            for fk in fk_cols:
                relationships.append({
                    "from_table": t.table_name,
                    "from_column": fk.column_name,
                    "to_table": fk.related_table,
                    "to_column": fk.related_column,
                    "description": fk.column_comment_llm or fk.column_comment,
                })

        return {
            "datasource_id": ds_id,
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "entities": entities,
            "relationships": relationships,
        }

    def update_table_meta(self, table_id: int, updates: dict) -> dict:
        """更新表的业务元数据（人工编辑）."""
        table = self.table_repo.get_by_id(table_id)
        if not table:
            raise NotFoundException(f"元数据表不存在: {table_id}")

        editable_fields = {"business_description", "purpose", "domain", "entity_candidate", "table_comment_llm"}
        for k, v in updates.items():
            if k in editable_fields:
                setattr(table, k, v)

        self.db.commit()
        return table.to_response_dict()

    def update_column_meta(self, column_id: int, updates: dict) -> dict:
        """更新字段的业务元数据（人工编辑）."""
        from app.db.models.metadata_model import MetaColumn

        col = self.db.query(MetaColumn).filter(MetaColumn.id == column_id).first()
        if not col:
            raise NotFoundException(f"字段元数据不存在: {column_id}")

        editable_fields = {"column_comment_llm", "semantic_type", "business_description",
                          "is_entity_identifier", "is_relationship_key", "related_table", "related_column"}
        for k, v in updates.items():
            if k in editable_fields:
                setattr(col, k, v)

        self.db.commit()
        return col.to_response_dict()
