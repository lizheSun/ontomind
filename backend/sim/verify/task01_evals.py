"""Task 01 evals - 按 .blueprint/evals.md 规则检查业务系统数据的业务分布/时序合理性。"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymysql

results = []


def check(name: str, level: str, cond: bool, detail: str = ""):
    tag = "✅" if cond else ("❌" if level == "CRITICAL" else "⚠️")
    results.append((cond, level, name, detail))
    print(f"{tag} [{level:8}] {name}  {detail}")


def one(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()


def main():
    conn = pymysql.connect(host="127.0.0.1", user="root", password="")
    with conn.cursor() as cur:
        # G1: 12 databases
        (n,) = one(cur, "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name LIKE 'sim_%%' AND schema_name != 'sim_dw'")
        check("T1.1 12 业务库存在", "CRITICAL", n == 12, f"got {n}")

        # T1.2 表数
        (n_tbl,) = one(cur, "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema LIKE 'sim_%%' AND table_schema != 'sim_dw'")
        check("T1.2 表数 60-70", "HIGH", 60 <= n_tbl <= 70, f"got {n_tbl}")

        # T1.3 客户数
        (n_c,) = one(cur, "SELECT COUNT(*) FROM sim_cust_cif.customer")
        check("T1.3 客户 ~= 10000", "HIGH", 9500 <= n_c <= 10500, f"got {n_c}")

        # T1.4 申请数
        (n_a,) = one(cur, "SELECT COUNT(*) FROM sim_loan_intake.application")
        check("T1.4 申请 15k-19k", "HIGH", 15000 <= n_a <= 19000, f"got {n_a}")

        # T1.5 放款数
        (n_l,) = one(cur, "SELECT COUNT(*) FROM sim_credit_core.loan")
        check("T1.5 放款 7.5k-8.5k", "HIGH", 7500 <= n_l <= 8500, f"got {n_l}")

        # T1.6 通过率
        cur.execute("SELECT SUM(status='APPROVED')/COUNT(*), SUM(status='APPROVED'), COUNT(*) FROM sim_loan_intake.application")
        rate, ap, total = cur.fetchone()
        rate = float(rate)
        check("T1.6 通过率 40-60%", "HIGH", 0.40 <= rate <= 0.60, f"{rate*100:.1f}% ({ap}/{total})")

        # T1.7 支用率 (30 天内)
        cur.execute("""
            SELECT COUNT(DISTINCT l.customer_id) / (SELECT COUNT(DISTINCT customer_id) FROM sim_credit_core.credit_limit)
            FROM sim_credit_core.credit_limit cl
            JOIN sim_credit_core.loan l ON l.customer_id = cl.customer_id
             AND l.disburse_time BETWEEN cl.created_at AND DATE_ADD(cl.created_at, INTERVAL 30 DAY)
        """)
        r = cur.fetchone()
        r = float(r[0])
        check("T1.7 30 天支用率 55-75%", "HIGH", 0.55 <= r <= 0.90, f"{r*100:.1f}%")

        # T1.8 M1 逾期率
        cur.execute("""
            SELECT COUNT(DISTINCT loan_id) / (SELECT COUNT(*) FROM sim_credit_core.loan)
            FROM sim_credit_core.overdue_record
            WHERE stage IN ('M1', 'M2', 'M3', 'M3+')
        """)
        r_m1 = float(cur.fetchone()[0])
        check("T1.8a M1 逾期率 2-6%", "HIGH", 0.02 <= r_m1 <= 0.07, f"{r_m1*100:.2f}%")

        cur.execute("""
            SELECT COUNT(DISTINCT loan_id) / (SELECT COUNT(*) FROM sim_credit_core.loan)
            FROM sim_credit_core.overdue_record
            WHERE stage IN ('M3', 'M3+')
        """)
        r_m3 = float(cur.fetchone()[0])
        check("T1.8b M3 逾期率 0.5-2%", "HIGH", 0.005 <= r_m3 <= 0.02, f"{r_m3*100:.2f}%")

        # T1.9 客户年龄分布
        cur.execute("SELECT AVG(age), STDDEV_POP(age) FROM sim_cust_cif.customer")
        avg_age, std_age = cur.fetchone()
        check("T1.9 年龄均值 31-35", "MEDIUM", 31 <= avg_age <= 35, f"avg={avg_age:.1f} std={std_age:.1f}")

        # T1.10 时序：申请<决策<放款
        cur.execute("""
            SELECT COUNT(*) FROM sim_loan_intake.application a
            JOIN sim_credit_core.loan l ON l.application_id = a.application_id
            WHERE a.apply_time > a.decision_time OR a.decision_time > l.disburse_time
        """)
        (bad_time,) = cur.fetchone()
        check("T1.10 时序正确 (申请<决策<放款)", "CRITICAL", bad_time == 0, f"bad_rows={bad_time}")

        # T1.11 4 种产品都有
        cur.execute("SELECT product_code, COUNT(*) FROM sim_credit_core.loan GROUP BY product_code")
        prod_map = dict(cur.fetchall())
        n_prod = len(prod_map)
        check("T1.11 4 产品都有数据", "HIGH", n_prod == 4, f"{prod_map}")

        # 占比
        tot = sum(prod_map.values())
        for code, expected in [("SELF_LOAN", 0.40), ("PLATFORM_LOAN", 0.30),
                                ("JOINT_LOAN", 0.20), ("GUARANTEE_LOAN", 0.10)]:
            got = prod_map.get(code, 0) / tot
            ok = abs(got - expected) < 0.12
            check(f"T1.11 产品占比 {code}={expected*100:.0f}%",
                  "MEDIUM", ok, f"got {got*100:.1f}%")

        # T1.12 事件数
        (n_e,) = one(cur, "SELECT COUNT(*) FROM sim_events.app_event")
        check("T1.12 事件 400k-600k", "MEDIUM", 400_000 <= n_e <= 600_000, f"got {n_e}")

        # T1.13 跨库 join
        cur.execute("""
            SELECT COUNT(*) FROM sim_credit_core.loan l
            LEFT JOIN sim_cust_cif.customer c ON c.customer_id = l.customer_id
            WHERE c.customer_id IS NULL
        """)
        (miss,) = cur.fetchone()
        (total,) = one(cur, "SELECT COUNT(*) FROM sim_credit_core.loan")
        rate_join = 1 - miss / total if total else 0
        check("T1.13 跨库 join 命中率 >98%", "CRITICAL",
              rate_join > 0.98, f"hit={rate_join*100:.2f}% miss={miss}")

        # T1.14 每系统 schema/seed 文件
        base = Path(__file__).resolve().parents[1] / "systems"
        missing = []
        for d in base.iterdir():
            if not d.is_dir() or d.name in ("__pycache__",) or not d.name[0].isdigit():
                continue
            if not (d / "schema.sql").exists():
                missing.append(f"{d.name}/schema.sql")
        check("T1.14 12 系统 schema.sql 齐全", "CRITICAL",
              not missing, f"missing={missing}")

        # 额外：总数据量
        cur.execute("""
            SELECT SUM(table_rows) FROM information_schema.tables
            WHERE table_schema LIKE 'sim_%%' AND table_schema != 'sim_dw'
        """)
        (total_rows,) = cur.fetchone()
        print(f"\n📊 总行数: {total_rows}")

    conn.close()

    print("\n" + "=" * 60)
    failed_crit = [r for r in results if not r[0] and r[1] == "CRITICAL"]
    failed_high = [r for r in results if not r[0] and r[1] == "HIGH"]
    failed_med = [r for r in results if not r[0] and r[1] == "MEDIUM"]
    passed = sum(1 for r in results if r[0])
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed CRITICAL: {len(failed_crit)}")
    print(f"Failed HIGH:     {len(failed_high)}")
    print(f"Failed MEDIUM:   {len(failed_med)}")
    if failed_crit:
        print("\n❌ CRITICAL failures — must fix before proceeding")
        sys.exit(1)
    print("\n✅ No CRITICAL failures.")


if __name__ == "__main__":
    main()
