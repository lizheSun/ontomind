"""数据平台-数据源服务：CRUD + Fernet + engine cache + 连接测试 + schema introspect。"""
from __future__ import annotations

import time
from typing import Any

from loguru import logger
from sqlalchemy import URL, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core import crypto
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models.dp_data_source_model import DpDataSource
from app.db.repositories.dp_data_source_repo import DpDataSourceRepository
from app.schemas.dp_data_source_schema import (
    DpDataSourceCreate,
    DpDataSourceRead,
    DpDataSourceTestResult,
    DpDataSourceUpdate,
)


# ==== 常量 =========================================================

_DIALECT_URL_PREFIX = {
    "mysql": "mysql+pymysql",
    "mysql_readonly": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "sqlite": "sqlite",
}


# ==== 服务 =========================================================

class DpDataSourceService:
    """数据平台-数据源服务。事务由本层负责（with db.begin()）。"""

    # --- 构造 -----------------------------------------------------------

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DpDataSourceRepository(db)

    def _reset_autobegin(self) -> None:
        """SQLAlchemy 2.0 会在任意读查询后 autobegin。写路径进入自己的 `with begin()` 前，
        必须先释放读取路径遗留的空事务，否则 `Session.begin()` 会抛
        `A transaction is already begun on this Session`。"""
        if self.db.in_transaction():
            self.db.rollback()

    # --- CRUD -----------------------------------------------------------

    def create(self, payload: DpDataSourceCreate, user_id: int) -> DpDataSourceRead:
        password_plain = payload.password.get_secret_value() if payload.password else None
        password_enc = None
        if password_plain:
            if crypto.ENCRYPTION_DISABLED:
                raise BusinessException(
                    code="ENCRYPTION_DISABLED",
                    message="加密未配置，请先设置 FERNET_KEY 再创建数据源",
                    status_code=500,
                )
            password_enc = crypto.encrypt(password_plain)

        data = payload.model_dump(exclude={"password"})
        data["password_enc"] = password_enc
        data["owner_user_id"] = user_id
        data["created_by_user_id"] = user_id
        data.setdefault("status", "active")

        self._reset_autobegin()
        with self.db.begin():
            if self.repo.name_exists(payload.name):
                raise BusinessException(
                    code="DP_DS_NAME_EXISTS",
                    message=f"数据源名称 {payload.name!r} 已存在",
                    status_code=409,
                )
            row = self.repo.create(data)
        return self._to_read(row)

    def get_by_id(self, id: int, user_id: int) -> DpDataSourceRead:
        row = self.repo.get_by_id(id)
        if row is None:
            raise NotFoundException(f"数据源 id={id} 不存在", code="DP_DS_NOT_FOUND")
        return self._to_read(row)

    def list_by_owner(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[DpDataSourceRead]:
        rows = self.repo.list_by_owner(user_id=user_id, skip=skip, limit=limit)
        return [self._to_read(r) for r in rows]

    def update(
        self, id: int, payload: DpDataSourceUpdate, user_id: int
    ) -> DpDataSourceRead:
        patch: dict[str, Any] = payload.model_dump(exclude_unset=True, exclude={"password"})

        if payload.password is not None:
            pw = payload.password.get_secret_value()
            if pw:
                if crypto.ENCRYPTION_DISABLED:
                    raise BusinessException(
                        code="ENCRYPTION_DISABLED",
                        message="加密未配置，请先设置 FERNET_KEY 再更新密码",
                        status_code=500,
                    )
                patch["password_enc"] = crypto.encrypt(pw)

        self._reset_autobegin()
        with self.db.begin():
            self._require_owner(id, user_id)
            new_name = patch.get("name")
            if new_name and self.repo.name_exists(new_name, exclude_id=id):
                raise BusinessException(
                    code="DP_DS_NAME_EXISTS",
                    message=f"数据源名称 {new_name!r} 已存在",
                    status_code=409,
                )
            self.repo.update(id, patch)
        _engine_cache_invalidate(id)
        return self.get_by_id(id, user_id)

    def delete(self, id: int, user_id: int) -> None:
        self._reset_autobegin()
        with self.db.begin():
            self._require_owner(id, user_id)
            self.repo.delete(id)
        _engine_cache_invalidate(id)

    # --- engine cache ---------------------------------------------------

    def get_engine(self, source_id: int) -> Engine:
        """取或建 engine。

        cache key = (source_id, cache_version)。cache_version 由 updated_at/created_at 时间戳与
        连接身份（host, port, database）共同哈希得来 —— 保证 update 后失效，也避免测试环境中
        不同 in-memory DB 复用 id=1 时命中错误 engine（时间戳同秒精度会冲撞）。
        """
        row = self.repo.get_by_id(source_id)
        if row is None:
            raise NotFoundException(f"数据源 id={source_id} 不存在", code="DP_DS_NOT_FOUND")
        stamp = row.updated_at or row.created_at
        ts_us = int(stamp.timestamp() * 1_000_000) if stamp else 0
        identity = hash((row.host, row.port, row.database, row.username, row.dialect))
        cache_version = ts_us ^ identity
        return _build_or_get_engine(source_id, cache_version, self.db)

    # --- connection test -----------------------------------------------

    def test_connection(self, source_id: int) -> DpDataSourceTestResult:
        row = self.repo.get_by_id(source_id)
        if row is None:
            raise NotFoundException(f"数据源 id={source_id} 不存在", code="DP_DS_NOT_FOUND")
        started = time.perf_counter()
        try:
            engine = self.get_engine(source_id)
            with engine.connect() as conn:
                if row.dialect.startswith("postgresql"):
                    version = conn.execute(text("SHOW server_version")).scalar_one()
                elif row.dialect.startswith("mysql"):
                    version = conn.execute(text("SELECT VERSION()")).scalar_one()
                elif row.dialect.startswith("sqlite"):
                    version = conn.execute(text("SELECT sqlite_version()")).scalar_one()
                else:
                    version = None
            elapsed = int((time.perf_counter() - started) * 1000)
            return DpDataSourceTestResult(
                ok=True,
                elapsed_ms=elapsed,
                server_version=str(version) if version else None,
            )
        except Exception as exc:  # noqa: BLE001 — bubble up as structured result
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.warning(f"[dp-ds] test_connection source_id={source_id} failed: {exc}")
            return DpDataSourceTestResult(
                ok=False,
                elapsed_ms=elapsed,
                error=str(exc)[:512],
            )

    # --- schema introspection ------------------------------------------

    def describe_schema(self, source_id: int) -> dict[str, Any]:
        row = self.repo.get_by_id(source_id)
        if row is None:
            raise NotFoundException(f"数据源 id={source_id} 不存在", code="DP_DS_NOT_FOUND")
        engine = self.get_engine(source_id)
        insp = inspect(engine)

        db_name = row.database or "default"
        table_names = insp.get_table_names()
        tables: list[dict[str, Any]] = []
        for tbl in table_names:
            cols = []
            for c in insp.get_columns(tbl):
                cols.append({"name": c["name"], "type": str(c["type"])})
            tables.append({"name": tbl, "columns": cols})

        return {"databases": [{"name": db_name, "tables": tables}]}

    # --- helpers -------------------------------------------------------

    def _require_owner(self, id: int, user_id: int) -> DpDataSource:
        row = self.repo.get_by_id(id)
        if row is None:
            raise NotFoundException(f"数据源 id={id} 不存在", code="DP_DS_NOT_FOUND")
        if row.owner_user_id != user_id:
            raise BusinessException(
                code="DP_DS_FORBIDDEN",
                message="仅数据源拥有者可修改",
                status_code=403,
            )
        return row

    @staticmethod
    def _to_read(row: DpDataSource) -> DpDataSourceRead:
        return DpDataSourceRead(
            id=row.id,
            name=row.name,
            source_type=row.source_type,
            dialect=row.dialect,
            host=row.host,
            port=row.port,
            username=row.username,
            database=row.database,
            default_schema=row.default_schema,
            charset=row.charset,
            description=row.description,
            status=row.status,
            read_only_flag=bool(row.read_only_flag),
            has_password=bool(row.password_enc),
            owner_user_id=row.owner_user_id,
            created_by_user_id=row.created_by_user_id,
            extra_params=row.extra_params,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


# ==== 内部：进程级 engine cache =====================================

# 键：(source_id, updated_at_epoch)。updated_at 变更 → 新键 → 老键在 update()/delete() 里被 dispose。
_ENGINE_STORE: dict[tuple[int, int], Engine] = {}


def _build_or_get_engine(source_id: int, cache_version: int, db: Session) -> Engine:
    key = (source_id, cache_version)
    engine = _ENGINE_STORE.get(key)
    if engine is not None:
        return engine
    # 淘汰这个 source_id 的旧版本
    for k in list(_ENGINE_STORE):
        if k[0] == source_id:
            try:
                _ENGINE_STORE[k].dispose()
            except Exception:  # noqa: BLE001
                pass
            del _ENGINE_STORE[k]

    # 现场加载 row → 建 engine
    row = db.query(DpDataSource).filter(DpDataSource.id == source_id).first()
    if row is None:
        raise NotFoundException(f"数据源 id={source_id} 不存在", code="DP_DS_NOT_FOUND")

    url = _build_url(row)
    connect_args = _dialect_connect_args(row.dialect)
    if row.dialect == "sqlite":
        # SQLite 用默认 SingletonThreadPool，不支持 pool_size/max_overflow 等 QueuePool 参数
        engine = create_engine(
            url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    else:
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=10,
            connect_args=connect_args,
            future=True,
        )
    _ENGINE_STORE[key] = engine
    return engine


def _engine_cache_invalidate(source_id: int) -> None:
    for k in list(_ENGINE_STORE):
        if k[0] == source_id:
            try:
                _ENGINE_STORE[k].dispose()
            except Exception:  # noqa: BLE001
                pass
            del _ENGINE_STORE[k]


def _build_url(row: DpDataSource) -> URL | str:
    prefix = _DIALECT_URL_PREFIX.get(row.dialect)
    if not prefix:
        raise BusinessException(
            code="DP_DS_UNKNOWN_DIALECT",
            message=f"不支持的方言：{row.dialect}",
            status_code=400,
        )
    if row.dialect == "sqlite":
        # database 字段视为文件路径；:memory: 会被原样传给 SQLite
        return f"{prefix}:///{row.database}"
    password = crypto.decrypt(row.password_enc) if row.password_enc else ""
    query: dict[str, str] = {}
    if row.charset and row.dialect.startswith("mysql"):
        query["charset"] = row.charset
    return URL.create(
        drivername=prefix,
        username=row.username or None,
        password=password or None,
        host=row.host or None,
        port=row.port,
        database=row.database,
        query=query,
    )


def _dialect_connect_args(dialect: str) -> dict[str, Any]:
    if dialect.startswith("postgresql"):
        return {"connect_timeout": 30, "options": "-c statement_timeout=30000"}
    if dialect.startswith("mysql"):
        return {"connect_timeout": 30, "read_timeout": 30, "write_timeout": 30}
    return {}
