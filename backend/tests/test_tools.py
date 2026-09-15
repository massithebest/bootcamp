"""각 Tool을 Mock Mode에서 호출하고 계약을 확인한다."""

import asyncio
import inspect

import pytest

from agent.sdk_tools import TOOL_NAMES
from scripts.seed_sample_db import main as seed_main
from services import result_store
from services.result_store import LocalParquetResultStore
from tools.knowledge_tool import (
    describe_table,
    get_kpi,
    get_recipe,
    list_kpis,
    list_recipes,
    list_tables,
)
from tools.rag_tool import search_knowledge
from tools.result_tool import get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql


ALL_TOOLS = (
    execute_sql,
    search_knowledge,
    list_simulation,
    run_simulation,
    list_tables,
    describe_table,
    list_kpis,
    get_kpi,
    list_recipes,
    get_recipe,
    get_result_summary,
    get_result_page,
)


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    db_path = seed_main(tmp_path / "sample.sqlite")
    monkeypatch.setattr("core.config.SAMPLE_DB_PATH", db_path)
    monkeypatch.setattr(
        result_store, "_store", LocalParquetResultStore(tmp_path / "results")
    )
    return db_path


def test_all_tools_are_async() -> None:
    for tool in ALL_TOOLS:
        assert inspect.iscoroutinefunction(tool)


def test_tool_names_cover_every_tool() -> None:
    short_names = {name.rsplit("__", 1)[-1] for name in TOOL_NAMES}

    assert short_names == {tool.__name__ for tool in ALL_TOOLS}


def test_execute_sql_returns_database_kind(seeded_db) -> None:
    result = asyncio.run(
        execute_sql("SELECT line_cd FROM LINE_MASTER", purpose="라인 확인")
    )

    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert result["table"]["columns"] == ["line_cd"]


def test_search_knowledge_returns_dict() -> None:
    result = asyncio.run(search_knowledge("리드타임 정의"))
    assert isinstance(result, dict)


def test_list_simulation_returns_dict() -> None:
    result = asyncio.run(list_simulation())
    assert isinstance(result, dict)
    assert isinstance(result["simulations"], list)


def test_run_simulation_returns_dict(seeded_db) -> None:
    result = asyncio.run(
        run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )
    assert isinstance(result, dict)
    assert result["status"] == "ok"


@pytest.mark.parametrize(
    ("call", "catalog_type"),
    [
        (lambda: list_tables(), "table_list"),
        (lambda: describe_table("FGS_INBOUND_RESULT"), "table"),
        (lambda: list_kpis(), "kpi_list"),
        (lambda: get_kpi("fgs_inbound"), "kpi"),
        (lambda: list_recipes(), "recipe_list"),
        (lambda: get_recipe("plan_vs_actual"), "recipe"),
    ],
)
def test_knowledge_tools_use_catalog_kind(call, catalog_type: str) -> None:
    """`knowledge` 는 프론트가 RAG 결과에 이미 쓰므로 `catalog` 여야 한다."""

    result = asyncio.run(call())

    assert result["status"] == "ok"
    assert result["kind"] == "catalog"
    assert result["catalog_type"] == catalog_type


def test_list_tables_keyword_filters() -> None:
    result = asyncio.run(list_tables(keyword="입고"))

    assert [row["table"] for row in result["data"]] == ["FGS_INBOUND_RESULT"]


def test_describe_table_unknown_is_error() -> None:
    result = asyncio.run(describe_table("없는것"))

    assert result["status"] == "error"
    assert "list_tables" in result["message"]


def test_get_kpi_unknown_is_error() -> None:
    result = asyncio.run(get_kpi("없는KPI"))

    assert result["status"] == "error"
    assert "list_kpis" in result["message"]


def test_get_kpi_exposes_diagnostics() -> None:
    result = asyncio.run(get_kpi("fgs_inbound"))

    assert result["verified"] is False
    assert [d["how"] for d in result["data"]["diagnostics"]] == [
        "simulation",
        "sql",
        "sql",
        "simulation",
    ]


def test_get_result_summary_unknown_id_is_error() -> None:
    result = asyncio.run(get_result_summary("missing"))

    assert result["status"] == "error"
    assert "만료" in result["message"]


def test_get_result_page_returns_slice(seeded_db) -> None:
    saved = asyncio.run(
        execute_sql(
            "SELECT line_cd, line_nm FROM LINE_MASTER ORDER BY line_cd",
            purpose="라인 목록 확인",
        )
    )

    result = asyncio.run(get_result_page(saved["result_id"], offset=1, limit=2))

    assert result["status"] == "ok"
    assert result["rows"] == [["B", "2라인"], ["C", "3라인"]]
    assert result["row_count"] == 4
