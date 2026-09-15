"""각 Tool을 Mock Mode에서 호출하고 계약을 확인한다."""

import asyncio
import inspect

import pytest

from agent.sdk_tools import TOOL_NAMES
from scripts.build_smt2020_db import DEFAULT_SOURCE_ROOT, main as build_smt2020_db
from services import result_store
from services.result_store import LocalParquetResultStore
from services import visualization_store
from services.visualization_store import LocalVisualizationStore
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
from tools.visualization_tool import prepare_visualization


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
    prepare_visualization,
)


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    db_path = build_smt2020_db(DEFAULT_SOURCE_ROOT, tmp_path / "smt2020.db")
    monkeypatch.setattr("core.config.SMT2020_DB_PATH", db_path)
    monkeypatch.setattr(
        result_store, "_store", LocalParquetResultStore(tmp_path / "results")
    )
    monkeypatch.setattr(
        visualization_store,
        "_store",
        LocalVisualizationStore(tmp_path / "visualizations"),
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
        execute_sql("SELECT part FROM part WHERE dataset='HVLM'", purpose="Part 확인")
    )

    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert result["table"]["columns"] == ["part"]


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
            simulation_type="SMT2020_입력검증",
            params={"dataset": "HVLM"},
        )
    )
    assert isinstance(result, dict)
    assert result["status"] == "ok"


@pytest.mark.parametrize(
    ("call", "catalog_type"),
    [
        (lambda: list_tables(), "table_list"),
        (lambda: describe_table("wip"), "table"),
        (lambda: list_kpis(), "kpi_list"),
        (lambda: get_kpi("initial_wip"), "kpi"),
        (lambda: list_recipes(), "recipe_list"),
    ],
)
def test_knowledge_tools_use_catalog_kind(call, catalog_type: str) -> None:
    """`knowledge` 는 프론트가 RAG 결과에 이미 쓰므로 `catalog` 여야 한다."""

    result = asyncio.run(call())

    assert result["status"] == "ok"
    assert result["kind"] == "catalog"
    assert result["catalog_type"] == catalog_type


def test_list_tables_keyword_filters() -> None:
    result = asyncio.run(list_tables(keyword="재공"))

    assert [row["table"] for row in result["data"]] == ["wip"]


def test_describe_table_unknown_is_error() -> None:
    result = asyncio.run(describe_table("없는것"))

    assert result["status"] == "error"
    assert "list_tables" in result["message"]


def test_get_kpi_unknown_is_error() -> None:
    result = asyncio.run(get_kpi("없는KPI"))

    assert result["status"] == "error"
    assert "list_kpis" in result["message"]


def test_get_kpi_exposes_diagnostics() -> None:
    result = asyncio.run(get_kpi("initial_wip"))

    assert result["verified"] is True
    assert [d["how"] for d in result["data"]["diagnostics"]] == ["simulation"]


def test_get_result_summary_unknown_id_is_error() -> None:
    result = asyncio.run(get_result_summary("missing"))

    assert result["status"] == "error"
    assert "만료" in result["message"]


def test_get_result_page_returns_slice(seeded_db) -> None:
    saved = asyncio.run(
        execute_sql(
            "SELECT part, route FROM part WHERE dataset='LVHM' ORDER BY part",
            purpose="Part 목록 확인",
        )
    )

    result = asyncio.run(get_result_page(saved["result_id"], offset=1, limit=2))

    assert result["status"] == "ok"
    assert result["rows"] == [["part_10", "r_10"], ["part_2", "r_2"]]
    assert result["row_count"] == 10


def test_prepare_visualization_returns_only_id_and_warnings(seeded_db) -> None:
    saved = asyncio.run(
        execute_sql(
            "SELECT part, COUNT(*) AS qty FROM wip WHERE dataset='LVHM' GROUP BY part",
            purpose="제품별 WIP 건수",
            access_scope="scope-a",
        )
    )

    result = asyncio.run(
        prepare_visualization(
            result_id=saved["result_id"],
            kind="bar",
            x="part",
            y=["qty"],
            access_scope="scope-a",
        )
    )

    assert set(result) == {"status", "visualization_id", "warnings"}
    assert result["status"] == "ok"


def test_prepare_visualization_preserves_service_error(seeded_db) -> None:
    saved = asyncio.run(
        execute_sql(
            "SELECT part, COUNT(*) AS qty FROM wip WHERE dataset='LVHM' GROUP BY part",
            purpose="제품별 WIP 건수",
            access_scope="scope-a",
        )
    )

    result = asyncio.run(
        prepare_visualization(
            result_id=saved["result_id"],
            kind="bar",
            x="missing",
            y=["qty"],
            access_scope="scope-a",
        )
    )

    assert result["status"] == "error"
    assert result["code"] == "COLUMN_NOT_FOUND"
    assert result["message"]


@pytest.mark.parametrize("state", ["expired", "missing-file", "corrupt-meta", "corrupt-data", "other-scope"])
@pytest.mark.parametrize("operation", ["summary", "page"])
def test_result_tools_reject_unavailable_results(tmp_path, monkeypatch, state, operation):
    import json
    from datetime import datetime, timedelta, timezone

    store = LocalParquetResultStore(tmp_path)
    monkeypatch.setattr(result_store, "_store", store)
    meta = store.save(["qty"], [[10]], source="test", conversation_id=None, access_scope="scope-a")
    path = tmp_path / f"{meta.result_id}.meta.json"
    if state == "expired":
        payload = json.loads(path.read_text())
        payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        path.write_text(json.dumps(payload))
    elif state == "missing-file":
        meta.path.unlink()
    elif state == "corrupt-meta":
        path.write_text("{")
    elif state == "corrupt-data":
        meta.path.write_text("broken parquet")
    scope = "scope-b" if state == "other-scope" else "scope-a"
    call = get_result_summary(meta.result_id, access_scope=scope) if operation == "summary" else get_result_page(meta.result_id, 0, 10, access_scope=scope)
    result = asyncio.run(call)
    assert result["status"] == "error"
    assert str(tmp_path) not in json.dumps(result)
    assert "rows" not in result and "summary" not in result
