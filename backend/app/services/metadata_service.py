"""元数据服务 — 从数据源提取表/字段元数据，浏览数据，LLM 自动注释."""
import json
import pymysql
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.db.repositories.metadata_repo import MetaTableRepository, MetaColumnRepository
from app.db.repositories.data_source_repo import DataSourceRepository
from app.db.models.metadata_model import MetaTable, MetaColumn
from app.core.exceptions import NotFoundException, BusinessException


class MetadataService:
    """元数据提取、浏览、注释服务."""

    def __init__(self, db: Session):
        self.db = db
        self.table_repo = MetaTableRepository(db)
        self.col_repo = MetaColumnRepository(db)
        self.ds_repo = DataSourceRepository(db)

    # ========== 元数据提取 ==========

    def extract_metadata(self, ds_id: int, database: Optional[str] = None) -> dict:
        """从数据源提取表和字段元数据.

        Args:
            ds_id: 数据源 ID
            database: 指定库名，None 则提取该数据源配置的默认库

        Returns:
            {"tables_synced": N, "columns_synced": M, "errors": [...]}
        """
        ds = self.ds_repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")

        source_type = ds.source_type.lower()
        db_drivers = {"mysql", "doris", "clickhouse"}

        if source_type not in db_drivers:
            raise BusinessException(f"暂不支持 {source_type} 类型的元数据提取", code="UNSUPPORTED_TYPE")

        target_db = database or ds.database
        if not target_db:
            raise BusinessException("未指定数据库名，无法提取元数据", code="NO_DATABASE")

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

        tables_synced = 0
        columns_synced = 0
        errors = []

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # 1. 提取表列表
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, ENGINE, TABLE_COLLATION,
                       TABLE_ROWS, AVG_ROW_LENGTH, DATA_LENGTH
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """, (target_db,))
            tables = cursor.fetchall()

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

                    # 2. 提取字段
                    cursor.execute("""
                        SELECT COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE,
                               IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (target_db, table_name))
                    columns = cursor.fetchall()

                    # 先删旧字段再重新插入
                    self.col_repo.delete_by_table(meta_table.id)

                    for c in columns:
                        col_key = (c.get("COLUMN_KEY") or "").upper()
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
                        )
                        self.db.add(col)
                        columns_synced += 1

                    # 更新字段数
                    meta_table.column_count = len(columns)
                    tables_synced += 1

                except Exception as e:
                    errors.append(f"表 {table_name}: {str(e)}")
                    continue

            self.db.commit()

        finally:
            conn.close()

        return {
            "tables_synced": tables_synced,
            "columns_synced": columns_synced,
            "errors": errors,
            "database": target_db,
        }

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

    # ========== LLM 自动注释 ==========

    async def auto_annotate(self, table_id: int, force: bool = False) -> dict:
        """使用 LLM 为表和字段自动生成注释/描述.

        Args:
            table_id: 元数据表 ID
            force: 是否强制重新生成（即使已有注释）
        """
        from app.services.llm_config_service import LLMConfigService

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

        llm_svc = LLMConfigService(self.db)

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

        try:
            result = await llm_svc.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4096,
            )

            content = result["content"].strip()

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
