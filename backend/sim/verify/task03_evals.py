"""Task 03 evals - 数据仓库检查。"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "systems"))
from common import mysql_conn

def check(name, level, cond, detail=""):
    tag = "✅" if cond else ("❌" if level == "CRITICAL" else "⚠️")
    print(f"{tag} [{level:8}] {name}  {detail}")
    return cond

def main():
    conn = mysql_conn("sim_dw")
    cur = conn.cursor()
    results = []

    # T3.1 库存在，表数 45-55
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sim_dw'")
    (n,) = cur.fetchone()
    results.append(check("T3.1 sim_dw 45-55 张表", "CRITICAL", 45 <= n <= 55, f"got {n}"))

    # T3.2 分层齐全
    for layer, min_n in [("ods_", 15), ("dim_", 6), ("dwd_", 10), ("dws_", 10), ("ads_", 5)]:
        cur.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sim_dw' AND table_name LIKE '{layer}%'")
        (m,) = cur.fetchone()
        results.append(check(f"T3.2 {layer.rstrip('_').upper()} 层 ≥ {min_n}", "HIGH",
                             m >= min_n, f"got {m}"))

    # T3.3 命名规范：所有表都以 layer_ 开头
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='sim_dw'
          AND table_name NOT LIKE 'ods_%' AND table_name NOT LIKE 'dim_%'
          AND table_name NOT LIKE 'dwd_%' AND table_name NOT LIKE 'dws_%'
          AND table_name NOT LIKE 'ads_%'
    """)
    bad = [r[0] for r in cur.fetchall()]
    results.append(check("T3.3 命名规范", "HIGH", not bad, f"bad={bad}"))

    # T3.4 每张表带 COMMENT
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema='sim_dw' AND (table_comment IS NULL OR table_comment='')
    """)
    (miss_c,) = cur.fetchone()
    results.append(check("T3.4 全部表带 COMMENT", "HIGH", miss_c == 0, f"missing={miss_c}"))

    # T3.6 SCD Type 2: dim_customer 有 valid_from/valid_to/is_current
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema='sim_dw' AND table_name='dim_customer'
          AND column_name IN ('valid_from', 'valid_to', 'is_current')
    """)
    (n_scd,) = cur.fetchone()
    results.append(check("T3.6 dim_customer SCD2 字段齐全", "HIGH", n_scd == 3,
                          f"got {n_scd}/3"))

    # T3.7 sample_queries 全跑通
    import subprocess
    sample_path = Path(__file__).resolve().parents[1] / "dwh" / "sample_queries.sql"
    with open(sample_path) as f:
        r = subprocess.run(["mysql", "-u", "root"], stdin=f,
                           capture_output=True, text=True)
    ok = r.returncode == 0 and "ERROR" not in r.stderr.upper()
    sql_text = sample_path.read_text()
    n_selects = sum(1 for line in sql_text.split("\n") if line.strip().upper().startswith("SELECT") and "COALESCE" not in line[:20])
    results.append(check(f"T3.7 sample_queries 全部跑通", "HIGH", ok,
                          f"return code {r.returncode}, {n_selects} queries, stderr={r.stderr[:100]}"))

    # T3.8 DW 中放款金额 vs 业务库
    cur.execute("SELECT SUM(principal) FROM dwd_credit_loan")
    dw_sum = float(cur.fetchone()[0])
    cur.execute("SELECT SUM(principal) FROM sim_credit_core.loan")
    biz_sum = float(cur.fetchone()[0])
    diff = abs(dw_sum - biz_sum)
    results.append(check("T3.8 DW=业务库放款金额", "CRITICAL", diff < 1.0,
                          f"DW={dw_sum:.2f} biz={biz_sum:.2f} diff={diff:.2f}"))

    # T3.9 关键 DWS 表不空
    for tbl in ["dws_customer_active_day", "dws_credit_customer_day",
                "dws_credit_product_day", "dws_finance_income_day",
                "dws_marketing_channel_day"]:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        (m,) = cur.fetchone()
        results.append(check(f"T3.9 {tbl} 非空", "HIGH", m > 0, f"got {m}"))

    conn.close()

    print("\n" + "=" * 60)
    passed = sum(results)
    print(f"Passed: {passed}/{len(results)}")
    crit_fail = 0  # 上面循环里已用 print，重跑一遍确认
    if passed < len(results):
        crit_fail = sum(1 for r in results if not r)
    if any(not r for r in results):
        print("有失败项，请查看上面")


if __name__ == "__main__":
    main()
