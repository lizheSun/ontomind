"""Task 02 evals - 检查系统文档齐全度与内容质量。"""
from __future__ import annotations
import sys, re
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]

SYSTEMS = ["01_cust_cif", "02_loan_intake", "03_risk_decision", "04_credit_core",
           "05_collection", "06_funding", "07_finance", "08_marketing",
           "09_events", "10_csm", "11_hr_iam", "12_dp_meta"]

CORE_SYS = {"01_cust_cif", "02_loan_intake", "03_risk_decision", "04_credit_core", "07_finance"}
DOCS = ["BRD_业务需求.md", "PRD_产品需求.md", "TDD_技术设计.md", "PROJECT_项目管理.md"]


def check(name, level, cond, detail=""):
    tag = "✅" if cond else ("❌" if level == "CRITICAL" else "⚠️")
    print(f"{tag} [{level:8}] {name}  {detail}")
    return cond


def main():
    results = []
    # T2.1 每系统 4 份齐全
    missing = []
    for s in SYSTEMS:
        for d in DOCS:
            p = BASE / "docs" / s / d
            if not p.exists():
                missing.append(f"{s}/{d}")
    results.append(check("T2.1 48 份文档齐全", "CRITICAL", not missing,
                          f"missing={len(missing)}"))

    # T2.2 重点系统 ≥ 2000 字
    fail_core = []
    for s in CORE_SYS:
        for d in DOCS:
            p = BASE / "docs" / s / d
            if p.exists():
                n = len(p.read_text())
                if n < 2000:
                    fail_core.append(f"{s}/{d}={n}")
    results.append(check("T2.2 重点系统 ≥ 2000 字", "HIGH", not fail_core,
                          f"failed={fail_core[:3]}"))

    # T2.3 其他 ≥ 1200 字
    fail_std = []
    for s in SYSTEMS:
        if s in CORE_SYS:
            continue
        for d in DOCS:
            p = BASE / "docs" / s / d
            if p.exists():
                n = len(p.read_text())
                if n < 1200:
                    fail_std.append(f"{s}/{d}={n}")
    results.append(check("T2.3 其他系统 ≥ 1200 字", "MEDIUM", not fail_std,
                          f"failed={fail_std[:3]}"))

    # T2.4 每系统 TDD 至少 1 张 mermaid
    fail_mermaid = []
    for s in SYSTEMS:
        p = BASE / "docs" / s / "TDD_技术设计.md"
        if p.exists() and "```mermaid" not in p.read_text():
            fail_mermaid.append(s)
    results.append(check("T2.4 每系统 TDD 有 mermaid", "HIGH", not fail_mermaid,
                          f"failed={fail_mermaid}"))

    # T2.5 CIF PRD 中出现的核心 schema 字段是否存在（宽松：把 phone 等 API 层字段排除，只查 schema 层字段）
    p = BASE / "docs" / "01_cust_cif" / "PRD_产品需求.md"
    schema = (BASE / "systems" / "01_cust_cif" / "schema.sql").read_text()
    prd_content = p.read_text()
    # 只校验 schema 层字段（不含 API 层如 phone）
    schema_fields = {"customer_id", "id_number", "monthly_income", "birth_date", "gender"}
    missing = [f for f in schema_fields if f in prd_content and f not in schema]
    results.append(check("T2.5 PRD schema 字段对齐 (抽样 CIF)", "HIGH", not missing,
                          f"missing={missing}"))

    # T2.6 每份 PROJECT 有 3 章节
    fail_project = []
    for s in SYSTEMS:
        p = BASE / "docs" / s / "PROJECT_项目管理.md"
        if p.exists():
            c = p.read_text()
            if not (("里程碑" in c) and ("RACI" in c) and ("风险" in c)):
                fail_project.append(s)
    results.append(check("T2.6 PROJECT 三章齐全 (里程碑/RACI/风险)", "MEDIUM",
                         not fail_project, f"failed={fail_project}"))

    # 总结
    print("\n" + "=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")
    if sum(results) < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
