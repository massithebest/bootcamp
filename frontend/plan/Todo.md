# Production Planning Agent Frontend 계획 및 이력

**상태: 진행 중. 마지막 갱신: 2026-09-22.**

이 문서는 Frontend 작업의 목표, 기대 API 계약, 다음 작업과 완료 이력을 관리하는
단일 기준 문서다. 폐쇄망 반입 후 Frontend workspace만 열어도 이해할 수 있도록
다른 workspace의 계획 문서를 전제로 하거나 링크하지 않는다.

## 목표와 책임

Vite·React·assistant-ui 기반 3-pane Agent Workbench에서 생산계획 Agent의
streaming 답변, 공개 실행 단계, Tool 결과, 표·차트와 지식 관리를 정확하고
접근 가능하게 제공한다.

Frontend가 소유하는 범위는 다음과 같다.

- 브라우저 SSE transport와 Backend conversation·fork 대응(메시지·분기·취소·편집·재생성 상태는 runtime)
- assistant-ui LocalRuntime(`ChatModelAdapter`)·세션 내 thread 목록과 Thread·Composer·메시지 렌더링
- Tool 실행 과정, 독립 표·차트와 안전한 payload parser
- Sidebar, Knowledge Manager, Context Inspector와 반응형 3-pane layout
- 접근성, focus·keyboard·reduced-motion, loading·empty·error 상태
- 폐쇄망 build·asset·환경 설정과 브라우저 회귀 검증

브라우저의 LLM 직접 호출, Cloud persistence, 원격 asset/CDN, 모바일 전용 UX와
Backend에 없는 기능을 동작하는 것처럼 표시하는 것은 범위 밖이다.

## 현재 구현 상태

| 영역 | 상태 | 현재 기준 |
| --- | --- | --- |
| 채팅 runtime | 완료 | LocalRuntime + SSE `ChatModelAdapter`, 분기(BranchPicker)·취소·편집·재생성, 다중 thread(브라우저 세션) |
| 메시지 lifecycle | 완료 | complete/cancelled/error, 부분 응답과 terminal event 구분 |
| 실행 과정 | 완료 | 공개 status, ToolGroup, 호출 ID별 args/result와 2단계 disclosure |
| 표 | 완료 | legacy 최대 100행 local 표 + `QueryTable` 최대 1,000건 서버 검색·정렬·10/25/50/100 pagination |
| 차트 | 완료 | legacy 검증 API bar/line + 조합형 `QueryChart`(bar/line/area, 서버 집계), loading/error와 데이터 표 대안 |
| 조합형 결과 | 구현(플래그 대기) | `present` Generative UI(`SqlPreview`·`QueryChart`·`QueryTable`·`SimulationSummary`); Backend `RESULT_UI_MODE=present` 전환 후 사용 |
| 후속질문 | 파서·UI 완료 | `done.data.suggestions`를 Backend가 보내면 표시(현재 미전송) |
| 지식 관리 | 완료 | 구조화 지식 조회·수정 요청·검토·승인(가이드 폼·원문 YAML·diff), 텍스트 등록·검토·활성화, 정확한 버전 인용 |
| Layout | 완료 | Sidebar·Chat·Inspector, Inspector resize, 좁은 화면 overlay |
| 접근성 감사 | 범위 내 완료 | keyboard/focus/label/landmark/reduced-motion/긴 문자열/0행·빈 응답 |
| 세션 목록 | 세션 내 유지 | ThreadListPrimitive, 브라우저 세션 동안만 유지; 영속 저장은 미구현 |
| 실행 환경 | 완료 | Frontend 기본 포트 3100, API 기본 주소 8100 |

## Backend에 기대하는 안정 계약

Frontend는 상대 workspace 문서를 읽지 않고 아래 입력 계약만 전제로 한다. 계약이
달라지면 이 문서를 먼저 갱신하고 parser·fixture·UI를 같은 작업에서 변경한다.

### AgentEvent와 메시지

- event type: `text`, `status`, `tool_call`, `tool_result`, `error`, `done`.
- `tool_call_id`는 같은 호출의 args와 결과를 연결한다.
- 성공한 `done.data.turn_id`는 편집·재생성의 `fork_from_turn_id`로 사용한다.
- 오류 흐름은 `error` 다음 terminal `done`으로 끝난다.
- `done.data.suggestions`(후속질문)는 선택 필드다. 엄격히 검증하고 없으면 표시하지 않는다.

### 조합형 결과 (`RESULT_UI_MODE=present`)

- Frontend가 받는 `present` Tool args root는 wrapper 없는 assistant-ui 표준 `$type` node(`$key` 선택)이며 허용 vocabulary는 여러 결과를 묶는 `Card`와 도메인 `SqlPreview`·`QueryChart`·`QueryTable`·`SimulationSummary`다. 범용 레이아웃·텍스트·상태 node는 허용하지 않고 일반 설명은 Assistant Markdown이 담당한다. prop 계약은 `tests/fixtures/present-vocabulary.json`과 `components/chat/generative/vocabulary.ts`.
  provider에 노출되는 Tool은 `tree` JSON 문자열을 받고, 그 안의 node도 assistant-ui 표준 `$type`/`$key`를 쓴다. Backend가 파싱·검증한 뒤 같은 트리를 공개 AgentEvent에 싣는다.
  Frontend는 backend Tool UI에서 package의 `renderGenerativeUI`로 그린다. `present` 결과는 성공 시 빈 객체, 실패는
  `{status:"error", code, message, details.path}`다.
- 이 모드의 `execute_sql`·`run_simulation` 결과는 전체 행 없이 preview(`result_id`, `row_count`, `columns`, `sample_rows`(객체,
  최대 5), `date_ranges`, `distinct_counts`, `statistics`, `top_groups`; simulation은 `simulation_type`·`scenario`·`summary`·`kpis`)다.
- `GET /api/query-results/{resultId}/table?page&page_size(≤100)&columns=…&search=&sort_column=&sort_direction=asc|desc`
  → `{status, result_id, page, page_size, row_count, filtered_row_count, source_truncated,
  columns[{name,dtype,role}], rows[[…]]}`. `QueryTable`은 TanStack Table 수동 모드로 저장된
  최대 1,000건 전체에 서버 검색·정렬을 적용하고 기본 10행씩 page를 받는다.
  `GET /api/query-results/{resultId}/chart?chart_type&x_column&y_column&group_by_column&aggregation&title` →
  `{status, result_id, chart{type(bar|line|area), x, series[], categories[], data[], title, x_label, y_label, unit}, warnings[]}`,
  `…/preview`. 없음·만료·타 세션은 동일한 404 `RESULT_NOT_FOUND`, 요청 오류는 422
  (`INVALID_REQUEST`·`COLUMN_NOT_FOUND`·`INVALID_COLUMN_ROLE`·`AGGREGATION_REQUIRED`·`EMPTY_RESULT`·`UNRENDERABLE_VALUES`).
- `done.data.suggestions?: string[]`(2~4개, 각 1~120자)는 선택 필드다. 형식이 다르면 표시하지 않는다.

### 표·차트·지식

- `prepare_table` 성공 결과는 columns, rows, row_count, displayed_count와
  source_truncated를 포함하며 rows는 최대 100행이다.
- `prepare_visualization` 성공 결과의 `visualization_id`로
  `/api/visualizations/{id}`를 조회한다.
- 지식 API는 Tool·Skill·구조화 entry와 버전형 text document, 구조화 지식 변경 요청을 제공한다.
- 문서 검색 Tool 이름은 `search_documents`이며 결과 `kind`는 `knowledge`다.
- 브라우저는 credential cookie를 포함하고 내부 path·scope를 표시하지 않는다.
- malformed·oversized·알 수 없는 payload는 안전한 오류 UI로 전환한다.

### 구조화 지식 변경 요청

구조화 YAML은 직접 수정 API가 없고 변경 요청이 승인될 때만 바뀐다. 요청마다 브라우저는
저장된 임시 사용자 id를 `X-User-Id`로 보낸다(없으면 서버 기본 사용자).

- `GET /api/me` → `{id, name, permissions[], mode: "stub"|"authenticated", knowledge_management,
  allow_self_approval, stub_users[{id,name}]}`. 권한은 `knowledge:write`(작성·제출·철회),
  `knowledge:approve`(승인·반려)다. 응답이 이 형태가 아니면 쓰기 UI를 켜지 않는다(읽기 전용).
  `stub_users`는 `mode: "stub"`일 때만 채워지며 이때만 사용자 선택기를 보인다.
- `GET /api/knowledge/guides/{kind}` → `{kind, key_field, fields[], template, immutable[]}`. kind는
  table·kpi·recipe·simulation·glossary·scenario. `fields[]`는 `{name, path, label, help, required,
  readonly, widget, example?, group?, options?, item_widget?, fields?, value?}`이며 widget은 string·
  text·sql·boolean·number·date·enum·string_list·record_list·object·map·json이다(`value`는 map의
  값 명세). `template`은 필수 필드만 빈 값으로 채운 골격이다.
- `GET /api/knowledge/source/{kind}/{key}` → `{kind, key, yaml, data}` 현재 승인본의 정규화 내용.
- `POST /api/knowledge/validate` `{kind, key?, yaml|data}` → 200 `{ok, parsed, yaml, data, key,
  errors[{path, line, message}]}`. `yaml`(원문)과 `data`(폼) 중 정확히 하나만 보낸다. `key`가 있으면
  기존 항목 수정이다. `parsed: false`면 폼으로 옮길 수 없다. 저장하지 않는다.
- `GET /api/knowledge/changes?state=&mine=` → `[{id, kind, key, is_new, state, revision,
  author{id,name}, created_at, updated_at}]`. state는 draft·submitted·approved·rejected·withdrawn.
- `POST /api/knowledge/changes` `{kind, key?, yaml|data}` → 201 상세(요약 + `yaml, data, current_yaml,
  history[{revision, action, actor_id, actor_name, note, self_approved, at}]`). `key`가 없으면 신규.
  `GET /changes/{id}`는 상세, `PUT /changes/{id}` `{expected_revision, yaml|data}`는 수정.
- `POST /changes/{id}/{submit|withdraw|approve|reject}` `{expected_revision, note}`. approve·reject는
  `knowledge:approve`와 note가 필요하다. 승인하면 서버가 YAML을 쓰고 즉시 반영한다.
- 오류(`{"detail"}`): 403 권한 없음·작성자 아님·자기 승인, 404, 409 revision 충돌·진행 중 요청
  존재·기준 변경·상태 불일치, 422 검증 실패, 503 저장소·반영 실패. 화면은 상태 코드별 문구만 쓴다.
- `GET /api/knowledge/entries`는 scenario를 포함하고 각 행에 `pending_change{id,state}|null`이 있다.

## 다음 작업

### P1

- [ ] **조합형 결과 운영 전환**: Backend가 `RESULT_UI_MODE=present`로 전환된 환경에서 관통 검증(SQL·simulation →
  `present` → 표·차트·SQL)하고 legacy `prepare_*` renderer·`chart` marker·`/api/visualizations` client 삭제 계획을 별도로 만든다.
- [ ] **후속질문 표시 검증**: Backend가 `done.data.suggestions`를 보내면 실제 응답에서 표시·전송·오류/취소 미표시를 확인한다.

### P2

- [ ] 실제 screen reader와 긴 대화 성능을 운영 환경에서 검증한다.
- [ ] 인증 principal이 연결되면 임시 사용자 선택기와 `lib/knowledge-user.ts`를 제거하고
  `GET /api/me`만으로 권한을 표시한다.
- [ ] Fast Refresh lint warning과 production bundle 크기 경고를 기능 변경과
  분리해 정리한다.
- [ ] 실제 모델 설정 API가 제공될 때 현재 비활성 모델·추론 강도 control의 표시
  정책을 재검토한다. API가 없으면 비활성 안내를 유지한다.
- [ ] 결과 필터·재집계 API가 제공될 때 Result Store 후속 탐색 UX를 별도 계획한다.

### P3

- [ ] 영속 대화·분기 API와 인증 principal이 제공될 때 `lib/agent-threads.ts`의 메모리
  `RemoteThreadListAdapter`·`ThreadHistoryAdapter`를 실제 저장소 adapter로 교체한다.
- [ ] 실제 사내 서비스 환경에서 SQL·RAG·simulation 오류, 장시간 streaming과
  재연결을 관통 검증한다.

## 완료 이력 요약

### 2026-09-08~14 — 기본 Workbench와 지식 조회

- SSE 채팅, 3-pane Workbench, Tool 결과 카드와 편집·재생성·취소·복사를
  구현했다.
- 구조화 지식·Skill 조회와 Context Inspector를 연결했다.
- 구조화 지식 상세 응답에서 simulation도 선택 필드 `aggregation_rules`, `visualization_hints`를
  가질 수 있다. 기존 상세 렌더러가 필드 이름별 라벨("집계 규칙", "시각화 안내")로 표시한다.

### 2026-09-15 — assistant-ui 안정화와 결과·차트

- External Store 상태 소유권을 정리하고 deprecated iteration과 과장된 capability를
  제거했다.
- streaming parser, terminal lifecycle, retry race와 오류 payload 표시를
  회귀 테스트로 고정했다.
- Result Store 대용량 요약과 검증된 bar/line 차트, loading·retry·fallback을
  구현했다.
- SMT2020 기반 예시 질문·정적 콘텐츠와 관통 흐름 검증을 정리했다.

### 2026-09-16~18 — Elements, Tool UI와 UX 감사

- assistant-ui Elements 기반 Thread·Composer·ToolCall·AgentPlan·ThreadList로
  공통 UI를 전환했다.
- delta 답변, ToolGroup, 공개 진행 안내와 호출 ID별 args/result 표시를 구현했다.
- standalone 표·차트와 TanStack Table을 적용하고 `도입 → 결과 → 해석`의 원래
  이벤트 문맥 순서를 보존했다.
- Sidebar 내비게이션, 지식 관리, Inspector resize와 스크롤 안정화를 구현했다.
- F01~F17 감사에서 표 소실, 성공 오인, hover-only action, 좁은 화면 panel,
  focus 복원, 대비·긴 문자열, 0행·빈 응답, 실제 client timing, reduced-motion과
  landmark를 개선했다.

### 2026-09-21 — 구조화 지식 편집·승인 화면

- 지식 관리에 구조화 YAML 6종의 수정 요청·검토·승인을 추가했다. 서버 가이드 명세로 그리는
  입력 폼, 원문 YAML 탭, 줄 단위 diff, 검증 요약, 승인·반려 근거 Dialog, 진행 이력과
  `전체 | 내 요청 | 검토 대기` 목록 보기를 구현했다.
- 임시 사용자 선택기(stub)로 작성자·승인자를 구분한다. 인증이 아님을 화면에 밝히고 권한은
  `/api/me`만 따른다. 새 의존성은 없다.
- 결정과 근거는 `docs/decisions.md`의 "구조화 지식 편집·검토·승인 화면"을 따른다.

### 2026-09-22 — assistant-ui 통합 전환

- 채팅 runtime을 External Store에서 LocalRuntime(`ChatModelAdapter`)+thread 목록으로 전환하고 분기(BranchPicker)·
  세션 내 다중 thread·thread별 초안을 도입했다. `use-agent-chat`·연결 재시도 배너·재생성 확인창과 미사용 Elements
  약 3,000줄, 더미 세션을 삭제했다.
- `present` Generative UI 결과(`SqlPreview`·`QueryChart`(area 포함)·`QueryTable`(서버 page)·`SimulationSummary`), Result API
  client(요청 공유·abort·성공만 cache), preview·legacy 겸용 결과 renderer, 12개 도구 toolkit 등록, 후속질문 파서·UI를
  구현했다. 신규 의존성은 `@assistant-ui/react-generative-ui@0.0.19`·`zod@4.6.5`(assistant-stream 전이 상향).
- `present` vocabulary는 여러 결과를 묶는 `Card`와 도메인 4종으로 축소했다. 일반 설명은 Assistant Markdown에 두고,
  로딩·경고·오류는 각 도메인 component가 검증된 상태로 직접 표시한다.
- Backend의 provider-facing `present` Tool은 `tree` JSON 문자열로 재귀 schema 호환성 문제를 피하며,
  문자열 내부와 공개 AgentEvent는 둘 다 assistant-ui 표준 `$type`/`$key`를 쓴다. Frontend에서는
  Python Backend가 실행한 Tool이므로 frontend `present()`를 재등록하지 않고 `renderGenerativeUI`로 트리만 그린다.
- 검증: `npm test` 113 passed, build 성공, lint 오류 0(warning 4), 브라우저 harness chat 9·workbench 9·knowledge 7 통과,
  fake SSE Backend로 스트리밍·중단·오류·편집 분기·older-branch fork·thread 전환·후속질문 확인.
- 결정과 한계는 `docs/decisions.md`의 "assistant-ui 통합 전환"을 따른다.

### 2026-09-22 — `QueryTable` TanStack 서버 표

- `QueryTable`을 `@tanstack/react-table` 9.2.4의 수동 filtering·sorting·pagination으로 전환했다.
  기본 10행, 페이지 크기 10/25/50/100, 전체 셀 검색, 단일 열 3상태 정렬을 제공한다.
- 브라우저는 최대 1,000건을 한 번에 받지 않고 검색·정렬된 현재 page만 받는다.
- 검증: `npm test` 113 passed, `npm run build` 성공, `npm run lint` 오류 0(기존 warning 4).

### 2026-09-21 — 실행·계획 기준 정리

- Vite dev/preview 포트를 3100, 기본 Backend 주소를 8100으로 통일했다.
- 상세 날짜형 계획을 이 문서로 통합하고 Frontend workspace 독립 계획 체계로
  전환했다.

## 유지할 UI 결정

- Chat이 primary이며 Sidebar 15.5rem, Inspector 기본 20rem(1280px 이상 23rem),
  Thread 읽기 폭 47.5rem을 기준으로 한다.
- Inspector는 16~35rem에서 조절하며 Chat 최소 폭을 보호한다. 1180px 아래에서
  Inspector, 860px 아래에서 Sidebar를 임계값 하향 통과 시 한 번만 접는다.
- pane은 마운트를 유지하고 좁은 화면 재개방은 Chat을 밀지 않는 overlay다.
- 일반 UI는 semantic CSS token과 light theme만 사용한다. 외부 font·CDN과 새
  remote runtime을 추가하지 않는다.
- Tool 실행은 최종 답변보다 낮은 위계로 두고 완료 후 자동으로 접는다.
- 표·코드에는 가로·세로 scroll cap을 적용하고 숫자·식별자는 mono와
  tabular-nums를 사용한다.
- 미연결 기능은 비활성화하고 이유를 표시한다. 실제 계약 없이 값을 추측하지 않는다.

## 검증 기준과 알려진 한계

- 필수 검증: `npm test && npm run build && npm run lint`.
- 2026-09-22 기준: **113 tests passed**, 브라우저 회귀 chat 9·workbench 9·knowledge 7건 통과, build 성공, lint 오류 0개와
  Fast Refresh warning 4개. production bundle 크기 경고는 남아 있다.
- 브라우저 회귀는 chat, knowledge, workbench 전용 harness에서 lifecycle·focus·
  창 폭 축소 시 패널 접힘(860/1180px)을 데스크톱 브라우저에서 확인한다.
  모바일 환경은 지원·검증 대상이 아니다.
- 실제 screen reader, 실제 provider 장시간 응답과 영속 세션은
  아직 검증하지 않았다.

## 계획 운영

- 작은 작업은 이 문서의 다음 작업·상태·완료 이력을 직접 갱신한다.
- 큰 작업만 같은 폴더에 `<yymmdd>-<topic>-plan.md`를 만들며 Frontend 목표·기대
  API·UI 상태·Task·검증을 문서 안에 완결한다.
- 다른 workspace 계획을 링크하거나 구현 상태를 추정하지 않는다. 필요한 외부
  계약은 요청·응답·오류·착수 조건으로 이 문서 또는 활성 계획에 직접 기록한다.
- 작업 완료 후 장기적으로 필요한 결정과 검증만 이 문서에 합치고 상세 실행 계획은
  제거해 이 폴더를 간결하게 유지한다.
