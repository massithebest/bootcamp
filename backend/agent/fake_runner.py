"""네트워크 없이 AgentEvent 흐름을 재현하는 Fake Runner.

`PLANNING_AGENT_FAKE=1` 일 때 `run_agent` 가 이 구현으로 대체된다.
Claude 모델은 호출하지 않고, Mock Service 를 실제로 거쳐 전체 이벤트
계약(text / status / tool_call / tool_result / done)을 검증할 수 있게 한다.

이벤트 순서는 SMT2020 관통 예제(KPI 확인 → 초기 WIP 조회 → 입력 관계 검증)를
따른다 — 프론트가 catalog/database/simulation 결과를 모두 받아본다.
"""

import uuid
from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from tools.knowledge_tool import get_kpi
from tools.simulation_tool import run_simulation
from tools.sql_tool import execute_sql
from tools.visualization_tool import prepare_visualization


DATASET = "LVHM"


def _fill_dataset(sql_template: str) -> str:
    return sql_template.replace(":dataset", f"'{DATASET}'").strip()


async def run_fake_agent(
    message: str,
    conversation_id: str | None = None,
    access_scope: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """고정된 시나리오로 AgentEvent 를 스트리밍한다."""

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "running", "label": "질의 분석"},
    )

    # 1) KPI 정의 확인 (kind: catalog)
    yield AgentEvent(type="tool_call", tool_name="get_kpi")
    kpi_result = await get_kpi(kpi_id="initial_wip")
    yield AgentEvent(type="tool_result", tool_name="get_kpi", data=kpi_result)
    yield AgentEvent(
        type="status",
        data={"step": "get_kpi", "status": "completed", "label": "KPI 정의 확인"},
    )

    # 2) LVHM 제품별 초기 WIP 조회 (kind: database)
    sql_template = kpi_result.get("data", {}).get("sql_template", "")
    purpose = "LVHM 제품별 초기 WIP Lot과 piece 수"
    yield AgentEvent(type="tool_call", tool_name="execute_sql")
    sql_result = await execute_sql(
        sql=_fill_dataset(sql_template), purpose=purpose, access_scope=access_scope
    )
    yield AgentEvent(type="tool_result", tool_name="execute_sql", data=sql_result)
    yield AgentEvent(
        type="status",
        data={"step": "execute_sql", "status": "completed", "label": "제품별 초기 WIP 조회"},
    )

    # 3) 같은 DB를 사용하는 SMT2020 입력 관계 검증
    yield AgentEvent(type="tool_call", tool_name="run_simulation")
    sim_result = await run_simulation(
        simulation_type="SMT2020_입력검증",
        params={"dataset": DATASET},
        access_scope=access_scope,
    )
    yield AgentEvent(type="tool_result", tool_name="run_simulation", data=sim_result)
    yield AgentEvent(
        type="status",
        data={"step": "run_simulation", "status": "completed", "label": "SMT2020 입력 관계 검증"},
    )

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "completed", "label": "질의 분석"},
    )

    # 4) 제품별 WIP Lot 수 bar chart 등록.
    yield AgentEvent(type="tool_call", tool_name="prepare_visualization")
    visualization_result = await prepare_visualization(
        result_id=sql_result.get("result_id", ""),
        kind="bar",
        x="part",
        y=["lot_count"],
        access_scope=access_scope,
    )
    yield AgentEvent(
        type="tool_result",
        tool_name="prepare_visualization",
        data=visualization_result,
    )
    yield AgentEvent(
        type="status",
        data={
            "step": "prepare_visualization",
            "status": "completed" if visualization_result.get("status") == "ok" else "error",
            "label": "제품별 WIP 차트 준비",
        },
    )

    # 5) 사용자 답변 스트리밍
    row_count = sql_result.get("row_count", 0)
    unmatched = sum(
        int(check.get("unmatched_rows", 0))
        for check in sim_result.get("results", [])
        if isinstance(check, dict)
    )
    for chunk in (
        f"SMT2020 {DATASET}의 제품별 초기 WIP를 조회했습니다. ",
        f"Part별 {row_count}건을 확인했고, 입력 관계의 미연결 건수는 {unmatched}건입니다. ",
        "이 검증은 실제 생산 완료량을 예측하는 이산사건 시뮬레이션이 아닙니다. ",
        "(Fake Runner 응답)",
    ):
        yield AgentEvent(type="text", content=chunk)
    visualization_id = visualization_result.get("visualization_id")
    if visualization_result.get("status") == "ok" and isinstance(visualization_id, str):
        yield AgentEvent(
            type="text",
            content=(
                "\n\n```chart\n"
                f'{{"visualization_id":"{visualization_id}"}}'
                "\n```"
            ),
        )

    # 실제 경로와 응답 형태를 맞춘다(편집/재생성이 참조하는 turn_id).
    # Fake Runner 는 진짜 SDK 세션이 없으므로 포크 자체는 지원하지 않는다 —
    # 매번 같은 고정 시나리오를 재생하므로 편집/재생성해도 결과가 달라지지 않는다.
    yield AgentEvent(type="done", data={"turn_id": str(uuid.uuid4())})
