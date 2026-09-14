"""Mock service 입력/출력 계약 검증."""

import asyncio

from services.mock import mock_rag_service
from services.mock import mock_simulation_service
from services.mock import mock_sql_service


def test_mock_sql_service_contract() -> None:
    result = asyncio.run(mock_sql_service.generate_and_query("생산 실적"))

    assert result["status"] == "ok"
    assert "generated_sql" in result
    assert isinstance(result["rows"], list)


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
