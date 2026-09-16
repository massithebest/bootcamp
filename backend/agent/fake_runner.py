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
from tools.table_tool import prepare_table
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
    kpi_call_id = "fake-get-kpi"
    yield AgentEvent(
        type="tool_call",
        tool_name="get_kpi",
        tool_call_id=kpi_call_id,
        data={"args": {"kpi_id": "initial_wip"}},
    )
    kpi_result = await get_kpi(kpi_id="initial_wip")
    yield AgentEvent(type="tool_result", tool_name="get_kpi", tool_call_id=kpi_call_id, data=kpi_result)
    yield AgentEvent(
        type="status",
        tool_name="get_kpi",
        tool_call_id=kpi_call_id,
        data={"step": kpi_call_id, "status": "completed", "label": "KPI 정의 확인"},
    )

    # 2) LVHM 제품별 초기 WIP 조회 (kind: database)
    sql_template = kpi_result.get("data", {}).get("sql_template", "")
    purpose = "LVHM 제품별 초기 WIP Lot과 piece 수"
    sql_call_id = "fake-execute-sql"
    sql = _fill_dataset(sql_template)
    yield AgentEvent(
        type="tool_call",
        tool_name="execute_sql",
        tool_call_id=sql_call_id,
        data={"args": {"sql": sql, "purpose": purpose}},
    )
    sql_result = await execute_sql(
        sql=sql, purpose=purpose, access_scope=access_scope
    )
    yield AgentEvent(type="tool_result", tool_name="execute_sql", tool_call_id=sql_call_id, data=sql_result)
    yield AgentEvent(
        type="status",
        tool_name="execute_sql",
        tool_call_id=sql_call_id,
        data={"step": sql_call_id, "status": "completed", "label": "제품별 초기 WIP 조회"},
    )

    # 3) 같은 DB를 사용하는 SMT2020 입력 관계 검증
    simulation_call_id = "fake-run-simulation"
    simulation_args = {"simulation_type": "SMT2020_입력검증", "params": {"dataset": DATASET}}
    yield AgentEvent(
        type="tool_call",
        tool_name="run_simulation",
        tool_call_id=simulation_call_id,
        data={"args": simulation_args},
    )
    sim_result = await run_simulation(
        simulation_type="SMT2020_입력검증",
        params={"dataset": DATASET},
        access_scope=access_scope,
    )
    yield AgentEvent(type="tool_result", tool_name="run_simulation", tool_call_id=simulation_call_id, data=sim_result)
    yield AgentEvent(
        type="status",
        tool_name="run_simulation",
        tool_call_id=simulation_call_id,
        data={"step": simulation_call_id, "status": "completed", "label": "SMT2020 입력 관계 검증"},
    )

    yield AgentEvent(
        type="status",
        data={"step": "plan", "status": "completed", "label": "질의 분석"},
    )

    row_count = sql_result.get("row_count", 0)
    unmatched = sum(
        int(check.get("unmatched_rows", 0))
        for check in sim_result.get("results", [])
        if isinstance(check, dict)
    )

    # 4) 표 도입 설명 다음에 제품별 WIP 결과를 독립적인 대화형 표로 준비.
    yield AgentEvent(
        type="text",
        content=f"SMT2020 {DATASET}의 제품별 초기 WIP {row_count}건을 표로 확인할 수 있습니다.",
    )
    table_call_id = "fake-prepare-table"
    table_args = {
        "result_id": sql_result.get("result_id", ""),
        "columns": ["part", "lot_count", "piece_count"],
        "title": "LVHM 제품별 초기 WIP",
    }
    yield AgentEvent(
        type="tool_call",
        tool_name="prepare_table",
        tool_call_id=table_call_id,
        data={"args": table_args},
    )
    table_result = await prepare_table(
        result_id=sql_result.get("result_id", ""),
        columns=table_args["columns"],
        title=table_args["title"],
        access_scope=access_scope,
    )
    yield AgentEvent(
        type="tool_result",
        tool_name="prepare_table",
        tool_call_id=table_call_id,
        data=table_result,
    )
    yield AgentEvent(
        type="status",
        tool_name="prepare_table",
        tool_call_id=table_call_id,
        data={
            "step": table_call_id,
            "status": "completed" if table_result.get("status") == "ok" else "error",
            "label": "제품별 WIP 표 준비",
        },
    )

    # 5) 표 해석과 차트 도입 설명 다음에 제품별 WIP Lot 수 bar chart 등록.
    yield AgentEvent(
        type="text",
        content=(
            f"표의 Part별 Lot·piece 수를 비교할 수 있으며, 입력 관계의 미연결 건수는 "
            f"{unmatched}건입니다. Lot 수의 제품별 차이는 다음 차트로 확인할 수 있습니다."
        ),
    )
    visualization_call_id = "fake-prepare-visualization"
    visualization_args = {
        "result_id": sql_result.get("result_id", ""),
        "kind": "bar",
        "x": "part",
        "y": ["lot_count"],
    }
    yield AgentEvent(
        type="tool_call",
        tool_name="prepare_visualization",
        tool_call_id=visualization_call_id,
        data={"args": visualization_args},
    )
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
        tool_call_id=visualization_call_id,
        data=visualization_result,
    )
    yield AgentEvent(
        type="status",
        tool_name="prepare_visualization",
        tool_call_id=visualization_call_id,
        data={
            "step": visualization_call_id,
            "status": "completed" if visualization_result.get("status") == "ok" else "error",
            "label": "제품별 WIP 차트 준비",
        },
    )

    # 6) 차트 해석과 검증 범위 설명을 스트리밍.
    for chunk in (
        "차트는 동일한 조회 결과의 Part별 Lot 수를 비교합니다. ",
        "이 입력 관계 검증은 실제 생산 완료량을 예측하는 이산사건 시뮬레이션이 아닙니다. ",
        "(Fake Runner 응답)",
    ):
        yield AgentEvent(type="text", content=chunk)
    # 실제 경로와 응답 형태를 맞춘다(편집/재생성이 참조하는 turn_id).
    # Fake Runner 는 진짜 SDK 세션이 없으므로 포크 자체는 지원하지 않는다 —
    # 매번 같은 고정 시나리오를 재생하므로 편집/재생성해도 결과가 달라지지 않는다.
    yield AgentEvent(type="done", data={"turn_id": str(uuid.uuid4())})
