"""Mock service contracts backed by a converted SMT2020 database."""

import asyncio
import re

import pytest

from services import result_store
from services.mock import mock_rag_service, mock_simulation_service, mock_sql_service
from services.result_store import LocalParquetResultStore


pytestmark = pytest.mark.mock_service


@pytest.fixture()
def smt_db(tmp_path, monkeypatch, smt2020_assets):
    db_path = smt2020_assets.main(
        smt2020_assets.DEFAULT_SOURCE_ROOT, tmp_path / "smt2020.db"
    )
    monkeypatch.setattr("core.config.SMT2020_DB_PATH", db_path)
    monkeypatch.setattr(result_store, "_store", LocalParquetResultStore(tmp_path / "results"))
    return db_path


def test_mock_execute_sql_returns_table_payload(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part, route FROM part WHERE dataset = 'LVHM' ORDER BY part",
            purpose="LVHM Part 목록",
        )
    )
    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert result["table"]["columns"] == ["part", "route"]
    assert result["table"]["rows"][0] == ["part_1", "r_1"]
    assert result["row_count"] == 10
    assert result["type"] == "inline"
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])


def test_mock_execute_sql_respects_max_rows_guardrail(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT * FROM route_step WHERE dataset = 'LVHM'", purpose="전체 Route Step"
        )
    )
    assert result["row_count"] == 1000
    meta = result_store.get_result_store().get_meta(result["result_id"])
    assert meta is not None and meta.source_truncated is True


def test_mock_execute_sql_distinguishes_exact_limit_from_overflow(smt_db, monkeypatch) -> None:
    query = "SELECT part FROM part WHERE dataset = 'HVLM' ORDER BY part"
    monkeypatch.setattr(mock_sql_service, "MAX_ROWS", 2)
    exact = asyncio.run(mock_sql_service.execute_sql(query, purpose="정확한 상한"))
    monkeypatch.setattr(mock_sql_service, "MAX_ROWS", 1)
    overflow = asyncio.run(mock_sql_service.execute_sql(query, purpose="상한 초과"))
    store = result_store.get_result_store()
    assert store.get_meta(exact["result_id"]).source_truncated is False
    assert store.get_meta(overflow["result_id"]).source_truncated is True


def test_mock_execute_sql_large_result_omits_rows(smt_db, monkeypatch) -> None:
    monkeypatch.setattr(mock_sql_service, "INLINE_ROW_THRESHOLD", 1)
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part, route FROM part WHERE dataset = 'HVLM'", purpose="Part 목록"
        )
    )
    assert result["type"] == "large_result"
    assert "table" not in result
    assert result["sample_rows"] and result["columns"] and "summary" in result


def test_mock_execute_sql_result_retrievable_via_store(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT part FROM part", purpose="Part 확인")
    )
    assert result_store.get_result_store().get_meta(result["result_id"]) is not None


def test_mock_execute_sql_rejects_write(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("DELETE FROM wip", purpose="지우기")
    )
    assert result["status"] == "error" and result["kind"] == "database"


def test_mock_execute_sql_unregistered_table_hints_list_tables(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM SECRET", purpose="시도")
    )
    assert result["status"] == "error" and "list_tables" in result["message"]


def test_mock_execute_sql_sqlite_error_is_reported(smt_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT no_such_column FROM part", purpose="오타")
    )
    assert result["status"] == "error" and "SQL 실행 오류" in result["message"]


def test_mock_execute_sql_without_db_tells_how_to_build(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("core.config.SMT2020_DB_PATH", tmp_path / "missing.db")
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM part", purpose="확인")
    )
    assert result["status"] == "error"
    assert "build_smt2020_db" in result["message"]


def test_mock_rag_service_contract() -> None:
    result = asyncio.run(mock_rag_service.search("리드타임 정의"))
    assert result["status"] == "ok" and isinstance(result["documents"], list)


def test_mock_list_simulation_contract() -> None:
    result = asyncio.run(mock_simulation_service.list_simulation())
    assert result["status"] == "ok"
    assert [item["type"] for item in result["simulations"]] == ["SMT2020_입력검증"]
    assert result["simulations"][0]["params"]["dataset"]["required"] is True


@pytest.mark.parametrize(
    ("dataset", "expected"),
    [("HVLM", (2, 926, 106, 2255)), ("lvhm", (10, 4013, 106, 2156))],
)
def test_mock_input_validation(smt_db, dataset: str, expected: tuple[int, ...]) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="SMT2020_입력검증", params={"dataset": dataset}
        )
    )
    assert result["status"] == "ok" and result["type"] == "inline"
    assert tuple(item["value"] for item in result["kpis"]) == expected
    assert all(check["unmatched_rows"] == 0 for check in result["results"])
    assert all(
        check["matched_rows"] + check["unmatched_rows"] == check["source_rows"]
        for check in result["results"]
    )
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])


def test_mock_input_validation_rejects_invalid_dataset(smt_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="SMT2020_입력검증", params={"dataset": "unknown"}
        )
    )
    assert result["status"] == "error"
    assert "HVLM" in result["message"] and "LVHM" in result["message"]


def test_mock_input_validation_requires_dataset(smt_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="SMT2020_입력검증", params={}
        )
    )
    assert result["status"] == "error" and "dataset" in result["message"]


def test_mock_input_validation_missing_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("core.config.SMT2020_DB_PATH", tmp_path / "missing.db")
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="SMT2020_입력검증", params={"dataset": "HVLM"}
        )
    )
    assert result["status"] == "error" and "build_smt2020_db" in result["message"]


def test_sql_and_simulation_store_access_scope(smt_db) -> None:
    sql = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part FROM part", purpose="scope 확인", access_scope="scope-a"
        )
    )
    simulation = asyncio.run(
        mock_simulation_service.run_simulation(
            "SMT2020_입력검증", {"dataset": "HVLM"}, access_scope="scope-b"
        )
    )
    store = result_store.get_result_store()
    assert store.get_meta(sql["result_id"]).access_scope == "scope-a"
    assert store.get_meta(simulation["result_id"]).access_scope == "scope-b"


def test_mock_run_simulation_unknown_type() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation("존재하지_않는_타입", {})
    )
    assert result["status"] == "error"


@pytest.mark.parametrize("source", ['"private_table"', '[private_table]', '`private_table`', '/* gap */ private_table'])
def test_sql_catalog_cannot_be_bypassed_with_quoted_or_commented_table(smt_db, source):
    import sqlite3

    with sqlite3.connect(smt_db) as conn:
        conn.execute("CREATE TABLE private_table (value TEXT)")
        conn.execute("INSERT INTO private_table VALUES ('hidden fixture')")
    result = asyncio.run(mock_sql_service.execute_sql(f"SELECT * FROM {source}", purpose="guard test"))
    assert result["status"] == "error"
    assert "hidden fixture" not in str(result)


def test_sql_catalog_allows_quoted_table_and_cte(smt_db):
    result = asyncio.run(mock_sql_service.execute_sql(
        'WITH source AS (SELECT part FROM "part") SELECT COUNT(*) AS n FROM source', purpose="CTE test"))
    assert result["status"] == "ok"
    assert result["table"]["rows"] == [[12]]


def test_mock_real_function_signatures_match():
    import inspect
    from services.real import sql_service, rag_service, simulation_service

    for mock, real, names in [
        (mock_sql_service, sql_service, ["execute_sql"]),
        (mock_rag_service, rag_service, ["search"]),
        (mock_simulation_service, simulation_service, ["list_simulation", "run_simulation"]),
    ]:
        for name in names:
            assert inspect.signature(getattr(mock, name), eval_str=True) == inspect.signature(getattr(real, name), eval_str=True)
