"""네트워크 없이 AgentEvent 흐름을 재현하는 Fake Runner.

`PLANNING_AGENT_FAKE=1` 일 때 `run_agent` 가 이 구현으로 대체된다.
Claude 모델은 호출하지 않고, Mock Service 를 실제로 거쳐 전체 이벤트
계약(text / status / tool_call / tool_result / done)을 검증할 수 있게 한다.

TODO:
- 실제 Agent SDK E2E 가 준비되면 데모/테스트 용도로만 유지한다.
"""

from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from tools.simulation_tool import run_simulation
from tools.sql_tool import query_database


async def run_fake_agent(
    message: str,
    conversation_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """고정된 시나리오로 AgentEvent 를 스트리밍한다."""

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "running", "label": "질의 분석"},
    )

    # 1) 구조화 데이터 조회
    yield AgentEvent(type="tool_call", tool_name="query_database")
    sql_result = await query_database(question=message)
    yield AgentEvent(
        type="tool_result",
        tool_name="query_database",
        data=sql_result,
    )
    yield AgentEvent(
        type="status",
        data={
            "step": "query_database",
            "status": "completed",
            "label": "생산 데이터 조회 완료",
        },
    )

    # 2) 실적 조회 시뮬레이션
    yield AgentEvent(type="tool_call", tool_name="run_simulation")
    sim_result = await run_simulation(
        simulation_type="실적_조회",
        params={"workMonthFrom": "202609", "workMonthTo": "202609"},
    )
    yield AgentEvent(
        type="tool_result",
        tool_name="run_simulation",
        data=sim_result,
    )
    yield AgentEvent(
        type="status",
        data={
            "step": "simulation",
            "status": "completed",
            "label": "생산계획 Simulation 수행",
        },
    )

    # 3) 사용자 답변 스트리밍
    results = sim_result.get("results")
    for chunk in (
        "조회 결과를 종합하면, ",
        f"해당 조건의 실적 조회 결과는 {results} 입니다. ",
        "(Fake Runner 응답)",
    ):
        yield AgentEvent(type="text", content=chunk)

    yield AgentEvent(type="done")
