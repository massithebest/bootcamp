"""Claude Agent SDK 용 Tool 등록 계층.

`tools/` 의 업무 함수를 그대로 재사용하고, Claude Agent SDK 가 인식할 수 있도록
in-process MCP 서버가 노출하는 Tool 로 감싸는 역할만 담당한다.

- 업무 로직은 여기 두지 않는다. (tools/ + services/ 담당)
- SDK 종속 코드(@tool, create_sdk_mcp_server)는 이 모듈과 event_adapter 에 모은다.
"""

import json
from typing import Any, NotRequired, TypedDict

from claude_agent_sdk import create_sdk_mcp_server, tool

from core.config import result_ui_mode
from tools.knowledge_tool import (
    describe_table,
    get_kpi,
    get_recipe,
    list_kpis,
    list_recipes,
    list_tables,
)
from services.present_service import PresentError, decode_present_input, present_input_schema
from tools.present_tool import present
from tools.rag_tool import search_documents
from tools.result_tool import get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql
from tools.table_tool import prepare_table
from tools.visualization_tool import prepare_visualization


MCP_SERVER_NAME = "planning"



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
    "search_documents",
    "공정 매뉴얼·업무 용어·생산계획 정책 등 비정형 도메인 지식을 검색한다.",
    {"query": str},
)
async def _search_documents(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await search_documents(query=args["query"]))


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


class _ListTablesInput(TypedDict):
    keyword: NotRequired[str]
    tag: NotRequired[str]


@tool(
    "list_tables",
    "조회 가능한 테이블 목록을 요약으로 돌려준다. "
    "keyword(테이블명·설명·태그·컬럼명 부분일치) 나 tag 로 좁힐 수 있으며 "
    "두 필터는 모두 생략할 수 있다.",
    _ListTablesInput,
)
async def _list_tables(args: _ListTablesInput) -> dict[str, Any]:
    return _ok(await list_tables(keyword=args.get("keyword"), tag=args.get("tag")))


@tool(
    "describe_table",
    "테이블 하나의 컬럼·키·조인·코드값·주의사항·조회 규칙·집계 가이드·"
    "시각화 안내와 질문·SQL 예시를 조회한다. "
    "SQL 을 작성하기 전에 반드시 호출한다.",
    {"table": str},
)
async def _describe_table(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await describe_table(table=args["table"]))


class _OptionalKeywordInput(TypedDict):
    keyword: NotRequired[str]


@tool(
    "list_kpis",
    "정의된 KPI 목록을 조회한다. 생략 가능한 keyword 로 이름·별칭·정의를 부분일치 검색한다.",
    _OptionalKeywordInput,
)
async def _list_kpis(args: _OptionalKeywordInput) -> dict[str, Any]:
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
    "생략 가능한 keyword 로 이름·설명·적용 목적을 부분일치 검색한다.",
    _OptionalKeywordInput,
)
async def _list_recipes(args: _OptionalKeywordInput) -> dict[str, Any]:
    return _ok(await list_recipes(keyword=args.get("keyword")))


@tool(
    "get_recipe",
    "레시피의 적용 목적·출력 단위·컬럼 의미·조회 규칙·집계 가이드·표현 힌트·"
    "CTE SQL과 질문·SQL 예시를 조회한다. "
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


class _PrepareTableInput(TypedDict):
    result_id: str
    columns: NotRequired[list[str]]
    title: NotRequired[str]


def _prepare_table_tool(access_scope: str | None):
    @tool(
        "prepare_table",
        "사용자가 표를 요청했거나 조회 결과의 행을 표로 제시할 때 반드시 호출한다. "
        "저장된 조회 결과를 현재 응답의 standalone 대화형 표로 준비하며 원본 행 배열은 받지 않는다. "
        "화면에는 최대 100행을 제공하고 같은 데이터를 Markdown 표로 반복하지 않는다. "
        "호출 뒤에는 '위/아래/다음 표' 같은 위치 표현 대신 '표에는'처럼 결과를 해석한다.",
        _PrepareTableInput,
    )
    async def _prepare_table(args: _PrepareTableInput) -> dict[str, Any]:
        return _ok(
            await prepare_table(
                result_id=args["result_id"],
                columns=args.get("columns"),
                title=args.get("title"),
                access_scope=access_scope,
            )
        )

    return _prepare_table


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
        "집계 SQL이나 data 배열은 받지 않는다. 호출 뒤에는 '위/아래/다음 차트' 같은 "
        "위치 표현 대신 '차트에서는'처럼 결과를 해석한다.",
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


def _present_tool(access_scope: str | None):
    @tool(
        "present",
        "SQL·시뮬레이션 결과를 사용자에게 보여 줄 UI 트리를 조합한다. "
        "tree 필드에 root UI node 하나를 JSON 문자열로 직렬화해 넣는다. "
        "문자열 안의 각 node는 $type으로 종류를 지정하고 children으로 중첩한다. "
        "execute_sql·run_simulation이 반환한 result_id와 표시 설정만 넣고 행·차트 데이터는 넣지 않는다. "
        "SQL은 SqlPreview, 추이·비교는 QueryChart, 상세 행은 QueryTable, 시뮬레이션은 SimulationSummary를 쓴다. "
        "한 응답에서 조합 UI는 한 번 호출하고, 성공한 결과를 Markdown 표나 코드 펜스로 반복하지 않는다. "
        "호출 뒤에는 '위/아래' 같은 위치 표현 대신 '표에는', '차트에서는'처럼 결과를 해석한다.",
        present_input_schema(),
    )
    async def _present(args: dict[str, Any]) -> dict[str, Any]:
        try:
            node = decode_present_input(args)
        except PresentError as exc:
            return _ok(exc.as_tool_result())
        return _ok(await present(node, access_scope=access_scope))

    return _present


def planning_tools(access_scope: str | None = None, mode: str | None = None):
    """Single source for SDK registration, allowed names and UI discovery.

    `RESULT_UI_MODE`가 결과 표시 도구를 정한다: legacy는 prepare_table·
    prepare_visualization, present는 present를 등록한다.
    """
    mode = mode or result_ui_mode()
    common = [
        _execute_sql_tool(access_scope), _search_documents, _list_simulation,
        _run_simulation_tool(access_scope), _list_tables, _describe_table,
        _list_kpis, _get_kpi, _list_recipes, _get_recipe,
        _get_result_summary_tool(access_scope), _get_result_page_tool(access_scope),
    ]
    if mode == "present":
        return [*common, _present_tool(access_scope)]
    return [
        *common, _prepare_table_tool(access_scope), _prepare_visualization_tool(access_scope),
    ]


def tool_names(mode: str | None = None) -> list[str]:
    return [f"mcp__{MCP_SERVER_NAME}__{item.name}" for item in planning_tools(mode=mode)]


TOOL_NAMES = tool_names()


def build_planning_mcp_server(access_scope: str | None = None, mode: str | None = None):
    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME, version="0.1.0", tools=planning_tools(access_scope, mode),
    )


async def tool_catalog(mode: str | None = None) -> list[dict]:
    # Read the SDK's actual advertised schema, including TypedDict optional fields.
    from mcp_types import PaginatedRequestParams
    server = build_planning_mcp_server(mode=mode)["instance"]
    result = await server._request_handlers["tools/list"].handler(None, PaginatedRequestParams())
    output = {
        "execute_sql": "조회 행·컬럼 또는 대용량 결과 참조",
        "search_documents": "검색 문서 발췌·출처·검토 버전",
        "list_simulation": "시뮬레이션 종류·입력·출력 정의",
        "run_simulation": "시뮬레이션 결과와 검증 상태",
        "list_tables": "테이블 이름·설명 목록", "describe_table": "컬럼·조인·조회·집계 규칙",
        "list_kpis": "KPI 요약 목록", "get_kpi": "KPI 공식·진단·SQL 정의",
        "list_recipes": "집계 recipe 요약 목록", "get_recipe": "CTE·출력 grain·사용 예시",
        "get_result_summary": "저장 결과 메타데이터·수치 요약", "get_result_page": "저장 결과의 일부 행",
        "prepare_table": "최대 100행의 대화형 표", "prepare_visualization": "검증된 bar/line 차트 ID",
        "present": "조합 UI 트리 검증 결과(빈 객체 또는 안전한 오류)",
    }
    return [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema,
             "output": output[t.name], "status": "available"} for t in result.tools]
