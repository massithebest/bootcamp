# assistant-ui 통합 전환을 위한 Backend 계획 (Result API·`present`·후속질문)

**상태: B0~B2 구현 완료(2026-09-22, `pytest -q` 426 passed, 6 deselected). 남은 항목: B3 후속질문, B4 대화 영속(설계만), 실제 provider e2e와 기본값 전환.**

구현 결과와 계획 대비 차이:

- 오류 코드에 `UNRENDERABLE_VALUES`(422)를 추가했다(NaN·무한대·null x/group).
- 시계열 point가 500개를 넘으면 재집계에 `aggregation`이 필요하고, 없으면 `AGGREGATION_REQUIRED`다.
- `present` 검증은 `resultId` 접근뿐 아니라 `QueryChart` 설정을 실제 projection으로, `QueryTable.columns`를 결과 컬럼으로 재검증해
  모델이 바로 고칠 수 있는 `code`·`details.path`를 돌려준다.
- 결과 표시 지침은 플래그별 작업 디렉터리(`agent/agent_sdk/` ↔ `agent/agent_sdk_present/`)로 분리했고 테스트가 일치를 검사한다.
- 상세 계약은 `Todo.md`의 "결과와 시각화"를 따른다. 이 문서는 B3·B4를 마치면 제거한다.

이 문서는 FastAPI·Claude Agent SDK Backend가 SQL 조회와 simulation 결과를 모델 주도
`present` Generative UI로 제공하고, 브라우저 채팅 UI의 runtime 전환(분기·다중 thread·후속질문)을
지원하기 위해 구현할 계약과 **전체 실행 순서·착수 조건**을 정의한다. 외부 UI 구현 문서의 존재를
전제하지 않으며 소비자가 필요로 하는 Tool·SSE·HTTP 계약을 이 문서에 모두 기록한다.
완료 후 장기적으로 필요한 결정과 실제 검증 수치만 `Todo.md`에 합치고 이 파일은 제거한다.

## 1. 결정 사항

사용자 결정(2026-09-21):

- 결과 UI 전환은 환경변수 **`RESULT_UI_MODE=legacy|present`** 기능 플래그로 단계 전환한다. 기본은 `legacy`이며
  운영 검증 뒤 기본값을 별도 결정한다. 롤백은 플래그를 `legacy`로 되돌리는 것이다.
- 소비자가 채팅 runtime을 자체 상태 관리에서 라이브러리 runtime(분기·세션 내 다중 thread·후속질문)으로 옮긴다.
  현재 `/api/chat`·AgentEvent는 그대로 소비 가능하므로 이 문서의 runtime 관련 항목(B3·B4)은 선택이다.

기술 결정:

- FastAPI, Claude Agent SDK, 현재 `/api/chat` SSE와 `AgentEvent` 종류는 유지한다.
- Claude Agent SDK의 `planning` in-process MCP 서버에 `present` Tool을 등록한다. 모델은 `tree`
  JSON 문자열 안에 assistant-ui 표준 `$type`/`$key` vocabulary로 UI 트리를 만들고, Backend는
  파싱·검증·공개한 뒤 빈 객체를 반환한다.
  SDK가 같은 응답 안에서 후속 설명을 계속 생성하므로 브라우저 Tool-result callback은 도입하지 않는다.
- `present` 모드에서 `execute_sql`·`run_simulation`은 전체 행 대신 Result Store 참조와 bounded preview만 모델에 반환한다. 모델은 데이터가 아니라 표시 방식만 결정한다.
- 신규 결과 UI는 `result_id` 기반 preview·table·chart API를 사용하며 chart의 집계·검증·축약은 서버 책임이다.
- `prepare_table`·`prepare_visualization`·`visualization_id`는 `present` 모드의 Agent 흐름에서 제외한다. 업무 함수, legacy route/store와 저장 파일은 한 번의 운영 검증 주기 동안 유지하고 이 작업에서 삭제하지 않는다.
- `get_result_summary`·`get_result_page`는 변경 없이 유지한다(Agent 전용 Tool).
- 현재 보안 경계는 인증 사용자가 아니라 `pp_session_scope` 브라우저 쿠키다. 모든 신규 API에 같은 scope 검사를 적용하며 실제 인증·행 수준 권한은 별도 선행 과제다.

### 검토로 확인한 충돌과 해소

| # | 충돌·공백 | 해소 |
| --- | --- | --- |
| C1 | Runtime 먼저 vs Generative UI 먼저 | Generative UI 먼저. Backend는 가산 단계(B1)를 먼저 끝내고 소비자 준비 후 전환(B2) |
| C2 | payload 형태를 바꾸면 기존 소비자 표시가 깨짐 | 플래그 `RESULT_UI_MODE`가 payload 형태·Tool 집합·Agent 지침·자동 표 보완을 함께 전환. `legacy`에서는 기존 동작이 바이트 단위로 같아야 한다 |
| C3 | 새 API의 404 통일과 기존 `/api/visualizations`의 410 구분 | 새 API는 없음·만료·타 scope를 모두 404 `RESULT_NOT_FOUND`로 통일(존재 노출 방지). `/api/visualizations`는 변경하지 않는다 |
| C8 | `present`의 `children` 허용 위치 | 여러 결과를 묶는 `Card`와 `SimulationSummary`(자식은 `QueryChart`/`QueryTable`만)에서만 허용 |
| C9 | 잘못된 `present`를 모델이 재호출 | 실패 결과는 `status:"error"`+안전한 code/message로 돌려 모델이 한 번 수정하거나 텍스트 fallback을 하게 한다 |
| C10 | 소비자 Zod와 Backend schema 드리프트, 소비자 패키지의 `present` schema는 flat(모든 component prop을 한 bag으로 병합) | 아래 3.1의 prop 표를 계약으로 고정. 같은 prop명은 component 간 같은 타입, Backend 검증은 `$type`별로 더 엄격하게 수행 |
| C11 | Agent 지침·문서의 "run_agent 자동 표 보완", "`/api/visualizations`만 조회 진입점", "SQL·simulation 결과에 자동 차트 없음" | `present` 모드 전환(B2)과 같은 작업에서 갱신 |
| C12 | 이전 선택 항목의 `/api/results/.../table`·`present` 초안 | 폐기. 경로는 `/api/query-results/{result_id}/{preview\|table\|chart}`로 단일화 |

## 2. 목표와 비범위

### 목표
1. SQL·simulation 실행과 UI 조합을 분리한다.
2. 원본 전체 행을 모델 context나 `present` args에 넣지 않는다.
3. 모델이 `Card` 안에서 SQL·차트·표의 배치만 안전한 도메인 vocabulary로 조합하게 한다.
4. 존재하지 않는 컬럼·부적합한 타입·과도한 계열·포인트를 서버에서 거부하거나 결정적 규칙으로 축약한다.
5. 기존 Result Store TTL·scope와 mock/real 서비스의 반환 계약을 유지한다.

### 비범위
- AI SDK·Node 채팅 서버 전환, assistant-ui Cloud, 원격 MCP, CDN 또는 외부 런타임 추가.
- 사용자 입력을 기다리는 `prompt_user`, interactive action vocabulary.
- Result Store 1,000행 저장 상한 확대와 대용량 저장 backend 교체.
- 실제 인증 principal, 실제 사내 DB·simulation provider 구현.
- 이 작업에서의 legacy visualization store·API·파일 삭제(운영 검증 1주기 뒤 별도).
- 대화·분기 영속 API 구현(B4는 설계만 기록).

## 3. 공개 계약

### 3.0 플래그

`core/config.py`에서만 읽는 `RESULT_UI_MODE`(`legacy` 기본, `present`). 잘못된 값은 시작 단계에서 실패한다. `.env.example`에 실제 값 없이 키를 추가한다.

| | `legacy` | `present` |
| --- | --- | --- |
| `execute_sql`·`run_simulation` | 기존 payload(인라인 `table`/`sample_rows`/`results`) | preview(3.2), 전체 행·`table`·`results` 없음 |
| `planning_tools()`·`TOOL_NAMES` | `prepare_table`·`prepare_visualization` 포함, `present` 제외 | `present` 포함, `prepare_*` 제외 |
| 누락 표 자동 보완(`run_agent`) | 유지 | 제거(모델의 `present`와 텍스트 fallback) |
| Agent 지침 | 기존 | `present` 절차 |
| Result API(3.3) | 항상 활성 | 항상 활성 |

### 3.1 `present` Agent Tool

`planning` in-process MCP 서버가 `mcp__planning__present` 이름으로 Tool을 노출하고 공개 이벤트에서는 짧은 이름
`present`를 쓴다. provider-facing 입력은 `tree` JSON 문자열 하나다. 문자열의 root는 UI node 객체이고
모든 node의 종류는 assistant-ui 표준 `$type`, 선택 key는 `$key`로 지정한다. Backend는 Tool 실행
경계에서 문자열을 파싱·검증하고, 공개 AgentEvent에 같은 `$type`/`$key` 트리를 싣는다.

```json
{ "tree": "{\"$type\":\"Card\",\"title\":\"월별 생산량\",\"children\":[{\"$type\":\"QueryChart\",\"resultId\":\"0123456789abcdef0123456789abcdef\",\"chartType\":\"line\",\"xColumn\":\"work_month\",\"yColumn\":\"actual_qty\",\"aggregation\":\"sum\",\"title\":\"월별 생산량 추이\"},{\"$type\":\"QueryTable\",\"resultId\":\"0123456789abcdef0123456789abcdef\",\"title\":\"조회 결과\"}]}" }
```

허용 `component`(공개 AgentEvent에서는 대응하는 `$type`): 여러 결과를 묶는 `Card` + 도메인 `SqlPreview`, `QueryChart`, `QueryTable`, `SimulationSummary`.

| component | props |
| --- | --- |
| `SqlPreview` | `sql: string`, `title?: string` |
| `QueryChart` | `resultId: 32자 소문자 hex`, `chartType: "bar"\|"line"\|"area"`, `xColumn`, `yColumn`, `groupByColumn?: string\|null`, `aggregation?: "sum"\|"avg"\|"count"\|"min"\|"max"`, `title?` |
| `QueryTable` | `resultId`, `columns?: string[]`, `title?` |
| `SimulationSummary` | `scenario`, `summary`, `kpis[{label, value: string\|number, unit?}]`, `resultId?`, `children?`(`QueryChart`/`QueryTable`만) |

범용 레이아웃·텍스트·상태 component와 기본 `Chart`·`Table`(inline `data` 요구), `Image`, `Markdown`, `Box`의 임의 background, form/control/action component는 제외한다. 일반 설명은 공개 답변 text가 담당하고 검증된 로딩·경고·오류는 도메인 component 내부에서 표시한다. `title`·`resultId` 등 공유 prop은 모든 component에서 같은 타입이다.

Tool schema와 별도로 실행 시 재검증한다.
- JSON 직렬화 크기 최대 64 KiB, 깊이 최대 8, 전체 node 최대 50.
- allowlist 밖 `component`(변환 후 `$type`), component별 미등록 prop, `$` 예약 prop(변환된 `$type`·`$key` 제외) 거부.
- `rows`·`data`·`series` 등 원본/차트 데이터 배열을 담는 prop 거부.
- 문자열 길이·`children` 형태·`resultId` 형식 검증. `resultId`는 호출한 scope에서 접근 가능한 결과여야 한다.
- URL·HTML·Markdown·임의 CSS·이벤트/action prop 불허.
- 실패는 `{status:"error", code, message}`(안전한 문구만), 성공은 `{}`이며 기존 `tool_result` 이벤트로 전달한다.

SSE 순서(기존 event type 안):

```text
execute_sql 또는 run_simulation tool_call/tool_result
→ present tool_call → present tool_result {}
→ 후속 text → done {turn_id}
```

### 3.2 Result preview (`present` 모드의 `execute_sql`·`run_simulation`)

```json
{ "status": "ok", "kind": "database", "result_id": "0123456789abcdef0123456789abcdef",
  "row_count": 120, "source_truncated": false,
  "columns": [{"name": "work_month", "dtype": "string", "role": "time"}, {"name": "actual_qty", "dtype": "number", "role": "measure"}],
  "sample_rows": [{"work_month": "2026-01", "actual_qty": 1200}],
  "date_ranges": {"work_month": {"min": "2026-01", "max": "2026-12"}},
  "distinct_counts": {"work_month": 12},
  "statistics": {"actual_qty": {"min": 900, "max": 1400, "avg": 1175, "sum": 14100, "null_count": 0}},
  "top_groups": {"work_month": [{"value": "2026-01", "count": 1}]} }
```

- `sample_rows`는 최대 5개이며 catalog에 노출 가능한 조회 컬럼만 담는다. 통계·그룹 목록은 표현 판단용 bounded metadata이고 그룹 값은 컬럼당 최대 10개다.
- simulation은 위 필드와 함께 `simulation_type`, `scenario`, `summary`, `kpis`를 유지할 수 있으나 원본 결과 행은 넣지 않는다.
- SQL 원문은 `execute_sql` Tool args로만 공개하며 preview API와 오류에 반복하지 않는다.

### 3.3 Result HTTP API

읽기 전용이며 CORS·credential 정책은 기존 API와 같다. 응답은 `Cache-Control: private`, `Vary: Cookie`, 내부 경로·scope·SQL을 노출하지 않는다.

- `GET /api/query-results/{result_id}/preview` → 3.2의 metadata(원본 전체 행·parquet 경로·scope·conversation 식별자 제외).
- `GET /api/query-results/{result_id}/table?page=1&page_size=10&columns=a&columns=b&search=&sort_column=&sort_direction=`
  → `page` 1 이상, `page_size` 1~100(기본 10), `columns` 선택적 반복, `search` 200자 이하,
  `sort_direction` asc/desc. 저장된 최대 1,000건을 검색·정렬한 뒤 page를 반환하며 응답은
  `{status:"ok", result_id, page, page_size, row_count, filtered_row_count, source_truncated, columns[{name,dtype,role}], rows[[…]]}`.
- `GET /api/query-results/{result_id}/chart?chart_type=&x_column=&y_column=&group_by_column=&aggregation=&title=` → 검증된 payload
  `{status:"ok", result_id, chart:{type, x, series[{key,label}], categories[], data[{…}], title, x_label, y_label, unit}, warnings[{code,message}]}`.

Chart 검증·축약 규칙:
- 모든 컬럼 존재 여부, 중복 mapping, dtype/role, 유한 숫자, null을 서버에서 검사. `y_column`은 count 이외에는 실제 numeric measure 컬럼, `x_column`은 category 또는 time.
- `aggregation` 생략 시 `(x_column, group_by_column)` grain이 유일한 경우에만 허용, 중복이면 `AGGREGATION_REQUIRED`.
- line/area의 x는 날짜·연월로 정렬 가능한 값이어야 한다.
- 집계 후 series 최대 8개(초과 그룹은 절대 집계값 상위 8개 + warning). x point 최대 500개(시계열은 일→주→월→분기→연 순으로 필요한 최소 단위까지 재집계, bar 범주는 절대 집계값 상위 500개 + warning).
- 빈 결과나 표현 불가능한 값은 빈 chart를 만들지 않고 오류를 반환한다.

오류: 없음·만료·다른 `pp_session_scope`는 모두 404 `RESULT_NOT_FOUND`. 요청 형식 422 `INVALID_REQUEST`, `COLUMN_NOT_FOUND`, `INVALID_COLUMN_ROLE`, `AGGREGATION_REQUIRED`, `EMPTY_RESULT`.
detail에는 SQL·원본 값 목록·파일 경로·provider 메시지·scope를 넣지 않는다.

### 3.4 후속질문 (`done.data.suggestions`, 선택)

- 출력: 성공한 `done.data.suggestions?: string[]` — 2~4개, 각 1~120자, 중복·빈 문자열 제거, 한국어 사용자 표현. 오류·취소·파싱 실패 시 필드를 생략하거나 빈 배열로 종료한다. 오류 흐름은 여전히 `error` 다음 `done`이다.
- 규칙: 비공개 추론을 노출하지 않고 데이터에 종속된 답을 담지 않으며 다음 질문 문구만 낸다. 제안 생성 실패가 응답 자체를 실패시키지 않는다.

### 3.5 대화·분기 영속 API (설계만, 이 계획에서 구현하지 않음)

- 착수 조건: 인증 principal 계약과 저장소(폐쇄망 반입 가능) 결정. 현재 stub principal은 보안 경계가 아니므로 그 위에 소유권을 얹지 않는다.
- 현재 한계: `conversation_id → session_id`와 `turn_id → TurnAnchor`는 `agent/session_store.py` 프로세스 메모리이며 재시작 시 소실되어 이전 `turn_id`로 fork하면 `error` 후 새 세션이 된다. 대화·메시지 조회·목록·삭제 API가 없다.
- 요청 계약 초안: `GET /api/conversations`(소유자 범위 `[{id,title,updated_at}]`), `GET /api/conversations/{id}`(메시지 트리 `[{id,parent_id,role,parts[],status,turn_id?}]`와 head),
  `PATCH`(제목), `DELETE`. 403/404 구분, 삭제 후 404, 저장소 오류 503(경로 미노출).
- 결정 필요: 저장소(SDK 세션 파일은 메시지 조회용이 아님 → 별도 store), fork 앵커 영속화(재시작 후 fork 가능 여부), 보존 기간, Result Store TTL(24h)과의 관계(만료된 result 참조 표시).

## 4. 통합 실행 순서

양 workspace가 같은 순서를 따른다. B는 Backend 단계이며 각 단계는 독립 커밋이다.

| 순서 | 단계 | 소비자 쪽 조건 |
| --- | --- | --- |
| 0 | B0 안전망 | 없음 |
| 1 | **B1 가산 구현**(Result API·preview service·`present` Tool·플래그, 기본 `legacy`) | 없음. 기존 동작 불변 |
| 2 | (소비자가 `present`와 preview를 양 shape로 렌더 가능하게 준비) | B1의 API 응답 shape를 fixture로 제공 |
| 3 | **B2 플래그 `present` 전환** | 소비자 준비 완료 확인 |
| 4 | B3 후속질문(선택) | B1 이후 언제든 |
| 5 | B4 대화 영속 | 수행 범위 밖, 3.5 설계만 |

## 5. 단계별 작업

### B0 — 안전망
- [ ] `source .venv/bin/activate && python -m pytest -q` 기준선을 기록한다.

### B1 — 가산 구현 (`legacy` 기본, 기존 동작 불변)
- [ ] preview service: Result Store metadata와 DataFrame에서 공통 preview를 만들고 SQL mock/real, simulation mock/real 반환 shape에 적용(플래그가 `present`일 때만 payload에 사용).
- [ ] table route/schema: page offset·선택 컬럼 검증은 service 계층에 둔다(route에 업무 로직 금지).
- [ ] chart projection: 기존 visualization 검증·직렬화를 **저장 없는** projection 함수로 분리하고 aggregation·area·상위 그룹·time bucket을 추가한다. `/api/visualizations`는 기존 동작 유지.
- [ ] preview/table/chart route는 service error를 3.3의 HTTP 계약으로 변환한다.
- [ ] `present` Tool: 읽기 전용 vocabulary JSON Schema와 재귀 validator(`agent/sdk_tools.py` 등록, `TOOL_NAMES`·`tool_catalog()` 반영). 소비자 schema와 비교 가능한 안정 계약으로 취급한다.
- [ ] `RESULT_UI_MODE` 플래그(`core/config.py`, `.env.example`). `legacy`에서는 `present`가 등록되지 않는다.
- 검증: `legacy` 모드 회귀(전 테스트 통과), 신규 API·validator 단위 테스트.

### B2 — `present` 전환
- [ ] `present` 모드: `execute_sql`·`run_simulation` preview-only payload, `planning_tools()`에서 `prepare_*` 제외·`present` 포함, `run_agent`의 누락 표 자동 보완 제거.
- [ ] 런타임 지침(`agent/agent_sdk/CLAUDE.md`, 관련 `.claude/skills/*/SKILL.md`)에 다음 규칙을 추가한다(스키마·업무 정의를 세 계층에 복제하지 않는다).
  - SQL·simulation 성공 뒤 보여줄 결과가 있으면 합성 `present`를 한 번 호출, SQL은 `SqlPreview`(기본 접힘).
  - 비교·추이에는 `QueryChart`, 상세 행에는 `QueryTable`. 숫자 컬럼이 없거나 chart 명세를 확정할 수 없으면 표와 설명만 사용.
  - 전체 행·chart data를 `present`에 복사하지 않고 `resultId`만 전달. 성공한 UI를 Markdown 표나 chart code fence로 중복하지 않는다.
- [ ] 문서 갱신: `AGENTS.md`("run_agent 자동 표 보완", "`prepare_visualization`이 등록하는 차트", "SQL·시뮬레이션 결과에 자동 차트 없음" 서술), README, `docs/CLOSED_NETWORK_SETUP.md`, 런타임 CLAUDE 지침.
- [ ] legacy 제거 후속 항목을 `Todo.md`에 남긴다(운영 검증 1주기 뒤 호출 로그·저장 대화 호환성 확인).
- 검증: 관통 시나리오(아래 6절)와 `pytest -q`. 실제 provider 환경에서는 별도 e2e로 Tool 호출 순서를 확인한다.

### B3 — 후속질문 (선택)
- [ ] 성공한 `done`에 3.4의 `suggestions`를 추가한다. 모델 출력 파싱 실패 시 빈 배열로 안전하게 종료한다.
- 검증: 파싱 실패·빈 출력·초과 개수·과장 길이 단위 테스트, 기존 `done.turn_id` 계약 회귀.

### B4 — 대화 영속
- [ ] 이 계획에서는 3.5 설계 기록만 유지한다. 인증 principal 계획과 함께 별도 계획으로 착수한다.

## 6. 테스트와 완료 조건

### 단위·API 테스트
- preview sample ≤5행이고 전체 `rows/table/results`를 포함하지 않으며 SQL과 simulation이 같은 preview 원칙을 지킨다.
- table API 기본 10행·최대 100행, page/columns/search/sort 검증, 저장된
  최대 1,000건에 검색·정렬을 먼저 적용, source truncation 표시.
- bar/line/area, 집계 5종, group series, time 정렬·bucket, deterministic top-N.
- 없는 컬럼, 문자열 y, 중복 grain, NaN/무한대, null x/group, 빈 결과 오류.
- 같은 scope 성공, 다른 scope·만료·없는 ID의 **동일한** 404 응답.
- `present` 정상 중첩, 알 수 없는 type/prop, 데이터 배열, 크기·깊이·node 제한, 접근 불가 `resultId`, `children` 허용 위치.
- Tool schema의 선택 필드와 업무 함수 기본값의 일치, 플래그별 `planning_tools()` 집합.
- SDK event 순서와 후속 text·`done.turn_id` 유지, thinking·내부 오류 비노출.
- `legacy` 모드와 legacy visualization API·저장 metadata 회귀, 잘못된 `RESULT_UI_MODE` 값 시작 실패.

### 관통 시나리오
1. 월별 범주 비교: SQL → preview → bar `QueryChart` + `QueryTable` → 해석.
2. 그룹별 시계열: group 설정 → line series → 해석.
3. 숫자 컬럼 없음: chart 없이 `QueryTable`과 설명.
4. simulation: `SimulationSummary` + 동일 `resultId`의 표/차트.
5. 잘못된 컬럼: 422와 수정 가능한 안전 메시지, SQL·DB 정보 비노출.
6. 저장 상한 초과: LLM/present에 전체 행이 없고 `source_truncated` 경고 유지.
7. 모델이 잘못된 `present`를 보낸 뒤 수정 호출: 실패 결과 → 성공 결과 순서가 이벤트로 그대로 전달.

완료: B0~B3 완료(B4 제외), `pytest -q` 통과, 실제 검증 수치와 결정은 `Todo.md`에 통합한다.

## 7. 위험 요소와 롤백

- 롤백: `RESULT_UI_MODE=legacy`로 되돌리면 `prepare_*` 흐름과 인라인 payload가 복원된다. 단계별 `git revert`도 가능하다.
- `legacy` 모드의 동작이 B1에서 바뀌는 실수 — 회귀 테스트를 B1의 필수 조건으로 한다.
- 소비자 schema와의 드리프트 — 3.1 표를 계약으로 고정하고 Tool schema 정합 테스트를 둔다.
- 모델이 `present`를 호출하지 않거나 반복 실패 — 텍스트·표 fallback 지침, 실제 provider e2e로 확인. 자동 표 보완 제거로 표가 비는 경우가 있는지 관통 시나리오로 확인.
- Result Store TTL(24h) 만료 후 참조 — 404 단일 응답과 재실행 안내가 소비자 책임임을 문서화한다.
- 플래그 기본값 전환 시점 — 운영 검증 결과로 별도 결정한다.
