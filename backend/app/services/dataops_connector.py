"""数据源连接器 — Doris / MySQL（MySQL 协议）+ Hive 占位."""
from __future__ import annotations

import time
from typing import Any, Optional

import pymysql

from app.core.exceptions import BusinessException


def _ident(name: str) -> str:
    if not name or any(ch in name for ch in (";", "`", "\x00")):
        raise BusinessException("非法标识符", code="INVALID_IDENTIFIER")
    return f"`{name.replace('`', '')}`"


def _normalize_sql(sql: str) -> str:
    text = (sql or "").strip()
    if not text:
        return ""
    # 只跑第一条语句，避免多语句注入面
    parts = [p.strip() for p in text.split(";") if p.strip()]
    if not parts:
        return ""
    if len(parts) > 1:
        raise BusinessException("一次只允许执行一条 SQL", code="SQL_MULTI_STATEMENT")
    return parts[0]


def _serialize_row(row: tuple[Any, ...]) -> list[Any]:
    cells: list[Any] = []
    for cell in row:
        if cell is None:
            cells.append(None)
        elif hasattr(cell, "isoformat"):
            cells.append(cell.isoformat())
        elif isinstance(cell, (bytes, bytearray)):
            cells.append(cell.decode("utf-8", errors="replace"))
        else:
            cells.append(cell)
    return cells


class DataSourceConnector:
    """按 source_type 探活 / 拉元数据 / 取样。"""

    def __init__(
        self,
        *,
        source_type: str,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        database: Optional[str] = None,
        charset: str = "utf8mb4",
    ) -> None:
        self.source_type = (source_type or "").lower()
        self.host = host
        self.port = port
        self.username = username
        self.password = password or ""
        self.database = database or None
        self.charset = charset or "utf8mb4"

    def test(self) -> dict[str, Any]:
        if self.source_type == "hive":
            raise BusinessException(
                "Hive 连接器尚未启用（需 HiveServer2 / Thrift）。请先用 Doris / MySQL。",
                code="HIVE_NOT_READY",
            )
        if self.source_type not in {"doris", "mysql"}:
            raise BusinessException(f"不支持的数据源类型: {self.source_type}", code="UNSUPPORTED_SOURCE")

        started = time.perf_counter()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
            latency = (time.perf_counter() - started) * 1000
            return {
                "ok": True,
                "message": "连接成功",
                "latency_ms": round(latency, 1),
                "server_info": str(version),
            }
        finally:
            conn.close()

    def list_databases(self) -> list[str]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW DATABASES")
                rows = cur.fetchall()
            skip = {"information_schema", "mysql", "performance_schema", "sys", "__internal_schema"}
            names = [str(r[0]) for r in rows if str(r[0]) not in skip]
            names.sort()
            return names
        finally:
            conn.close()

    def list_tables(self, database: str) -> list[dict[str, Any]]:
        return self.list_tables_meta(database)

    def list_tables_meta(self, database: str) -> list[dict[str, Any]]:
        _ident(database)
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, TABLE_ROWS, ENGINE, CREATE_TIME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    """,
                    (database,),
                )
                rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                create_time = row[5]
                out.append(
                    {
                        "name": str(row[0]),
                        "type": str(row[1] or "BASE TABLE"),
                        "comment": str(row[2] or "") or None,
                        "row_count": int(row[3]) if row[3] is not None else None,
                        "engine": str(row[4]) if row[4] is not None else None,
                        "create_time": create_time.isoformat()
                        if hasattr(create_time, "isoformat")
                        else (str(create_time) if create_time else None),
                    }
                )
            return out
        finally:
            conn.close()

    def list_columns(self, database: str, table: str) -> list[dict[str, Any]]:
        _ident(database)
        _ident(table)
        conn = self._connect()
        try:
            return self._list_columns_on_conn(conn, database, [table]).get(table, [])
        finally:
            conn.close()

    def batch_columns(self, database: str, tables: list[str]) -> dict[str, list[dict[str, Any]]]:
        _ident(database)
        names = [t for t in tables if t]
        if not names:
            return {}
        for t in names:
            _ident(t)
        conn = self._connect()
        try:
            return self._list_columns_on_conn(conn, database, names)
        finally:
            conn.close()

    def _list_columns_on_conn(
        self, conn: Any, database: str, tables: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        placeholders = ", ".join(["%s"] * len(tables))
        sql = f"""
            SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE,
                   IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        with conn.cursor() as cur:
            cur.execute(sql, (database, *tables))
            rows = cur.fetchall()
        out: dict[str, list[dict[str, Any]]] = {t: [] for t in tables}
        for row in rows:
            tname = str(row[0])
            out.setdefault(tname, []).append(
                {
                    "name": str(row[1]),
                    "ordinal": int(row[2]) if row[2] is not None else 0,
                    "data_type": str(row[3] or ""),
                    "type": str(row[4] or row[3] or ""),
                    "nullable": str(row[5] or "").upper() in {"YES", "TRUE", "1"},
                    "key": str(row[6] or ""),
                    "default": row[7],
                    "extra": str(row[8] or ""),
                    "comment": str(row[9] or "") or None,
                }
            )
        return out

    def profile_column(
        self,
        database: str,
        table: str,
        column: str,
        *,
        sample_rows: int = 10000,
    ) -> dict[str, Any]:
        db = _ident(database)
        tb = _ident(table)
        col = _ident(column)
        sample_rows = max(100, min(int(sample_rows), 50000))
        conn = self._connect(database=database)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS total,
                           COUNT({col}) AS non_null,
                           COUNT(DISTINCT {col}) AS distinct_count,
                           MIN({col}) AS min_v,
                           MAX({col}) AS max_v
                    FROM (
                        SELECT {col} FROM {db}.{tb} LIMIT {sample_rows}
                    ) s
                    """
                )
                row = cur.fetchone() or (0, 0, 0, None, None)
                total = int(row[0] or 0)
                non_null = int(row[1] or 0)
                distinct_count = int(row[2] or 0)
                min_v, max_v = row[3], row[4]
                null_rate = 0.0 if total == 0 else round(1.0 - (non_null / total), 6)
                distinct_ratio = 0.0 if non_null == 0 else round(distinct_count / non_null, 6)

                top_k: list[dict[str, Any]] = []
                data_type = ""
                try:
                    cur.execute(
                        """
                        SELECT DATA_TYPE FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
                        """,
                        (database, table, column),
                    )
                    dt_row = cur.fetchone()
                    data_type = str(dt_row[0] or "").lower() if dt_row else ""
                except Exception:
                    data_type = ""

                numericish = data_type in {
                    "int", "bigint", "smallint", "tinyint", "mediumint",
                    "decimal", "double", "float", "numeric", "real",
                    "date", "datetime", "timestamp", "time",
                }
                if not numericish:
                    min_v, max_v = None, None
                    try:
                        cur.execute(
                            f"""
                            SELECT {col} AS v, COUNT(*) AS cnt
                            FROM (
                                SELECT {col} FROM {db}.{tb} LIMIT {sample_rows}
                            ) s
                            WHERE {col} IS NOT NULL
                            GROUP BY {col}
                            ORDER BY cnt DESC
                            LIMIT 10
                            """
                        )
                        for r in cur.fetchall():
                            val = r[0]
                            if hasattr(val, "isoformat"):
                                val = val.isoformat()
                            elif isinstance(val, (bytes, bytearray)):
                                val = val.decode("utf-8", errors="replace")
                            top_k.append({"value": val, "count": int(r[1] or 0)})
                    except Exception:
                        top_k = []
                else:
                    if hasattr(min_v, "isoformat"):
                        min_v = min_v.isoformat()
                    if hasattr(max_v, "isoformat"):
                        max_v = max_v.isoformat()

            return {
                "total": total,
                "null_rate": null_rate,
                "distinct_count": distinct_count,
                "distinct_ratio": distinct_ratio,
                "min": min_v,
                "max": max_v,
                "top_k": top_k,
                "sampled": True,
                "sample_rows": sample_rows,
                "data_type": data_type or None,
            }
        finally:
            conn.close()

    def overlap_ratio(
        self,
        database: str,
        left_table: str,
        left_col: str,
        right_table: str,
        right_col: str,
        *,
        limit: int = 10000,
    ) -> float:
        try:
            db = _ident(database)
            lt = _ident(left_table)
            lc = _ident(left_col)
            rt = _ident(right_table)
            rc = _ident(right_col)
            limit = max(100, min(int(limit), 50000))
            conn = self._connect(database=database)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT COUNT(*) FROM (
                            SELECT DISTINCT {lc} AS v
                            FROM {db}.{lt}
                            WHERE {lc} IS NOT NULL
                            LIMIT {limit}
                        ) l
                        """
                    )
                    left_n = int((cur.fetchone() or (0,))[0] or 0)
                    if left_n <= 0:
                        return 0.0
                    cur.execute(
                        f"""
                        SELECT COUNT(*) FROM (
                            SELECT DISTINCT {lc} AS v
                            FROM {db}.{lt}
                            WHERE {lc} IS NOT NULL
                            LIMIT {limit}
                        ) l
                        WHERE l.v IN (
                            SELECT DISTINCT {rc}
                            FROM {db}.{rt}
                            WHERE {rc} IS NOT NULL
                            LIMIT {limit}
                        )
                        """
                    )
                    hit = int((cur.fetchone() or (0,))[0] or 0)
                return round(hit / left_n, 6)
            finally:
                conn.close()
        except Exception:
            return 0.0

    def sample(
        self, database: Optional[str], table: str, limit: int = 10
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        db = database or self.database
        if not db:
            raise BusinessException("请指定 database", code="DATABASE_REQUIRED")
        sql = f"SELECT * FROM {_ident(db)}.{_ident(table)} LIMIT {limit}"
        return self.execute(sql, database=db, max_rows=limit)

    def execute(
        self,
        sql: str,
        *,
        database: Optional[str] = None,
        max_rows: int = 200,
    ) -> dict[str, Any]:
        """执行单条 SQL，返回过程日志 + 结果集（或 affected rows）。"""
        cleaned = _normalize_sql(sql)
        if not cleaned:
            raise BusinessException("SQL 不能为空", code="SQL_EMPTY")
        max_rows = max(1, min(int(max_rows), 1000))
        db = database or self.database
        logs: list[dict[str, Any]] = []
        started = time.perf_counter()
        logs.append({"level": "info", "message": f"连接 {self.source_type}://{self.host}:{self.port}"})
        if db:
            logs.append({"level": "info", "message": f"使用库 `{db}`"})
        logs.append({"level": "info", "message": f"执行 SQL（最多返回 {max_rows} 行）"})

        conn = self._connect(database=db)
        try:
            with conn.cursor() as cur:
                cur.execute(cleaned)
                has_result = cur.description is not None
                if has_result:
                    columns = [d[0] for d in cur.description]
                    rows_raw = cur.fetchmany(max_rows + 1)
                    truncated = len(rows_raw) > max_rows
                    rows_raw = rows_raw[:max_rows]
                    rows = [_serialize_row(row) for row in rows_raw]
                    affected = None
                    logs.append(
                        {
                            "level": "success",
                            "message": f"查询完成 · {len(rows)} 行"
                            + (" · 已截断" if truncated else ""),
                        }
                    )
                else:
                    columns = []
                    rows = []
                    truncated = False
                    affected = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else None
                    conn.commit()
                    logs.append(
                        {
                            "level": "success",
                            "message": f"语句完成"
                            + (f" · affected={affected}" if affected is not None else ""),
                        }
                    )
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            return {
                "ok": True,
                "columns": columns,
                "rows": rows,
                "truncated": truncated,
                "affected_rows": affected,
                "sql": cleaned,
                "latency_ms": latency_ms,
                "logs": logs,
            }
        except BusinessException:
            raise
        except Exception as exc:
            logs.append({"level": "error", "message": str(exc)})
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            return {
                "ok": False,
                "columns": [],
                "rows": [],
                "truncated": False,
                "affected_rows": None,
                "sql": cleaned,
                "latency_ms": latency_ms,
                "logs": logs,
                "message": str(exc),
            }
        finally:
            conn.close()

    def _connect(self, database: Optional[str] = None):
        if self.source_type == "hive":
            raise BusinessException(
                "Hive 连接器尚未启用",
                code="HIVE_NOT_READY",
            )
        try:
            return pymysql.connect(
                host=self.host,
                port=int(self.port),
                user=self.username,
                password=self.password,
                database=database or self.database or None,
                charset=self.charset,
                connect_timeout=8,
                read_timeout=30,
                write_timeout=30,
                cursorclass=pymysql.cursors.Cursor,
            )
        except pymysql.Error as exc:
            raise BusinessException(
                f"连接失败: {exc}",
                code="SOURCE_CONNECT_FAILED",
            ) from exc
