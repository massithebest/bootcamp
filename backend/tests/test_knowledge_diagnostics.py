"""Deliberately broken tiny fixtures; benchmark input files are never modified."""
import sqlite3

import pytest

from services.knowledge.catalog import get_store

pytestmark = pytest.mark.usefixtures("bundled_knowledge")


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
