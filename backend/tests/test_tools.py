"""각 Tool을 Mock Mode에서 호출하고 계약을 확인한다."""

import asyncio
import inspect

from tools.rag_tool import search_knowledge
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import query_database


def test_all_tools_are_async() -> None:
    for tool in (
        query_database,
        search_knowledge,
        list_simulation,
        run_simulation,
    ):
        assert inspect.iscoroutinefunction(tool)


def test_query_database_returns_dict() -> None:
    result = asyncio.run(query_database("9월 A라인 생산 실적"))
    assert isinstance(result, dict)


def test_search_knowledge_returns_dict() -> None:
    result = asyncio.run(search_knowledge("리드타임 정의"))
    assert isinstance(result, dict)


def test_list_simulation_returns_dict() -> None:
    result = asyncio.run(list_simulation())
    assert isinstance(result, dict)
    assert isinstance(result["simulations"], list)


def test_run_simulation_returns_dict() -> None:
    result = asyncio.run(
        run_simulation(
            simulation_type="실적_조회",
            params={"workMonthFrom": "202608", "workMonthTo": "202608"},
        )
    )
    assert isinstance(result, dict)
    assert result["status"] == "ok"
