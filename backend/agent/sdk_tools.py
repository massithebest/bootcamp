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


def sql_dialect_note() -> str:
    """현재 SQL 서비스의 방언 안내. 방언을 모르면 빈 문자열."""

    from services import sql_service

    dialect = getattr(sql_service, "SQL_DIALECT", "")
    if not dialect:
        return ""
    note = (
        f"이 DB의 SQL 방언은 {dialect}이다. 함수·날짜 문법은 {dialect}에 맞게 쓰고, 카탈로그 규칙에 다른 DB "
        f"함수(예: NVL)가 적혀 있으면 {dialect}의 같은 기능 함수로 바꿔 쓴다. 날짜 함수를 쓰기 전에 describe_table 의 "
        f"컬럼 설명에서 저장 형식(예: YYYYMMDD 문자열)을 확인한다. "
    )
    if dialect.lower() == "sqlite":
        note += (
            "예: NVL→COALESCE. 오늘 연월은 서버 현지 시간 기준 strftime('%Y%m', 'now', 'localtime')('now' 만 쓰면 UTC). strftime·date 는 'YYYY-MM-DD' 형식에만 동작하고 "
            "YYYYMMDD 문자열에는 NULL 을 돌려주므로, 그런 컬럼의 연월은 substr(컬럼, 1, 6)으로 구하거나 연월 컬럼을 쓴다. "
        )
    return note


def _execute_sql_tool(access_scope: str | None):
    @tool(
        "execute_sql",
        "데이터베이스/DB에 저장된 계획·실적·제품 행과 수치를 카탈로그 등록 테이블에서 SELECT 로 조회한다. "
        + sql_dialect_note() +
        "사용자가 DB/데이터베이스/SQL 조회를 명시한 경우 이 도구를 사용한다. "
        "테이블·컬럼은 describe_table 로 먼저 확인한다. 테이블·컬럼 구조는 describe_table 로만 확인하며, "
        "DB 시스템 테이블·메타데이터(pragma, sqlite_master, information_schema 등)는 조회할 수 없다. "
        "1:N 관계(예: Part 1개에 Route Step 여러 행)를 조인한 뒤 SUM·COUNT 하면 1쪽 수량이 N배로 부풀어 오른다. "
        "grain 이 다른 테이블의 수치는 각 테이블에서 먼저 집계(CTE·서브쿼리)한 뒤 공통 키로 결합하고, "
        "등록된 집계 레시피가 있으면 활용한다. "
        "purpose 에는 이 쿼리로 확인하려는 것을 한 줄로 쓴다. "
        "표·차트로 보여 줄 결과는 컬럼 이름이 그대로 표 머리글·차트 축·범례가 되므로 "
        "SELECT 컬럼마다 한국어 별칭(예: FAC_ID AS \"공장\", SUM(PLAN_QTY) AS \"계획수량\")을 붙이고, "
        "범례·x축으로 쓸 년월 코드(예: 202605)는 '2026-05'처럼 읽을 수 있는 값으로 만든다. "
        "답변에 적용 조건을 밝힐 때는 SQL 식(PLAN_QTY > 0, IS NULL, <> 등)이 아니라 "
        "'계획수량이 0보다 큰 행'처럼 말로 쓴다. "
        "반환된 result_id 는 present_*·결과 조회 Tool 인자로만 쓰고 답변 본문에 적지 않는다. "
        "결과 요약 필드 이름(row_count·distinct_counts·top_groups 등)도 답변에 쓰지 않고 "
        "'고유 Part 10개'처럼 풀어 쓴다. "
        "조건을 건 조회가 0행이면 조건 없이 그 기간·대상의 행이 있는지 확인해, 데이터 자체가 없으면 "
        "'조건에 맞는 항목이 없다'가 아니라 '해당 기간 데이터가 없다'고 먼저 밝힌다. 다른 기간의 건수를 함께 "
        "보여 줄 때는 무엇을 센 값인지(예: 실적이 없는 계획 수, 전체 계획 행 수) 밝힌다.",
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
    "실제 저장 수치 조회나 simulation 실행을 대신하지 않는다. "
    "결과에 그 용어를 직접 정의한 문서가 없으면 일반 지식으로 정의를 만들지 말고 찾지 못했다고 먼저 밝힌다. "
    "이때 사용자에게 뜻을 되묻기 전에 그 용어를 keyword 로 list_tables 를 호출해 테이블·컬럼 정의에 근거가 "
    "있는지 확인하고, 있으면 describe_table 의 컬럼 설명을 출처와 함께 제시한다. 검색어는 답변에 적지 않는다. "
    "프로세스·절차·흐름을 물었는데 그 절차를 직접 설명한 문서가 없으면 개별 용어 문서를 이어 붙여 흐름을 만들지 말고, "
    "찾지 못했다고 밝힌 뒤 관련 문서 이름만 출처와 함께 나열하고 멈춘다.",
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
        "적합한 등록 종류가 없으면 임의의 종류를 만들지 않는다. "
        "결과를 표로 보여 줬다면 답변 근거에 표의 행을 한 줄씩 다시 적지 말고, 검증 결과는 문제(미일치 등)가 "
        "있는 항목만 짚는다. 모두 통과했으면 '5개 관계 모두 미일치 0건'처럼 한 문장으로 요약한다. "
        "params 의 이름·값(예: view=swapped)은 답변에 그대로 쓰지 말고 'swap이 발생한 행만'처럼 풀어 쓴다.",
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
    "두 필터는 모두 생략할 수 있다. 키워드는 공백으로 나눈 단어 중 하나라도 맞으면 찾는다. "
    "결과가 0건이면 테이블이 없다고 단정하지 말고 필터 없이 다시 호출해 전체 목록을 보고 판단한다.",
    _ListTablesInput,
)
async def _list_tables(args: _ListTablesInput) -> dict[str, Any]:
    return _ok(await list_tables(keyword=args.get("keyword"), tag=args.get("tag")))


@tool(
    "describe_table",
    "테이블 하나의 컬럼·키·조인·코드값·주의사항·조회 규칙·집계 가이드·"
    "시각화 안내와 질문·SQL 예시를 조회한다. "
    "SQL 을 작성하기 전에 반드시 호출한다. "
    "질문의 기준(예: '세그먼트별')이 이 테이블의 컬럼·코드값에 없으면 비슷한 컬럼으로 가정해 조회하지 말고, "
    "후보 컬럼(이름과 의미)을 들어 어느 기준인지 묻고 멈춘다. "
    "요청한 정보를 담은 컬럼이 어느 테이블에도 없으면 일반 지식으로 후보를 만들어 선택지로 내지 말고, "
    "등록된 데이터가 없다고 밝힌 뒤 그 정보를 관리하는 테이블·화면 이름을 알려 달라고만 한다. "
    "결과의 verified 가 false 이면 답변에 '아직 검토되지 않은 테이블 정의 기준'처럼 풀어 쓰고 "
    "verified 같은 필드 이름은 쓰지 않는다.",
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
    "집계 가이드·레시피 참조·SQL 템플릿·원인 후보(diagnostics)를 조회한다. "
    "답변에서는 kpi_id 대신 결과의 name 으로 부른다.",
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
    "cte_sql 을 WITH 절로 복사해 execute_sql 에 조합해 쓴다 (자동 치환 없음). "
    "답변에서는 recipe_id 대신 결과의 name 으로 부른다.",
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
        "stacked는 chart_type=bar와 group_by_column이 필요하다. "
        "계획·실적처럼 사용자가 비교를 요청한 여러 지표는 지표마다 차트를 나누지 않고 한 차트에 묶는다: "
        "SQL을 지표 이름 컬럼(예: 지표)과 값 컬럼(예: 수량)의 long 형식으로 조회한 뒤 "
        "y_column=값 컬럼, group_by_column=지표 이름 컬럼으로 한 번 호출한다. "
        "모든 행이 같은 값인 컬럼(예: 조회 월)은 group_by_column으로 쓰지 않는다. "
        "차트는 x_column·group_by_column 외의 행을 aggregation으로 합치므로, 지표 이름 컬럼(지표)을 "
        "그 둘 중 하나로 쓰지 않으면 서로 다른 지표가 더해진다(서버가 오류로 거부한다). "
        "차트의 '표로 보기'로 값을 볼 수 있으므로 같은 result_id로 present_table을 또 호출하지 않는다"
        "(사용자가 표도 요청했거나 차트에 없는 컬럼을 보여 줘야 할 때만 더한다). "
        "Lot 수와 수량처럼 단위가 다른 지표는 한 차트에 묶지 말고 SQL에서 지표 하나만 남겨 지표별로 따로 호출한다. "
        "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다. "
        "호출 뒤에는 '위/아래' 같은 위치 표현 대신 '차트에서는'처럼 결과를 해석한다. "
        "결론 문장에는 핵심 수치(합계·비율·최대·최소)를 직접 쓰고 최대·최소 값에는 그 대상도 함께 쓴다. '차트로 보여드렸습니다' 같은 결론은 쓰지 않는다. "
        "차트에 나온 대상별 값을 근거에서 다시 나열하지 않는다('계산에 사용한 값은 다음과 같습니다'도 같다).",
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
        "호출 뒤에는 '위/아래' 같은 위치 표현 대신 '표에는'처럼 결과를 해석한다. "
        "결론 문장에는 핵심 수치(합계·비율·최대·최소)를 직접 쓰고 최대·최소 값에는 그 대상도 함께 쓴다. '표로 보여드렸습니다' 같은 결론은 쓰지 않는다. "
        "같은 result_id를 present_chart로 이미 보여 줬으면 사용자가 표를 요청하지 않는 한 호출하지 않는다. "
        "표의 행을 본문에 한 줄씩 다시 나열하지 않고('계산에 사용한 값은 다음과 같습니다'도 같다), 결과 컬럼 이름·영문 코드 값(예: source_rows, "
        "part_to_route_step)은 지식에 적힌 한국어 뜻으로 풀어 쓴다.",
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
    "다시 묻지 않는다. 각 질문은 답변에 없던 새 기준(다른 기간·지표·세부 대상·비율 같은 파생 값)을 하나 이상 "
    "더하고, 같은 결과를 정렬 순서만 바꾸거나 '설명해 주세요'·'정리해 주세요'로 다시 묻지 않는다. "
    "'~ 기준으로 정렬해줘', '상위 N개만 보여줘'처럼 방금 보여 준 표를 다시 정렬·잘라 보는 질문도 같은 결과이므로 "
    "내지 않는다(특히 결과가 몇 행뿐이거나 정렬 기준 값이 모두 같을 때). "
    "describe_table 의 caveats 에 어긋나는 질문도 내지 않는다. 예: SEG_A·SEG_B는 같은 Part ID라도 다른 제품이므로 "
    "'Part별 차이'처럼 ID를 짝지은 세그먼트 비교 대신 세그먼트 전체 합계·분포 비교로 묻는다. "
    "'특정 제품'처럼 대상을 비워 두지 말고 결과에 나온 실제 대상(예: PROD_0001)이나 "
    "기준을 넣어, 누르면 확인 질문 없이 바로 답할 수 있게 쓴다. 화면에는 답변 뒤 선택지로 표시되므로, 답변 본문에는 '원하시면 ~해 드리겠습니다' "
    "같은 추가 제안 문장을 쓰지 않는다.",
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
