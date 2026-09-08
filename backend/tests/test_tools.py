"""각 Tool을 Mock Mode에서 호출하고 계약을 확인한다."""

import asyncio
import inspect

from tools.line_capacity_tool import simulate_line_capacity
from tools.line_comparison_tool import simulate_line_comparison
from tools.material_constraint_tool import (
    MaterialConstraint,
    simulate_material_constraint,
)
from tools.rag_tool import search_knowledge
from tools.sql_tool import query_database


def test_all_tools_are_async() -> None:
    for tool in (
        query_database,
        search_knowledge,
        simulate_line_capacity,
        simulate_material_constraint,
        simulate_line_comparison,
    ):
        assert inspect.iscoroutinefunction(tool)


def test_query_database_returns_dict() -> None:
    result = asyncio.run(query_database("9월 A라인 생산 실적"))
    assert isinstance(result, dict)


def test_search_knowledge_returns_dict() -> None:
    result = asyncio.run(search_knowledge("리드타임 정의"))
    assert isinstance(result, dict)


def test_simulate_line_capacity_returns_dict() -> None:
    result = asyncio.run(
        simulate_line_capacity(line="A", period="2026-09", target_qty=1000)
    )
    assert isinstance(result, dict)


def test_simulate_material_constraint_accepts_pydantic_input() -> None:
    result = asyncio.run(
        simulate_material_constraint(
            line="A",
            period="2026-09",
            materials=[
                MaterialConstraint(material_id="X", available_qty=500),
                MaterialConstraint(material_id="Y", available_qty=300),
            ],
        )
    )
    assert isinstance(result, dict)


def test_simulate_line_comparison_returns_dict() -> None:
    result = asyncio.run(
        simulate_line_comparison(
            lines=["A", "B"],
            period_start="2026-10-01",
            period_end="2026-10-31",
        )
    )
    assert isinstance(result, dict)
