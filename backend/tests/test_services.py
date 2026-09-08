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


def test_mock_line_capacity_contract() -> None:
    result = asyncio.run(
        mock_simulation_service.run_line_capacity(
            line="A",
            period="2026-09",
            target_qty=1000,
        )
    )

    assert result["status"] == "ok"
    assert result["line"] == "A"
    assert "achievable_qty" in result


def test_mock_material_constraint_contract() -> None:
    result = asyncio.run(
        mock_simulation_service.run_material_constraint(
            line="A",
            period="2026-09",
            materials=[{"material_id": "X", "available_qty": 500}],
        )
    )

    assert result["status"] == "ok"
    assert result["limiting_material"] == "X"
    assert isinstance(result["material_usage"], list)


def test_mock_line_comparison_contract() -> None:
    result = asyncio.run(
        mock_simulation_service.run_line_comparison(
            lines=["A", "B", "C"],
            period_start="2026-10-01",
            period_end="2026-10-31",
            metric="efficiency",
        )
    )

    assert result["status"] == "ok"
    assert len(result["ranking"]) == 3
    assert result["ranking"][0]["rank"] == 1
