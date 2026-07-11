"""
公共工具库 —— seed 数据生成通用组件

包含：
- 稳定的随机种子
- 中国身份证号生成（校验位正确、行政区划真实）
- ID 生成器（跨系统一致）
- 时序采样工具
- MySQL 连接
"""
from __future__ import annotations
import hashlib
import random
import datetime as dt
from pathlib import Path
from typing import Iterable

import pymysql
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/sim/
CONFIG = yaml.safe_load((BASE_DIR / "config" / "databases.yaml").read_text())

SEED = 20260710
random.seed(SEED)

DATE_START = dt.date.fromisoformat(CONFIG["timeline"]["data_start"])
DATE_END = dt.date.fromisoformat(CONFIG["timeline"]["data_end"])
TODAY = dt.date.fromisoformat(CONFIG["timeline"]["today"])


# ---------- ID 生成器 ----------


def customer_id(seq: int) -> str:
    return f"C{seq:08d}"


def application_id(day: dt.date, seq: int) -> str:
    return f"AP{day.strftime('%Y%m%d')}{seq:06d}"


def loan_id(day: dt.date, seq: int) -> str:
    return f"LN{day.strftime('%Y%m%d')}{seq:06d}"


def contract_id(loan_id_str: str) -> str:
    return "CT" + loan_id_str[2:]


# ---------- 身份证 & 手机号 ----------

# 常见省份行政区划前 2 位（真实），后 4 位随机固定
_REGION_CODES = {
    "北京": "1101", "上海": "3101", "广东": "4401", "江苏": "3201", "山东": "3701",
    "浙江": "3301", "河南": "4101", "四川": "5101", "湖北": "4201", "湖南": "4301",
    "福建": "3501", "河北": "1301", "辽宁": "2101", "陕西": "6101", "安徽": "3401",
    "江西": "3601", "云南": "5301", "重庆": "5001", "黑龙江": "2301", "吉林": "2201",
}
REGION_LIST = list(_REGION_CODES.items())
REGION_WEIGHTS = [1.5, 1.0, 3.0, 2.5, 2.5, 2.0, 2.5, 1.5, 1.8, 1.5,
                  1.2, 1.5, 1.0, 1.0, 1.0, 0.8, 0.8, 1.2, 0.7, 0.6]


def gen_id_card(rng: random.Random, birth: dt.date) -> tuple[str, str]:
    """返回 (身份证号, 户籍省份)"""
    province, code_prefix = rng.choices(REGION_LIST, weights=REGION_WEIGHTS, k=1)[0]
    region_full = code_prefix + f"{rng.randint(1, 99):02d}"  # 6 位
    body = f"{region_full}{birth.strftime('%Y%m%d')}{rng.randint(1, 999):03d}"
    # 校验位
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = "10X98765432"
    s = sum(int(c) * w for c, w in zip(body, weights))
    check = check_map[s % 11]
    return body + check, province


def gen_phone(rng: random.Random) -> str:
    """13800000001 ~ 13899999999，虚构段。"""
    return f"138{rng.randint(0, 99999999):08d}"


def gen_bank_card(rng: random.Random) -> str:
    """6222 开头，中间 10 位随机，最后 2 位为 '00'。"""
    mid = f"{rng.randint(0, 9999999999):010d}"
    return f"6222{mid}00"


# ---------- 时序 & 分布 ----------


def business_days(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def weighted_date(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    """工作日更多，早期少晚期多（业务逐步上量）。"""
    total = (end - start).days
    # 线性增加权重（模拟业务起量）
    idx = int(rng.triangular(0, total, total * 0.65))
    return start + dt.timedelta(days=idx)


def random_time_of_day(rng: random.Random) -> dt.time:
    """20-22 点、午 12 点是高峰，采样为混合分布。"""
    r = rng.random()
    if r < 0.35:  # 晚高峰 20-22
        h = 20 + rng.randint(0, 2)
    elif r < 0.55:  # 午高峰 12-13
        h = 12 + rng.randint(0, 1)
    elif r < 0.9:  # 白天工作时间
        h = rng.randint(9, 19)
    else:  # 夜间
        h = rng.choice([0, 1, 2, 6, 7, 8, 23])
    m = rng.randint(0, 59)
    s = rng.randint(0, 59)
    return dt.time(h, m, s)


def dt_at(day: dt.date, rng: random.Random) -> dt.datetime:
    return dt.datetime.combine(day, random_time_of_day(rng))


def normal_age(rng: random.Random) -> int:
    while True:
        a = int(rng.gauss(33, 8))
        if 18 <= a <= 60:
            return a


# ---------- 产品 & 组织 ----------

PRODUCTS = CONFIG["products"]
PRODUCT_CODES = [p["code"] for p in PRODUCTS]
PRODUCT_WEIGHTS = [p["share"] for p in PRODUCTS]


def choose_product(rng: random.Random) -> dict:
    code = rng.choices(PRODUCT_CODES, weights=PRODUCT_WEIGHTS, k=1)[0]
    return next(p for p in PRODUCTS if p["code"] == code)


BRANCHES = CONFIG["company"]["branches"]


def choose_branch(rng: random.Random) -> dict:
    return rng.choice(BRANCHES)


# ---------- MySQL ----------


def mysql_conn(db: str | None = None):
    m = CONFIG["mysql"]
    return pymysql.connect(
        host=m["host"], port=m["port"], user=m["user"], password=m["password"],
        database=db, charset="utf8mb4", autocommit=False,
        local_infile=True,
    )


def ensure_database(db: str):
    with mysql_conn() as conn, conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4")
        conn.commit()


def exec_sql_file(db: str, sql_path: Path):
    sql = sql_path.read_text()
    # 简单按 ; 拆分（SQL 内不含 stored procedure）
    stmts = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    with mysql_conn(db) as conn, conn.cursor() as cur:
        for s in stmts:
            cur.execute(s)
        conn.commit()


def load_csv(db: str, table: str, csv_path: Path, columns: list[str]):
    with mysql_conn(db) as conn, conn.cursor() as cur:
        col_list = ",".join(f"`{c}`" for c in columns)
        cur.execute(
            f"LOAD DATA LOCAL INFILE %s INTO TABLE `{table}` "
            "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
            "LINES TERMINATED BY '\\n' IGNORE 1 LINES "
            f"({col_list})",
            (str(csv_path),),
        )
        conn.commit()


# ---------- CSV writer ----------

import csv


class CsvWriter:
    def __init__(self, path: Path, columns: list[str]):
        self.path = path
        self.columns = columns
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = path.open("w", newline="", encoding="utf-8")
        self.w = csv.writer(self.f, quoting=csv.QUOTE_MINIMAL)
        self.w.writerow(columns)
        self.count = 0

    def row(self, row: list):
        # None → 空串（LOAD DATA 用 NULL 需要 \\N，这里用 IGNORE + 默认值处理）
        cleaned = ["\\N" if v is None else v for v in row]
        self.w.writerow(cleaned)
        self.count += 1

    def close(self):
        self.f.close()
