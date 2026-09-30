"""Deterministic synthetic production-planning data to a local SQLite database.

No external dataset files are needed — every row is fabricated with a fixed
random seed so repeated builds are reproducible. Two kinds of tables exist:

- ``TABLE_COLUMNS``: a generic discrete-manufacturing placeholder schema
  (part/route/tool/orders/wip/setup/calendars/transport), segmented by a
  synthetic ``dataset`` key (``SEGMENTS``: SEG_A/SEG_B).
- ``STANDALONE_TABLE_COLUMNS``: tables mirroring real closed-network schema
  info supplied by the user (table/column names, business rules), with no
  synthetic ``dataset`` column since the real table doesn't have one.

Run from ``backend/``::

    python -m scripts.generate_mock_database
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "mock_planning.db"
DEFAULT_SEED = 20260101

BASE_START = datetime(2026, 1, 1)


@dataclass(frozen=True)
class SegmentSpec:
    """Row-count targets for one production segment.

    Defaults intentionally keep the bundled ``knowledge/mock/scenarios``
    expectation numbers working unchanged (dataset labels SEG_A/SEG_B).
    """

    dataset: str
    part_count: int
    route_step_count: int
    tool_count: int
    order_count: int
    wip_count: int
    setup_count: int
    setup_group_count: int
    down_calendar_count: int
    pm_calendar_count: int
    calendar_attach_count: int
    transport_count: int


SEGMENTS: tuple[SegmentSpec, ...] = (
    SegmentSpec(
        dataset="SEG_A", part_count=2, route_step_count=926, tool_count=106,
        order_count=5, wip_count=2255, setup_count=13, setup_group_count=9,
        down_calendar_count=11, pm_calendar_count=292,
        calendar_attach_count=303, transport_count=1,
    ),
    SegmentSpec(
        dataset="SEG_B", part_count=10, route_step_count=4013, tool_count=106,
        order_count=21, wip_count=2156, setup_count=13, setup_group_count=9,
        down_calendar_count=11, pm_calendar_count=292,
        calendar_attach_count=303, transport_count=1,
    ),
)

#: table -> [(column, sqlite affinity), ...]. ``dataset`` is prefixed to every
#: table by the writer, so it is not listed here.
TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "part": [
        ("partgrp", "TEXT"), ("partfam", "TEXT"), ("part", "TEXT"),
        ("routefile", "TEXT"), ("route", "TEXT"),
    ],
    "route_step": [
        ("route", "TEXT"), ("step", "INTEGER"), ("description", "TEXT"),
        ("stnfam", "TEXT"), ("pdist", "TEXT"), ("ptime", "REAL"), ("ptime2", "REAL"),
        ("ptunits", "TEXT"), ("ptper", "TEXT"), ("batchmn", "INTEGER"),
        ("batchmx", "INTEGER"), ("setup", "TEXT"), ("when_value", "TEXT"),
        ("stime", "INTEGER"), ("stunits", "TEXT"), ("svestn", "TEXT"),
        ("forstep", "INTEGER"), ("batch_interval", "REAL"), ("batch_int_units", "TEXT"),
        ("part_interval", "REAL"), ("part_int_units", "TEXT"), ("rwkstep", "INTEGER"),
        ("rework", "REAL"), ("rwktype", "TEXT"), ("step_percent", "INTEGER"),
        ("step_cqt", "INTEGER"), ("cqt", "INTEGER"), ("cqtunits", "TEXT"),
        ("ignore_value", "TEXT"),
    ],
    "tool": [
        ("stnfam", "TEXT"), ("stn", "TEXT"), ("rule", "TEXT"), ("fwlrank", "TEXT"),
        ("wakeresrank", "TEXT"), ("batchcritf", "TEXT"), ("batchper", "TEXT"),
        ("ltime", "REAL"), ("ltunits", "TEXT"), ("ultime", "REAL"), ("ultunits", "TEXT"),
        ("stncap", "REAL"), ("stnqty", "REAL"), ("stngrp", "TEXT"),
        ("stnfamstep_actlist", "TEXT"), ("stnfamloc", "TEXT"), ("prerulerwl", "TEXT"),
        ("setupgrp", "TEXT"),
    ],
    "orders": [
        ("lot", "TEXT"), ("part", "TEXT"), ("prior", "INTEGER"), ("pieces", "INTEGER"),
        ("start", "TEXT"), ("rdist", "TEXT"), ("repeat", "REAL"), ("runits", "TEXT"),
        ("rpt_no", "INTEGER"), ("lotsperrpt", "INTEGER"), ("due", "TEXT"),
        ("order_id", "TEXT"), ("hotlot", "TEXT"),
    ],
    "wip": [
        ("lot", "TEXT"), ("part", "TEXT"), ("prior", "INTEGER"), ("pieces", "INTEGER"),
        ("start", "TEXT"), ("curstep", "INTEGER"), ("due", "TEXT"), ("order_id", "TEXT"),
        ("hotlot", "TEXT"), ("trace", "TEXT"),
    ],
    "setup": [
        ("cursetup", "TEXT"), ("newsetup", "TEXT"), ("stime", "INTEGER"),
        ("stunits", "TEXT"), ("ignore_value", "TEXT"),
    ],
    "setup_group": [
        ("setupgrp", "TEXT"), ("setup", "TEXT"), ("minrun", "INTEGER"),
        ("ignore_value", "TEXT"),
    ],
    "down_calendar": [
        ("downcalname", "TEXT"), ("downcaltype", "TEXT"), ("mttfdist", "TEXT"),
        ("mttf", "INTEGER"), ("mttfunits", "TEXT"), ("mttrdist", "TEXT"),
        ("mttr", "REAL"), ("mttrunits", "TEXT"), ("ignore_value", "TEXT"),
    ],
    "pm_calendar": [
        ("pmcalname", "TEXT"), ("pmcaltype", "TEXT"), ("mtbpm", "INTEGER"),
        ("mtbpmunits", "TEXT"), ("mttrdist", "TEXT"), ("mttr", "REAL"),
        ("mttr2", "REAL"), ("mttrunits", "TEXT"), ("ignore_value", "TEXT"),
    ],
    "calendar_attach": [
        ("calname", "TEXT"), ("caltype", "TEXT"), ("restype", "TEXT"),
        ("resname", "TEXT"), ("foadist", "TEXT"), ("foa", "REAL"), ("foaunits", "TEXT"),
    ],
    "transport": [
        ("fromloc", "TEXT"), ("toloc", "TEXT"), ("ddist", "TEXT"), ("dtime", "REAL"),
        ("dtime2", "REAL"), ("dunits", "TEXT"),
    ],
}

#: Tables mirrored from real closed-network schema info the user supplied
#: directly (table/column names, business rules) rather than invented to
#: match the placeholder segments above. These have no ``dataset``
#: segmentation column since the real table doesn't have one.
STANDALONE_TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "FP_TARGET": [
        ("MP_VER", "TEXT"), ("FAC_ID", "TEXT"), ("PLAN_DT", "TEXT"),
        ("PLAN_OPT_CD", "TEXT"), ("PLAN_PROD_ID", "TEXT"), ("WORK_YM", "TEXT"),
        ("PLAN_QTY", "REAL"), ("ACT_QTY", "REAL"), ("REMAIN_PLAN_QTY", "REAL"),
        ("GRADE_CD", "TEXT"), ("SWAP_QTY", "REAL"), ("SALES_BATCH_CD", "TEXT"),
        ("PNT_SITE_CD", "TEXT"), ("COMPLT_DT", "TEXT"), ("PLAN_STATE_DT", "TEXT"),
        ("PRIORTY", "INTEGER"), ("PRODUCT_GUBUN", "TEXT"), ("OUT_AREA", "TEXT"),
        ("USER_TARGET_QTY", "REAL"), ("TARGET_QTY", "REAL"), ("WORK_DT", "TEXT"),
    ],
}

#: Row count target per standalone table. Adjust once real volumes are known.
STANDALONE_ROW_COUNTS: dict[str, int] = {"FP_TARGET": 500}

_FP_TARGET_FAC_IDS = ["FAC001", "FAC002", "FAC003"]
_FP_TARGET_PNT_SITE_CDS = ["SITE_A", "SITE_B"]
_FP_TARGET_GRADE_CDS = ["A", "B", "C"]
_FP_TARGET_SALES_BATCH_CDS = [f"BATCH_{i:02d}" for i in range(1, 6)]
_FP_TARGET_PRODUCT_GUBUNS = ["GB1", "GB2"]
_FP_TARGET_OUT_AREAS = ["AREA_1", "AREA_2", "AREA_3"]
_FP_TARGET_PLAN_PROD_IDS = [f"PROD_{i:04d}" for i in range(1, 21)]


def _ymd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _generate_fp_target_rows(rng: random.Random) -> list[tuple]:
    """``FP_TARGET``: 계획/실적/swap 수량과 제품 속성을 담는 FP 결과 IF 테이블.

    grain, 코드값 도메인과 정확한 row 규모는 아직 확인되지 않아 최선 추정치다
    (``knowledge/mock/catalog/tables/fp_target.yaml``도 ``status: draft``).
    """

    rows = []
    for _ in range(STANDALONE_ROW_COUNTS["FP_TARGET"]):
        work_dt = BASE_START + timedelta(days=rng.randint(0, 180))
        plan_dt = work_dt - timedelta(days=rng.randint(0, 5))
        complt_dt = work_dt + timedelta(days=rng.randint(1, 20))
        work_ym = work_dt.strftime("%Y%m")

        plan_opt_cd = "X" if rng.random() < 0.1 else "N"
        plan_qty = 0.0 if plan_opt_cd == "X" else float(rng.randint(0, 5000))
        has_actual = rng.random() < 0.7
        act_qty = round(plan_qty * rng.uniform(0.5, 1.05), 1) if has_actual else None
        remain_plan_qty = max(plan_qty - (act_qty or 0.0), 0.0)
        swap_qty = round(plan_qty * rng.uniform(0.01, 0.1), 1) if rng.random() < 0.2 else 0.0
        user_target_qty = float(rng.randint(0, 5000))
        target_qty = round(user_target_qty * rng.uniform(0.8, 1.0), 2)

        rows.append((
            f"MP_{work_ym}", rng.choice(_FP_TARGET_FAC_IDS), _ymd(plan_dt), plan_opt_cd,
            rng.choice(_FP_TARGET_PLAN_PROD_IDS), work_ym, plan_qty, act_qty, remain_plan_qty,
            rng.choice(_FP_TARGET_GRADE_CDS), swap_qty, rng.choice(_FP_TARGET_SALES_BATCH_CDS),
            rng.choice(_FP_TARGET_PNT_SITE_CDS), _ymd(complt_dt), _ymd(plan_dt),
            rng.randint(1, 10), rng.choice(_FP_TARGET_PRODUCT_GUBUNS), rng.choice(_FP_TARGET_OUT_AREAS),
            user_target_qty, target_qty, _ymd(work_dt),
        ))
    return rows


STANDALONE_GENERATORS: dict[str, Callable[[random.Random], list[tuple]]] = {
    "FP_TARGET": _generate_fp_target_rows,
}


INDEX_SQL = (
    "CREATE UNIQUE INDEX idx_part_dataset_part ON part(dataset, part)",
    "CREATE INDEX idx_part_dataset_route ON part(dataset, route)",
    "CREATE UNIQUE INDEX idx_route_step_dataset_route_step ON route_step(dataset, route, step)",
    "CREATE INDEX idx_route_step_dataset_stnfam ON route_step(dataset, stnfam)",
    "CREATE UNIQUE INDEX idx_tool_dataset_stnfam ON tool(dataset, stnfam)",
    "CREATE INDEX idx_orders_dataset_part ON orders(dataset, part)",
    "CREATE INDEX idx_orders_dataset_order_id ON orders(dataset, order_id)",
    "CREATE INDEX idx_wip_dataset_part ON wip(dataset, part)",
    "CREATE INDEX idx_wip_dataset_part_curstep ON wip(dataset, part, curstep)",
    "CREATE INDEX idx_calendar_attach_dataset_calname ON calendar_attach(dataset, calname)",
    "CREATE INDEX idx_calendar_attach_dataset_resource ON calendar_attach(dataset, restype, resname)",
)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _generate_part_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    rows = []
    for i in range(1, spec.part_count + 1):
        partgrp = f"grp_{((i - 1) % 3) + 1}"
        partfam = f"fam_{((i - 1) % 2) + 1}"
        part = f"part_{i}"
        route = f"route_{i}"
        rows.append((partgrp, partfam, part, f"{route}.txt", route))
    return rows


def _generate_route_step_rows(
    rng: random.Random, spec: SegmentSpec, routes: list[str], stnfams: list[str]
) -> tuple[list[tuple], dict[str, list[int]]]:
    n_routes = len(routes)
    base, remainder = divmod(spec.route_step_count, n_routes)
    rows: list[tuple] = []
    steps_by_route: dict[str, list[int]] = {}
    for index, route in enumerate(routes):
        step_count = base + (1 if index < remainder else 0)
        steps: list[int] = []
        for step in range(1, step_count + 1):
            stnfam = rng.choice(stnfams)
            steps.append(step)
            rows.append((
                route, step, f"{route} step {step} 공정", stnfam,
                "constant", round(rng.uniform(0.5, 30.0), 2), round(rng.uniform(0.5, 30.0), 2),
                "min", "lot", 1, rng.choice([1, 5, 10, 25]),
                f"SETUP_{rng.randint(1, spec.setup_count)}", "arrive", rng.choice([0, 60, 120]), "min",
                stnfam, step + 1 if step < step_count else None,
                round(rng.uniform(0, 5), 2), "min", round(rng.uniform(0, 5), 2), "min",
                None, 0.0, "percent", 0, None, None, "lots", None,
            ))
        steps_by_route[route] = steps
    return rows, steps_by_route


def _generate_tool_rows(rng: random.Random, spec: SegmentSpec) -> tuple[list[tuple], list[str]]:
    rows = []
    stnfams = [f"STN_{i:03d}" for i in range(1, spec.tool_count + 1)]
    for i, stnfam in enumerate(stnfams, start=1):
        rows.append((
            stnfam, f"{stnfam}_1", "FIFO", "fwl", "wakerule",
            "first", "batch", round(rng.uniform(1.0, 20.0), 2), "min",
            round(rng.uniform(1.0, 20.0), 2), "min", round(rng.uniform(1.0, 8.0), 2),
            float(rng.randint(1, 4)), f"GRP_{((i - 1) % 5) + 1}", None, "floor1",
            None, f"SG_{((i - 1) % spec.setup_group_count) + 1}",
        ))
    return rows, stnfams


def _generate_order_rows(rng: random.Random, spec: SegmentSpec, parts: list[str]) -> list[tuple]:
    rows = []
    for i in range(1, spec.order_count + 1):
        part = parts[(i - 1) % len(parts)]
        lot = f"Lot_{i}"
        start = BASE_START + timedelta(days=rng.randint(0, 30), minutes=rng.randint(0, 1440))
        due = start + timedelta(days=rng.randint(5, 40))
        rows.append((
            lot, part, rng.randint(1, 10), rng.randint(10, 500), _fmt(start),
            "constant", round(rng.uniform(10.0, 200.0), 2), "min", rng.randint(1, 5),
            rng.randint(50000, 500000), _fmt(due), f"O_{lot}",
            "yes" if rng.random() < 0.05 else "no",
        ))
    return rows


def _generate_wip_rows(
    rng: random.Random, spec: SegmentSpec, parts: list[str],
    steps_by_part: dict[str, list[int]],
) -> list[tuple]:
    rows = []
    for i in range(1, spec.wip_count + 1):
        part = parts[(i - 1) % len(parts)]
        curstep = rng.choice(steps_by_part[part])
        lot = f"Init_Lot_{i}"
        start = BASE_START - timedelta(days=rng.randint(0, 20))
        due = start + timedelta(days=rng.randint(5, 30))
        has_trace = rng.random() < 0.9
        rows.append((
            lot, part, rng.randint(1, 10), rng.randint(1, 200), _fmt(start), curstep,
            _fmt(due), f"O_{lot}",
            ("yes" if rng.random() < 0.05 else "no") if has_trace else None,
            f"T{i}" if has_trace else None,
        ))
    return rows


def _generate_setup_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    return [
        (f"SETUP_{i}", f"SETUP_{(i % spec.setup_count) + 1}", rng.choice([0, 30, 60, 90]), "min", None)
        for i in range(1, spec.setup_count + 1)
    ]


def _generate_setup_group_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    return [
        (f"SG_{i}", f"SETUP_{i}", rng.randint(1, 20), None)
        for i in range(1, spec.setup_group_count + 1)
    ]


def _generate_down_calendar_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    rows = []
    for i in range(1, spec.down_calendar_count + 1):
        rows.append((
            f"DOWNCAL_{i}", "unscheduled", "exponential", rng.randint(500, 5000), "min",
            "exponential", round(rng.uniform(10.0, 300.0), 2), "min", None,
        ))
    return rows


def _generate_pm_calendar_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    rows = []
    for i in range(1, spec.pm_calendar_count + 1):
        rows.append((
            f"PMCAL_{i}", "scheduled", rng.randint(1000, 20000), "min", "constant",
            round(rng.uniform(30.0, 240.0), 2), round(rng.uniform(30.0, 240.0), 2), "min", None,
        ))
    return rows


def _generate_calendar_attach_rows(
    rng: random.Random, spec: SegmentSpec, stnfams: list[str],
    down_names: list[str], pm_names: list[str],
) -> list[tuple]:
    rows = []
    for i in range(1, spec.calendar_attach_count + 1):
        use_pm = i % 2 == 0
        calname = pm_names[i % len(pm_names)] if use_pm else down_names[i % len(down_names)]
        caltype = "pm" if use_pm else "down"
        rows.append((
            calname, caltype, "station", stnfams[i % len(stnfams)],
            "constant", round(rng.uniform(0.0, 1.0), 3), "fraction",
        ))
    return rows


def _generate_transport_rows(rng: random.Random, spec: SegmentSpec) -> list[tuple]:
    return [
        ("DOCK", "FLOOR", "constant", round(rng.uniform(1.0, 10.0), 2),
         round(rng.uniform(1.0, 10.0), 2), "min")
        for _ in range(spec.transport_count)
    ]


def _generate_segment(
    rng: random.Random, spec: SegmentSpec
) -> dict[str, list[tuple]]:
    part_rows = _generate_part_rows(rng, spec)
    parts = [row[2] for row in part_rows]
    routes = [row[4] for row in part_rows]

    tool_rows, stnfams = _generate_tool_rows(rng, spec)
    route_step_rows, steps_by_route = _generate_route_step_rows(rng, spec, routes, stnfams)
    steps_by_part = {
        part: steps_by_route[route] for part, route in zip(parts, routes, strict=True)
    }

    setup_rows = _generate_setup_rows(rng, spec)
    setup_group_rows = _generate_setup_group_rows(rng, spec)
    down_calendar_rows = _generate_down_calendar_rows(rng, spec)
    pm_calendar_rows = _generate_pm_calendar_rows(rng, spec)
    down_names = [row[0] for row in down_calendar_rows]
    pm_names = [row[0] for row in pm_calendar_rows]

    return {
        "part": part_rows,
        "route_step": route_step_rows,
        "tool": tool_rows,
        "orders": _generate_order_rows(rng, spec, parts),
        "wip": _generate_wip_rows(rng, spec, parts, steps_by_part),
        "setup": setup_rows,
        "setup_group": setup_group_rows,
        "down_calendar": down_calendar_rows,
        "pm_calendar": pm_calendar_rows,
        "calendar_attach": _generate_calendar_attach_rows(rng, spec, stnfams, down_names, pm_names),
        "transport": _generate_transport_rows(rng, spec),
    }


def _generate_all_segments(seed: int) -> dict[str, dict[str, list[tuple]]]:
    return {
        spec.dataset: _generate_segment(random.Random(f"{seed}:{spec.dataset}"), spec)
        for spec in SEGMENTS
    }


def _generate_standalone_tables(seed: int) -> dict[str, list[tuple]]:
    return {
        table: generator(random.Random(f"{seed}:standalone:{table}"))
        for table, generator in STANDALONE_GENERATORS.items()
    }


def _create_database(
    temp_path: Path,
    all_rows: dict[str, dict[str, list[tuple]]],
    standalone_rows: dict[str, list[tuple]],
) -> None:
    connection = sqlite3.connect(temp_path)
    try:
        with connection:
            for table, columns in TABLE_COLUMNS.items():
                definitions = ["dataset TEXT NOT NULL"] + [
                    f'"{name}" {affinity}' for name, affinity in columns
                ]
                connection.execute(f'CREATE TABLE "{table}" ({", ".join(definitions)})')
            for table, columns in STANDALONE_TABLE_COLUMNS.items():
                definitions = [f'"{name}" {affinity}' for name, affinity in columns]
                connection.execute(f'CREATE TABLE "{table}" ({", ".join(definitions)})')

            for dataset, segment_rows in all_rows.items():
                for table, rows in segment_rows.items():
                    width = len(TABLE_COLUMNS[table])
                    placeholders = ", ".join("?" for _ in range(width + 1))
                    connection.executemany(
                        f'INSERT INTO "{table}" VALUES ({placeholders})',
                        [(dataset, *row) for row in rows],
                    )
            for table, rows in standalone_rows.items():
                width = len(STANDALONE_TABLE_COLUMNS[table])
                placeholders = ", ".join("?" for _ in range(width))
                connection.executemany(
                    f'INSERT INTO "{table}" VALUES ({placeholders})', rows
                )

            for statement in INDEX_SQL:
                connection.execute(statement)

            for table in TABLE_COLUMNS:
                expected = sum(
                    len(segment_rows[table]) for segment_rows in all_rows.values()
                )
                actual = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if actual != expected:
                    raise RuntimeError(
                        f"{table}: 적재 건수 불일치: expected={expected}, actual={actual}"
                    )
            for table, rows in standalone_rows.items():
                actual = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if actual != len(rows):
                    raise RuntimeError(
                        f"{table}: 적재 건수 불일치: expected={len(rows)}, actual={actual}"
                    )
        check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"SQLite integrity_check 실패: {check}")
    finally:
        connection.close()


def main(db_path: Path | None = None, *, seed: int = DEFAULT_SEED) -> Path:
    """Build and atomically replace the synthetic mock planning database."""

    db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = _generate_all_segments(seed)
    standalone_rows = _generate_standalone_tables(seed)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{db_path.name}.", suffix=".tmp", dir=db_path.parent
    )
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        _create_database(temp_path, all_rows, standalone_rows)
        temp_path.replace(db_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    print(f"created: {db_path}")
    for dataset, segment_rows in all_rows.items():
        for table, rows in segment_rows.items():
            print(f"{dataset}.{table}: {len(rows)}")
    for table, rows in standalone_rows.items():
        print(f"{table}: {len(rows)}")
    return db_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic mock planning SQLite database")
    parser.add_argument("--output", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = _parse_args()
    main(arguments.output, seed=arguments.seed)
