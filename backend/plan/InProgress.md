# Backend 진행 중 및 현재 계약

진행 중인 작업의 목표·결정·막힌 점과 현재 유효한 구현·계약을 기록한다. [할 일과 아이디어](Todo.md) · [완료 이력](History.md)

## 진행 중인 작업

현재 착수 상태로 기록된 작업은 없다. 착수 시 담당 범위, 현재 단계, 다음 행동, 검증 상태를 이곳에 기록한다.

## 목표와 책임

FastAPI와 Claude Agent SDK를 사용해 생산계획 데이터를 자연어로 조회·분석하고,
읽기 전용 SQL·입력 검증 simulation·지식 검색·표·차트 결과를 안정적인
`AgentEvent` SSE로 제공한다.

Backend가 소유하는 범위는 다음과 같다.

- API schema, SSE 변환, Agent 실행과 세션·포크·취소 lifecycle
- 구조화 YAML 및 버전형 텍스트 지식의 로드·검증·검색
- 읽기 전용 SQL 가드, mock/production service 경계와 simulation registry
- Result Store, 표 payload, 시각화 명세와 access scope·TTL
- 폐쇄망 실행·운영 문서, 오류 은닉과 service logging

운영 데이터 쓰기와 근거 없는 업무 수치 생성은 범위 밖이다. 모델 thinking(chain-of-thought)은
어떤 경우에도 공개하지 않는다. 실제 사내 DB·RAG·simulation 연동은 아직 후속 작업이다.

## 현재 구현 상태

| 영역 | 상태 | 현재 기준 |
| --- | --- | --- |
| 채팅·Agent SSE | 완료 | `text`, `status`, `tool_call`, `tool_result`, `error`, `done`; delta 중복 제거, 안전한 종료·취소·포크 |
| Tool trace | 완료 | 동일 호출의 `tool_call_id`, 공개 가능한 args와 결과 연결 |
| 구조화 지식 | 완료 | table·KPI·recipe·scenario·simulation·glossary YAML 검증과 조회 Tool |
| 텍스트 지식 | 완료 | SQLite 버전·revision 충돌·검토·활성화·보관·local 검색 |
| 구조화 지식 변경·승인 | 완료 | 변경 요청(초안·제출·승인·반려)·정합성 게이트·승인 시 YAML 원자 반영·즉시 reload, principal 스텁 |
| SQL | Mock 완료 / Production stub | 등록 table만 허용하는 SELECT/WITH, 1,000행 저장 상한 |
| Simulation | Mock 완료 / Production stub | 합성 mock SEG_A/SEG_B 입력 관계·정합성 검증 |
| Result Store | 1차 완료 | parquet+metadata, TTL·용량 정리, browser access scope |
| 결과 API·표·시각화 | 완료 | `/api/query-results/{id}/preview|table|chart`, `present_sql_preview`·`present_chart`·`present_table`·`present_simulation` flat Tool·검증(유일한 결과 표시 경로, 최대 500 points·8 series), `present_chart.bar_mode=grouped|stacked` |
| RAG | Local 완료 / Vector 미구현 | 활성 검토 문서 local 검색; Milvus·문서 색인 후속 |
| 실행 환경 | 완료 | Python 3.11 `.venv`, Backend 기본 포트 8100 |
| LLM provider | 완료 | `anthropic`·`openrouter`·`azure_openai`(백엔드 `/anthropic` 프록시가 Anthropic Messages↔Azure OpenAI chat completions 변환, 프로세스별 토큰 인증)·`local`(폐쇄망 구현 반입 전 501) |
| Service logging | 완료 | 공개 작업 시작·완료·실패, 소요 시간, 중첩 DEBUG와 민감정보 비노출 |

## 외부에 제공하는 안정 계약

상대 workspace 문서를 참조하지 않고 아래 계약을 Backend 자체 기준으로 유지한다.

### AgentEvent

- 안정 event type: `text`, `status`, `tool_call`, `tool_result`, `error`, `done`.
- 같은 Tool 호출은 안정적인 `tool_call_id`를 공유한다.
- `tool_call.data.args`에는 공개 가능한 모델 입력만 포함한다.
- 성공한 `done.data.turn_id`만 이후 포크 anchor로 사용한다.
- 성공한 `done.data.suggestions?: string[]`는 선택 필드다. 앞뒤 공백·중복을 제거한
  2~4개의 한국어 질문(각 1~120자)만 싣고, 형식이 맞지 않거나 Agent가 등록하지
  않았으면 생략한다. 오류·취소 turn의 `done`에는 붙이지 않는다. 출처는 내부 Tool
  `suggest_follow_ups`이며 이 Tool은 `tool_call`·`tool_result`·`status`로 공개하지 않는다.
- streaming 실패는 내부 예외를 숨긴 `error` 다음 terminal `done`을 보낸다.
- 모델 thinking(`ThinkingBlock`), signature와 불완전 Tool JSON은 공개하지 않는다.

### 결과와 시각화

- `execute_sql`과 simulation 결과는 `result_id`로 Result Store에 저장한다.
- 내부 파일 경로, access scope 값과 원본 대량 행은 Tool payload에 넣지 않는다.
- `execute_sql`·`run_simulation`은 bounded preview(`result_id`, `row_count`,
  `source_truncated`, `columns`, `sample_rows`(≤5, 객체), `date_ranges`, `distinct_counts`, `statistics`,
  `top_groups`(컬럼당 ≤10); simulation은 `simulation_type`·`scenario`·`summary`·`kpis`; SQL은 `purpose`만)만 반환하고,
  flat(스칼라 인자) Tool 4개를 등록한다: `present_sql_preview(sql, title?)`,
  `present_chart(result_id, chart_type, x_column, y_column, group_by_column?, aggregation?, title?, bar_mode?)`,
  `present_table(result_id, columns?, title?)`, `present_simulation(scenario, summary, kpis, result_id?)`.
  (과거에는 `present` tool 하나가 UI 트리 전체를 `tree` JSON-문자열 하나로 받았으나, 실제
  tool-calling 모델이 문자열 타입을 지키지 못해 Claude Agent SDK의 강제 `jsonschema.validate`에
  막혀 `is_error=True`로 반복 실패하는 문제(2026-09-22 확인·재현)가 있어 이중 인코딩 자체를
  없앴다. `resultId`·chart 설정을 실제 결과로 재검증하고, 성공 `{}`/실패
  `{status:"error", code, message, details.path}`를 반환하는 계약은 그대로다. 여러 결과를
  한 화면에 시각적으로 묶는 기능(과거 `Card`)은 없다 — 같은 `result_id`로 여러 `present_*`를
  호출해도 화면에는 순차적으로 나열되며 연결은 모델이 텍스트로 설명한다. 자동 표 보완은
  하지 않는다.
- `present_chart.bar_mode`는 선택 enum `grouped|stacked`이며 기본은 `grouped`다.
  `stacked`는 막대 차트에서만 허용하고 `group_by_column`이 필요하다. 표시 모드만
  바꾸므로 `/api/query-results/{id}/chart` 응답 payload는 바뀌지 않는다.
- `GET /api/query-results/{result_id}/preview|table|chart`(같은 `pp_session_scope`): table `page`·`page_size`(기본 10, ≤100)·
  `columns`·`search`(≤200)·`sort_column`·`sort_direction(asc|desc)`를 저장된 최대 1,000건 전체에 적용하고
  `row_count`·`filtered_row_count`와 현재 page를 반환한다. chart는 `chart_type(bar|line|area)`·`x_column`·`y_column`·
  `group_by_column`·`aggregation(sum|avg|count|min|max)`·`title`.
  없음·만료·타 scope는 404 `RESULT_NOT_FOUND`(동일 응답), 422 `INVALID_REQUEST`·`COLUMN_NOT_FOUND`·`INVALID_COLUMN_ROLE`·
  `AGGREGATION_REQUIRED`·`EMPTY_RESULT`·`UNRENDERABLE_VALUES`. chart는 series ≤8(초과 시 상위만+`SERIES_LIMITED`),
  point ≤500(시계열은 `TIME_BUCKETED`, 범주는 `CATEGORIES_LIMITED`; 시계열 재집계는 aggregation 필요).

### 지식과 SQL

- 실행 중인 `KNOWLEDGE_DIR` YAML이 구조화 지식의 source of truth다. 개발 기본은
  `knowledge/mock/`, 폐쇄망 반입 기본 위치는 `knowledge/production/`이다.
- `query_rules`, `aggregation_rules`, `visualization_hints`의 역할을 섞지 않는다.
- table/recipe `sample_queries`는 `question`, `sql`만 허용한다.
- SQL은 항상 조회 전용이며 mock과 production 구현의 함수 시그니처·반환 형태를 맞춘다.
- `ENV=prod`는 `SERVICE_MODE=production`(기존 `real` 별칭 허용)과 bundled mock 지식이 아닌 명시적인
  운영 `KNOWLEDGE_DIR`을 요구한다. 조건이 맞지 않으면 시작 단계에서 실패한다.

### 구조화 지식 변경 요청·승인

구조화 YAML은 직접 수정 API가 없고 변경 요청이 승인될 때만 파일이 바뀐다. 상세 절차와
운영 전제는 `docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md`의 "구조화 지식 변경 요청과 승인"이 기준이다.

- 권한: 요청마다 `X-User-Id`(생략 시 `KNOWLEDGE_DEFAULT_PRINCIPAL`)를 `KNOWLEDGE_PRINCIPALS`와
  대조한다. 권한은 `knowledge:write`(작성·제출·철회), `knowledge:approve`(승인·반려)다.
  알 수 없는 id·권한 부족·`KNOWLEDGE_MANAGEMENT_ENABLED=false`는 403 `{"detail"}`이다.
  스텁은 보안 경계가 아니며 실제 인증이 오면 `core/principal.py::current_principal`만 바꾼다.
- `GET /api/me` → `{id, name, permissions[], mode: "stub"|"authenticated",
  knowledge_management, allow_self_approval, stub_users[{id,name}]}`. `stub_users`는 스텁에서만 채운다.
- `GET /api/knowledge/guides/{kind}` → `{kind, key_field, fields[], template, immutable[]}`.
  `fields[]`는 `{name, path, label, help, required, readonly, widget, example?, group?,
  options?, item_widget?, fields?, value?}`이며 widget은 string·text·sql·boolean·number·date·enum·
  string_list·record_list·object·map·json이다. 구조는 pydantic 모델, 문구는
  `services/knowledge/guides.py`가 소유한다. `item_widget`(string|text)은 string_list 항목이 여러 줄 입력이 필요한지 알린다.
  `template`은 필수 필드만 빈 값으로 채운 골격이다.
- `GET /api/knowledge/source/{kind}/{key}` → `{kind, key, yaml, data}` 현재 항목의 정규화 내용(404).
- `POST /api/knowledge/validate` `{kind, key?, yaml|data}` → 200 `{ok, parsed, yaml, data, key,
  errors[{path, line, message}]}`. `yaml`(원문)과 `data`(폼) 중 정확히 하나만 보낸다.
  `key`가 있으면 기존 항목 수정으로 보고 식별자 변경을 막는다. `parsed`는 입력이 mapping으로
  읽혔는지이며 `data` 입력이 모델 검증에 실패해도 원문 탭용 `yaml`을 돌려준다. 저장하지 않는다.
- `GET /api/knowledge/changes?state=&kind=&mine=` → 요약 목록
  `{id, kind, key, is_new, state, revision, author{id,name}, created_at, updated_at}`.
- `POST /api/knowledge/changes` `{kind, key?, yaml|data}` → 201 상세. `key` 없으면 신규 항목.
  `GET /changes/{id}` 상세는 요약에 `yaml, data, current_yaml, history[]`를 더한다.
  history: `{revision, action, actor_id, actor_name, note, self_approved, at}`,
  action은 create·save·submit·withdraw·approve·reject.
- `PUT /changes/{id}` `{expected_revision, yaml|data}`, `POST /changes/{id}/{submit|withdraw|
  approve|reject}` `{expected_revision, note}`. approve·reject는 `knowledge:approve`와 note가 필요하다.
- 오류: 403 권한·작성자 아님·자기 승인, 404, 409 revision 충돌·진행 중 요청 존재·기준 변경·
  상태 불일치·이미 있는 키, 422 검증 실패, 503 저장소·반영 실패(경로 미노출).
- `GET /api/knowledge/entries`는 scenario를 포함하고 각 행에 `pending_change{id,state}|null`을 더한다.

## 검증 기준과 알려진 한계

- 기본 검증: `source .venv/bin/activate && python -m pytest -q`.
- 2026-09-23 기준 전체 개발 검증: **377 passed, 6 deselected**. 마커 제외
  프로필(`not bundled_knowledge and not mock_service and not e2e`)은
  **312 passed, 71 deselected**다. 이 검증은 실제 사내 provider 연결을 포함하지 않는다.
- 재측정한 검증은 Starlette TestClient의 upstream deprecation warning 1건만 남는다.
- E2E는 실제 CLI/provider 인증이 있는 환경에서만 `python -m pytest -m e2e`로
  실행한다.
- 실제 provider 성공 응답, 실제 업무 데이터 정의와 폐쇄망 인프라 연결은 검증되지
  않았다.
