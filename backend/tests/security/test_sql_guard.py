"""SQL guard 单元测试 — 15 case TDD 契约。

RED-first：先运行 pytest 期望全部失败（模块尚未实现），
再实现 sql_guard.py 让所有测试变绿。
"""
from __future__ import annotations

import pytest

from app.core.sql_guard import validate_and_shape, SqlGuardError


# ---------- 拒绝：DML / DDL ----------

def test_reject_insert() -> None:
    with pytest.raises(SqlGuardError, match="非 SELECT|forbidden"):
        validate_and_shape("INSERT INTO users (id) VALUES (1)", dialect="mysql", max_rows=100)


def test_reject_update() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("UPDATE users SET a = 1", dialect="mysql", max_rows=100)


def test_reject_delete() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("DELETE FROM users", dialect="mysql", max_rows=100)


def test_reject_drop() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("DROP TABLE users", dialect="mysql", max_rows=100)


def test_reject_truncate() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("TRUNCATE TABLE users", dialect="mysql", max_rows=100)


def test_reject_create() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("CREATE TABLE t (a INT)", dialect="mysql", max_rows=100)


def test_reject_alter() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape("ALTER TABLE users ADD COLUMN x INT", dialect="mysql", max_rows=100)


# ---------- 拒绝：多语句 / 堆叠注入 ----------

def test_reject_multi_statement() -> None:
    with pytest.raises(SqlGuardError, match="多语句|multi|single"):
        validate_and_shape("SELECT 1; SELECT 2", dialect="mysql", max_rows=100)


def test_reject_multi_statement_with_trailing_comment() -> None:
    # 尾部注释是 sqlparse.split 的经典绕过点 — 必须显式测。
    with pytest.raises(SqlGuardError):
        validate_and_shape("SELECT 1; --", dialect="mysql", max_rows=100)


def test_reject_stacked_ddl_injection() -> None:
    with pytest.raises(SqlGuardError):
        validate_and_shape(
            "SELECT * FROM users WHERE 1=1; DROP TABLE users",
            dialect="mysql", max_rows=100,
        )


# ---------- 拒绝：CTE 里藏 DML ----------

def test_reject_cte_with_dml() -> None:
    # PostgreSQL 允许 WITH x AS (INSERT ...) SELECT ...；MySQL 不支持但语法层可解析。
    # 我们用 postgres 方言测这个更贴近真实攻击面。
    sql = "WITH x AS (INSERT INTO logs (a) VALUES (1) RETURNING a) SELECT * FROM x"
    with pytest.raises(SqlGuardError):
        validate_and_shape(sql, dialect="postgres", max_rows=100)


# ---------- 表白名单 ----------

def test_reject_when_table_not_in_whitelist() -> None:
    with pytest.raises(SqlGuardError, match="白名单|whitelist|allowed"):
        validate_and_shape(
            "SELECT * FROM users",
            dialect="mysql", max_rows=100,
            allowed_tables={"orders"},
        )


def test_accept_when_table_in_whitelist() -> None:
    shaped = validate_and_shape(
        "SELECT * FROM users LIMIT 10",
        dialect="mysql", max_rows=100,
        allowed_tables={"users"},
    )
    assert "users" in {t.lower() for t in shaped.tables}


# ---------- LIMIT 注入 / 夹紧 ----------

def test_accept_preserves_limit_when_below_cap() -> None:
    shaped = validate_and_shape(
        "SELECT id FROM users LIMIT 500",
        dialect="mysql", max_rows=1000,
    )
    # 500 <= 1000, keep it.
    assert "500" in shaped.sql
    assert shaped.limit == 500


def test_accept_injects_limit_when_missing() -> None:
    shaped = validate_and_shape(
        "SELECT id FROM users",
        dialect="mysql", max_rows=100,
    )
    assert "100" in shaped.sql
    assert shaped.limit == 100


def test_accept_clamps_limit_when_over_cap() -> None:
    shaped = validate_and_shape(
        "SELECT id FROM users LIMIT 5000",
        dialect="mysql", max_rows=1000,
    )
    # 5000 > 1000, clamp.
    assert "1000" in shaped.sql
    assert "5000" not in shaped.sql
    assert shaped.limit == 1000


# ---------- 附加：UNION / 嵌套 ----------

def test_accept_union_all_selects() -> None:
    shaped = validate_and_shape(
        "SELECT id FROM users UNION ALL SELECT id FROM orders",
        dialect="mysql", max_rows=100,
        allowed_tables={"users", "orders"},
    )
    assert {"users", "orders"}.issubset({t.lower() for t in shaped.tables})


def test_shaped_sql_returns_tables_list() -> None:
    shaped = validate_and_shape(
        "SELECT u.id, o.total FROM users u JOIN orders o ON o.uid = u.id",
        dialect="mysql", max_rows=100,
    )
    names = {t.lower() for t in shaped.tables}
    assert "users" in names
    assert "orders" in names
