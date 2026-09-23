"""각 Tool을 Mock Mode에서 호출하고 계약을 확인한다."""

import asyncio
import inspect

import pytest

from agent.sdk_tools import TOOL_NAMES
from services.results import store as result_store
from services.knowledge.documents import KnowledgeError
from services.results.store import LocalParquetResultStore
from tools.knowledge_tool import (
    describe_table,
    get_kpi,
    get_recipe,
    list_kpis,
    list_recipes,
    list_tables,
)
from tools.present_tool import (
    present_chart,
    present_simulation,
    present_sql_preview,
    present_table,
)
from tools.rag_tool import search_documents
from tools.result_tool import get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql


ALL_TOOLS = (
    execute_sql,
    search_documents,
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
    present_sql_preview,
    present_chart,
    present_table,
    present_simulation,
)


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch, mock_database):
    db_path = mock_database.main(tmp_path / "mock_planning.db")
    monkeypatch.setattr("core.config.MOCK_DB_PATH", db_path)
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
        execute_sql("SELECT part FROM part WHERE dataset='SEG_A'", purpose="Part 확인")
    )

    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert [column["name"] for column in result["columns"]] == ["part"]


@pytest.mark.mock_service
def test_search_documents_returns_dict() -> None:
    result = asyncio.run(search_documents("리드타임 정의"))
    assert isinstance(result, dict)


def test_search_documents_keeps_safe_knowledge_error_shape(monkeypatch) -> None:
    async def fail(query: str) -> dict:
        raise KnowledgeError(404, "검토 완료된 문서를 찾을 수 없습니다.")

    monkeypatch.setattr("tools.rag_tool.knowledge_search_service.search", fail)

    result = asyncio.run(search_documents("리드타임"))

    assert result == {
        "kind": "knowledge",
        "status": "error",
        "query": "리드타임",
        "documents": [],
        "message": "검토 완료된 문서를 찾을 수 없습니다.",
    }


@pytest.mark.mock_service
def test_list_simulation_returns_dict() -> None:
    result = asyncio.run(list_simulation())
    assert isinstance(result, dict)
    assert isinstance(result["simulations"], list)


def test_run_simulation_returns_dict(seeded_db) -> None:
    result = asyncio.run(
        run_simulation(
            simulation_type="입력_정합성_검증",
            params={"dataset": "SEG_A"},
        )
    )
    assert isinstance(result, dict)
    assert result["status"] == "ok"


@pytest.mark.usefixtures("bundled_knowledge")
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


@pytest.mark.usefixtures("bundled_knowledge")
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


@pytest.mark.usefixtures("bundled_knowledge")
def test_get_kpi_exposes_diagnostics() -> None:
    result = asyncio.run(get_kpi("initial_wip"))

    assert result["verified"] is False  # expanded diagnostics await domain review
    assert {d["how"] for d in result["data"]["diagnostics"]} == {"sql", "simulation"}


def test_get_result_summary_unknown_id_is_error() -> None:
    result = asyncio.run(get_result_summary("missing"))

    assert result["status"] == "error"
    assert "만료" in result["message"]


def test_get_result_page_returns_slice(seeded_db) -> None:
    saved = asyncio.run(
        execute_sql(
            "SELECT part, route FROM part WHERE dataset='SEG_B' ORDER BY part",
            purpose="Part 목록 확인",
        )
    )

    result = asyncio.run(get_result_page(saved["result_id"], offset=1, limit=2))

    assert result["status"] == "ok"
    assert result["rows"] == [["part_10", "route_10"], ["part_2", "route_2"]]
    assert result["row_count"] == 10


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
