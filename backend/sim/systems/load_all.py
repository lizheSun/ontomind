"""批量把 seed_data/*.csv 用 executemany 导入 MySQL。"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import csv
import time
from common import BASE_DIR, mysql_conn

SYSTEMS_DIR = BASE_DIR / "systems"

SYS_DIR_MAP = {
    "01_cust_cif": "sim_cust_cif",
    "02_loan_intake": "sim_loan_intake",
    "03_risk_decision": "sim_risk_decision",
    "04_credit_core": "sim_credit_core",
    "05_collection": "sim_collection",
    "06_funding": "sim_funding",
    "07_finance": "sim_finance",
    "08_marketing": "sim_marketing",
    "09_events": "sim_events",
    "10_csm": "sim_csm",
    "11_hr_iam": "sim_hr_iam",
    "12_dp_meta": "sim_dp_meta",
}

BATCH = 2000


def load_csv_to_table(conn, db: str, table: str, csv_path: Path):
    if not csv_path.exists():
        return 0
    with csv_path.open() as f:
        reader = csv.reader(f)
        columns = next(reader)
        rows = list(reader)
    if not rows:
        return 0
    # \\N -> None
    for row in rows:
        for i, v in enumerate(row):
            if v == "\\N" or v == "":
                row[i] = None
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE `{db}`.`{table}`")
        placeholders = ",".join(["%s"] * len(columns))
        col_list = ",".join(f"`{c}`" for c in columns)
        sql = f"INSERT INTO `{db}`.`{table}` ({col_list}) VALUES ({placeholders})"
        for i in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[i:i+BATCH])
    conn.commit()
    return len(rows)


def main():
    t0 = time.time()
    conn = mysql_conn()
    total = 0
    for sys_dir, db in SYS_DIR_MAP.items():
        seed_dir = SYSTEMS_DIR / sys_dir / "seed_data"
        if not seed_dir.exists():
            print(f"  ! {sys_dir}: no seed_data/")
            continue
        for csv_file in sorted(seed_dir.glob("*.csv")):
            table = csv_file.stem
            n = load_csv_to_table(conn, db, table, csv_file)
            total += n
            print(f"  {db}.{table:<30}  {n:>10} rows")
    conn.close()
    print(f"\ntotal {total} rows in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
