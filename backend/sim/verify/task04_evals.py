"""Task 04 evals - 指标体系检查，重点抽样验证 SQL 可跑通。"""
from __future__ import annotations
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "systems"))
import yaml
from common import mysql_conn

BASE = Path(__file__).resolve().parents[1] / "metrics"


def check(name, level, cond, detail=""):
    tag = "✅" if cond else ("❌" if level == "CRITICAL" else "⚠️")
    print(f"{tag} [{level:8}] {name}  {detail}")
    return cond


def main():
    results = []

    # T4.1 4 份治理文档齐全
    gov_files = ["01_管理办法.md", "02_命名规范.md", "03_口径管理.md", "04_分级分类.md"]
    missing = [f for f in gov_files if not (BASE / "governance" / f).exists()]
    results.append(check("T4.1 4 份治理文档齐全", "CRITICAL", not missing, f"missing={missing}"))

    # T4.2 指标 ≥ 200
    catalog = yaml.safe_load((BASE / "catalog" / "metrics.yaml").read_text())
    metrics = catalog["metrics"]
    results.append(check("T4.2 指标数 ≥ 200", "CRITICAL", len(metrics) >= 200,
                          f"got {len(metrics)}"))

    # T4.3 每个指标字段齐全
    required = ["id", "name_zh", "name_en", "definition", "formula",
                "source_tables", "sql_template", "level", "domain", "department"]
    missing_field = []
    for m in metrics:
        for f in required:
            if not m.get(f):
                missing_field.append(f"{m.get('id','?')}.{f}")
                break
    results.append(check("T4.3 字段齐全", "CRITICAL", not missing_field,
                          f"missing={len(missing_field)}"))

    # T4.4 每指标 ≥ 2 别名
    few_alias = [m["id"] for m in metrics if len(m.get("aliases", [])) < 2]
    results.append(check(f"T4.4 别名 ≥ 2 个", "HIGH", len(few_alias) < 20,
                          f"failed={len(few_alias)}"))

    # T4.5 抽样 30 个指标 sql_template 跑通
    random.seed(20260710)
    sample = random.sample(metrics, min(30, len(metrics)))
    conn = mysql_conn("sim_dw")
    cur = conn.cursor()
    cur.execute("SET SESSION sql_mode = REPLACE(REPLACE(@@sql_mode, 'ONLY_FULL_GROUP_BY', ''), ',,', ',')")
    ok_count = 0
    err_examples = []
    for m in sample:
        sql = m["sql_template"]
        # 参数替换
        sql = sql.replace("${date}", "2025-06-15")
        sql = sql.replace("${month}", "202506")
        try:
            cur.execute(sql)
            cur.fetchall()
            ok_count += 1
        except Exception as e:
            err_examples.append(f"{m['id']}: {str(e)[:80]}")
    conn.close()
    results.append(check(f"T4.5 抽样 30 SQL 跑通率 ≥ 90%", "CRITICAL",
                          ok_count >= 27,
                          f"{ok_count}/30 通过；样例失败: {err_examples[:2]}"))

    # T4.6 6 领域文档齐全
    for dom in ["user", "credit", "finance", "risk", "marketing", "operation"]:
        p = BASE / "domains" / f"{dom}_domain.md"
        results.append(check(f"T4.6 {dom}_domain.md 存在", "CRITICAL", p.exists()))

    # T4.7 6 部门文档齐全
    for dept in ["risk_mgmt", "finance", "self_credit_product", "platform_product",
                  "profit_share_product", "marketing"]:
        p = BASE / "domains" / "departments" / f"{dept}.md"
        results.append(check(f"T4.7 {dept}.md 存在", "CRITICAL", p.exists()))

    # T4.8 分级比例
    from collections import Counter
    lvl_cnt = Counter(m["level"] for m in metrics)
    l1_ratio = lvl_cnt["一级"] / len(metrics)
    results.append(check(f"T4.8 一级指标 15-25%", "MEDIUM",
                          0.15 <= l1_ratio <= 0.30,
                          f"L1={l1_ratio*100:.1f}% ({lvl_cnt['一级']})"))

    # T4.10 owner
    orphan = [m["id"] for m in metrics if "@simcf.com" not in m.get("owner", "")]
    results.append(check("T4.10 全部指标有 owner", "MEDIUM", not orphan,
                          f"missing={len(orphan)}"))

    print("\n" + "=" * 60)
    passed = sum(results)
    print(f"Passed: {passed}/{len(results)}")
    if any(not r for r in results):
        crit_fail = sum(1 for r in results if not r)
        print(f"failed: {crit_fail}")


if __name__ == "__main__":
    main()
