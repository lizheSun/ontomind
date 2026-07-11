"""SQL 守卫模块 — 数据平台查询安全的第一道防线。

契约（`validate_and_shape`）：
1. 拒绝多语句：`sqlparse.split()` 返回 >1 段（尾部注释也算）。
2. 要求 SELECT：`sqlparse.parse()[0].get_type() == 'SELECT'`。
3. AST 深度扫描：`sqlglot.parse_one(sql, dialect)` 后 walk 整棵树，
   任何 Insert/Update/Delete/Merge/Create/Drop/Alter/TruncateTable/Command
   节点都拒绝（防 CTE-DML 绕过）。
4. LIMIT 治理：缺失 → 注入 `max_rows`；存在但 > max_rows → 夹紧到 max_rows；
   存在且 <= max_rows → 保留。
5. 表白名单（可选）：所有 Table 节点必须命中 `allowed_tables`。

用法：
    shaped = validate_and_shape(
        "SELECT * FROM users",
        dialect="mysql", max_rows=1000, allowed_tables={"users"},
    )
    engine.execute(text(shaped.sql))

`SqlGuardError` 是本模块内部异常；service 层应捕获后转换为 `BusinessException`。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sqlglot
import sqlparse
from sqlglot import exp
from sqlparse.sql import Statement


# ---- 异常 --------------------------------------------------------------

class SqlGuardError(ValueError):
    """SQL 守卫拒绝一条查询时抛出。message 使用中文，可直接透出给前端。"""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


# ---- 结果类型 ----------------------------------------------------------

@dataclass(frozen=True)
class ShapedSql:
    """经守卫处理后的 SQL 结果。"""

    sql: str
    limit: int
    tables: list[str] = field(default_factory=list)


# ---- 禁用节点白名单 ----------------------------------------------------
# 任何 AST 里出现这些节点即拒绝（包括 CTE 内部）。
_FORBIDDEN_NODES: tuple[type, ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    # sqlglot 里各种未识别的裸命令都会落到 Command 节点：
    # GRANT/REVOKE/SET/CALL/COPY/VACUUM/ATTACH/LOAD 等。
    exp.Command,
)

# 顶层节点必须是这些类型之一（SELECT / CTE / UNION / 子查询）。
_ALLOWED_TOP: tuple[type, ...] = (exp.Select, exp.Union, exp.With, exp.Subquery)


# ---- 主入口 ------------------------------------------------------------

def validate_and_shape(
    sql: str,
    dialect: str,
    max_rows: int,
    allowed_tables: Optional[set[str]] = None,
) -> ShapedSql:
    """校验并塑形 SQL，返回可安全执行的语句。

    Args:
        sql: 用户或 LLM 输入的原始 SQL。
        dialect: sqlglot 方言名，例：`mysql` / `postgres` / `sqlite`。
        max_rows: LIMIT 上限。缺失时注入此值；超出时夹紧到此值。
        allowed_tables: 可选。传入时所有引用表必须命中（大小写不敏感）。

    Raises:
        SqlGuardError: 任一契约条款被违反。
    """
    if not sql or not sql.strip():
        raise SqlGuardError("empty", "SQL 不能为空")

    # (1) 多语句拒绝：sqlparse.split() 会保留结尾的分号和空段。
    parts = [p for p in sqlparse.split(sql) if p and p.strip() and p.strip() != ";"]
    if len(parts) != 1:
        raise SqlGuardError(
            "multi",
            f"多语句被拒绝：仅允许 single SELECT 语句，检测到 {len(parts)} 段",
        )

    only = parts[0].strip().rstrip(";").strip()
    if not only:
        raise SqlGuardError("empty", "SQL 不能为空")

    # (2) 顶层类型必须是 SELECT。
    parsed_list = sqlparse.parse(only)
    if len(parsed_list) != 1 or not isinstance(parsed_list[0], Statement):
        raise SqlGuardError("parse", "SQL 解析失败或包含多个语句")
    top_type = parsed_list[0].get_type()
    if top_type != "SELECT":
        raise SqlGuardError(
            "non_select",
            f"非 SELECT 语句被拒绝（当前为 {top_type or 'UNKNOWN'}）",
        )

    # (3) sqlglot AST 深度扫描 —— 拒绝任何 forbidden 节点。
    try:
        root = sqlglot.parse_one(only, read=dialect)
    except sqlglot.errors.ParseError as e:  # pragma: no cover - error path
        raise SqlGuardError("parse", f"SQL 语法解析失败：{e}") from e

    if root is None:
        raise SqlGuardError("parse", "SQL 解析结果为空")

    if not isinstance(root, _ALLOWED_TOP):
        raise SqlGuardError(
            "non_select",
            f"非 SELECT 顶层节点被拒绝（{type(root).__name__}）",
        )

    for node in root.walk():
        # sqlglot.walk() yields (node, parent, key); 第一个是 node
        expr = node[0] if isinstance(node, tuple) else node
        if isinstance(expr, _FORBIDDEN_NODES):
            raise SqlGuardError(
                "forbidden",
                f"forbidden operation: {type(expr).__name__}（禁止的操作）",
            )

    # (4) 表白名单校验（大小写不敏感、schema 前缀敏感）。
    tables_found: list[str] = []
    for tbl in root.find_all(exp.Table):
        name = tbl.name  # 不带 schema/db 前缀
        if name:
            tables_found.append(name)

    if allowed_tables is not None:
        allowed_lc = {t.lower() for t in allowed_tables}
        for t in tables_found:
            if t.lower() not in allowed_lc:
                raise SqlGuardError(
                    "whitelist",
                    f"表 {t!r} 不在白名单内（allowed={sorted(allowed_tables)}）",
                )

    # (5) LIMIT 治理（在表提取之后，因为 wrap 可能引入子查询节点）。
    final_limit = _apply_limit(root, max_rows)

    return ShapedSql(sql=root.sql(dialect=dialect), limit=final_limit, tables=tables_found)


# ---- LIMIT 逻辑 --------------------------------------------------------

def _apply_limit(root: exp.Expression, cap: int) -> int:
    """就地修改 root 的 LIMIT，返回最终生效的行数上限。"""
    # WITH-SELECT 内部就是 Select，直接对内层 SELECT 处理。
    if isinstance(root, exp.With):
        inner_select = root.this
        if isinstance(inner_select, exp.Select):
            return _apply_limit_on_select(inner_select, cap)
        # 内层是 UNION 等的兜底
        return cap

    # UNION：LIMIT 可以直接挂在 UNION 上。
    if isinstance(root, exp.Union):
        existing = root.args.get("limit")
        if existing is None:
            root.set("limit", exp.Limit(expression=exp.Literal.number(cap)))
            return cap
        lit = existing.expression
        if isinstance(lit, exp.Literal) and lit.is_int:
            current = int(lit.name)
            if current > cap:
                root.set("limit", exp.Limit(expression=exp.Literal.number(cap)))
                return cap
            return current
        root.set("limit", exp.Limit(expression=exp.Literal.number(cap)))
        return cap

    if isinstance(root, exp.Select):
        return _apply_limit_on_select(root, cap)

    return cap  # fallback，不应到达


def _apply_limit_on_select(select: exp.Select, cap: int) -> int:
    existing = select.args.get("limit")
    if existing is None:
        select.limit(cap, copy=False)
        return cap

    # 取出 LIMIT 表达式的字面量
    lit = existing.expression
    if isinstance(lit, exp.Literal) and lit.is_int:
        current = int(lit.name)
        if current > cap:
            # 夹紧
            select.limit(cap, copy=False)
            return cap
        return current

    # LIMIT 参数不是字面量（比如是 ? 占位符或表达式）：视为不可信 → 强制 cap
    select.limit(cap, copy=False)
    return cap
