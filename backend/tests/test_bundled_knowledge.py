"""번들 mock knowledge YAML의 고정 값 회귀 테스트.

집계 guidance가 Tool로 노출되고 실제 SQL과 맞는지, diagnostics recipe가 끊긴 연결과
집계 부풀림을 잡는지 확인한다. 의도적으로 망가뜨린 작은 fixture만 쓰고 번들 입력
파일은 수정하지 않는다.
"""

import asyncio
import sqlite3

import pytest

from core.config import DEFAULT_KNOWLEDGE_DIR
from services.knowledge.catalog import KnowledgeStore, get_store
from tools.knowledge_tool import describe_table, get_kpi

pytestmark = pytest.mark.usefixtures("bundled_knowledge")


@pytest.fixture(scope="module")
def store() -> KnowledgeStore:
    return KnowledgeStore.load(DEFAULT_KNOWLEDGE_DIR)


@pytest.fixture(scope="module")
def db(tmp_path_factory, mock_database):
    return mock_database.main(tmp_path_factory.mktemp("aggregation") / "mock.db")


def test_catalog_exposes_aggregation_guidance(store: KnowledgeStore) -> None:
    for name in store.table_names():
        result = asyncio.run(describe_table(name))
        assert result["data"]["aggregation_rules"]
        assert result["verified"] is (store.tables[name].status == "verified")


def test_initial_wip_kpi_contract(store: KnowledgeStore) -> None:
    result = asyncio.run(get_kpi("initial_wip"))
    kpi = result["data"]
    assert result["verified"] is False  # expanded diagnostics await domain review
    assert kpi["grain"] == ["dataset", "part"]
    assert kpi["aggregation_rules"]
    assert {("simulation", "입력_정합성_검증"), ("sql", "recipes/wip_integrity_diagnostics")} <= {
        (item["how"], item["ref"]) for item in kpi["diagnostics"]
    }


def test_initial_wip_sql_matches_source(db, store: KnowledgeStore) -> None:
    sql = store.kpis["initial_wip"].sql_template.replace(":dataset", "?")
    with sqlite3.connect(db) as conn:
        rows = conn.execute(sql, ("SEG_A",)).fetchall()
        reference = conn.execute(
            """
            SELECT dataset, part, COUNT(*), SUM(pieces) FROM wip
             WHERE dataset = ?
             GROUP BY dataset, part
             ORDER BY part
            """,
            ("SEG_A",),
        ).fetchall()
    assert rows == reference
    assert {row[1] for row in rows} == {"part_1", "part_2"}


def test_dataset_key_prevents_cross_join_inflation(db) -> None:
    with sqlite3.connect(db) as conn:
        total_route_steps = conn.execute("SELECT COUNT(*) FROM route_step").fetchone()[0]
        safe = conn.execute(
            """
            SELECT COUNT(*) FROM part p JOIN route_step r
              ON r.dataset=p.dataset AND r.route=p.route
            """
        ).fetchone()[0]
        unsafe = conn.execute(
            "SELECT COUNT(*) FROM part p JOIN route_step r ON r.route=p.route"
        ).fetchone()[0]
    assert safe == total_route_steps
    assert unsafe > safe


def test_diagnostics_find_missing_links_and_aggregation_hazards():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
      CREATE TABLE wip (dataset TEXT, part TEXT, curstep INTEGER, pieces INTEGER);
      CREATE TABLE part (dataset TEXT, part TEXT, route TEXT);
      CREATE TABLE route_step (dataset TEXT, route TEXT, step INTEGER, stnfam TEXT);
      CREATE TABLE tool (dataset TEXT, stnfam TEXT);
      INSERT INTO part VALUES ('SEG_B','p','r'),('SEG_A','p','r');
      INSERT INTO wip VALUES ('SEG_B','p',1,25),('SEG_A','p',1,100);
      INSERT INTO route_step VALUES ('SEG_B','r',1,'t'),('SEG_B','r',2,'t'),('SEG_A','r',1,'t');
      INSERT INTO tool VALUES ('SEG_B','t'),('SEG_A','t');
    """)
    recipe = get_store().get_recipe("wip_integrity_diagnostics")
    sql = f"WITH {recipe['cte_name']} AS ({recipe['cte_sql']}) SELECT * FROM {recipe['cte_name']} WHERE dataset='SEG_B'"
    before = dict(conn.execute(sql).fetchone())
    assert before["wip_lot_count"] == 1 and before["wip_piece_count"] == 25
    assert before["wip_missing_part"] == before["wip_missing_step"] == before["route_missing_tool"] == 0
    assert before["cross_dataset_part_matches"] == 1  # omission would connect SEG_A too
    assert before["route_join_rows"] == 2  # naive SUM(pieces) becomes 50
    naive = conn.execute("SELECT SUM(w.pieces) FROM wip w JOIN part p ON p.dataset=w.dataset AND p.part=w.part JOIN route_step r ON r.dataset=p.dataset AND r.route=p.route WHERE w.dataset='SEG_B'").fetchone()[0]
    assert naive == 2 * before["wip_piece_count"]
    conn.execute("INSERT INTO wip VALUES ('SEG_B','missing',1,5)")
    conn.execute("UPDATE wip SET curstep=99 WHERE dataset='SEG_B' AND part='p'")
    conn.execute("DELETE FROM tool WHERE dataset='SEG_B'")
    broken = dict(conn.execute(sql).fetchone())
    assert broken["wip_missing_part"] == 1
    assert broken["wip_missing_step"] == 2
    assert broken["route_missing_tool"] == 2
    assert broken["wip_lot_count"] == 2 and broken["wip_piece_count"] == 30
    conn.close()
