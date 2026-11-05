"""실행부 중립 Tool 명세.

Tool 이름·설명·입력 JSON schema·handler·화면 노출 여부를 한 목록으로 둔다.
Claude 실행부(`agent/sdk_tools.py`)와 다른 실행부가 이 목록에서 각자의 Tool 형식을
만들므로, 설명과 schema 는 이곳에만 쓴다.

- 업무 로직은 여기 두지 않는다. (tools/ + services/ 담당)
- `access_scope`는 handler 인자로만 받고 모델 입력 schema 에는 넣지 않는다.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from services.results.aggregate import aggregate_input_schema
from services.results.present import (
    present_chart_input_schema,
    present_simulation_input_schema,
    present_sql_preview_input_schema,
    present_table_input_schema,
)
from tools.knowledge_tool import (
    describe_table,
    get_kpi,
    get_recipe,
    list_kpis,
    list_recipes,
    list_tables,
)
from tools.present_tool import (
    present_chart,
    present_simulation,
    present_sql_preview,
    present_table,
)
from tools.rag_tool import search_documents
from tools.result_tool import aggregate_result, get_result_page, get_result_summary
from tools.simulation_tool import list_simulation, run_simulation
from tools.sql_tool import execute_sql
from tools.suggestion_tool import suggest_follow_ups, suggest_follow_ups_input_schema


#: 화면의 Tool 사용 기록에 표시하지 않고 `done.data.suggestions` 로만 전달하는 Tool.
SUGGESTION_TOOL_NAME = "suggest_follow_ups"

ToolHandler = Callable[[dict[str, Any], str | None], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    """Tool 하나의 실행부 중립 명세.

    `handler(args, access_scope)`는 업무 결과 dict 를 돌려준다. 실행부별 결과 형식
    변환은 각 실행부의 등록 계층이 맡는다. `output`은 Tool 목록 화면의 출력 설명이고,
    `visible`이 False 인 Tool 은 화면 Tool 사용 기록에 내보내지 않는다.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    output: str
    visible: bool = True


def _object_schema(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required is not None:
        schema["required"] = required
    return schema


_STRING = {"type": "string"}
_INTEGER = {"type": "integer"}
_OBJECT = {"type": "object"}


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


def _execute_sql_description() -> str:
    return (
        "데이터베이스/DB에 저장된 계획·실적·제품 행과 수치를 카탈로그 등록 테이블에서 SELECT 로 조회한다. "
        + sql_dialect_note() +
        "사용자가 DB/데이터베이스/SQL 조회를 명시한 경우 이 도구를 사용한다. "
        "테이블·컬럼 구조는 SQL 작성 전에 describe_table 로만 확인하며, DB 시스템 테이블·메타데이터(pragma, sqlite_master, information_schema 등)는 조회할 수 없다. "
        "1:N 관계(예: Part 1개에 Route Step 여러 행)를 조인한 뒤 SUM·COUNT 하면 1쪽 수량이 N배로 부풀어 오른다. "
        "grain 이 다른 테이블의 수치는 각 테이블에서 먼저 집계(CTE·서브쿼리)한 뒤 공통 키로 결합하고, 등록된 집계 레시피가 있으면 활용한다. "
        "purpose 에는 이 쿼리로 확인하려는 것을 한 줄로 쓴다. "
        "질문이나 query_rules에 없는 필터(예: GRADE_CD IS NOT NULL)를 덧붙이지 않으며, 답변에서 '규칙에 따라'라고 밝히는 조건은 describe_table의 query_rules에 실제로 있는 것만이다. "
        "반환된 result_id 는 Tool 인자로만 쓰고 답변 본문에 적지 않는다. "
        "결과 요약 필드 이름(row_count·distinct_counts·top_groups 등)도 '고유 Part 10개'처럼 풀어 쓴다."
    )


async def _execute_sql(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await execute_sql(
        sql=args["sql"], purpose=args.get("purpose", ""), access_scope=access_scope
    )


async def _search_documents(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await search_documents(query=args["query"])


async def _list_simulation(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await list_simulation()


async def _run_simulation(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await run_simulation(
        simulation_type=args["simulation_type"],
        params=args.get("params", {}),
        access_scope=access_scope,
    )


async def _list_tables(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await list_tables(keyword=args.get("keyword"), tag=args.get("tag"))


async def _describe_table(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await describe_table(table=args["table"])


async def _list_kpis(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await list_kpis(keyword=args.get("keyword"))


async def _get_kpi(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await get_kpi(kpi_id=args["kpi_id"])


async def _list_recipes(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await list_recipes(keyword=args.get("keyword"))


async def _get_recipe(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await get_recipe(recipe_id=args["recipe_id"])


async def _get_result_summary(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await get_result_summary(result_id=args["result_id"], access_scope=access_scope)


async def _get_result_page(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await get_result_page(
        result_id=args["result_id"],
        offset=args["offset"],
        limit=args["limit"],
        access_scope=access_scope,
    )


async def _aggregate_result(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await aggregate_result(
        result_id=args["result_id"],
        group_by=args["group_by"],
        value_column=args["value_column"],
        aggregation=args["aggregation"],
        labels=args.get("labels"),
        extra_value_columns=args.get("extra_value_columns"),
        access_scope=access_scope,
    )


async def _present_sql_preview(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await present_sql_preview(args, access_scope=access_scope)


async def _present_chart(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await present_chart(args, access_scope=access_scope)


async def _present_table(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await present_table(args, access_scope=access_scope)


async def _present_simulation(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await present_simulation(args, access_scope=access_scope)


async def _suggest_follow_ups(args: dict[str, Any], access_scope: str | None) -> dict[str, Any]:
    return await suggest_follow_ups(args.get("questions"))


def tool_specs() -> list[ToolSpec]:
    """등록 Tool 명세 전체. 실행부 등록·허용 이름·UI Tool 목록의 단일 출처다.

    `execute_sql` 설명은 현재 SQL 방언을 반영하므로 호출할 때마다 새로 만든다.
    결과 표시 도구는 항상 present_sql_preview·present_chart·present_table·
    present_simulation을 등록한다.
    """

    return [
        ToolSpec(
            "execute_sql",
            _execute_sql_description(),
            _object_schema({"sql": _STRING, "purpose": _STRING}, ["sql", "purpose"]),
            _execute_sql,
            "조회 행·컬럼 또는 대용량 결과 참조",
        ),
        ToolSpec(
            "search_documents",
            "공정 매뉴얼·업무 용어·생산계획 정책 등 비정형 도메인 지식을 검색한다. 옵션·결과의 의미·화면 버튼·변경 위치·조회 방법을 설명할 때 사용한다. "
            "실제 저장 수치 조회나 simulation 실행을 대신하지 않는다.",
            _object_schema({"query": _STRING}, ["query"]),
            _search_documents,
            "검색 문서 발췌·출처·검토 버전",
        ),
        ToolSpec(
            "list_simulation",
            "사용 가능한 시뮬레이션 종류와 별칭·사용 목적·입력 파라미터·출력 정의를 확인한다. "
            "자연어 요청에 맞는 등록 종류가 있는지 실행 전에 찾을 때 사용한다.",
            _object_schema({}, []),
            _list_simulation,
            "시뮬레이션 종류·입력·출력 정의",
        ),
        ToolSpec(
            "run_simulation",
            "사용자가 요청한 등록 simulation을 지정한 simulation_type 과 params 로 수행한다. "
            "종류/파라미터를 모르면 list_simulation 을 먼저 호출한다. "
            "적합한 등록 종류가 없으면 임의의 종류를 만들지 않는다. "
            "결과를 표로 보여 줬다면 답변 근거에 표의 행을 한 줄씩 다시 적지 말고, 검증 결과는 문제(미일치 등)가 "
            "있는 항목만 짚는다. 입력 검증 결과의 sample_rows 에는 미일치가 있는 관계만 담기고 check_summary 에 점검·미일치 관계 수가 있다"
            "(전체 점검 표는 present_table 로 result_id 를 보여 준다). "
            "모두 통과했으면 '5개 관계 모두 미일치 0건'처럼 한 문장으로 요약하고 통과한 관계 이름을 "
            "나열하지 않는다('점검한 관계는 Part→Route 연결, Route Step→설비 Family 연결, … 5개이며'처럼 이름을 늘어놓는 것도 "
            "나열이며, 관계 이름은 표에 있다). present_simulation 요약 카드에 보인 지표 값(예: Part 2개, Route Step 926개)도 근거에서 다시 쓰지 않는다. "
            "params 의 이름·값(예: view=swapped)은 답변에 그대로 쓰지 말고 'swap이 발생한 행만'처럼 풀어 쓴다. "
            "결과를 어떤 기준 컬럼(방향·사이트·등급·제품·고객 등)별 합계·건수로 비교하든 aggregate_result로 서버에서 집계해 그 값과 새 result_id를 쓴다. "
            "시뮬레이션 결과는 DB 테이블이 아니므로 execute_sql로 조회하지 않고(읽은 행 값을 SQL에 옮겨 적어 계산하는 것도 안 된다), get_result_page로 읽은 행을 직접 더하지 않는다. "
            "결과 컬럼은 'Swap 방향', 'Swap 수량', '계획 제품'처럼 한국어 이름으로 저장되므로 그 이름으로 부른다. "
            "Swap 수량은 swap 하나를 GIVE·RECEIVE 두 행에 같은 값으로 적은 것이므로, 가장 큰 swap 등을 쓸 때는 한 행(수취·RECEIVE)이 아니라 "
            "swap 단위로 'PROD_0006의 SITE_B→SITE_A swap 828.4'처럼 보내는 쪽과 받는 쪽을 함께 쓴다. "
            "목록 요청처럼 해석할 계산이 없으면 결론 뒤에는 조회 범위·조건과 mock 안내만 쓰고 끝낸다. "
            "'표에는 제품·사이트·swap 방향을 확인할 수 있게 정리했습니다'처럼 표에 담은 열을 설명하거나 표를 가리키는 문장은 쓰지 않는다. "
            "status가 missing_params면 파라미터 이름·목록 형식(예: [\"PROD_0001\"])·view 값을 보이지 말고 "
            "'볼 제품 ID를 알려 주세요(예: PROD_0001, PROD_0002)'처럼 말로 되묻는다.",
            _object_schema(
                {"simulation_type": _STRING, "params": _OBJECT}, ["simulation_type", "params"]
            ),
            _run_simulation,
            "시뮬레이션 결과와 검증 상태",
        ),
        ToolSpec(
            "list_tables",
            "조회 가능한 테이블 목록을 요약으로 돌려준다. "
            "keyword(테이블명·설명·태그·컬럼명·컬럼 설명·코드값 뜻 부분일치) 나 tag 로 좁힐 수 있으며 "
            "두 필터는 모두 생략할 수 있다. 키워드는 공백으로 나눈 단어 중 하나라도 맞으면 찾는다. "
            "결과가 0건이면 테이블이 없다고 단정하지 말고 필터 없이 다시 호출해 전체 목록을 보고 판단한다. "
            "용어가 붙어 있으면(예: 계획수립옵션) 핵심 단어로 나눠(예: '계획 옵션', '미수립') 다시 찾는다. "
            "찾은 테이블은 describe_table로 컬럼 설명·코드값을 확인한 뒤에만 카탈로그에 근거가 없다고 판단한다.",
            _object_schema({"keyword": _STRING, "tag": _STRING}),
            _list_tables,
            "테이블 이름·설명 목록",
        ),
        ToolSpec(
            "describe_table",
            "테이블 하나의 컬럼·키·조인·코드값·주의사항·조회 규칙·집계 가이드·시각화 안내와 질문·SQL 예시를 조회한다. SQL 을 작성하기 전에 반드시 호출한다. "
            "질문의 기준(예: '세그먼트별')이 이 테이블의 컬럼·코드값에 없거나 caveats 가 다른 컬럼으로 대신하지 말라고 하면 비슷한 컬럼으로 가정해 조회하지 말고, 후보 컬럼(이름과 의미)을 들어 어느 기준인지 묻고 멈춘다. "
            "묻고 멈추는 응답은 Tool 호출 없이 텍스트로만 끝낸다(execute_sql·present_*·suggest_follow_ups 모두 호출하지 않는다).",
            _object_schema({"table": _STRING}, ["table"]),
            _describe_table,
            "컬럼·조인·조회·집계 규칙",
        ),
        ToolSpec(
            "list_kpis",
            "정의된 KPI 목록을 조회한다. 생략 가능한 keyword 로 이름·별칭·정의를 부분일치 검색한다.",
            _object_schema({"keyword": _STRING}),
            _list_kpis,
            "KPI 요약 목록",
        ),
        ToolSpec(
            "get_kpi",
            "KPI 하나의 정의·공식·원천 테이블·비교 기준·부진 판정 규칙·"
            "집계 가이드·레시피 참조·SQL 템플릿·원인 후보(diagnostics)를 조회한다. "
            "답변에서는 kpi_id 대신 결과의 name 으로 부른다.",
            _object_schema({"kpi_id": _STRING}, ["kpi_id"]),
            _get_kpi,
            "KPI 공식·진단·SQL 정의",
        ),
        ToolSpec(
            "list_recipes",
            "자주 쓰는 집계·조인 패턴을 담은 재사용 CTE 목록을 조회한다. "
            "생략 가능한 keyword 로 이름·설명·적용 목적을 부분일치 검색한다.",
            _object_schema({"keyword": _STRING}),
            _list_recipes,
            "집계 recipe 요약 목록",
        ),
        ToolSpec(
            "get_recipe",
            "레시피의 적용 목적·출력 단위·컬럼 의미·조회 규칙·집계 가이드·표현 힌트·"
            "CTE SQL과 질문·SQL 예시를 조회한다. "
            "cte_sql 을 WITH 절로 복사해 execute_sql 에 조합해 쓴다 (자동 치환 없음). "
            "답변에서는 recipe_id 대신 결과의 name 으로 부른다.",
            _object_schema({"recipe_id": _STRING}, ["recipe_id"]),
            _get_recipe,
            "CTE·출력 grain·사용 예시",
        ),
        ToolSpec(
            "get_result_summary",
            "저장된 대용량 조회 결과의 메타데이터와 숫자 컬럼 요약 통계를 확인한다.",
            _object_schema({"result_id": _STRING}, ["result_id"]),
            _get_result_summary,
            "저장 결과 메타데이터·수치 요약",
        ),
        ToolSpec(
            "get_result_page",
            "저장된 대용량 조회 결과에서 직접 확인할 특정 구간의 행을 조회한다.",
            _object_schema(
                {"result_id": _STRING, "offset": _INTEGER, "limit": _INTEGER},
                ["result_id", "offset", "limit"],
            ),
            _get_result_page,
            "저장 결과의 일부 행",
        ),
        ToolSpec(
            "aggregate_result",
            "execute_sql·run_simulation이 반환한 result_id를 group_by 컬럼별로 서버에서 다시 집계해 새 result_id로 저장한다. "
            "SQL로 다시 조회할 수 없는 결과(시뮬레이션 등)를 결과의 어떤 기준 컬럼(예: 방향·사이트·등급·제품)별로든 합계·건수로 비교할 때 쓴다. "
            "execute_sql 결과에는 쓰지 않는다: 필요한 집계 단위(예: 공장별)는 처음 SQL의 GROUP BY에서 만들고, 다른 단위가 필요하면 SQL을 다시 작성해 실행한다. "
            "원본 행을 get_result_page로 읽어 직접 더하지 않고, 답변 수치는 이 Tool이 돌려준 값을 그대로 쓴다. "
            "aggregation은 sum·count·avg·min·max 중 하나다. "
            "여러 값(예: 계획수량과 목표수량)을 같은 기준으로 함께 비교하려면 extra_value_columns에 나머지 값 컬럼을 넣어 한 번에 집계한다. "
            "이렇게 값 열이 여럿인 결과는 한 차트에 담을 수 없으므로 present_chart를 호출하지 않고 present_table로만 보여 준다. "
            "labels에는 집계 값의 표시 이름을 넣는다(예: {\"Swap 수량\": \"Swap 수량 합계\"}). "
            "기준 값이 비어 있는 행(예: swap이 없는 행)은 집계에서 빠지고 excluded_blank_group_rows로 그 수를 알려 준다. "
            "표·차트에는 원본 result_id가 아니라 이 Tool이 돌려준 새 result_id를 넘겨, 그룹별 집계 행만 보여 준다. "
            "비교를 물었으면 present_chart(chart_type=bar, x_column=첫 기준, group_by_column=둘째 기준(있으면), y_column=값, aggregation=sum)로 보여 주고, 표는 사용자가 표를 요청했을 때만 더한다. "
            "새 result_id도 답변 본문에 적지 않는다.",
            aggregate_input_schema(),
            _aggregate_result,
            "그룹별 재집계 결과 참조(새 result_id·집계 행 preview)",
        ),
        ToolSpec(
            "present_sql_preview",
            "실행한 SQL 원문을 사용자에게 보여 준다(기본 접힘). "
            "sql에는 실제로 실행한 SQL을 그대로 넣는다. "
            "SQL 식은 이 미리보기로만 보여 주므로 답변 근거에는 WORK_YM = '202605', SUM(PLAN_QTY), PLAN_QTY > 0 같은 "
            "컬럼=값·비교·집계 식을 옮겨 쓰지 않고 '2026년 5월 행의 계획수량 합계', '계획수량이 0보다 큰 행'처럼 말로 쓴다. "
            "사용한 컬럼은 '월 기준 WORK_YM(제품 계획 년월)'처럼 이름과 뜻만 밝힌다.",
            present_sql_preview_input_schema(),
            _present_sql_preview,
            "SQL 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        ),
        ToolSpec(
            "present_chart",
            "execute_sql·run_simulation이 반환한 result_id를 서버가 집계한 bar/line/area 차트로 보여준다. "
            "행·차트 데이터는 넣지 않고 result_id와 표시 설정만 넣는다. 추이·비교를 보여줄 때 쓴다. "
            "막대 차트는 기본 grouped이며, 같은 단위의 합산 가능한 값을 group_by_column별 구성으로 비교할 때만 bar_mode=stacked를 지정한다. "
            "stacked는 chart_type=bar와 group_by_column이 필요하다. "
            "계획·실적처럼 사용자가 비교를 요청한 여러 지표는 지표마다 차트를 나누지 않고 한 차트에 묶는다: SQL을 지표 이름 컬럼(예: 지표)과 값 컬럼(예: 수량)의 long 형식으로 조회한 뒤 y_column=값 컬럼, group_by_column=지표 이름 컬럼으로 한 번 호출한다. "
            "모든 행이 같은 값인 컬럼(예: 조회 월)은 group_by_column으로 쓰지 않는다. "
            "차트는 x_column·group_by_column 외의 행을 aggregation으로 합치므로, 지표 이름 컬럼(지표)을 그 둘 중 하나로 쓰지 않으면 서로 다른 지표가 더해진다(서버가 오류로 거부한다). "
            "Lot 수와 수량처럼 단위가 다른 지표는 한 차트에 묶지 말고 SQL에서 지표 하나만 남겨 지표별로 따로 호출한다. "
            "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다. 호출 뒤에는 '위/아래' 같은 위치 표현 대신 '차트에서는'처럼 결과를 해석한다.",
            present_chart_input_schema(),
            _present_chart,
            "차트 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        ),
        ToolSpec(
            "present_table",
            "execute_sql·run_simulation이 반환한 result_id를 페이지 단위 표로 보여준다. "
            "행 데이터는 넣지 않고 result_id와 표시 설정만 넣는다. 상세 행을 보여줄 때 쓴다. 필요하면 한 응답에서 여러 번 호출할 수 있다. "
            "여러 지표(예: 계획·실적)를 표로 보여 줄 때는 지표마다 열을 두는 wide 형식(공장, 계획수량, 실적수량, 차이)으로 조회한 결과를 넘긴다. "
            "지표 이름 열(지표)과 값 열을 둔 long 형식은 한 행에 비교할 값이 없어 차트에만 쓴다. "
            "미리보기 repeated_columns 의 열(예: 배치 행마다 반복되는 공장 합계·공장 달성률)은 columns 에서 빼고 그 값은 결론 문장에 쓴다. "
            "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다. 호출 뒤에는 '위/아래' 같은 위치 표현 대신 '표에는'처럼 결과를 해석한다. "
            "모든 행에서 같은 값인 컬럼(예: 20행 모두 등급 개수 3)은 columns에서 빼고 그 값은 결론 한 문장으로 쓴다. "
            "남는 컬럼까지 모든 행이 같으면(예: 모든 제품이 등급 A·B·C) 표를 띄우지 않는다.",
            present_table_input_schema(),
            _present_table,
            "표 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        ),
        ToolSpec(
            "present_simulation",
            "시뮬레이션 시나리오·요약·KPI를 보여준다. "
            "같은 결과의 차트·표를 함께 보여줘야 하면 같은 응답에서 present_chart·present_table을 result_id를 공유해 별도로 호출하고 텍스트로 그 연결을 설명한다. "
            "성공한 호출을 Markdown 표나 코드 펜스로 반복하지 않는다.",
            present_simulation_input_schema(),
            _present_simulation,
            "시뮬레이션 요약 표시 설정 검증 결과(빈 객체 또는 안전한 오류)",
        ),
        ToolSpec(
            SUGGESTION_TOOL_NAME,
            "최종 답변을 쓰기 직전에 사용자가 이어서 물어볼 만한 후속질문 2~4개를 등록한다. "
            "질문에 답하지 않고 기준·기간을 사용자에게 되묻고 멈추는 응답에서는 호출하지 않는다(선택지는 본문 질문에 쓴다). "
            "각 질문은 사용자가 그대로 보낼 수 있는 1~120자의 한국어 질문 문장으로 쓰고 서로 겹치지 않게 한다. "
            "내용 기준은 CLAUDE.md 후속질문 규칙을 따른다. "
            "화면에는 답변 뒤 선택지로 표시되므로, 답변 본문에는 '원하시면 ~해 드리겠습니다' 같은 추가 제안 문장을 쓰지 않는다.",
            suggest_follow_ups_input_schema(),
            _suggest_follow_ups,
            "후속질문 검증 결과(화면에는 답변 뒤 선택지로만 표시)",
            visible=False,
        ),
    ]


async def tool_catalog() -> list[dict]:
    """UI Tool 목록(`/api/knowledge/tools`)용 명세. 모델에 보내는 schema 와 같다."""

    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
            "output": spec.output,
            "status": "available",
        }
        for spec in tool_specs()
    ]
