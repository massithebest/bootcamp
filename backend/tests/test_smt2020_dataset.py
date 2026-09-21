"""SMT2020 converter schema, counts, atomic replacement, and joins."""

import csv
import shutil
import sqlite3
from pathlib import Path

import pytest

from core.config import KNOWLEDGE_DIR
from services.knowledge_service import KnowledgeStore
from services.mock.mock_simulation_service import _input_validation
from services.sql_guard import check_sql


pytestmark = [pytest.mark.smt2020, pytest.mark.mock_service]


EXPECTED_COUNTS = {
    "HVLM": {"part": 2, "route_step": 926, "tool": 106, "orders": 5, "wip": 2255,
             "setup": 13, "setup_group": 9, "down_calendar": 11, "pm_calendar": 292,
             "calendar_attach": 303, "transport": 1},
    "LVHM": {"part": 10, "route_step": 4013, "tool": 106, "orders": 21, "wip": 2156,
             "setup": 13, "setup_group": 9, "down_calendar": 11, "pm_calendar": 292,
             "calendar_attach": 303, "transport": 1},
}


@pytest.fixture(scope="module")
def db(tmp_path_factory, smt2020_assets) -> Path:
    return smt2020_assets.main(
        smt2020_assets.DEFAULT_SOURCE_ROOT,
        tmp_path_factory.mktemp("smt") / "smt2020.db",
    )


def test_tables_and_counts(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert tables == set(EXPECTED_COUNTS["HVLM"])
        for dataset, expected in EXPECTED_COUNTS.items():
            for table, count in expected.items():
                actual = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE dataset = ?', (dataset,)
                ).fetchone()[0]
                assert actual == count, (dataset, table)


def test_schema_types_and_reserved_names(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        order_columns = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(orders)")}
        route_columns = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(route_step)")}
        assert order_columns["order_id"] == "TEXT"
        assert order_columns["rpt_no"] == "INTEGER"
        assert order_columns["repeat"] == "REAL"
        assert route_columns["description"] == "TEXT"
        assert route_columns["when_value"] == "TEXT"
        assert route_columns["batch_interval"] == "REAL"


def test_catalog_columns_and_types_match_database(db: Path) -> None:
    type_affinity = {
        "varchar": "TEXT",
        "datetime": "TEXT",
        "int": "INTEGER",
        "number": "REAL",
    }
    store = KnowledgeStore.load(KNOWLEDGE_DIR)

    with sqlite3.connect(db) as conn:
        for table in store.tables.values():
            actual = {
                row[1]: row[2]
                for row in conn.execute(f'PRAGMA table_info("{table.table}")')
            }
            expected = {
                column.name: type_affinity[column.type]
                for column in table.columns
            }
            assert actual == expected, table.table


def test_expected_indexes_exist(db: Path) -> None:
    expected = {
        "idx_part_dataset_part", "idx_part_dataset_route",
        "idx_route_step_dataset_route_step", "idx_route_step_dataset_stnfam",
        "idx_tool_dataset_stnfam", "idx_orders_dataset_part",
        "idx_orders_dataset_order_id", "idx_wip_dataset_part",
        "idx_wip_dataset_part_curstep", "idx_calendar_attach_dataset_calname",
        "idx_calendar_attach_dataset_resource",
    }
    with sqlite3.connect(db) as conn:
        actual = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )}
    assert expected <= actual


def test_hvlm_short_wip_row_is_padded_with_null(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT hotlot, trace FROM wip WHERE dataset='HVLM' AND lot='Init_Lot_3_2'"
        ).fetchone()
    assert row == (None, None)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT COUNT(*) FROM part p LEFT JOIN route_step r ON r.dataset=p.dataset AND r.route=p.route WHERE r.route IS NULL",
        "SELECT COUNT(*) FROM route_step r LEFT JOIN tool t ON t.dataset=r.dataset AND t.stnfam=r.stnfam WHERE t.stnfam IS NULL",
        "SELECT COUNT(*) FROM wip w LEFT JOIN part p ON p.dataset=w.dataset AND p.part=w.part WHERE p.part IS NULL",
        "SELECT COUNT(*) FROM orders o LEFT JOIN part p ON p.dataset=o.dataset AND p.part=o.part WHERE p.part IS NULL",
        "SELECT COUNT(*) FROM wip w JOIN part p ON p.dataset=w.dataset AND p.part=w.part LEFT JOIN route_step r ON r.dataset=p.dataset AND r.route=p.route AND r.step=w.curstep WHERE r.step IS NULL",
    ],
)
def test_relationships_have_no_unmatched_rows(db: Path, query: str) -> None:
    with sqlite3.connect(db) as conn:
        assert conn.execute(query).fetchone()[0] == 0


def test_required_example_queries_execute(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        wip_rows = conn.execute(
            "SELECT dataset, part, COUNT(*) AS lot_count FROM wip GROUP BY dataset, part"
        ).fetchall()
        route_rows = conn.execute(
            """
            SELECT p.dataset, p.part, p.route, COUNT(r.step) AS step_count
              FROM part p LEFT JOIN route_step r
                ON p.dataset=r.dataset AND p.route=r.route
             GROUP BY p.dataset, p.part, p.route
            """
        ).fetchall()
    assert len(wip_rows) == 12 and len(route_rows) == 12


def test_recipe_samples_execute_against_generated_database(db: Path) -> None:
    store = KnowledgeStore.load(KNOWLEDGE_DIR)
    with sqlite3.connect(db) as conn:
        for recipe in store.recipes.values():
            for sample in recipe.sample_queries:
                sql = f"WITH {recipe.cte_name} AS ({recipe.cte_sql})\n{sample.sql}"
                guarded = check_sql(sql, store.table_names())
                conn.execute(guarded).fetchall()


def test_table_samples_execute_against_generated_database(db: Path) -> None:
    store = KnowledgeStore.load(KNOWLEDGE_DIR)
    with sqlite3.connect(db) as conn:
        for table in store.tables.values():
            for sample in table.sample_queries:
                guarded = check_sql(sample.sql, store.table_names())
                conn.execute(guarded).fetchall()


def test_scenario_expectations_match_generated_database(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core import config

    monkeypatch.setattr(config, "SMT2020_DB_PATH", db)
    store = KnowledgeStore.load(KNOWLEDGE_DIR)

    for scenario in store.scenarios.values():
        result = _input_validation(scenario.dataset)
        table_counts = dict(result["table"]["rows"])
        actual_unmatched = {
            row["check"]: row["unmatched_rows"] for row in result["results"]
        }
        assert scenario.expected.table_counts == {
            table: table_counts[table]
            for table in scenario.expected.table_counts
        }
        assert scenario.expected.unmatched_rows == {
            check: actual_unmatched[check]
            for check in scenario.expected.unmatched_rows
        }


def test_repeated_build_is_deterministic(tmp_path: Path, smt2020_assets) -> None:
    target = tmp_path / "smt2020.db"
    smt2020_assets.main(smt2020_assets.DEFAULT_SOURCE_ROOT, target)
    with sqlite3.connect(target) as conn:
        first = conn.execute("SELECT dataset, part, route FROM part ORDER BY 1,2").fetchall()
    smt2020_assets.main(smt2020_assets.DEFAULT_SOURCE_ROOT, target)
    with sqlite3.connect(target) as conn:
        second = conn.execute("SELECT dataset, part, route FROM part ORDER BY 1,2").fetchall()
    assert first == second


def test_failed_rebuild_keeps_previous_database(tmp_path: Path, smt2020_assets) -> None:
    target = tmp_path / "smt2020.db"
    smt2020_assets.main(smt2020_assets.DEFAULT_SOURCE_ROOT, target)
    before = target.read_bytes()
    broken = tmp_path / "datasets"
    shutil.copytree(
        smt2020_assets.DEFAULT_SOURCE_ROOT / "SMT2020_HVLM",
        broken / "SMT2020_HVLM",
    )
    shutil.copytree(
        smt2020_assets.DEFAULT_SOURCE_ROOT / "SMT2020_LVHM",
        broken / "SMT2020_LVHM",
    )
    part = broken / "SMT2020_HVLM" / "part.txt"
    rows = list(csv.reader(part.open(encoding="utf-8"), delimiter="\t"))
    rows[0][0] = "BROKEN"
    part.write_text("\n".join("\t".join(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="헤더"):
        smt2020_assets.main(broken, target)
    assert target.read_bytes() == before
