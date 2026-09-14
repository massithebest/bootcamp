"""네트워크 없이 AgentEvent 흐름을 재현하는 Fake Runner.

`PLANNING_AGENT_FAKE=1` 일 때 `run_agent` 가 이 구현으로 대체된다.
Claude 모델은 호출하지 않고, Mock Service 를 실제로 거쳐 전체 이벤트
계약(text / status / tool_call / tool_result / done)을 검증할 수 있게 한다.

이벤트 순서는 설계 §5 관통 예제의 앞부분(KPI 확인 → 달성률 조회 → 계획 변경
확인)을 따른다 — 프론트가 `catalog` / `database` 두 kind 를 모두 받아본다.
"""

import uuid
from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from tools.knowledge_tool import get_kpi
from tools.simulation_tool import run_simulation
from tools.sql_tool import execute_sql


#: 관통 예제 기간. KPI sql_template 의 바인드 파라미터를 이 값으로 채운다.
PERIOD_FROM = "2026-09-01"
PERIOD_TO = "2026-09-30"


def _fill_period(sql_template: str) -> str:
    return (
        sql_template.replace(":from", f"'{PERIOD_FROM}'")
        .replace(":to", f"'{PERIOD_TO}'")
        .strip()
    )


async def run_fake_agent(
    message: str,
    conversation_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """고정된 시나리오로 AgentEvent 를 스트리밍한다."""

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "running", "label": "질의 분석"},
    )

    # 1) KPI 정의 확인 (kind: catalog)
    yield AgentEvent(type="tool_call", tool_name="get_kpi")
    kpi_result = await get_kpi(kpi_id="fgs_inbound")
    yield AgentEvent(type="tool_result", tool_name="get_kpi", data=kpi_result)
    yield AgentEvent(
        type="status",
        data={"step": "get_kpi", "status": "completed", "label": "KPI 정의 확인"},
    )

    # 2) 계획 대비 달성률 조회 (kind: database)
    sql_template = kpi_result.get("data", {}).get("sql_template", "")
    purpose = "계획 대비 입고 달성률"
    yield AgentEvent(type="tool_call", tool_name="execute_sql")
    sql_result = await execute_sql(sql=_fill_period(sql_template), purpose=purpose)
    yield AgentEvent(type="tool_result", tool_name="execute_sql", data=sql_result)
    yield AgentEvent(
        type="status",
        data={"step": "execute_sql", "status": "completed", "label": "계획 대비 달성률 조회"},
    )

    # 3) 첫 번째 가설: 확정 MP 가 바뀌었는가
    yield AgentEvent(type="tool_call", tool_name="run_simulation")
    sim_result = await run_simulation(simulation_type="MP_확정조회", params={})
    yield AgentEvent(type="tool_result", tool_name="run_simulation", data=sim_result)
    yield AgentEvent(
        type="status",
        data={"step": "run_simulation", "status": "completed", "label": "확정 MP 변경 확인"},
    )

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "completed", "label": "질의 분석"},
    )

    # 4) 사용자 답변 스트리밍
    row_count = sql_result.get("row_count", 0)
    for chunk in (
        f"{PERIOD_FROM}~{PERIOD_TO} 기간의 계획 대비 입고 달성률을 조회했습니다. ",
        f"일자·라인별 {row_count}건을 확인했고, 확정 MP 변경 여부도 함께 확인했습니다. ",
        "(Fake Runner 응답)",
    ):
        yield AgentEvent(type="text", content=chunk)

    # 실제 경로와 응답 형태를 맞춘다(편집/재생성이 참조하는 turn_id).
    # Fake Runner 는 진짜 SDK 세션이 없으므로 포크 자체는 지원하지 않는다 —
    # 매번 같은 고정 시나리오를 재생하므로 편집/재생성해도 결과가 달라지지 않는다.
    yield AgentEvent(type="done", data={"turn_id": str(uuid.uuid4())})
