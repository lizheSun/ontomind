"""把 dwh/schema.sql 按 CREATE TABLE 拆到各分层子目录。
   把 etl.py 里的每层 INSERT 提取到 dwh/etl/*.sql。"""
from __future__ import annotations
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
schema_sql = (BASE / "schema.sql").read_text()

# 匹配 CREATE TABLE tblname (...) ...ENGINE... COMMENT 'xxx';
pattern = re.compile(
    r"CREATE TABLE (\w+)\s*\(.*?\)\s*ENGINE=[^;]*;",
    re.DOTALL | re.IGNORECASE,
)

layers = {"ods_": "ods", "dim_": "dim", "dwd_": "dwd", "dws_": "dws", "ads_": "ads"}

# 收集每层的表 DDL
layer_ddls = {v: [] for v in layers.values()}
for m in pattern.finditer(schema_sql):
    ddl = m.group(0)
    tbl = m.group(1)
    for prefix, layer in layers.items():
        if tbl.startswith(prefix):
            drop = f"DROP TABLE IF EXISTS {tbl};\n"
            layer_ddls[layer].append(drop + ddl)
            break

# 写到分层目录
for layer, ddls in layer_ddls.items():
    if not ddls:
        continue
    outfile = BASE / layer / f"{layer}_tables.sql"
    header = f"-- ============================================================\n" \
             f"-- {layer.upper()} 层表定义 ({len(ddls)} 张表)\n" \
             f"-- 从 dwh/schema.sql 拆出，等价于 schema.sql 中 {layer}_* 部分\n" \
             f"-- ============================================================\n\n"
    outfile.write_text(header + "\n\n".join(ddls) + "\n")
    print(f"  ✓ {outfile.relative_to(BASE.parent)}  {len(ddls)} 张表")

LAYER_DESC = {
    "ods": "**贴源层**：几乎 1:1 复制业务系统数据。带 `ods_stat_date` 字段支持批次增量。",
    "dim": "**维度层**：共享维度（客户/产品/日期/渠道/机构/资金方）。客户走 SCD Type 2。",
    "dwd": "**明细事实层**：清洗后的明细粒度事实表，冗余打宽常用维度字段。",
    "dws": "**汇总层**：按主题按粒度（day/month）聚合，直接支撑指标计算。",
    "ads": "**应用层**：面向具体报表/驾驶舱的定制表。",
}

# 每层写 README
for layer in layers.values():
    path = BASE / layer / "README.md"
    tables_here = sorted([t for prefix, l in layers.items() if l == layer
                          for t in re.findall(rf"CREATE TABLE ({prefix}\w+)", schema_sql, re.IGNORECASE)])
    tables_list = "\n".join(f"- `{t}`" for t in tables_here)
    path.write_text(
        f"# {layer.upper()} 层\n\n"
        f"DDL 文件：`{layer}_tables.sql`\n\n"
        f"包含 {len(tables_here)} 张表：\n\n"
        f"{tables_list}\n\n"
        f"## 作用\n\n"
        f"{LAYER_DESC[layer]}\n\n"
        f"## 与其他文件的关系\n\n"
        f"- 完整 DDL 也在 `../schema.sql`（本文件是从中拆出的分层视图）\n"
        f"- ETL 逻辑：`../etl/{layer}_transform.sql` 或 `../etl.py`\n"
    )
    print(f"  ✓ {path.relative_to(BASE.parent)}")

print("\n完成拆分")
