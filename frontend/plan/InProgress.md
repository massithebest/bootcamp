# Frontend 진행 중 및 현재 계약

진행 중인 작업의 목표·결정·막힌 점과 현재 유효한 구현·계약을 기록한다. [할 일과 아이디어](Todo.md) · [완료 이력](History.md)

## 진행 중인 작업

현재 착수 상태로 기록된 작업은 없다. 착수 시 담당 범위, 현재 단계, 다음 행동, 검증 상태를 이곳에 기록한다.

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
| 차트 | 완료 | `QueryChart`(bar/line/area, 서버 집계), grouped/stacked 막대 표시, loading/error와 데이터 표 대안 |
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
  `present_chart(result_id, chart_type, x_column, y_column, group_by_column?, aggregation?, title?, bar_mode?: grouped|stacked)`,
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
  이중 인코딩을 없애는 재설계로 바꿨다. 상세 근거는 [완료 이력](History.md) 참고.)
- `bar_mode`는 막대 렌더링 전용이며 생략하면 grouped다. stacked는 `chart_type=bar`와
  `group_by_column`을 요구한다. 누적 막대의 접근성 요약도 누적 표시를 알린다.
- 이 모드의 `execute_sql`·`run_simulation` 결과는 전체 행 없이 preview(`result_id`, `row_count`, `columns`, `sample_rows`(객체,
  최대 5), `date_ranges`, `distinct_counts`, `statistics`, `top_groups`; simulation은 `simulation_type`·`scenario`·`summary`·`kpis`)다.
- `GET /api/query-results/{resultId}/table?page&page_size(≤100)&columns=…&search=&sort_column=&sort_direction=asc|desc`
  → `{status, result_id, page, page_size, row_count, filtered_row_count, source_truncated,
  columns[{name,dtype,role}], rows[[…]]}`. `QueryTable`은 TanStack Table 수동 모드로 저장된
  최대 1,000건 전체에 서버 검색·정렬을 적용하고 기본 10행씩 page를 받는다.
  동일 결과·열·검색·정렬·페이지 크기의 페이지 전환 중에는 마지막 성공 행과
  버튼 포커스를 유지하며, 지연·실패 시 요청 페이지와 유지 중인 페이지를 안내한다.
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
  이전 결정의 근거는 [완료 이력](History.md)의 "accent를 signature color로 확장"을 참고한다.
- Tool 실행은 최종 답변보다 낮은 위계로 두고 완료 후 자동으로 접는다.
- 표·코드에는 가로·세로 scroll cap을 적용하고 숫자·식별자는 mono와
  tabular-nums를 사용한다.
- 차트는 bar·line·area 모두 그래프 영역과 범례를 가로 중앙에 놓고 회전된 Y축
  제목을 그래프 높이의 중앙에 맞춘다. X축 제목·눈금·범례는 서로 겹치지 않는다.
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
