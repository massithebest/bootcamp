"""Claude Agent SDK 용 Tool 등록 계층.

`tools/` 의 업무 함수를 그대로 재사용하고, Claude Agent SDK 가 인식할 수 있도록
in-process MCP 서버가 노출하는 Tool 로 감싸는 역할만 담당한다.

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
from services.results.present import (
    present_chart_input_schema,
    present_simulation_input_schema,
    present_sql_preview_input_schema,
    present_table_input_schema,
)
from tools.present_tool import (
    present_chart,
    present_simulation,
    present_sql_preview,
    present_table,
)
from tools.rag_tool import search_documents
from tools.result_tool import get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql
from tools.suggestion_tool import suggest_follow_ups, suggest_follow_ups_input_schema


MCP_SERVER_NAME = "planning"

#: 화면의 Tool 사용 기록에 표시하지 않고 `done.data.suggestions` 로만 전달하는 Tool.
SUGGESTION_TOOL_NAME = "suggest_follow_ups"



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
        "데이터베이스/DB에 저장된 계획·실적·제품 행과 수치를 카탈로그 등록 테이블에서 SELECT 로 조회한다. "
        "사용자가 DB/데이터베이스/SQL 조회를 명시한 경우 이 도구를 사용한다. "
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
    "공정 매뉴얼·업무 용어·생산계획 정책 등 비정형 도메인 지식을 검색한다. "
    "옵션·결과의 의미·화면 버튼·변경 위치·조회 방법을 설명할 때 사용한다. "
    "실제 저장 수치 조회나 simulation 실행을 대신하지 않는다.",
    {"query": str},
)
async def _search_documents(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await search_documents(query=args["query"]))


@tool(
    "list_simulation",
    "사용 가능한 시뮬레이션 종류와 별칭·사용 목적·입력 파라미터·출력 정의를 확인한다. "
    "자연어 요청에 맞는 등록 종류가 있는지 실행 전에 찾을 때 사용한다.",
    {},
)
async def _list_simulation(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await list_simulation())


def _run_simulation_tool(access_scope: str | None):
    @tool(
        "run_simulation",
        "사용자가 요청한 등록 simulation을 지정한 simulation_type 과 params 로 수행한다. "
        "종류/파라미터를 모르면 list_simulation 을 먼저 호출한다. "
        "적합한 등록 종류가 없으면 임의의 종류를 만들지 않는다.",
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


def _present_sql_preview_tool(access_scope: str | None):
    @tool(
        "present_sql_preview",
        "실행한 SQL 원문을 사용자에게 보여 준다(기본 접힘). "
        "sql에는 실제로 실행한 SQL을 그대로 넣는다.",
        present_sql_preview_input_schema(),
    )
    async def _present_sql_preview(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(await present_sql_preview(args, access_scope=access_scope))

    return _present_sql_preview


def _present_chart_tool(access_scope: str | None):
    @tool(
        "present_chart",
        "execute_sql·run_simulation이 반환한 result_id를 서버가 집계한 bar/line/area 차트로 "
        "보여준다. 행·차트 데이터는 넣지 않고 result_id와 표시 설정만 넣는다. "
        "추이·비교를 보여줄 때 쓴다. 막대 차트는 기본 grouped이며, 같은 단위의 합산 가능한 "
        "값을 group_by_column별 구성으로 비교할 때만 bar_mode=stacked를 지정한다. "
        "stacked는 chart_type=bar와 group_by_column이 필요하다. 필요하면 한 응답에서 여러 번 호출할 수 있다(예: 지표별로 "
        "따로 보여줄 때). 성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다. "
        "호출 뒤에는 '위/아래' 같은 위치 표현 대신 '차트에서는'처럼 결과를 해석한다.",
        present_chart_input_schema(),
    )
    async def _present_chart(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(await present_chart(args, access_scope=access_scope))

    return _present_chart


def _present_table_tool(access_scope: str | None):
    @tool(
        "present_table",
        "execute_sql·run_simulation이 반환한 result_id를 페이지 단위 표로 보여준다. "
        "행 데이터는 넣지 않고 result_id와 표시 설정만 넣는다. "
        "상세 행을 보여줄 때 쓴다. 필요하면 한 응답에서 여러 번 호출할 수 있다. "
        "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다. "
        "호출 뒤에는 '위/아래' 같은 위치 표현 대신 '표에는'처럼 결과를 해석한다.",
        present_table_input_schema(),
    )
    async def _present_table(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(await present_table(args, access_scope=access_scope))

    return _present_table


def _present_simulation_tool(access_scope: str | None):
    @tool(
        "present_simulation",
        "시뮬레이션 시나리오·요약·KPI를 보여준다. "
        "같은 결과의 차트·표를 함께 보여줘야 하면 같은 응답에서 present_chart·present_table을 "
        "result_id를 공유해 별도로 호출하고 텍스트로 그 연결을 설명한다. "
        "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다.",
        present_simulation_input_schema(),
    )
    async def _present_simulation(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(await present_simulation(args, access_scope=access_scope))

    return _present_simulation


@tool(
    SUGGESTION_TOOL_NAME,
    "최종 답변을 쓰기 직전에 사용자가 이어서 물어볼 만한 후속질문 2~4개를 등록한다. "
    "각 질문은 사용자가 그대로 보낼 수 있는 1~120자의 한국어 질문 문장으로 쓰고 서로 겹치지 않게 한다. "
    "조회 결과의 수치·결론을 질문에 미리 적지 않고, 이번 답변이나 앞선 대화에서 이미 다룬 내용은 "
    "다시 묻지 않는다. 화면에는 답변 뒤 선택지로만 표시된다.",
    suggest_follow_ups_input_schema(),
)
async def _suggest_follow_ups(args: dict[str, Any]) -> dict[str, Any]:
    return _ok(await suggest_follow_ups(args.get("questions")))


def planning_tools(access_scope: str | None = None):
    """Single source for SDK registration, allowed names and UI discovery.

    결과 표시 도구는 항상 present_sql_preview·present_chart·present_table·
    present_simulation을 등록한다.
    """
    return [
        _execute_sql_tool(access_scope), _search_documents, _list_simulation,
        _run_simulation_tool(access_scope), _list_tables, _describe_table,
        _list_kpis, _get_kpi, _list_recipes, _get_recipe,
        _get_result_summary_tool(access_scope), _get_result_page_tool(access_scope),
        _present_sql_preview_tool(access_scope),
        _present_chart_tool(access_scope),
        _present_table_tool(access_scope),
        _present_simulation_tool(access_scope),
        _suggest_follow_ups,
    ]


def tool_names() -> list[str]:
    return [f"mcp__{MCP_SERVER_NAME}__{item.name}" for item in planning_tools()]


TOOL_NAMES = tool_names()


def build_planning_mcp_server(access_scope: str | None = None):
    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME, version="0.1.0", tools=planning_tools(access_scope),
    )


async def tool_catalog() -> list[dict]:
    # Read the SDK's actual advertised schema, including TypedDict optional fields.
    from mcp_types import PaginatedRequestParams
    server = build_planning_mcp_server()["instance"]
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
        "present_sql_preview": "SQL 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        "present_chart": "차트 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        "present_table": "표 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        "present_simulation": "시뮬레이션 요약 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        SUGGESTION_TOOL_NAME: "후속질문 검증 결과(화면에는 답변 뒤 선택지로만 표시)",
    }
    return [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema,
             "output": output[t.name], "status": "available"} for t in result.tools]
