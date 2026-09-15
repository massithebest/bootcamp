"""Mock service 입력/출력 계약 검증."""

import asyncio
import re

import pytest

from scripts.seed_sample_db import main as seed_main
from services import result_store
from services.mock import mock_rag_service
from services.mock import mock_simulation_service
from services.mock import mock_sql_service
from services.result_store import LocalParquetResultStore


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """시드 DB 를 tmp_path 에 만들고 `SAMPLE_DB_PATH` 를 그쪽으로 돌린다."""

    db_path = seed_main(tmp_path / "sample.sqlite")
    monkeypatch.setattr("core.config.SAMPLE_DB_PATH", db_path)
    monkeypatch.setattr(
        result_store, "_store", LocalParquetResultStore(tmp_path / "results")
    )
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
    assert result["type"] == "inline"
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])


def test_mock_execute_sql_respects_max_rows_guardrail(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT * FROM FGS_INBOUND_RESULT", purpose="전체 실적"
        )
    )

    assert result["row_count"] == 500
    assert "truncated" not in result


def test_mock_execute_sql_large_result_omits_rows(seeded_db, monkeypatch) -> None:
    monkeypatch.setattr(mock_sql_service, "INLINE_ROW_THRESHOLD", 1)

    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT line_cd, line_nm FROM LINE_MASTER ORDER BY line_cd",
            purpose="라인 목록 확인",
        )
    )

    assert result["type"] == "large_result"
    assert "table" not in result
    assert result["sample_rows"]
    assert result["columns"]
    assert "summary" in result


def test_mock_execute_sql_result_retrievable_via_store(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT line_cd FROM LINE_MASTER", purpose="라인 확인"
        )
    )

    assert result_store.get_result_store().get_meta(result["result_id"]) is not None


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


def test_mock_list_simulation_exposes_param_detail() -> None:
    """PARAM_SCHEMA 가 합쳐지지 않아 에이전트에게 안 가던 문제(설계 §현재 상태)."""

    result = asyncio.run(mock_simulation_service.list_simulation())
    performance = next(s for s in result["simulations"] if s["type"] == "실적_조회")

    assert performance["params"]["workMonthFrom"]["description"]
    assert performance["params"]["workMonthFrom"]["required"] is True
    assert performance["when_to_use"]
    assert performance["output_schema"]["results"]["desc"]
    assert performance["follows"] == []


def test_mock_run_simulation_performance_lookup(seeded_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )

    assert result["status"] == "ok"
    assert isinstance(result["results"], list)
    assert {row["line"] for row in result["results"]} == {"A", "B", "C", "D"}
    assert all(row["workMonth"] == "202608" for row in result["results"])


def test_mock_run_simulation_performance_lookup_gets_result_id(seeded_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )

    assert result["type"] == "inline"
    assert re.fullmatch(r"[0-9a-f]{32}", result["result_id"])
    assert {row["line"] for row in result["results"]} == {"A", "B", "C", "D"}


def test_mock_run_simulation_large_result_uses_sample(seeded_db, monkeypatch) -> None:
    monkeypatch.setattr(mock_simulation_service, "INLINE_ROW_THRESHOLD", 1)

    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )

    assert result["type"] == "large_result"
    assert "results" not in result
    assert len(result["sample_rows"]) == 4
    assert result["summary"]["qty"]["null_count"] == 0


def test_mock_run_simulation_reflects_scenario(seeded_db) -> None:
    """시뮬레이션이 SQL 과 같은 시드 DB 를 본다 — 부진 라인이 두 경로에서 일치해야 한다."""

    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202607", "workMonthTo": "202609"},
        )
    )
    by_month = {
        (row["line"], row["workMonth"]): row["qty"] for row in result["results"]
    }

    assert by_month[("B", "202609")] < by_month[("B", "202607")]


def test_mock_run_simulation_fixed_mp_reads_seed(seeded_db) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            simulation_type="MP_확정조회", params={}
        )
    )

    assert result["status"] == "ok"
    assert result["mpVersion"] == "MP-202609-FIXED"
    # 시나리오가 계획 변경 흔적을 남기지 않았으므로 이 가설은 기각돼야 한다.
    assert result["changed"] == 0


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
