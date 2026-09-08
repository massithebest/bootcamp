"""네트워크 없이 AgentEvent 흐름을 재현하는 Fake Runner.

`PLANNING_AGENT_FAKE=1` 일 때 `run_agent` 가 이 구현으로 대체된다.
Claude 모델은 호출하지 않고, Mock Service 를 실제로 거쳐 전체 이벤트
계약(text / status / tool_call / tool_result / done)을 검증할 수 있게 한다.

TODO:
- 실제 Agent SDK E2E 가 준비되면 데모/테스트 용도로만 유지한다.
"""

from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from tools.line_capacity_tool import simulate_line_capacity
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

    # 2) 라인 capacity 시뮬레이션
    yield AgentEvent(type="tool_call", tool_name="simulate_line_capacity")
    sim_result = await simulate_line_capacity(
        line="A",
        period="2026-09",
        target_qty=1000,
    )
    yield AgentEvent(
        type="tool_result",
        tool_name="simulate_line_capacity",
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
    achievable = sim_result.get("achievable_qty")
    for chunk in (
        "조회 결과를 종합하면, ",
        f"해당 조건에서 예상 생산 가능 수량은 약 {achievable}개입니다. ",
        "(Fake Runner 응답)",
    ):
        yield AgentEvent(type="text", content=chunk)

    yield AgentEvent(type="done")
