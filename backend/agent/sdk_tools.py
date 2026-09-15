"""Claude Agent SDK 용 Tool 등록 계층.

`tools/` 의 업무 함수를 그대로 재사용하고, Claude Agent SDK 가 인식할 수 있는
in-process MCP Tool 로 감싸는 역할만 담당한다.

- 업무 로직은 여기 두지 않는다. (tools/ + services/ 담당)
- SDK 종속 코드(@tool, create_sdk_mcp_server)는 이 모듈과 event_adapter 에 모은다.
"""

import json
from typing import Any, NotRequired, TypedDict

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.knowledge_tool import (
    describe_table,
    get_kpi,
    get_recipe,
    list_kpis,
    list_recipes,
    list_tables,
)
from tools.rag_tool import search_knowledge
from tools.result_tool import get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql
from tools.visualization_tool import prepare_visualization


MCP_SERVER_NAME = "planning"

#: SDK 가 노출하는 Tool 이름. `mcp__<server>__<tool>` 규칙을 따른다.
TOOL_NAMES = [
    f"mcp__{MCP_SERVER_NAME}__execute_sql",
    f"mcp__{MCP_SERVER_NAME}__search_knowledge",
    f"mcp__{MCP_SERVER_NAME}__list_simulation",
    f"mcp__{MCP_SERVER_NAME}__run_simulation",
    f"mcp__{MCP_SERVER_NAME}__list_tables",
    f"mcp__{MCP_SERVER_NAME}__describe_table",
    f"mcp__{MCP_SERVER_NAME}__list_kpis",
    f"mcp__{MCP_SERVER_NAME}__get_kpi",
    f"mcp__{MCP_SERVER_NAME}__list_recipes",
    f"mcp__{MCP_SERVER_NAME}__get_recipe",
    f"mcp__{MCP_SERVER_NAME}__get_result_summary",
    f"mcp__{MCP_SERVER_NAME}__get_result_page",
    f"mcp__{MCP_SERVER_NAME}__prepare_visualization",
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


def _execute_sql_tool(access_scope: str | None):
    @tool(
        "execute_sql",
        "카탈로그에 등록된 테이블을 SELECT 로 조회한다. "
        "테이블·컬럼은 describe_table 로 먼저 확인한다. "
        "purpose 에는 이 쿼리로 확인하려는 것을 한 줄로 쓴다.",
        {"sql": str, "purpose": str},
    )
    async def _execute_sql(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(
            await execute_sql(
                sql=args["sql"],
                purpose=args.get("purpose", ""),
                access_scope=access_scope,
            )
        )

    return _execute_sql


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


def _run_simulation_tool(access_scope: str | None):
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
                access_scope=access_scope,
            )
        )

    return _run_simulation


@tool(
    "list_tables",
    "조회 가능한 테이블 목록을 요약으로 돌려준다. "
    "keyword(테이블명·설명·태그·컬럼명 부분일치) 나 tag 로 좁힐 수 있다.",
    {"keyword": str, "tag": str},
)
async def _list_tables(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await list_tables(keyword=args.get("keyword"), tag=args.get("tag")))


@tool(
    "describe_table",
    "테이블 하나의 컬럼·키·조인·코드값·주의사항·집계 가이드를 조회한다. "
    "SQL 을 작성하기 전에 반드시 호출한다.",
    {"table": str},
)
async def _describe_table(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await describe_table(table=args["table"]))


@tool(
    "list_kpis",
    "정의된 KPI 목록을 조회한다. keyword 로 이름·별칭·정의를 부분일치 검색한다.",
    {"keyword": str},
)
async def _list_kpis(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await list_kpis(keyword=args.get("keyword")))


@tool(
    "get_kpi",
    "KPI 하나의 정의·공식·원천 테이블·비교 기준·부진 판정 규칙·"
    "집계 가이드·레시피 참조·SQL 템플릿·원인 후보(diagnostics)를 조회한다.",
    {"kpi_id": str},
)
async def _get_kpi(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await get_kpi(kpi_id=args["kpi_id"]))


@tool(
    "list_recipes",
    "자주 쓰는 집계·조인 패턴을 담은 재사용 CTE 목록을 조회한다. "
    "keyword 로 이름·설명·적용 목적을 부분일치 검색한다.",
    {"keyword": str},
)
async def _list_recipes(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await list_recipes(keyword=args.get("keyword")))


@tool(
    "get_recipe",
    "레시피의 적용 목적·출력 단위·컬럼 의미·집계 가이드·표현 힌트·CTE SQL·샘플을 조회한다. "
    "cte_sql 을 WITH 절로 복사해 execute_sql 에 조합해 쓴다 (자동 치환 없음).",
    {"recipe_id": str},
)
async def _get_recipe(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await get_recipe(recipe_id=args["recipe_id"]))


def _get_result_summary_tool(access_scope: str | None):
    @tool(
        "get_result_summary",
        "저장된 대용량 조회 결과의 메타데이터와 숫자 컬럼 요약 통계를 확인한다.",
        {"result_id": str},
    )
    async def _get_result_summary(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(
            await get_result_summary(
                result_id=args["result_id"], access_scope=access_scope
            )
        )

    return _get_result_summary


def _get_result_page_tool(access_scope: str | None):
    @tool(
        "get_result_page",
        "저장된 대용량 조회 결과에서 직접 확인할 특정 구간의 행을 조회한다.",
        {"result_id": str, "offset": int, "limit": int},
    )
    async def _get_result_page(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(
            await get_result_page(
                result_id=args["result_id"],
                offset=args["offset"],
                limit=args["limit"],
                access_scope=access_scope,
            )
        )

    return _get_result_page


class _PrepareVisualizationInput(TypedDict):
    result_id: str
    kind: str
    x: str
    y: list[str]
    group_by: NotRequired[str]


def _prepare_visualization_tool(access_scope: str | None):
    @tool(
        "prepare_visualization",
        "저장된 집계 결과의 실제 컬럼과 grain을 검증하고 bar/line 시각화를 등록한다. "
        "집계 SQL이나 data 배열은 받지 않는다.",
        _PrepareVisualizationInput,
    )
    async def _prepare_visualization(args: _PrepareVisualizationInput) -> dict[str, Any]:
        return _ok(
            await prepare_visualization(
                result_id=args["result_id"],
                kind=args["kind"],
                x=args["x"],
                y=args["y"],
                group_by=args.get("group_by"),
                access_scope=access_scope,
            )
        )

    return _prepare_visualization


def build_planning_mcp_server(access_scope: str | None = None):
    """생산계획 Tool 을 담은 in-process MCP Server 를 생성한다.

    `access_scope`는 요청 브라우저 세션의 불투명 scope다(§6.1). 모델
    입력 스키마에는 노출하지 않고, scope가 필요한 tool은 이 값을 클로저로
    감싼 wrapper를 매 요청마다 새로 만들어 등록한다.
    """

    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME,
        version="0.1.0",
        tools=[
            _execute_sql_tool(access_scope),
            _search_knowledge,
            _list_simulation,
            _run_simulation_tool(access_scope),
            _list_tables,
            _describe_table,
            _list_kpis,
            _get_kpi,
            _list_recipes,
            _get_recipe,
            _get_result_summary_tool(access_scope),
            _get_result_page_tool(access_scope),
            _prepare_visualization_tool(access_scope),
        ],
    )
