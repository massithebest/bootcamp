"""SMT2020 aggregation guidance is exposed and matches executable SQL."""

import asyncio
import sqlite3

import pytest

from core.config import DEFAULT_KNOWLEDGE_DIR
from services.knowledge_service import KnowledgeStore
from tools.knowledge_tool import describe_table, get_kpi

pytestmark = pytest.mark.usefixtures("bundled_knowledge")


@pytest.fixture(scope="module")
def store() -> KnowledgeStore:
    return KnowledgeStore.load(DEFAULT_KNOWLEDGE_DIR)


@pytest.fixture(scope="module")
def db(tmp_path_factory, smt2020_assets):
    return smt2020_assets.main(
        smt2020_assets.DEFAULT_SOURCE_ROOT,
        tmp_path_factory.mktemp("aggregation") / "smt.db",
    )


def test_catalog_exposes_aggregation_guidance(store: KnowledgeStore) -> None:
    for name in store.table_names():
        result = asyncio.run(describe_table(name))
        assert result["data"]["aggregation_rules"]
        assert result["verified"] is True


def test_initial_wip_kpi_contract(store: KnowledgeStore) -> None:
    kpi = asyncio.run(get_kpi("initial_wip"))["data"]
    assert kpi["grain"] == ["dataset", "part"]
    assert kpi["aggregation_rules"]
    assert {("simulation", "SMT2020_입력검증"), ("sql", "recipes/wip_integrity_diagnostics")} <= {
        (item["how"], item["ref"]) for item in kpi["diagnostics"]
    }


@pytest.mark.smt2020
@pytest.mark.mock_service
def test_initial_wip_sql_matches_source(db, store: KnowledgeStore) -> None:
    sql = store.kpis["initial_wip"].sql_template.replace(":dataset", "?")
    with sqlite3.connect(db) as conn:
        rows = conn.execute(sql, ("HVLM",)).fetchall()
    assert rows == [("HVLM", "part_3", 1432, 35800), ("HVLM", "part_4", 823, 20575)]


@pytest.mark.smt2020
@pytest.mark.mock_service
def test_dataset_key_prevents_cross_join_inflation(db) -> None:
    with sqlite3.connect(db) as conn:
        safe = conn.execute(
            """
            SELECT COUNT(*) FROM part p JOIN route_step r
              ON r.dataset=p.dataset AND r.route=p.route
            """
        ).fetchone()[0]
        unsafe = conn.execute(
            "SELECT COUNT(*) FROM part p JOIN route_step r ON r.route=p.route"
        ).fetchone()[0]
    assert safe == 4939
    assert unsafe > safe
