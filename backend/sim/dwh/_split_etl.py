"""从 dwh/etl.py 里抽出所有 INSERT SQL，按层输出到 dwh/etl/*.sql。"""
from __future__ import annotations
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
etl_py = (BASE / "etl.py").read_text()

# 匹配 exec_sql(cur, """<sql>""", "label")
pattern = re.compile(
    r'exec_sql\(cur,\s*f?"""\s*(?P<sql>.*?)"""\s*,\s*"(?P<label>[^"]*)"\s*\)',
    re.DOTALL,
)

# 收集
layer_sqls = {"dim": [], "ods": [], "dwd": [], "dws": [], "ads": []}
for m in pattern.finditer(etl_py):
    sql = m.group("sql").strip()
    label = m.group("label").strip()
    if not sql.upper().startswith(("INSERT", "TRUNCATE")):
        continue
    # 找目标表名判断层
    tbl_m = re.search(r"(dim|ods|dwd|dws|ads)_\w+", sql, re.IGNORECASE)
    if not tbl_m:
        # TRUNCATE 单独的语句用 label
        tbl_m = re.search(r"(dim|ods|dwd|dws|ads)_\w+", label, re.IGNORECASE)
    if not tbl_m:
        continue
    layer = tbl_m.group(1).lower()
    layer_sqls[layer].append((label, sql))

# 也把 etl.py 里 f-string 拼接的 ODS 部分拆出来
# 遍历 ods_tables 列表
ods_tables_match = re.search(r"ods_tables\s*=\s*\[(.*?)\]", etl_py, re.DOTALL)
if ods_tables_match:
    tuples_text = ods_tables_match.group(1)
    tuple_pattern = re.compile(r'\("(?P<tbl>ods_\w+)",\s*"(?P<src>[^"]+)",\s*"""(?P<sel>.*?)"""\)', re.DOTALL)
    for m in tuple_pattern.finditer(tuples_text):
        tbl = m.group("tbl")
        src = m.group("src")
        sel = m.group("sel").strip().replace("{today}", "2025-07-01")
        sql = f"TRUNCATE {tbl};\nINSERT INTO {tbl} {sel} FROM {src};"
        layer_sqls["ods"].append((f"{tbl} insert", sql))

# 写文件
for layer, items in layer_sqls.items():
    if not items:
        continue
    out = BASE / "etl" / f"{layer}_transform.sql"
    lines = [
        f"-- ============================================================\n",
        f"-- {layer.upper()} 层 ETL：{len(items)} 步\n",
        f"-- 从 etl.py 抽出（去除注释、模板变量已替换为示例值）\n",
        f"-- 生产环境中，模板变量 ${{today}} / ${{date}} / ${{month}} 应由调度器填充\n",
        f"-- ============================================================\n\n",
    ]
    for label, sql in items:
        lines.append(f"-- {label}\n{sql};\n\n")
    out.write_text("".join(lines))
    print(f"  ✓ {out.relative_to(BASE.parent)}  {len(items)} 步")

# etl/README.md
readme = BASE / "etl" / "README.md"
readme.write_text("""# ETL 脚本目录

## 生产入口

Python 脚本 `../etl.py` 是一键跑通所有层的入口（推荐执行方式）：

```bash
python3 dwh/etl.py
```

## 分层 SQL 文件

从 `etl.py` 抽出的分层 SQL，方便按需查看/调试：

- `ods_transform.sql`  业务库 → ODS
- `dim_transform.sql`  维度装载（含 SCD Type 2 客户维）
- `dwd_transform.sql`  ODS + 维度打宽 → 明细事实
- `dws_transform.sql`  按主题聚合
- `ads_transform.sql`  应用集市

## 依赖顺序

```
dim ← 独立
ods ← 业务库
dwd ← ods + dim
dws ← dwd
ads ← dws + dwd
```

`etl.py` 中已按此顺序执行；单独跑 SQL 文件时请遵循同样顺序。

## 模板变量

SQL 中的占位符（生产用调度器填充）：
- `${today}` — 抽数日期（默认 `2025-07-01`）
- `${date}` — 统计日期（如 `2025-06-15`）
- `${month}` — 统计月份（如 `202506`）
""")
print(f"  ✓ etl/README.md")
