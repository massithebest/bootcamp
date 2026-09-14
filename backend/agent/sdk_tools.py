"""Claude Agent SDK 용 Tool 등록 계층.

`tools/` 의 업무 함수를 그대로 재사용하고, Claude Agent SDK 가 인식할 수 있는
in-process MCP Tool 로 감싸는 역할만 담당한다.

- 업무 로직은 여기 두지 않는다. (tools/ + services/ 담당)
- SDK 종속 코드(@tool, create_sdk_mcp_server)는 이 모듈과 event_adapter 에 모은다.
"""

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.rag_tool import search_knowledge
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import query_database


MCP_SERVER_NAME = "planning"

#: SDK 가 노출하는 Tool 이름. `mcp__<server>__<tool>` 규칙을 따른다.
TOOL_NAMES = [
    f"mcp__{MCP_SERVER_NAME}__query_database",
    f"mcp__{MCP_SERVER_NAME}__search_knowledge",
    f"mcp__{MCP_SERVER_NAME}__list_simulation",
    f"mcp__{MCP_SERVER_NAME}__run_simulation",
]


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    """업무 결과 dict 를 SDK Tool 결과 형식으로 변환한다.

    Frontend 에서 표현할 구조화 결과는 JSON 문자열로 담아 전달하고,
    event_adapter 가 다시 dict 로 복원한다.
    """

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False),
            }
        ]
    }


@tool(
    "query_database",
    "생산 실적·재고·제품·설비/라인 등 구조화된 생산계획 데이터를 조회한다.",
    {"question": str},
)
async def _query_database(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await query_database(question=args["question"]))


@tool(
    "search_knowledge",
    "공정 매뉴얼·업무 용어·생산계획 정책 등 비정형 도메인 지식을 검색한다.",
    {"query": str},
)
async def _search_knowledge(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await search_knowledge(query=args["query"]))


@tool(
    "list_simulation",
    "사용 가능한 시뮬레이션 종류와 각 종류가 요구하는 파라미터 목록을 조회한다.",
    {},
)
async def _list_simulation(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await list_simulation())


@tool(
    "run_simulation",
    "지정한 simulation_type 을 params 로 실행한다. "
    "종류/파라미터를 모르면 list_simulation 을 먼저 호출한다.",
    {"simulation_type": str, "params": dict},
)
async def _run_simulation(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(
        await run_simulation(
            simulation_type=args["simulation_type"],
            params=args.get("params", {}),
        )
    )


def build_planning_mcp_server():
    """생산계획 Tool 을 담은 in-process MCP Server 를 생성한다."""

    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME,
        version="0.1.0",
        tools=[
            _query_database,
            _search_knowledge,
            _list_simulation,
            _run_simulation,
        ],
    )
