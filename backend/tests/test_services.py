"""Mock service 입력/출력 계약 검증."""

import asyncio

import pytest

from scripts.seed_sample_db import main as seed_main
from services.mock import mock_rag_service
from services.mock import mock_simulation_service
from services.mock import mock_sql_service


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """시드 DB 를 tmp_path 에 만들고 `SAMPLE_DB_PATH` 를 그쪽으로 돌린다."""

    db_path = seed_main(tmp_path / "sample.sqlite")
    monkeypatch.setattr("core.config.SAMPLE_DB_PATH", db_path)
    return db_path


def test_mock_execute_sql_returns_table_payload(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT line_cd, line_nm FROM LINE_MASTER ORDER BY line_cd",
            purpose="라인 목록 확인",
        )
    )

    assert result["status"] == "ok"
    assert result["kind"] == "database"
    assert result["purpose"] == "라인 목록 확인"
    assert result["table"]["columns"] == ["line_cd", "line_nm"]
    assert result["table"]["rows"][0] == ["A", "1라인"]
    assert result["row_count"] == 4
    assert result["truncated"] is False


def test_mock_execute_sql_truncates_over_max_rows(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT * FROM FGS_INBOUND_RESULT", purpose="전체 실적"
        )
    )

    assert result["truncated"] is True
    assert result["row_count"] == 500


def test_mock_execute_sql_rejects_write(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "DELETE FROM FGS_INBOUND_RESULT", purpose="지우기"
        )
    )

    assert result["status"] == "error"
    assert result["kind"] == "database"


def test_mock_execute_sql_unregistered_table_hints_list_tables(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM SECRET", purpose="시도")
    )

    assert result["status"] == "error"
    assert "list_tables" in result["message"]


def test_mock_execute_sql_sqlite_error_is_reported(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT no_such_column FROM LINE_MASTER", purpose="오타"
        )
    )

    assert result["status"] == "error"
    assert "SQL 실행 오류" in result["message"]


def test_mock_execute_sql_without_seed_db_tells_how_to_seed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("core.config.SAMPLE_DB_PATH", tmp_path / "missing.sqlite")

    result = asyncio.run(
        mock_sql_service.execute_sql("SELECT * FROM LINE_MASTER", purpose="확인")
    )

    assert result["status"] == "error"
    assert "seed_sample_db" in result["message"]


def test_mock_rag_service_contract() -> None:
    result = asyncio.run(mock_rag_service.search("공정 매뉴얼"))

    assert result["status"] == "ok"
    assert isinstance(result["documents"], list)


def test_mock_list_simulation_contract() -> None:
    result = asyncio.run(mock_simulation_service.list_simulation())

    assert result["status"] == "ok"
    types = {item["type"] for item in result["simulations"]}
    assert types == {"실적_조회", "MP_최신조회", "MP_확정조회", "SWAP_결과조회"}


def test_mock_run_simulation_performance_lookup() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )

    assert result["status"] == "ok"
    assert isinstance(result["results"], list)


def test_mock_run_simulation_swap_result() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="SWAP_결과조회",
            params={"productId": "0000000000-00001"},
        )
    )

    assert result["status"] == "ok"
    assert result["productId"] == "0000000000-00001"


def test_mock_run_simulation_missing_required_param() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608"},
        )
    )

    assert result["status"] == "error"


def test_mock_run_simulation_unknown_type() -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="존재하지_않는_타입",
            params={},
        )
    )

    assert result["status"] == "error"
