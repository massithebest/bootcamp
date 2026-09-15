# 차트 v2 실행 계획 (백엔드)

**상태: 착수 대기.** 기준 설계는 [docs/chart-visualization.md](../../docs/chart-visualization.md)다.
이 계획은 다음 흐름의 백엔드 작업만 다룬다.

~~~text
Knowledge 기반 집계 SQL
  → Result Store(result_id)
  → prepare_visualization
  → 검증된 명세 저장(visualization_id)
  → GET /api/visualizations/{visualization_id}
~~~

기존 계획의 Result별 집계 API, Knowledge charts 규칙, applicable_chart,
원시 차트 스펙 마커는 폐기한다. 차트 서버는 업무 집계를 수행하지 않고,
LLM이 선택한 이미 집계된 결과의 컬럼을 검증·정렬·시리즈화한다.

프론트 작업은 [frontend 차트 v2 계획](../../frontend/plan/260915-chart-v2-plan.md)을 따른다.
백엔드 Task 0~6이 끝나 조회 계약이 고정된 뒤 프론트를 시작하고,
Task 7의 v1 제거는 프론트 전환과 같은 변경 단위에서 수행한다.

## 착수 조건

- [Result Store 계획](260915-result-store-plan.md)의 구현이 완료되어
  ResultStore, LocalParquetResultStore, result_id, 결과 조회 tool이 동작한다.
- [집계 가이드](../../docs/aggregation-guide.md)의 catalog + kpi + recipes 필드와
  검증 테스트가 반영되어 있다.
- Task 0의 미확정 계약을 기준 설계 문서와 이 계획에 기록하기 전에는 구현을 시작하지 않는다.

~~~bash
cd backend
python -c "from services.result_store import get_result_store; print(get_result_store())"
python -m pytest -q
~~~

## 실행 세션 시작 방법

backend 디렉터리에서 시작한다. 첫 요청에는 다음 내용을 포함한다.

> plan/260915-chart-v2-plan.md를 Task 0부터 순서대로 실행해 줘.
> 각 Task의 검증을 통과한 뒤 다음 Task로 이동하고, 설계에 없던 판단을
> 내릴 때마다 문서 끝 결정 기록에 무엇을 왜 정했는지 즉시 남겨 줘.

## 공통 실행 규칙

- route → tool → service → store 경계를 유지한다. 검증·변환 로직을 route나 SDK wrapper에 넣지 않는다.
- prepare_visualization의 입력에는 result_id와 표현 명세만 받는다.
  SQL, HTML, JavaScript, 수치 배열, 접근 권한 값은 받지 않는다.
- Knowledge의 aggregation_rules와 visualization_hints는 LLM을 위한 가이드다.
  ChartRule, charts, when.has_columns 같은 자동 매칭 모델은 만들지 않는다.
- Result Store의 원본 데이터는 변경하지 않는다. 다른 집계 단위가 필요하면 새 SQL 또는
  지원되는 시뮬레이션 재실행으로 새 result_id를 만든다.
- infer_chart는 v2 폴백이 아니다. v2 전체 경로가 검증될 때까지 v1만 유지하고 마지막에 제거한다.
- 새 tool은 TOOL_NAMES, agent_sdk/CLAUDE.md, fake runner, frontend tool 메타데이터,
  prompt-consistency 테스트를 같은 변경에서 맞춘다.
- Skill에는 실제 테이블·컬럼명이나 집계 SQL을 복제하지 않는다.
- 새 외부 패키지를 추가하지 않는다. 영속 저장은 현재 로컬 파일 기반 추상화와 폐쇄망 원칙을 따른다.
- 구현 중 기준 설계와 충돌하거나 이 계획에 없는 보안·데이터 의미 결정이 필요하면
  임의로 진행하지 말고 기준 설계와 결정 기록을 먼저 갱신한다.

## Task 0. 구현 계약 확정

**파일:** docs/chart-visualization.md, 이 계획, frontend/plan/260915-chart-v2-plan.md

**스펙:**

구현 전에 아래 값을 백엔드·프론트 공통 계약으로 확정한다.

1. bar와 line의 최대 포인트 수, 최대 시리즈 수
2. 표시 한도 초과 시 반환할 오류 코드와 사용자가 범위를 줄이는 방법
3. VisualizationMeta의 저장 위치, schema_version, TTL과 정리 주기
4. 조회 API의 성공 payload와 오류 상태
5. 현재 인증 체계에서 사용할 서버 발급 access scope

현재 애플리케이션의 conversation_id는 브라우저가 만든 값이므로 권한 증명이 아니다.
visualization_id나 conversation_id만으로 조회를 허용하지 않는다. 인증 주체가 아직 없다면
백엔드가 발급한 불투명한 브라우저 세션 scope를 HttpOnly 쿠키로 전달하고,
POST /api/chat과 GET /api/visualizations/{id}가 같은 scope를 사용하도록 한다.
쿠키를 쓸 경우 명시적 CORS origin, credentials, SameSite, Secure의 개발·운영 값을 함께 정한다.
향후 사내 인증이 연결되면 이 scope 생성부만 인증 principal로 교체할 수 있어야 한다.

초기 조회 응답 계약은 아래 형태를 기준으로 확정한다.

~~~json
{
  "visualization_id": "b8c19235da17461ab3e8ec82a942f017",
  "result_id": "a30f90f8da934a35a931ba694e130a65",
  "schema_version": 1,
  "expires_at": "2026-09-16T00:00:00+00:00",
  "chart": {
    "type": "line",
    "x": "work_month",
    "series": [
      {"key": "series_0", "label": "actual"}
    ],
    "categories": ["2026-07", "2026-08"],
    "data": [
      {"work_month": "2026-07", "series_0": 100}
    ],
    "title": null,
    "x_label": "work_month",
    "y_label": null,
    "unit": null
  },
  "warnings": [
    {"code": "SOURCE_TRUNCATED", "message": "조회 결과가 저장 한도에서 잘렸습니다."}
  ]
}
~~~

JSON 필드명과 null/생략 규칙을 확정한 뒤 프론트 계획에도 똑같이 반영한다.

**검증:**

- 두 계획의 예시 payload와 오류 코드가 서로 일치한다.
- conversation_id 단독 검증이나 ID 추측 난이도에 의존하는 항목이 없다.
- 결정한 한도·수명·접근 방식이 기준 설계의 구현 전 확정 사항에 기록되어 있다.

**완료 기준:** 구현자가 추가 설계 판단 없이 모델·API·UI 타입을 작성할 수 있다.

---

## Task 1. Result Store 계약 보완과 access scope 연결

**파일:** services/result_store.py, services/mock/mock_sql_service.py,
services/mock/mock_simulation_service.py, services/real/* 대응 구현,
tools/sql_tool.py, tools/simulation_tool.py, agent/agent.py, agent/sdk_tools.py,
api/routes_chat.py, api/schemas.py, core/config.py, .env.example,
tests/test_result_store.py, tests/test_services.py, tests/test_api.py

**스펙:**

1. ResultMeta에 원본 조회 잘림 여부와 Task 0에서 확정한 access_scope를 저장한다.
   row_count는 저장된 행 수라는 의미를 유지하고, 원래 전체 건수처럼 표현하지 않는다.
2. SQL은 MAX_ROWS + 1행 조회 결과로 source_truncated를 계산한 뒤 최대 MAX_ROWS만 저장한다.
   외부 집계가 완료된 최종 결과에 적용된 상한임을 명확히 하고, 잘린 결과를 전체 원본으로 표시하지 않는다.
3. SQL inline/large_result 양쪽과 표형 시뮬레이션 양쪽에 columns 메타데이터를 같은 형태로 반환한다.
   각 컬럼은 name, dtype, role을 포함한다. role은 휴리스틱이며 검증된 업무 의미로 취급하지 않는다.
4. POST /api/chat에서 확정된 access scope를 만들거나 읽고 run_agent까지 전달한다.
   build_planning_mcp_server는 요청 scope에 묶인 tool wrapper를 생성한다.
   모델의 tool 입력으로 access_scope를 노출하지 않는다.
5. execute_sql과 run_simulation 저장 호출이 요청 scope를 ResultMeta에 전달한다.
   mock/real 서비스의 공개 시그니처와 테스트 대역을 함께 맞춘다.
6. 기존 conversation_id는 세션 이어가기 용도로 유지하되 결과 접근 권한으로 사용하지 않는다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_result_store.py tests/test_services.py tests/test_api.py tests/test_tools.py
~~~

추가 테스트:

- inline과 large_result가 동일한 columns 메타데이터를 제공한다.
- 정확히 MAX_ROWS와 MAX_ROWS + 1 이상 결과의 source_truncated가 구분된다.
- row_count는 저장 행 수이고 잘림 경고와 별개다.
- 서로 다른 access scope의 결과가 구분된다.
- 모델에게 전달되는 tool 스키마에 access_scope가 없다.
- 기존 conversation/session resume와 fork 동작에 회귀가 없다.

**완료 기준:** 모든 차트 대상 result_id에 컬럼 메타데이터·잘림 정보·서버 신뢰 access scope가 있다.

---

## Task 2. 시각화 요청 모델과 영속 저장소

**파일:** services/visualization_store.py(신규), services/visualization_models.py(신규),
core/config.py, .env.example, tests/test_visualization_store.py(신규)

**스펙:**

다음 도메인 모델을 정의한다.

- VisualizationRequest: result_id, kind(bar 또는 line), x, y(비어 있지 않은 문자열 배열),
  선택적 group_by
- NormalizedVisualizationSpec: 검증된 컬럼 연결과 표시 메타데이터
- VisualizationWarning: code, message
- VisualizationMeta: visualization_id, result_id, schema_version, 정규화 명세,
  warnings, access_scope, created_at, expires_at

VisualizationStore 추상화와 LocalVisualizationStore를 구현한다.

- visualization_id는 uuid4 hex다.
- 메타데이터만 JSON sidecar로 원자적으로 저장한다. 수치 배열·HTML·JavaScript는 저장하지 않는다.
- 생성한 명세는 불변이다. 같은 result_id의 다른 표현은 새 visualization_id를 받는다.
- 만료 시각은 원본 ResultMeta.expires_at을 넘지 않는다.
- get, save, delete, delete_for_result, cleanup_expired를 제공한다.
- 손상된 sidecar, 잘못된 ID, 이미 삭제된 원본을 안전하게 처리한다.
- 주기 정리는 만료 명세와 원본이 사라진 고아 명세를 제거한다.
- 조회 중 원본이 삭제되는 경합은 이후 서비스에서 RESULT_UNAVAILABLE로 처리한다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_visualization_store.py
~~~

추가 테스트:

- 재인스턴스화 후 같은 명세를 읽을 수 있다.
- 다른 표현은 다른 ID를 받고 기존 명세는 바뀌지 않는다.
- TTL이 원본보다 길어지지 않는다.
- delete_for_result와 고아 정리가 연결된 모든 메타데이터를 제거한다.
- 저장 파일에 data 배열이나 HTML이 없다.

**완료 기준:** 서버 재시작 이후에도 원본 수명을 넘지 않는 검증 명세를 조회할 수 있다.

---

## Task 3. 시각화 검증과 렌더링용 데이터 구성

**파일:** services/visualization_service.py(신규),
tests/test_visualization_service.py(신규)

**스펙:**

prepare_visualization 서비스는 ResultStore에서 메타데이터와 parquet을 읽고 다음 순서로 검증한다.

1. 결과 존재·만료·access scope 일치
2. 지원 kind와 result_id/x/y/group_by 입력 형식
3. 요청한 컬럼의 존재, x·y·group_by 간 중복·충돌 여부
4. 모든 y의 실제 숫자 dtype과 표시 가능한 유한 값 존재 여부
5. line x 값의 날짜·연월 해석 가능 여부
6. group_by가 없으면 x, 있으면 x + group_by 조합의 유일성
7. 빈 결과, 전체 NULL 계열, 포인트·시리즈 한도, source_truncated 여부

서버는 다음 원칙만 적용한다.

- SUM, 평균, 비율 재계산 등 업무 집계를 하지 않는다.
- 중복 grain을 합산하거나 마지막 행으로 덮어쓰지 않고 DUPLICATE_GRAIN을 반환한다.
- NULL을 0으로 바꾸지 않는다.
- line은 해석한 시간 순서로 정렬한다. bar는 입력 의미를 보존하며 임의 top N을 적용하지 않는다.
- x + group_by는 wide data로 피벗하되 내부 series key를 표시 label과 분리한다.
- group_by와 여러 y를 함께 쓰면 계열은 group 값 × y로 만들며 Task 0의 시리즈 상한을 적용한다.
- 코드·명 쌍이 실제 결과에 함께 있고 안전하게 연결할 근거가 있을 때만 이름을 label로 사용한다.
  코드는 identity로 유지하고 동명 label도 내부 key 충돌을 만들지 않는다.
- source_truncated는 성공 가능한 경우 경고로 보존한다. 한도 초과는 조용히 자르지 않고
  DISPLAY_LIMIT_EXCEEDED 오류로 SQL 범위 축소를 요구한다.

고정 오류 코드를 정의하고 tool과 API에서 공유한다.

- RESULT_NOT_FOUND, RESULT_EXPIRED, RESULT_FORBIDDEN, RESULT_UNAVAILABLE
- COLUMN_NOT_FOUND, INVALID_COLUMN_ROLE, DUPLICATE_MAPPING, DUPLICATE_GRAIN
- EMPTY_RESULT, UNRENDERABLE_VALUES, DISPLAY_LIMIT_EXCEEDED, UNSUPPORTED_KIND

prepare 성공 시 정규화 명세를 VisualizationStore에 저장하고 ID와 warnings만 반환한다.
별도 read_visualization 서비스는 저장 명세와 현재 원본을 다시 확인하고 ChartSpec을 구성한다.
이렇게 하면 등록 뒤 원본 삭제·만료 경합도 조회 시점에 감지된다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_visualization_service.py
~~~

필수 케이스:

- bar/line, y 한 개·여러 개, group_by 유무, 같은 result_id의 복수 명세
- 없는 컬럼, 비수치 y, x와 group_by 충돌, 중복 grain
- NULL 보존, 전부 NULL인 계열 거부, 날짜·연월의 실제 시간 정렬
- 동일 표시 이름의 그룹, y 컬럼명과 그룹값 충돌, 안정적인 내부 series key
- 표시 한도 초과 시 오류이며 자동 slice/downsample이 없음
- source_truncated 경고와 표시 한도 오류가 서로 구분됨
- 다른 access scope, 만료, 등록·조회 사이 원본 삭제

**완료 기준:** 유효 명세만 저장되며 렌더링 데이터가 parquet 수치를 변경하지 않는다.

---

## Task 4. prepare_visualization tool 등록

**파일:** tools/visualization_tool.py(신규), agent/sdk_tools.py,
agent/agent_sdk/CLAUDE.md, agent/fake_runner.py,
tests/test_tools.py, tests/test_prompt_consistency.py, tests/test_agent.py

**스펙:**

모델 입력은 다음 필드만 허용한다.

~~~json
{
  "result_id": "a30f90f8da934a35a931ba694e130a65",
  "kind": "line",
  "x": "work_month",
  "y": ["actual"],
  "group_by": "line_cd"
}
~~~

group_by는 선택 필드다. wrapper는 요청에 묶인 access scope를 내부에서 서비스에 전달한다.
성공 응답은 status, visualization_id, warnings만 포함한다.
실패 응답은 status:error와 공유 오류 code, 수정 가능한 message, 필요한 최소 details를 포함한다.
parquet 값이나 렌더링용 data는 tool 응답에 복제하지 않는다.

TOOL_NAMES와 build_planning_mcp_server에 prepare_visualization을 등록하고,
agent_sdk/CLAUDE.md 도구 표·사용 규칙, fake runner, prompt-consistency 검사를 함께 갱신한다.
tool이 등록되기 전에는 Skill에 이름을 먼저 추가하지 않는다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_tools.py tests/test_prompt_consistency.py tests/test_agent.py
~~~

추가 테스트:

- SDK tool 목록과 런타임 도구 표가 정확히 일치한다.
- 선택적 group_by가 생략 가능하다.
- 모델 입력으로 SQL, data, HTML, access scope를 받을 수 없다.
- 서비스 오류 code/message가 손실 없이 tool 결과로 전달된다.
- fake runner에서도 성공 마커와 실패 폴백을 결정론적으로 검증할 수 있다.

**완료 기준:** 현재 에이전트가 실제 result_id에 대해 검증·등록 tool을 호출할 수 있다.

---

## Task 5. 조회 API와 수명주기 연결

**파일:** api/routes_visualizations.py(신규), api/schemas.py, main.py,
services/result_store.py, services/visualization_store.py,
tests/test_api.py, tests/test_result_store.py

**스펙:**

GET /api/visualizations/{visualization_id}를 추가한다.

- URL은 visualization_id만 받으며 축·집계 query parameter를 받지 않는다.
- Task 0의 서버 신뢰 access scope를 요청에서 읽어 서비스로 넘긴다.
- route는 read_visualization 결과를 API schema로 직렬화할 뿐 parquet 처리나 검증을 하지 않는다.
- 성공은 Task 0의 payload를 반환한다.
- 잘못되거나 존재하지 않는 ID는 404, 만료·삭제된 원본은 410,
  접근 불가는 존재 여부를 노출하지 않는 정책으로 응답한다.
- 오류 본문은 FastAPI의 detail 형태와 안정된 code/message를 사용한다.
- Cache-Control은 원본 TTL과 불변 명세 특성을 반영하되 access scope별 응답이 공유 캐시에 섞이지 않게 한다.
- Result Store 주기 정리 후 visualization 고아 정리도 실행한다.
- 명시적 결과 삭제 경로가 추가되면 delete_for_result를 같은 수명주기 서비스에서 호출한다.

기존 GET /api/results/{result_id}/chart 집계 API는 만들지 않는다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_api.py tests/test_result_store.py tests/test_visualization_store.py
~~~

수동 확인:

~~~bash
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
# 같은 access scope로 등록된 visualization_id 조회 → 200
# 다른 scope → 비노출 오류
# 만료·삭제된 result 연결 → 410
# type/x/y query parameter로 새 차트를 만들 수 없음 확인
~~~

**완료 기준:** 유효한 ID와 access scope로만 ChartSpec을 조회하며 원본 수명주기와 함께 정리된다.

---

## Task 6. 에이전트 절차 연동

**파일:** agent/agent_sdk/.claude/skills/sql-analysis/SKILL.md,
agent/agent_sdk/.claude/skills/simulation/SKILL.md,
agent/agent_sdk/CLAUDE.md, tests/test_prompt_consistency.py,
tests/test_aggregation_guidance.py, tests/test_e2e_scenario.py

**스펙:**

두 Skill에 절차만 추가한다.

1. 질문에 필요한 집계 grain을 먼저 정하고 Knowledge의 catalog, KPI, recipe를 확인한다.
2. SQL 또는 표형 시뮬레이션으로 그 grain의 result_id를 만든다.
3. 비교·추이가 유용하거나 사용자가 요청한 경우 실제 columns와 결과를 확인해
   prepare_visualization을 호출한다.
4. tool 오류는 최대 2회 안에서 명세 수정 또는 새 집계 결과로 보정한다.
5. 성공한 visualization_id만 최종 답변의 chart 마커에 넣는다.
6. tool 미호출, 보정 실패, 빈 결과, 지원하지 않는 표현은 표·텍스트로 답하고 차트를 약속하지 않는다.

최종 답변 마커는 다음 형태만 허용한다.

~~~~text
```chart
{"visualization_id":"b8c19235da17461ab3e8ec82a942f017"}
```
~~~~

Skill에는 실제 테이블명·컬럼명·업무 SQL을 넣지 않는다.
Knowledge visualization_hints는 권장 표현으로만 사용하고 자동 규칙처럼 설명하지 않는다.
표형 시뮬레이션은 SQL 재조회가 불가능할 수 있으므로 지원 파라미터 변경 또는 표 폴백을 안내한다.

**검증:**

~~~bash
cd backend
python -m pytest -q tests/test_prompt_consistency.py tests/test_aggregation_guidance.py
python -m pytest -m e2e
~~~

e2e는 자격 증명이 있을 때만 실행하고, 미실행 시 기본 테스트와 fake runner 시나리오를 근거로 남긴다.
대표 시나리오는 차트 요청 성공, tool 미호출, 잘못된 컬럼 1회 보정,
2회 실패 뒤 표 폴백, 같은 결과의 복수 차트다.

**완료 기준:** 에이전트가 Knowledge → 집계 → tool → 성공 ID 마커 순서를 지키며,
검증되지 않은 ID나 원시 스펙을 답변에 쓰지 않는다.

---

## Task 7. v1 경로 제거와 공동 전환

**의존성:** 프론트 계획 Task 1~5 완료 및 통합 검증 성공

**파일:** services/mock/mock_sql_service.py,
services/mock/mock_simulation_service.py, services/chart_inference.py,
관련 테스트, 프론트의 tool 결과 렌더러

**스펙:**

- SQL·시뮬레이션 결과에 자동 chart를 붙이는 호출을 제거한다.
- tool 카드의 중복 차트 제거가 같은 변경에 포함됐는지 확인한다.
- infer_chart와 전용 테스트는 남은 사용처를 rg로 확인한 뒤 사용처가 없을 때만 삭제한다.
- v2 tool 미호출 시 자동 infer_chart 폴백을 추가하지 않는다.
- 기존 표·요약 결과는 그대로 유지한다.
- 배포를 나눠야 한다면 v1 제거는 마지막 호환 단계로 미루고,
  백엔드에서 먼저 차트가 사라지는 중간 상태를 만들지 않는다.

**검증:**

~~~bash
cd backend
rg -n "infer_chart|infer_chart_from_records|applicable_chart|ChartRule|when\.has_columns" .
python -m pytest -q
~~~

검색 결과에 의도하지 않은 v1 호출이나 폐기 설계가 없어야 한다.
프론트 전체 검증은 프론트 계획의 명령을 함께 실행한다.

**완료 기준:** 최종 답변 ID 마커가 유일한 v2 차트 진입점이며 tool 카드·자동 추론 차트가 중복되지 않는다.

## 전체 완료 기준

- 동일 result_id에서 수량 비교와 비율 추이를 각각 등록할 수 있다.
- 서버 재시작 후 유효한 명세 조회가 가능하다.
- 중복 grain, NULL, 시간 정렬, 동명 그룹, 다중 시리즈, 결과 잘림을 테스트한다.
- 표시 한도 초과 시 조용한 잘림이나 다운샘플링이 없다.
- 잘못된 ID, access scope 불일치, 원본 만료·삭제가 안전하게 처리된다.
- 기본 백엔드 테스트 전체가 통과한다.
- 프론트 계획의 build/lint와 수동 스트리밍 검증까지 통과한 뒤 v1을 제거한다.

~~~bash
cd backend
python -m pytest -q
~~~

## 범위 밖

- pie와 Gantt
- LLM이 생성한 HTML·JavaScript 실행 또는 HTML 사전 생성
- Result Store에서의 추가 SUM·비율 계산
- ChartRule/charts 자동 매칭과 infer_chart 폴백
- 자동 top N, 자동 다운샘플링
- 신뢰 가능한 단위·컬럼 계보가 없는 상태에서의 의미 검증 완료 선언

## 결정 기록

*(실행 세션이 설계에 없던 판단을 내릴 때마다 여기에 남긴다.)*
