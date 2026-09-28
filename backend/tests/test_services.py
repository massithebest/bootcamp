"""Mock service contracts backed by a synthetic mock database."""

import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient

from main import app
from services.results import store as result_store
from services.mock import mock_rag_service, mock_simulation_service, mock_sql_service
from services.results.store import LocalParquetResultStore
from tools.result_tool import get_result_page


pytestmark = pytest.mark.mock_service


@pytest.fixture()
def mock_db(tmp_path, monkeypatch, mock_database):
    db_path = mock_database.main(tmp_path / "mock_planning.db")
    monkeypatch.setattr("core.config.MOCK_DB_PATH", db_path)
    monkeypatch.setattr(result_store, "_store", LocalParquetResultStore(tmp_path / "results"))
    return db_path


def test_mock_execute_sql_returns_preview_payload(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part, route FROM part WHERE dataset = 'SEG_B' ORDER BY part",
            purpose="SEG_B Part 목록",
        )
    )
    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert [column["name"] for column in result["columns"]] == ["part", "route"]
    assert result["sample_rows"][0] == {"part": "part_1", "route": "route_1"}
    assert result["row_count"] == 10
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])


def test_mock_execute_sql_preview_omits_full_rows_and_is_readable_via_api(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT route, step FROM route_step WHERE dataset='SEG_A' LIMIT 300",
            purpose="Part 확인",
            access_scope="scope-a",
        )
    )

    assert result["status"] == "ok" and result["kind"] == "database"
    assert result["purpose"] == "Part 확인"
    assert len(result["sample_rows"]) <= 5
    assert result["row_count"] > 5
    assert set(result) >= {
        "result_id", "row_count", "source_truncated", "columns", "sample_rows",
        "date_ranges", "distinct_counts", "statistics", "top_groups",
    }
    assert not {"table", "results", "type", "sql", "summary_rows"} & set(result)
    assert "SELECT" not in json.dumps(result)

    # 같은 결과를 Result API로 페이지 단위 조회할 수 있다.
    client = TestClient(app)
    client.cookies.set("pp_session_scope", "scope-a")
    page = client.get(f"/api/query-results/{result['result_id']}/table?page_size=3")
    assert page.status_code == 200 and len(page.json()["rows"]) == 3


def test_mock_execute_sql_respects_max_rows_guardrail(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT * FROM route_step WHERE dataset = 'SEG_B'", purpose="전체 Route Step"
        )
    )
    assert result["row_count"] == 1000
    meta = result_store.get_result_store().get_meta(result["result_id"])
    assert meta is not None and meta.source_truncated is True


def test_mock_execute_sql_distinguishes_exact_limit_from_overflow(mock_db, monkeypatch) -> None:
    query = "SELECT part FROM part WHERE dataset = 'SEG_A' ORDER BY part"
    monkeypatch.setattr(mock_sql_service, "MAX_ROWS", 2)
    exact = asyncio.run(mock_sql_service.execute_sql(query, purpose="정확한 상한"))
    monkeypatch.setattr(mock_sql_service, "MAX_ROWS", 1)
    overflow = asyncio.run(mock_sql_service.execute_sql(query, purpose="상한 초과"))
    store = result_store.get_result_store()
    assert store.get_meta(exact["result_id"]).source_truncated is False
    assert store.get_meta(overflow["result_id"]).source_truncated is True


def test_mock_execute_sql_rejects_write(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("DELETE FROM wip", purpose="지우기")
    )
    assert result["status"] == "error" and result["kind"] == "database"


def test_mock_execute_sql_unregistered_table_hints_list_tables(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM SECRET", purpose="시도")
    )
    assert result["status"] == "error" and "list_tables" in result["message"]


def test_mock_execute_sql_sqlite_error_is_reported(mock_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT no_such_column FROM part", purpose="오타")
    )
    assert result["status"] == "error" and "SQL 실행 오류" in result["message"]


def test_mock_execute_sql_without_db_tells_how_to_build(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("core.config.MOCK_DB_PATH", tmp_path / "missing.db")
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM part", purpose="확인")
    )
    assert result["status"] == "error"
    assert "generate_mock_database" in result["message"]


def test_mock_rag_service_contract() -> None:
    result = asyncio.run(mock_rag_service.search("리드타임 정의"))
    assert result["status"] == "ok" and isinstance(result["documents"], list)


def test_mock_list_simulation_contract() -> None:
    result = asyncio.run(mock_simulation_service.list_simulation())
    assert result["status"] == "ok"
    by_type = {item["type"]: item for item in result["simulations"]}
    assert set(by_type) == {"입력_정합성_검증", "PKT_목표수량_스왑산출"}
    assert by_type["입력_정합성_검증"]["params"]["dataset"]["required"] is True
    assert by_type["PKT_목표수량_스왑산출"]["params"]["view"]["required"] is True


@pytest.mark.parametrize(
    ("dataset", "expected"),
    [("SEG_A", (2, 926, 106, 2255)), ("seg_b", (10, 4013, 106, 2156))],
)
def test_mock_input_validation(mock_db, dataset: str, expected: tuple[int, ...]) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="입력_정합성_검증", params={"dataset": dataset}
        )
    )
    assert result["status"] == "ok" and result["kind"] == "simulation"
    assert result["scenario"] and result["summary"]
    assert tuple(item["value"] for item in result["kpis"]) == expected
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])
    assert "results" not in result and "table" not in result and "type" not in result

    page = asyncio.run(
        get_result_page(result["result_id"], offset=0, limit=result["row_count"])
    )
    columns = [column["name"] for column in result["columns"]]
    checks = [dict(zip(columns, row)) for row in page["rows"]]
    assert all(check["unmatched_rows"] == 0 for check in checks)
    assert all(
        check["matched_rows"] + check["unmatched_rows"] == check["source_rows"]
        for check in checks
    )


def test_mock_input_validation_rejects_invalid_dataset(mock_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="입력_정합성_검증", params={"dataset": "unknown"}
        )
    )
    assert result["status"] == "error"
    assert "SEG_A" in result["message"] and "SEG_B" in result["message"]


def test_mock_input_validation_missing_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("core.config.MOCK_DB_PATH", tmp_path / "missing.db")
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="입력_정합성_검증", params={"dataset": "SEG_A"}
        )
    )
    assert result["status"] == "error" and "generate_mock_database" in result["message"]


def test_sql_and_simulation_store_access_scope(mock_db) -> None:
    sql = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part FROM part", purpose="scope 확인", access_scope="scope-a"
        )
    )
    simulation = asyncio.run(
        mock_simulation_service.run_simulation(
            "입력_정합성_검증", {"dataset": "SEG_A"}, access_scope="scope-b"
        )
    )
    store = result_store.get_result_store()
    assert store.get_meta(sql["result_id"]).access_scope == "scope-a"
    assert store.get_meta(simulation["result_id"]).access_scope == "scope-b"


def test_mock_pkt_swap_all_view_returns_items_and_metadata(mock_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "all"}
        )
    )
    assert result["status"] == "ok" and result["kind"] == "simulation"
    assert result["simulation_type"] == "PKT_목표수량_스왑산출"
    labels = {kpi["label"]: kpi["value"] for kpi in result["kpis"]}
    assert labels["행 수"] > 0
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])


def test_mock_pkt_swap_swapped_view_only_includes_swap_rows(mock_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "swapped"}
        )
    )
    assert result["status"] == "ok"
    page = asyncio.run(
        get_result_page(result["result_id"], offset=0, limit=result["row_count"])
    )
    columns = [column["name"] for column in result["columns"]]
    rows = [dict(zip(columns, row)) for row in page["rows"]]
    assert rows  # 합성 데이터는 swap이 적어도 한 건 발생하도록 구성됨
    assert all(row["swap_direction"] in {"GIVE", "RECEIVE"} for row in rows)


def test_mock_pkt_swap_by_ids_filters_products(mock_db) -> None:
    all_result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "all"}
        )
    )
    page = asyncio.run(
        get_result_page(all_result["result_id"], offset=0, limit=all_result["row_count"])
    )
    columns = [column["name"] for column in all_result["columns"]]
    first_id = dict(zip(columns, page["rows"][0]))["planProductId"]

    by_ids_result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출",
            params={"view": "by_ids", "plan_prod_ids": [first_id]},
        )
    )
    assert by_ids_result["status"] == "ok"
    filtered_page = asyncio.run(
        get_result_page(by_ids_result["result_id"], offset=0, limit=by_ids_result["row_count"])
    )
    filtered_ids = {dict(zip(columns, row))["planProductId"] for row in filtered_page["rows"]}
    assert filtered_ids == {first_id}


def test_mock_pkt_swap_by_ids_requires_plan_prod_ids() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "by_ids"}
        )
    )
    assert result["status"] == "missing_params"
    assert result["missing"][0]["name"] == "plan_prod_ids"


def test_mock_pkt_swap_requires_view() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={}
        )
    )
    assert result["status"] == "missing_params"
    assert result["missing"][0]["name"] == "view"


def test_mock_pkt_swap_deterministic(mock_db) -> None:
    first = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "all"}
        )
    )
    second = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="PKT_목표수량_스왑산출", params={"view": "all"}
        )
    )
    assert first["row_count"] == second["row_count"]
    assert first["kpis"] == second["kpis"]


@pytest.mark.parametrize("source", ['"private_table"', '[private_table]', '`private_table`', '/* gap */ private_table'])
def test_sql_catalog_cannot_be_bypassed_with_quoted_or_commented_table(mock_db, source):
    import sqlite3

    with sqlite3.connect(mock_db) as conn:
        conn.execute("CREATE TABLE private_table (value TEXT)")
        conn.execute("INSERT INTO private_table VALUES ('hidden fixture')")
    result = asyncio.run(mock_sql_service.execute_sql(f"SELECT * FROM {source}", purpose="guard test"))
    assert result["status"] == "error"
    assert "hidden fixture" not in str(result)


def test_sql_catalog_allows_quoted_table_and_cte(mock_db):
    result = asyncio.run(mock_sql_service.execute_sql(
        'WITH source AS (SELECT part FROM "part") SELECT COUNT(*) AS n FROM source', purpose="CTE test"))
    assert result["status"] == "ok"
    assert result["sample_rows"] == [{"n": 12}]
