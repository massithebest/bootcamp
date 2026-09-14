"""카탈로그 YAML 에서 합성 SQLite 를 생성한다. (설계 §6-1)

`knowledge/catalog/tables/*.yaml` 이 DDL 의 source of truth 다. 기준 데이터를
고정 seed 로 만든 뒤 `knowledge/scenarios/*.yaml` 의 이상치를 심는다. 시나리오가
곧 "에이전트가 찾아내야 할 원인"이며, 같은 파일을 테스트가 정답으로 쓴다.

실행:
    python -m scripts.seed_sample_db
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from core.config import KNOWLEDGE_DIR, SAMPLE_DB_PATH
from services.knowledge_service import KnowledgeStore, KnowledgeTable, Scenario


RANDOM_SEED = 20260914
PERIOD_START = date(2026, 6, 1)
PERIOD_END = date(2026, 9, 30)

#: 라인 코드 -> (라인명, 생산 품목)
LINES: dict[str, tuple[str, list[str]]] = {
    "A": ("1라인", ["P-1001", "P-1002"]),
    "B": ("2라인", ["P-1002", "P-1003"]),
    "C": ("3라인", ["P-1004", "P-1005"]),
    "D": ("4라인", ["P-1006", "P-1007", "P-1008"]),
}

#: 품목 ID -> 기준 일일 계획량
BASE_DAILY_QTY: dict[str, int] = {
    "P-1001": 500,
    "P-1002": 420,
    "P-1003": 260,
    "P-1004": 600,
    "P-1005": 340,
    "P-1006": 200,
    "P-1007": 380,
    "P-1008": 450,
}

#: 카탈로그 `Column.type` -> SQLite 타입
SQLITE_TYPES = {"date": "TEXT", "varchar": "TEXT", "number": "REAL", "int": "INTEGER"}


def _sqlite_type(column_type: str) -> str:
    return SQLITE_TYPES.get(column_type.lower(), "TEXT")


def _create_table_sql(table: KnowledgeTable) -> str:
    columns = ", ".join(
        f"{column.name} {_sqlite_type(column.type)}" for column in table.columns
    )
    return f"CREATE TABLE {table.table} ({columns})"


def _workdays(start: date, end: date) -> list[date]:
    """주말을 제외한 날짜 목록. 계획은 평일에만 있다 (PRODUCTION_PLAN caveats)."""

    days, current = [], start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _insert(conn: sqlite3.Connection, table: str, rows: list[tuple], width: int) -> None:
    if not rows:
        return
    placeholders = ", ".join("?" * width)
    conn.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)


def _seed_masters(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "LINE_MASTER",
        [(line_cd, name, "PLANT1") for line_cd, (name, _) in LINES.items()],
        3,
    )
    _insert(
        conn,
        "PRODUCT_MASTER",
        [
            (product_id, f"품목{index}", BASE_DAILY_QTY[product_id])
            for index, product_id in enumerate(sorted(BASE_DAILY_QTY), start=1)
        ],
        3,
    )


def _seed_mp_versions(conn: sqlite3.Connection) -> list[str]:
    """월별 확정 MP 1행. 시나리오가 건드리지 않는 한 changed = 0 이다."""

    versions, rows = [], []
    for month in range(PERIOD_START.month, PERIOD_END.month + 1):
        plan_month = f"{PERIOD_START.year}{month:02d}"
        version = f"MP-{plan_month}-FIXED"
        fixed_month = date(PERIOD_START.year, month, 1) - timedelta(days=1)
        fixed_at = fixed_month.replace(day=25)
        rows.append((plan_month, version, fixed_at.isoformat(), 0))
        versions.append(version)
    _insert(conn, "MP_VERSION", rows, 4)
    return versions


def _seed_plan_and_result(conn: sqlite3.Connection, rng: random.Random) -> None:
    plan_rows, result_rows = [], []

    for work_date in _workdays(PERIOD_START, PERIOD_END):
        iso = work_date.isoformat()
        mp_version = f"MP-{work_date.year}{work_date.month:02d}-FIXED"

        for line_cd, (_, products) in LINES.items():
            for product_id in products:
                plan_qty = int(BASE_DAILY_QTY[product_id] * rng.uniform(0.9, 1.1))
                plan_rows.append((iso, line_cd, product_id, plan_qty, mp_version))

                inbound_qty = max(0, int(plan_qty * rng.gauss(0.97, 0.05)))
                draw = rng.random()
                status_cd = "C" if draw < 0.97 else ("P" if draw < 0.99 else "X")
                result_rows.append((iso, line_cd, product_id, inbound_qty, status_cd))

    _insert(conn, "PRODUCTION_PLAN", plan_rows, 5)
    _insert(conn, "FGS_INBOUND_RESULT", result_rows, 5)


def _apply_scenario(conn: sqlite3.Connection, scenario: Scenario) -> None:
    """시나리오 기간의 실적을 깎고, 원인 테이블에 흔적을 남긴다."""

    start, end = (day.isoformat() for day in scenario.period)
    keep = 1.0 - scenario.drop_ratio

    if "FGS_INBOUND_RESULT" not in scenario.unchanged:
        conn.execute(
            """
            UPDATE FGS_INBOUND_RESULT
               SET inbound_qty = CAST(inbound_qty * ? AS INTEGER)
             WHERE work_date BETWEEN ? AND ?
               AND line_cd = ? AND product_id = ?
            """,
            (keep, start, end, scenario.line_cd, scenario.product_id),
        )

    if scenario.cause == "material_shortage" and "MATERIAL_SHORTAGE" not in scenario.unchanged:
        shortage_rows = conn.execute(
            """
            SELECT p.work_date, p.product_id, p.plan_qty - r.inbound_qty AS short_qty
              FROM PRODUCTION_PLAN p
              JOIN FGS_INBOUND_RESULT r
                ON r.work_date = p.work_date AND r.line_cd = p.line_cd
               AND r.product_id = p.product_id
             WHERE p.work_date BETWEEN ? AND ?
               AND p.line_cd = ? AND p.product_id = ?
               AND p.plan_qty > r.inbound_qty
            """,
            (start, end, scenario.line_cd, scenario.product_id),
        ).fetchall()

        _insert(
            conn,
            "MATERIAL_SHORTAGE",
            [
                (work_date, product_id, f"M-{product_id}", int(short_qty), "SUPPLIER_DELAY")
                for work_date, product_id, short_qty in shortage_rows
            ],
            5,
        )

    if scenario.cause == "plan_change" and "MP_VERSION" not in scenario.unchanged:
        conn.execute(
            "UPDATE MP_VERSION SET changed = 1 WHERE plan_month = ?",
            (f"{scenario.period[0].year}{scenario.period[0].month:02d}",),
        )


def main(db_path: Path | None = None) -> Path:
    """카탈로그와 시나리오로 합성 SQLite 를 새로 만든다. 기존 파일은 덮어쓴다."""

    db_path = Path(db_path or SAMPLE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)

    store = KnowledgeStore.load(KNOWLEDGE_DIR)
    rng = random.Random(RANDOM_SEED)

    conn = sqlite3.connect(db_path)
    try:
        for table in store.tables.values():
            conn.execute(_create_table_sql(table))

        _seed_masters(conn)
        _seed_mp_versions(conn)
        _seed_plan_and_result(conn, rng)

        for scenario in store.list_scenarios():
            _apply_scenario(conn, scenario)

        conn.commit()
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    path = main()
    print(f"seeded: {path}")
