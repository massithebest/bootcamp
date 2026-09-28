# Production Planning Agent Frontend 계획 및 이력

**상태: 진행 중. 마지막 갱신: 2026-09-26.**

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
| 표 | 완료 | `QueryTable` 최대 1,000건 서버 검색·정렬·10/25/50/100 pagination |
| 차트 | 완료 | `QueryChart`(bar/line/area, 서버 집계), loading/error와 데이터 표 대안 |
| 조합형 결과 | 완료 | flat `present_sql_preview`·`present_chart`·`present_table`·`present_simulation` Tool renderer(`SqlPreview`·`QueryChart`·`QueryTable`·`SimulationSummary`) |
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

### 조합형 결과

- Backend는 `present` Tool 하나 대신 flat(스칼라 인자) Tool 4개를 보낸다:
  `present_sql_preview(sql, title?)`,
  `present_chart(result_id, chart_type, x_column, y_column, group_by_column?, aggregation?, title?)`,
  `present_table(result_id, columns?, title?)`,
  `present_simulation(scenario, summary, kpis, result_id?)`. 각 Tool 이름이 곧 렌더링할 컴포넌트를
  정하므로 `$type` 트리 파싱이 없다. 인자는 snake_case로 wire와 그대로 일치한다.
  prop 계약은 `tests/fixtures/present-vocabulary.json`(Tool 이름별 schema)과
  `components/chat/generative/vocabulary.ts`(같은 이름의 Zod schema, snake_case)다.
  Frontend는 `components/chat/generative/present-tool-uis.tsx`의 Tool별 renderer가 인자를
  Zod로 파싱해 `QueryChart`/`QueryTable`/`SqlPreview`/`SimulationSummary`(모두 flat camelCase
  prop, resultId 기반 API 조회는 그대로)에 매핑한다. `renderGenerativeUI`/
  `@assistant-ui/react-generative-ui`는 더 쓰지 않는다(패키지 의존성 제거).
  Tool 결과는 성공 시 빈 객체, 실패는 `{status:"error", code, message, details.path}`다.
  여러 결과를 한 화면에 시각적으로 묶는 기능(과거 `Card`)은 없다 — 같은 `result_id`로
  `present_*`를 여러 번 호출해도 메시지 안에서 순차적으로 나열된다(`execute_sql` 여러 번
  호출과 같은 방식). (과거에는 Tool 하나가 UI 트리 전체를 `tree` JSON-문자열로 받았으나,
  실제 provider가 그 문자열 타입을 지키지 못해 반복 실패하는 문제가 있어 2026-09-22
  이중 인코딩을 없애는 재설계로 바꿨다. 상세 근거는 아래 완료 이력 참고.)
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

- 같은 assistant 답변에 인자가 유효하고 성공 결과가 확인된 `present_table`이 있으면
  Markdown 표는 renderer에서 숨긴다. 설명·결론·코드 블록과 원문은 보존한다.
  미호출·미완료·실패·잘못된 인자는 Markdown 표를 숨기지 않는다.

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

- [ ] **후속질문 표시 검증**: Backend가 `done.data.suggestions`를 보내면 실제 응답에서 표시·전송·오류/취소 미표시를 확인한다.

### P2

- [ ] 실제 screen reader와 긴 대화 성능을 운영 환경에서 검증한다.
- [ ] 인증 principal이 연결되면 임시 사용자 선택기와 `lib/knowledge-user.ts`를 제거하고
  `GET /api/me`만으로 권한을 표시한다.
- [ ] 실제 모델 설정 API가 제공될 때 현재 비활성 모델·추론 강도 control의 표시
  정책을 재검토한다. API가 없으면 비활성 안내를 유지한다.
- [ ] 결과 필터·재집계 API가 제공될 때 Result Store 후속 탐색 UX를 별도 계획한다.

### P3

- [ ] 영속 대화·분기 API와 인증 principal이 제공될 때 `lib/agent-threads.ts`의 메모리
  `RemoteThreadListAdapter`·`ThreadHistoryAdapter`를 실제 저장소 adapter로 교체한다.
- [ ] 실제 사내 서비스 환경에서 SQL·RAG·simulation 오류, 장시간 streaming과
  재연결을 관통 검증한다.

## 완료 이력 요약

### 2026-09-26 — present_table과 Markdown 표 중복 표시 제거

- runtime이 같은 답변의 유효한 `present_table` 성공 결과를 판정해 로컬 metadata에
  `hideMarkdownTables`를 기록한다. Markdown renderer의 table 슬롯이 이를 구독해
  GFM 표 노드만 숨긴다. 이미 streaming 중 표시된 표도 Tool 성공 시 숨긴다.
- Markdown 원문은 수정하지 않아 설명·결론·근거·코드 펜스와 복사 원문을 유지한다.
  다른 답변, 사용자 메시지, Markdown 단독 답변과 Tool 실패 시 표는 보존한다.
  Backend API·AgentEvent·Tool payload 계약은 변경하지 않았다.
- 검증: `npm test` **102 passed**, build 성공, lint 오류·경고 0개.
  1280px Workbench browser 회귀 **11개 통과**: streaming 전환·코드 펜스 보존·실패 대안 표 확인.


### 2026-09-26 — 결과 client 책임 분리와 lint·bundle 경고 정리

- 결과 응답의 순수 검증은 `lib/query-result-parser.ts`, 진행 중 요청 공유·구독 해제·
  취소는 `lib/query-result-request-pool.ts`로 분리했다. `query-result-api.ts`는 URL·
  HTTP·안전한 오류 변환과 결과별 요청 연결을 담당하며 기존 공개 export를 유지한다.
  cookie·TTL·완료 응답 미보관·마지막 구독자의 abort 동작은 변경하지 않았다.
- 공개 AgentEvent와 `present_*` schema를 Backend 정의와 대조했다. fixture의 오래된
  출처 경로를 수정하고 계약 테스트가 enum·필수 여부뿐 아니라 타입·pattern·
  maxLength·maxItems·nullable 제약까지 비교하도록 보강했다.
- Button·Tabs·ToolGroup의 variant 함수와 Sidebar context/hook을 컴포넌트 파일에서
  분리했다. 공유 함수 소비자 import를 갱신해 Fast Refresh warning 4건을 제거했다.
  semantic token·CSS·컴포넌트 동작과 assistant-ui runtime 구성은 유지한다.
- Vite가 React·assistant-ui·Base UI·차트·Markdown·Zod를 별도 로컬 vendor chunk로
  출력하도록 했다. 단일 JS 1,586.26kB에서 앱 259.54kB·최대 vendor 406.05kB로 분리해
  500kB 경고를 제거했다. 총 다운로드 용량 감소나 지연 로딩을 의미하지 않는다.
- 최종 검증: `npm test` **101 passed**, build 성공, lint **0 errors / 0 warnings**.
  1280px 브라우저 회귀 chat 9·knowledge 8·workbench 10 모두 통과했다.
  production preview에서도 결정적 SSE/API fixture로 채팅→표·차트와 데이터 표 대안,
  로컬 chunk 로딩을 확인했다(JS 오류·외부 resource 요청 0). 실제 provider 검증은 아니다.
- 남은 build 경고: Zod 의존성의 Rollup 주석 annotation 2건. 경고를 숨기거나
  의존성 버전을 변경하지 않았다. 브라우저 검증 산출물은 Git 제외 `artifacts/`에 둔다.


### 2026-09-23 — accent를 signature color로 확장

- `--accent`(blue)를 live 상태(streaming·running·connected·selected)·focus
  전용에서 프로젝트 유일의 signature color 겸용으로 넓혔다. Composer 전송
  버튼, 메시지 편집 후 "저장하고 다시 실행" 버튼, 지식 편집기의 검토 요청·
  승인·승인하고 반영 버튼, 지식 관리 탭(`tabs.tsx` line variant)의 active
  밑줄, 사이드바 로고 배지를 ink에서 accent 채움으로 바꿨다(`globals.css`,
  `entry-editor.tsx`, `thread.aui.tsx`, `edit-message.aui.tsx`,
  `app-sidebar.tsx`, `ui/tabs.tsx`). `--shadcn-primary`도 accent로
  재매핑했다. Composer 중단(취소) 버튼은 1차 CTA가 아니므로 ink를 유지했다.
- 새 색상 토큰은 도입하지 않고 기존 `--accent`/`--accent-hover`/
  `--accent-weak`/`--accent-ink`만 재사용했다. 라이트 테마 유지, dark mode
  미도입 결정은 그대로다.
- 결정과 근거는 `docs/decisions.md`의 "accent를 signature color로 확장"을
  따른다(2026-09-22 "CTA는 ink" 결정을 대체).
- 검증: `npm test` 101 passed, `npm run build` 성공(기존 대형 bundle warning만
  유지), `npm run lint` 오류 0(기존 warning 4, 신규 없음).

### 2026-09-23 — 결과 조회 수명·지식 편집 lifecycle 분리

- Result API client는 동일한 진행 중 요청만 공유하고 완료 응답은 보관하지 않는다.
  Backend의 `Cache-Control`·`Vary: Cookie`가 세션·TTL 경계를 결정한다.
- Query 결과 표는 같은 요청의 재시도 중에만 직전 데이터를 유지하며, 결과 ID·검색·
  페이지 등 요청 키 변경과 오류·만료 응답에서는 이전 행을 지운다.
- `useDocumentEditor`로 텍스트 문서 로딩·폼·저장·검토 action lifecycle을 분리했다.
  브라우저 회귀는 403·409·422 실패 시 초안 보존과 서버 상세 비노출, 사용자 전환 시
  미저장 초안 보존을 확인한다.
- Result API 동시 요청·완료 뒤 재요청 및 QueryTable 전환/404 회귀를 보강했다.
- 검증: **101 passed**, build 성공(기존 대형 bundle 및 Rollup dependency 주의 포함),
  lint 오류 0개(Fast Refresh warning 4개), 1280px browser harness chat 9·knowledge 8·
  workbench 10 시나리오 통과.

### 2026-09-22 — legacy 결과 모드 삭제

- Backend가 legacy `prepare_table`/`prepare_visualization` Tool과 `RESULT_UI_MODE`
  플래그를 완전히 제거하기로 함에 따라(원래 계획한 운영 관통 검증·observation
  gate는 사용자 결정으로 건너뜀), Frontend의 legacy 전용 코드를 모두 제거했다.
  이제 결과 렌더링은 `present_*` Tool 경로 하나만 존재한다.
- 삭제: `lib/visualization-api.ts`, `lib/table-tool.ts`, `lib/chart-marker.ts`,
  `hooks/use-visualization.ts`, `components/chat/tool-results/table-tool-ui.tsx`,
  `visualization-tool-ui.tsx`, `chart-marker.tsx`, `interactive-data-table.tsx`.
- `query-result-api.ts`가 `parseChartSpec`/`parseWarnings`를 자체 소유하도록
  옮겼다(기존에는 legacy `visualization-api.ts`에서 가져다 썼다).
- `toolkit/index.tsx`·`standalone-tools.ts`·`tool-result-card.tsx`에서
  `prepare_table`/`prepare_visualization` 등록·메타데이터를 제거했다(toolkit은
  이제 16개 Tool: 실행 과정 12개 + `present_*` 4개).
- `chat-runtime.ts`: legacy Tool 이름에 의존하던 `removeMarkdownTables`
  Markdown 표 중복 제거(및 그 호출부 `successfulTables`)와
  `isSuccessfulStandalonePart`의 `prepare_table`/`prepare_visualization` 분기를
  제거했다. standalone 성공 판정은 이제 `result !== undefined &&
  toolResultError(result) === null` 하나로 단순화됐다.
- `result-summary.tsx`·`shared.ts`(`isLargeResult` 삭제)·`database-result.tsx`·
  `simulation-result.tsx`에서 legacy 인라인 payload 모양(배열의 배열
  `sample_rows`, `type: "large_result"`, top-level `summary` 객체) 분기를
  제거하고 present preview 모양(`statistics`, 객체 배열 `sample_rows`)만 남겼다.
- `markdown-text.tsx`의 `chart` 코드펜스 → `ChartMarker` 인라인 렌더 경로를
  제거했다(present 모드는 차트를 `present_chart` Tool로만 그린다).
- 관련 테스트(`chat-state`·`workbench`·`elements`·`generative`·`suggestions`·
  `chat-model-adapter`·`results`·`workbench-browser`)를 present 전용 시나리오로
  갱신했다. `tests/fixtures/present-vocabulary.json` 계약은 변경 없음.
- 검증: `npm test`(101 passed) · `npm run build`(`tsc -b` 0 errors) ·
  `npm run lint`(0 errors, 기존 Fast Refresh warning 4개만) 통과.

- `AGENTS.md`는 Frontend 구조·공유 계약·검증만 남기고, `CLAUDE.md`는 상세 내용을
  복제하지 않는 문서 진입점으로 축약했다.
- assistant-ui 공통 디자인 원문은 `docs/assistant-ui-design.md`, 프로젝트별 결정과
  예외는 `docs/decisions.md`, 구현 계약과 검증 이력은 이 문서가 맡도록 분리했다.
- README와 Elements 반입 안내를 현재 LocalRuntime과 flat `present_*` Tool 구현에 맞췄다.

### 2026-09-22 — 지식 관리 등록·전환 UX 개선

- `knowledge-manager.tsx`: "텍스트 지식 등록" 버튼과 값이 가려진 "구조화 지식
  추가" `<select>`를 하나의 `DropdownMenu`("+ 새 지식 추가")로 합쳤다. 열면
  텍스트 항목과(쓰기 권한이 있으면) 구조화 종류 전체가 한 번에 보인다.
  `ui/dropdown-menu.tsx`(기존 미사용 shadcn 소스)를 재사용했고,
  `DropdownMenuLabel`은 `DropdownMenuGroup`으로 감싸야 한다(감싸지 않으면
  base-ui `MenuGroupContext is missing` 런타임 오류).
- "전체 / 내 요청 / 검토 대기"를 `role="group"` 버튼 묶음에서 `ui/tabs.tsx`
  (`variant="line"`)의 실제 `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`로
  바꿨다. 편집기 내부의 `입력 폼 | 원문 YAML | 변경 검토` 커스텀
  `role="tablist"`로 구현된 접근성 계약은 건드리지 않았다.
- `ui/tabs.tsx`가 이번에 처음 실사용되며 `globals.css`에 빠져 있던
  `data-horizontal`/`data-vertical` custom variant(기존 `data-open`/
  `data-closed`와 같은 패턴)를 추가로 정의했다. 없으면 base-ui `Tabs` root의
  `data-horizontal:flex-col`이 적용되지 않아 `TabsList`와 `TabsContent`가
  세로로 쌓이지 않고 가로로 늘어나며(둘 다 7000px대 높이로 stretch) 탭이
  전혀 보이지 않는다 — 브라우저로 직접 확인해서 찾은 문제였다.
- `editor/field-editor.tsx`의 `Field`: 렌더 순서를 `label → help → control`
  에서 `label → control → help`로 바꿨다. `record_list`(예: table의
  `columns`) 같은 2열 grid에서 `help`가 있는 필드(예: 타입의 "SQL 타입")만
  라벨이 두 줄이 되어 입력 박스가 같은 행의 다른 필드보다 아래로 밀리던
  정렬 문제를 고쳤다.
- `editor/entry-editor.tsx`: 편집기 헤더(제목·상태 문구·"편집 닫기" 버튼)를
  `sticky top-0 z-10 bg-canvas`로 바꿔 긴 폼을 스크롤해도 항상 보이게 했다.
  처음에는 헤더에 직접 음수 margin(`-mx-4 sm:-mx-6`)을 줘서 부모 section의
  padding을 상쇄하려 했으나, section 자체가 `overflow-y-auto`인 스크롤
  컨테이너라 그 padding은 스크롤과 무관하게 항상 고정된 여백으로 남고,
  깊이 중첩된 자손의 음수 margin은 그 여백까지 정확히 도달하지 못해 스크롤
  중 헤더 위치가 흔들리고 뒤 내용이 비치는 문제가 있었다. `knowledge-
  manager.tsx`의 "지식 상세" section에서 padding(`p-4 sm:p-6`)을 section
  자체가 아니라 스크롤되는 내부 wrapper(`div.flex.min-h-full.flex-1.flex-col`)로
  옮겨 section의 스크롤 뷰포트 자체는 padding이 없게 만들고, entry-editor의
  sticky 헤더는 그 wrapper의 세로 padding만 `-mt-4 sm:-mt-6`로 상쇄해 진짜
  section 상단(사이드바의 "+ 새 지식 추가" 버튼과 같은 높이)에 흔들림 없이
  고정되게 했다(표 헤더의 `interactive-data-table.tsx`/`query-table.tsx`
  `sticky top-0 z-10` 패턴, Composer의 `sticky bottom-0 bg-canvas` 패턴과
  같은 관례). 빈 상태(`!hasPane`)의 중앙 안내 문구(`my-auto`)가 계속
  세로 중앙에 오도록 wrapper에도 `flex flex-col`을 유지했다.
- 검증: `npm test`(111 passed) · `npm run build`(type check 포함) ·
  `npm run lint`(0 errors, 기존 무관 warning 4개만) 통과. 개발 서버
  (localhost:3100)에서 Playwright로 새 드롭다운 전체 옵션 노출, 탭 전환(전체/
  내 요청/검토 대기), `table` 신규 등록 화면의 컬럼 1·2 필드 정렬과 폼 끝까지
  스크롤해도 편집기 헤더·닫기 버튼이 고정되는 것을 직접 확인했다.

### 2026-09-22 — `present` Generative UI를 flat `present_*` Tool renderer로 재설계

- Backend가 `present` Tool 하나(재귀 `$type`/`children` 트리를 `tree` JSON-문자열 하나로
  받음)를 `present_sql_preview`·`present_chart`·`present_table`·`present_simulation` 4개
  flat Tool로 교체했다(실제 provider가 `tree` 문자열 타입을 지키지 못해 SDK 강제 검증에
  막혀 반복 실패하는 문제 때문 — Backend `plan/Todo.md` 참고). Frontend도 같은 작업에서
  맞춰 재설계했다.
- `components/chat/generative/vocabulary.ts`의 Zod schema 필드명을 snake_case로 바꿔
  wire와 그대로 맞췄다(`resultId`→`result_id` 등). `library.tsx`(`GenerativeUILibrary`)와
  `present-tool-ui.tsx`(`renderGenerativeUI` 호출)를 삭제하고, Tool 이름별 renderer 4개
  (`components/chat/generative/present-tool-uis.tsx`)로 교체했다 — 각 renderer가 Zod로
  인자를 파싱해 기존 `QueryChart`/`QueryTable`/`SqlPreview`/`SimulationSummary`(변경 없음)에
  camelCase prop으로 매핑한다. `@assistant-ui/react-generative-ui` 의존성을 제거했다
  (`package.json`, `npm prune`).
  `toolkit/index.tsx`·`lib/standalone-tools.ts`에 새 Tool 이름 4개를 등록했다.
- `lib/chat-runtime.ts`의 standalone dedup 로직(`isSuccessfulStandalonePart`,
  `shouldShowStandalonePart`)이 `toolName === "present"` 리터럴에 의존하던 특수 분기를
  없애고 `toolName.startsWith("present_")`로 일반화했다. 이제 한 턴에 서로 다른
  `result_id`로 `present_chart`를 여러 번 호출할 수 있으므로(예: 지표 2개), dedup을
  Tool 이름만으로 하지 않고 `result_id`까지 함께 봐서 서로 다른 호출을 잘못 묶어
  숨기지 않게 했다.
- `tests/fixtures/present-vocabulary.json`을 `$type` 키 맵에서 Tool 이름별 schema 맵으로
  다시 만들고, `tests/generative.test.mjs`·`tests/suggestions.test.mjs`의 `$type` 트리
  기반 테스트를 flat 인자 기반으로 재작성했다.
- 검증: `npm test` 111 passed, `npm run build`(type check 포함) 성공, `npm run lint`
  0 errors(기존 무관 warning 4개만). Backend와 함께 실제 provider(GLM-5.3-flash)로
  이전에 반복 실패하던 "지표 2개, 차트 2개" 시나리오를 재현해 `present_chart` 2회 호출이
  모두 성공하는 것을 확인했다.
- 미수행: `present_*` 운영 기본값 결정, Card 상당의 시각적 grouping 필요 여부는 실사용
  피드백을 보고 재검토(위 P1 항목).

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
  client(진행 중 요청 공유·abort·완료 응답 미보관), preview·legacy 겸용 결과 renderer, 12개 도구 toolkit 등록, 후속질문 파서·UI를
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

### 2026-09-22 — assistant-ui Design System 정합화

- assistant-ui 공식 design.md 기준으로 radius를 5단계 의미 체계
  (`rounded`=document 6px, `rounded-md`=control 8px, `rounded-lg`=surface
  10px, `rounded-xl`=floating card 12px, `rounded-2xl`=thread 16px,
  Composer 전용 명시적 예외 유지)로 갱신했다(`globals.css`, `tailwind.config.ts`,
  `components/ui/{button,input,textarea,select,tooltip}.tsx`,
  `assistant-ui/elements/surfaces.ts`).
- `--accent`(blue)를 streaming·running·connected·selected와 그 연장인
  focus 전용으로 좁혔다. 전송/중단 버튼, 사이드바 로고 배지, 지식 편집기의
  승인·검토·초안 저장 CTA를 `--ink`/`--ink-strong` 채움으로 교체하고
  `--shadcn-primary`도 `--ink`로 재매핑했다. 스트리밍 커서·실행 중 스피너·
  선택된 대화/탭 항목의 accent는 유지했다.
- 아이콘 크기를 `size-3.5`(버튼 내부 보조)/`size-4`(독립 배치)/`size-7`
  (아이콘 버튼 컨테이너)/`size-8`(1차 액션 버튼) 4단계로 정리했다. 실제
  스윕 결과 이탈값은 없었다(기존 `size-3~3.5` 문서 규칙과 실제 사용이 이미
  대부분 일치).
- `tool-group.aui.tsx`의 `text-sm` 2곳을 `text-ui`로, `context-inspector.tsx`의
  `space-y-1~5` 5종 혼용을 2단계(`space-y-1` 항목 내부/`space-y-3` 목록)로
  정리했다.
- assistant-ui 공식 `design.md` 원문을
  [assistant-ui 디자인 기준](../docs/assistant-ui-design.md)에 폐쇄망용으로
  미러링하고 `AGENTS.md`에서 1차 참고 문서로 연결했다. 프로젝트별 차이(라이트 전용,
  시스템 폰트만 사용, Reasoning UI 미사용, Composer의 `rounded-2xl`, 하이퍼링크
  accent 색 유지)는 `docs/decisions.md`에 기록했다.
- 검증: `npm test` 113 passed, `npm run build` 성공(type check 포함),
  `npm run lint` 오류 0(기존 warning 4, 신규 없음). 데스크톱 브라우저
  (1440×900)에서 홈 화면·Composer·Sidebar·지식 관리 화면을 눈으로 확인해
  전송 버튼·로고 배지의 ink 색, 선택 상태의 accent 유지, radius 변화를
  검증했다.
- 남은 판단 필요 항목(변경하지 않음, 의도적 유지로 기록): 마크다운·Skill
  링크의 `text-accent`, `chat-window.tsx`의 pane resize handle
  hover 색은 공식 규칙("blue는 live 상태 전용")과 엄밀히는 어긋나지만
  기존 링크 관행·리사이즈 어포던스로 판단해 그대로 뒀다. `docs/decisions.md`에
  근거를 남겼다.

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
- Radius는 document(6px, `rounded`)/control(8px, `rounded-md`)/surface(10px,
  `rounded-lg`)/floating card(12px, `rounded-xl`)/thread(16px, `rounded-2xl`,
  Composer 전용)/capsule(9999px, `rounded-full`) 5단계 의미 체계를 따른다.
  `--accent`(blue)는 streaming·running·connected·selected·focus에 더해
  프로젝트 유일의 signature color를 겸해 1차 CTA·탭 active·사이드바 로고
  배지에도 쓴다. Composer 중단 버튼 등 1차 CTA가 아닌 상태 전환 액션은
  `--ink`/`--ink-strong`을 유지한다. 상세는
  [assistant-ui 디자인 기준](../docs/assistant-ui-design.md)과
  `docs/decisions.md`의 "accent를 signature color로 확장"을 참고한다.
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
