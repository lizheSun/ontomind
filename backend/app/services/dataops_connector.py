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
        conn = self._connect(database=database)
        try:
            with conn.cursor() as cur:
                cur.execute(f"SHOW FULL TABLES FROM {_ident(database)}")
                rows = cur.fetchall()
            # Doris/MySQL: (name, type) or (name,)
            out: list[dict[str, Any]] = []
            for row in rows:
                name = str(row[0])
                kind = str(row[1]) if len(row) > 1 else "BASE TABLE"
                out.append({"name": name, "type": kind})
            out.sort(key=lambda x: x["name"])
            return out
        finally:
            conn.close()

    def list_columns(self, database: str, table: str) -> list[dict[str, Any]]:
        conn = self._connect(database=database)
        try:
            with conn.cursor() as cur:
                cur.execute(f"DESCRIBE {_ident(database)}.{_ident(table)}")
                rows = cur.fetchall()
            cols: list[dict[str, Any]] = []
            for row in rows:
                # Field, Type, Null, Key, Default, Extra
                cols.append(
                    {
                        "name": str(row[0]),
                        "type": str(row[1]) if len(row) > 1 else "",
                        "nullable": str(row[2]).upper() in {"YES", "TRUE", "1"} if len(row) > 2 else True,
                        "key": str(row[3]) if len(row) > 3 else "",
                        "default": None if len(row) < 5 else row[4],
                        "extra": str(row[5]) if len(row) > 5 else "",
                    }
                )
            return cols
        finally:
            conn.close()

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
