# Frontend 완료 이력

완료한 업무의 결과, 중요한 결정과 검증 근거를 보존한다. 현재 계약은 [진행 중](InProgress.md), 남은 일은 [할 일과 아이디어](Todo.md)를 따른다.

## 2026-10-23 — 시뮬레이션 KPI 카드 숫자·단위 표기

- 실제 시뮬레이션 요약 카드에 초기 WIP가 "2255lot"처럼 천 단위 구분 없이 단위와 붙어 표시됐다.
  `lib/format-cell.ts`에 `displayKpiValue`(천 단위 구분, 소수 최대 2자리)와 `kpiUnitSeparator`(영문 단위만 띄움,
  한글 단위·기호는 붙임)를 두고 `SimulationSummary`·`SimulationResult` KPI 카드에 적용했다. 표 셀은 복사용으로
  천 단위 구분을 붙이지 않는 기존 규칙을 유지한다.
- 브라우저의 같은 답변에서 "2개 · 926개 · 106개 · 2,255 lot" 표시를 확인했다. Frontend 108 tests passed,
  build·lint 성공.

## 2026-10-23 — 물결표 범위 표기의 취소선 오표시 수정

- 실제 답변 "part_3~part_10: 각 215~216 Lot"이 `part_10: 각 215` 취소선으로 표시됐다. `remark-gfm` 기본값이
  물결표 하나(`~…~`)도 취소선으로 처리하기 때문이다. 한국어 범위 표기에 물결표를 흔히 쓰므로
  `lib/markdown-options.ts`의 `GFM_OPTIONS`(`singleTilde: false`)를 채팅 답변(`CHAT_REMARK_PLUGINS`)과
  지식 관리 Markdown(`skill-markdown.tsx`)에 함께 적용했다. `~~삭제~~`는 그대로 취소선이다.
- 같은 답변을 브라우저에서 다시 그려 취소선 0개, "215~216" 원문 표시를 확인했다. Frontend 107 tests passed,
  build·lint 성공.

## 2026-10-15 — 후속질문 실제 응답 검증

- Backend가 성공한 `done.data.suggestions`를 보내기 시작해, 실제 Agent 응답 뒤에
  후속질문 4개가 표시되고 클릭하면 그 문구가 바로 전송되며 실행 중에는 숨겨지는 것을
  확인했다. 오류·취소 turn 미표시는 `tests/suggestions.test.mjs`가 검증한다.

## 2026-10-15 — 표 숫자의 부동소수점 오차 제거

- SQL 집계 실수값이 `13083.199999999999`처럼 표시되던 문제를 고쳤다.
  `lib/format-cell.ts`의 `displayCell`은 정수가 아닌 유한 숫자를 유효숫자 12자리로
  정리한다. 천 단위 구분은 붙이지 않아 기존 표시 규칙을 유지한다.
- 차트 "데이터 표로 보기"도 같은 규칙을 사용한다.
- 실제 Agent 응답의 결과 표에서 `13083.2` 표시를 확인했다. Frontend 106 tests
  passed, build·lint 성공.

## 2026-10-06 — 표 페이지 전환 중 데이터·포커스 유지

- 같은 결과·열·검색·정렬·페이지 크기에서 페이지를 전환할 때 마지막 성공 행과
  표 영역을 유지한다. 지연·실패 시 요청 페이지와 유지 중인 페이지를 안내한다.
- 페이지 버튼은 `aria-disabled`와 클릭 가드로 중복 요청을 막고 포커스를 유지한다.
- 브라우저 회귀의 막대 SVG 선택자·애니메이션 대기와 페이지 실패 안내 기대값을
  실제 렌더링에 맞췄다. 1280px workbench 13건과 차트 축 3종 검사 통과,
  Frontend 105 tests passed, build·lint 성공.

## 2026-10-01 — 차트 비율과 축 제목 정렬

- bar·line·area 차트 높이를 264px로 맞추고 상단 20px·하단 12px 여백을 사용한다.
  Y축 예약 폭에 대응하는 오른쪽 여백을 둬 그래프 영역을 수평 중앙에 놓고,
  범례도 전체 차트 폭을 기준으로 중앙 정렬한다.
- 회전된 Y축 제목의 기준점을 가운데로 바꿔 긴 제목도 그래프 높이의 중앙에
  표시한다. 범례와 데이터 표 버튼 사이 빈 공간은 52px에서 20px로 줄었다.
- 1280px 데스크톱 브라우저의 680px 차트 영역에서 3계열 누적 막대·선·영역
  차트의 축 제목·그래프·범례 중심, X축 간격과 가로 넘침을 확인했다.
  Frontend `npm test` 105개 통과, build·lint 성공.

## 2026-10-01 — 차트 X축 제목 겹침 수정

- 기존 `tickMargin`과 차트 `bottom` 여백은 X축 제목이 배치되는 축 높이를 늘리지 않아,
  `WORK_YM`이 월 눈금과 범례에 겹쳤다. bar·line·area의 X축 높이를 제목 유무에 따라
  지정하고 제목을 축 안쪽으로 이동했다.
- 1280px 데스크톱 브라우저에서 축 제목과 눈금 사이 약 12.5px, 제목과 범례 사이
  9px을 확인했다. `tests/chart-axis-browser.html`이 세 차트 유형의 간격을 검사한다.
  Frontend `npm test` 105개 통과, build·lint 성공.

## 2026-10-01 — grouped/stacked 막대 차트

- `present_chart.bar_mode`의 선택값 `grouped|stacked`를 Tool fixture·Zod schema와
  renderer에 연결했다. 기본 grouped는 유지하고 stacked bar는 모든 그룹 시리즈에
  공통 `stackId`를 적용한다.
- 스크린 리더 요약도 누적 막대 표시를 알린다. Backend 전체 365 passed, Frontend
  105 tests passed, build·lint 성공.

## 2026-09-30 — 시작 화면 문구 교체

- Composer 입력 안내와 시작 화면의 기본 질의 5개를 요청 문구로 교체했다.
- 시작 화면의 기능 안내를 "생산계획 데이터 조회부터 계획 수립 과정과 운영 기준까지 확인해 보세요."로 교체했다.
- Frontend 검증: `npm test` 103개 통과, `npm run build`와 `npm run lint` 성공.
  1280px 데스크톱 브라우저에서 입력 안내와 질문 버튼 5개 표시를 확인했다.

## 2026-09-30 — 계획·가이드 문서 역할 정리

- 할 일과 아이디어를 `Todo.md`, 현재 상태·계약을 `InProgress.md`, 완료 기록을
  이 파일로 분리했다. 과거 기술 결정과 반입 점검 기록은 아래에 보존했다.
- docs에는 반복해서 쓰는 디자인·폐쇄망 운영 가이드만 남겼다. 현재 UI 결정은
  `InProgress.md`로 모으고 별도 결정 기록 파일은 제거했다. 계획·docs의
  `AGENTS.md`·`CLAUDE.md` 및 README 링크를 새 역할에 맞췄다.

## 완료 기록

### 2026-09-28 — LLM 응답 지연 안내 표시

- Backend가 LLM 응답 지연 시 보내는 기존 `error`·`done` AgentEvent를 현재
  `MessageError` 오류 상태와 다시 실행 동작으로 그대로 표시한다. 별도 wire 타입이나
  UI 경로를 만들지 않는다.

### 2026-09-28 — 폐쇄망 설정 문서명과 Vite 서버 옵션 정리

- 폐쇄망 운영 문서를 `docs/CLOSED_NETWORK_SETUP.md`로 대문자화하고,
  Frontend README·작업 지침의 링크를 갱신했다. 로컬 `.env.local`에
  `VITE_API_BASE_URL=http://localhost:8100`을 명시했다(파일은 Git 제외).
- Vite dev·preview 서버를 포트 3100, `strictPort: true`, `host: true`,
  `allowedHosts: []`로 고정하고 build source map은 생성하지 않는다.

### 2026-09-28 — 화면 제품명 P&T FP 통일

- Composer placeholder, 빈 대화 안내, 대화 헤더, simulation·Tool 결과의 화면 표기와
  HTML 설명 metadata에서 `생산계획`/`SMT2020` 대신 `P&T FP`를 사용하도록 통일했다.
  Backend 식별자와 payload 원문은 변경하지 않는다.

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
- 결정과 근거는 `History.md`의 "accent를 signature color로 확장"을
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
- 당시 assistant-ui 공통 디자인 원문과 프로젝트별 결정·예외를 분리했으며,
  현재 제품별 결정은 `InProgress.md`, 그 이전 결정은 이 문서에 보존한다.
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
- 결정과 근거는 `History.md`의 "구조화 지식 편집·검토·승인 화면"을 따른다.

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
- 결정과 한계는 `History.md`의 "assistant-ui 통합 전환"을 따른다.

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
  accent 색 유지)는 `History.md`에 기록했다.
- 검증: `npm test` 113 passed, `npm run build` 성공(type check 포함),
  `npm run lint` 오류 0(기존 warning 4, 신규 없음). 데스크톱 브라우저
  (1440×900)에서 홈 화면·Composer·Sidebar·지식 관리 화면을 눈으로 확인해
  전송 버튼·로고 배지의 ink 색, 선택 상태의 accent 유지, radius 변화를
  검증했다.
- 남은 판단 필요 항목(변경하지 않음, 의도적 유지로 기록): 마크다운·Skill
  링크의 `text-accent`, `chat-window.tsx`의 pane resize handle
  hover 색은 공식 규칙("blue는 live 상태 전용")과 엄밀히는 어긋나지만
  기존 링크 관행·리사이즈 어포던스로 판단해 그대로 뒀다. `History.md`에
  근거를 남겼다.

### 2026-09-21 — 실행·계획 기준 정리

- Vite dev/preview 포트를 3100, 기본 Backend 주소를 8100으로 통일했다.
- 상세 날짜형 계획을 이 문서로 통합하고 Frontend workspace 독립 계획 체계로
  전환했다.


## 이전 기술 결정 기록 (2026-09-26 이전)

아래는 docs에서 이동한 과거 결정 원문이다. 당시 경로와 상태 표현은 역사적 기록이며 현재 적용 기준은 `InProgress.md`를 따른다.

# Frontend 기술 결정 기록

이 문서는 지속적으로 유효한 결정과 대체된 결정의 이유만 보존한다. 구현 Task와
검증 이력은 `plan/Todo.md`에 요약한다.

## 결정 요약

| 날짜 | 결정 | 상태 |
| --- | --- | --- |
| 2026-09-08 | 3-pane 워크벤치 | 활성 |
| 2026-09-11 | Tailwind v4와 shadcn/ui | 활성 |
| 2026-09-14 | AI Elements를 복사 소스로 제한해 사용 | 2026-09-16 대체 |
| 2026-09-14 | Next.js에서 Vite SPA로 이전 | 활성 |
| 2026-09-14 | assistant-ui를 UI plumbing 계층으로 도입 | 활성 |
| 2026-09-15 | 차트를 최종 답변의 `visualization_id` marker로 전환 | 2026-09-16 대체 |
| 2026-09-16 | assistant-ui Elements를 공통 채팅 UI의 기준으로 사용 | 활성 |
| 2026-09-16 | 홈페이지형 Composer와 공개 상태 Reasoning·답변 delta 스트리밍 | 활성 |
| 2026-09-16 | 조회 1,000행·표시 10행과 Composer 준비 중 제어 | 같은 날 100행 결정으로 대체 |
| 2026-09-16 | 검증된 차트를 standalone Tool UI로 표시 | 활성 |
| 2026-09-16 | 표시 100행과 standalone 대화형 표 Tool UI | 활성 |
| 2026-09-16 | ChatGPT형 좌측 전역 내비게이션 | 같은 날 단일 채팅 메뉴 결정으로 대체 |
| 2026-09-16 | 좌측 채팅 메뉴 단일화 | 활성 — `새 채팅`만 유지 |

## 3-pane 워크벤치

사이드바, 대화, context inspector를 한 화면에 둔다. 대화와 Skills는 실제 API,
세션 목록·사용자는 아직 로컬 데이터다. Metadata·Prompt 패널은 아래 지식 관리 결정으로 제거했다. 실제 연결되지 않은
패널을 영속 기능으로 설명하지 않는다.

왼쪽 sidebar 셸은 `components/chat/app-sidebar.tsx`, 목록은 assistant-ui의
standalone `ThreadList`다. 설치된 shadcn Sidebar provider는 사용하지 않는다.

## Tailwind v4와 shadcn/ui

UI primitive는 shadcn 소스를 저장소에 복사해 관리한다. registry CLI는 인터넷이
되는 준비 환경에서 실행하고 생성 파일을 함께 반입한다. 컴포넌트는 프로젝트의
semantic CSS token을 사용하며 shadcn 기본 팔레트를 독립적으로 유지하지 않는다.

초기 스캐폴드의 “custom Tailwind 컴포넌트만 사용” 결정은 이 결정으로 대체됐다.

## AI Elements

2026-09-16 assistant-ui Elements 전환으로 대체됐다. 이전에는
`chain-of-thought`, `tool`, `task` 복사 소스를 제한해 사용했다.
`ai`, `@ai-sdk/react`, `useChat`, `streamdown`과
AI SDK streaming protocol은 사용하지 않는다. 이유는 Backend SSE 계약과 맞지 않고
불필요한 의존성·외부 endpoint 가능성을 늘리기 때문이다.

## Next.js에서 Vite로 이전

Frontend는 router 없는 Vite SPA다. `src/app` 이름은 CSS와 asset 경로 호환을 위해
남은 디렉터리일 뿐 Next.js App Router가 아니다. Browser가 FastAPI를 직접 호출하고
dev·preview 포트는 CORS 계약과 맞춘 3100으로 고정한다.

## assistant-ui

> 2026-09-22 갱신: 아래 초기 결정 중 External Store·선형 대화·`use-agent-chat.ts`·예시 세션·
> BranchPicker 보류·재생성 확인창은 [assistant-ui 통합 전환](#assistant-ui-통합-전환-2026-09-22-활성)으로
> 대체되었다. 이력으로 남기며 현재 기준은 그 절이다.

assistant-ui는 thread, viewport, composer, message, action bar와 Markdown rendering을
담당한다. 애플리케이션 메시지 상태와 SSE transport는
`hooks/use-agent-chat.ts`가 소유하고 `useExternalStoreRuntime`으로 연결한다.

- 어시스턴트 메시지는 text와 tool의 도착 순서를 보존하는 `MessagePart[]`다.
- status/progress는 메시지 metadata에 연결한다.
- edit와 regenerate는 Backend의 `turn_id`/`fork_from_turn_id` 계약을 사용한다.
- Runtime이나 transport를 바꾸려면 기대 streaming 계약을 포함한 새 Frontend 계획이 필요하다.
- External Store adapter는 실제로 지원하는 capability만 노출한다. 선형 대화만
  유지하는 동안 `setMessages`(branch switch/delete)는 제거했다.
- 메시지 종료 상태는 공식 `MessageStatus`(`complete`/`incomplete(cancelled,error)`)로
  정규화하고 오류 표시는 `MessagePrimitive.Error`를 사용한다.
- Tool UI는 stable `tool_call_id` 계약을 도입해 `GroupedParts`에 연결했다.
  thread-list adapter는 세션 persistence 계약이 생기기 전까지 보류한다.

### Elements 중심 UI (2026-09-16, 활성)

사용자 요청에 따라 UI plumbing만 적용하던 범위를 공통 채팅 화면 전체로
확대했다. 공식 Base 템플릿을 참고하되 Vite와 기존 SSE를 유지한다.

- 루트 `App`에 `AssistantRuntimeProvider`와 tooltip provider를 둔다.
- 공식 Thread 구조(메시지, welcome, ViewportFooter, composer, scroll-to-bottom)를
  복사·조정하고 생산계획 `AssistantMessage`/`Welcome` 및 재시도 슬롯을 연결한다.
- 세션 목록은 standalone ThreadList, 도구 결과는 ToolCall, 진행 단계는
  AgentPlan이다. AI Elements 소스와 전용 controllable-state 훅은 제거한다.
- 목록의 미연결 편집/삭제 장식은 제외한다. AgentPlan은 activeIndex로 완료를
  추측하지 않고 명시적 단계 상태를 받고 취소는 runtime 종료 상태에서 판정한다.
  최종 상태가 없는 단계는 `완료 미확인`으로 표시한다.
  ToolCall은 ReactNode 결과와 오류 슬롯을 추가해 SQL·표·지식 renderer를 쓴다.
- 코드 소스와 MIT 고지는 저장소에 포함한다. 새 npm 의존성은 없다.
  `tw-shimmer`, 첨부·음성·Cloud 등 미사용 의존성을 자동 설치하지 않는다.
- 기존 3-pane 폭·semantic token·폰트·읽기 폭·완료 후 접힘 규칙은 유지한다.
  empty 화면은 중앙 정렬, composer는 Thread의 sticky ViewportFooter에 둔다.

요청된 `useChatRuntime with AI SDK transport`는 기존 SSE 결정과 충돌하므로
AGENTS.md에 일반 패턴과 현재 적용 예외를 함께 기록했다. 공식 External Store
경로로 Elements를 사용하는 데 문제없다. `AssistantModal`은 위젯용 패턴이며
현재 full-page 채팅에는 적용하지 않는다. 원격 thread adapter·tool toolkit
보류 결정과 백엔드 계약은 바뀌지 않는다.

근거: [Thread](https://www.assistant-ui.com/elements/thread),
[ToolCall](https://www.assistant-ui.com/elements/tool-call),
[AgentPlan](https://www.assistant-ui.com/elements/agent-plan),
[계획 이력 요약](History.md).

감사 결과와 후속 작업은
[계획 이력 요약](History.md)에 둔다.

### 요청 종료와 재시도 경계 (2026-09-15, 활성)

SSE envelope 검증은 `lib/chat-sse.ts`, 순수 메시지 전이는 `lib/chat-state.ts`로
분리하며 상태 소유자는 계속 `use-agent-chat.ts`다. transport가 반환하는
완료/실패/취소 결과로 Backend의 `error` 이벤트와 연결 실패를 구분한다.
재시도는 원래 사용자 메시지와 fork 지점을 재사용한다. 현재 controller와
일치하는 요청만 메시지·retry·running 상태를 갱신할 수 있다.

이 결정은 기존 External Store와 공개 AgentEvent 계약을 보완한다. 구현·회귀
근거는 [계획 이력 요약](History.md)에 둔다.

## 차트 v2 marker

도구 카드의 v1 자동 차트는 폐기했다. 최종 답변의 `chart` 코드 펜스에는
`visualization_id`만 허용하며, marker가 `/api/visualizations/{id}` 응답을 런타임
검증한 뒤 Recharts에 전달한다.

동일 ID의 진행 중 요청은 공유하고 마지막 구독자가 사라지면 취소한다. 프론트는
수치를 집계·정렬·피벗하지 않으며 Backend가 검증한 payload를 렌더링한다. 네트워크
재시도는 같은 조회만 반복하고 Agent tool을 자동으로 다시 실행하지 않는다.

현재 기대 계약과 완료 이력은 [Frontend 계획](History.md)을 따른다.

## 폐쇄망 공통 결정

외부 font, CDN, script, telemetry와 브라우저의 외부 LLM 호출을 금지한다. 패키지
버전과 전이 의존성을 사내 registry에서 확인하고 오프라인 build를 검증한다.
세부 절차는 [폐쇄망 운영 원칙](../docs/CLOSED_NETWORK_SETUP.md)을 따른다.


### 공식 registry CLI 설치 후속 (2026-09-16, 활성)

사용자 지정 `npx shadcn@latest add @assistant-ui/thread @assistant-ui/thread-list`
실행으로 관련 소스를 추가했다. 기존 수정 파일은 보존하며 runtime ThreadList는
세션 adapter가 준비되기 전까지 설치된 소스로만 유지한다. 현재 standalone
예시 목록·Thread 슬롯과 SSE 연결은 동일하다.

이 요청 범위에서 “새 npm 의존성 없음” 결정은 tw-shimmer 0.4.13 추가와
zustand 5.0.15 직접 선언으로 보완한다. 정확한 버전을 lockfile과 함께 관리한다.
설치 당시에는 첨부·reasoning·원격 연결을 활성화하지 않았다. Reasoning은 아래
후속 결정에서 공개 status 표시로 연결했다.


### Elements 카탈로그의 적용 경계 (2026-09-16, 활성)

[공식 목록](https://www.assistant-ui.com/elements#messages)을 검토해 기존
Thread·MessageActions·ToolCall·AgentPlan에 다음 요소를 추가했다.

| Element | 적용 위치와 동작 |
| --- | --- |
| ErrorState | 연결 실패·메시지 오류. 연결 실패는 기존 retry context, 메시지 오류는 runtime Reload를 사용한다. |
| EditMessage | inline 편집. 이후 답변 수와 대화 교체를 안내하고 runtime 입력·취소·저장을 유지한다. |
| StoppedRun | 취소된 응답 뒤. 받은 내용은 유지하고 같은 질문을 다시 실행한다. |
| RetrievalChunks | 지식 검색 도구 결과. 제목·위치·본문·유효 관련도를 실제 payload에서 읽는다. |

기존 External Store 결정과 충돌하지 않는다. 다만 공식 편집 예제의 분기 보존
설명은 현재 선형 adapter와 다르므로 기존 대화로 돌아갈 수 있다고 표시하지
않는다. StoppedRun의 Continue 역시 실제 이어쓰기가 아니므로 “다시 실행”으로
명명한다. 오류의 재실행은 다른 요청 실행 중에 runtime이 비활성화한다.

현재 미적용: Branches(분기 저장소 없음), Queue(큐 동작 없음), Feedback(저장 API
없음), Timestamps(실제 메시지 시각 계약 없음), Regenerate with(모델 선택 없음),
Confidence(신뢰도 근거 없음). Speaker identity는 단일 assistant에서 추가 역할
데이터가 없어 보류한다. 공식 DataTable은 모델·context·가격 전용 예제이므로
동적 SQL 표와 Result Store·Recharts를 대체하지 않는다. 첨부·음성·Cloud 보류는 유지한다.

관련도는 답변 신뢰도가 아니다. 누락·비정상 값은 숨기고 유효한 0은 표시한다.
새 npm 의존성과 외부 런타임 요청을 추가하지 않았다. PromptLibrary는 아래
홈페이지형 Composer 결정에서 제거됐다.

### 홈페이지형 Composer와 공개 실행 스트리밍 (2026-09-16, 활성)

공식 홈페이지의 빈 Thread를 참고해 중앙 영역을 제목, 둥근 Composer, suggestion
pill 순으로 배치한다. 대화가 시작되면 Composer는 기존처럼 viewport 하단에
고정된다. 별도 질문 모음 popover와 Enter/Shift+Enter 안내는 제거한다. 예시 질문은
기존 `ThreadPrimitive.Suggestion`으로 유지하므로 클릭하면 바로 전송된다.

Composer focus는 form 외곽선 하나로 표현한다. 전역 키보드 focus 규칙은 유지하고
`aui_composer-input` textarea에만 내부 outline을 제거한다.

assistant-ui Reasoning disclosure에는 Backend `status` 이벤트의 공개 업무 단계만
표시한다. 실행 중 자동으로 열리고 진행 label과 단계가 스트리밍되며 완료 후
접힌다. Claude Agent SDK의 `thinking_delta`와 ThinkingBlock은 계속 폐기하므로
모델의 비공개 chain-of-thought를 노출하지 않는다.

실 응답은 `include_partial_messages`로 받은 `text_delta`를 기존 AgentEvent `text`로
즉시 전달한다. `message_start`의 provider message id가 같은 최종 누적 TextBlock은 adapter가 생략해
중복을 막는다. 공개 AgentEvent와 FastAPI SSE 형식은 바뀌지 않으며
frontend external-store 계약도 동일하다.

근거: [계획 이력 요약](History.md),
[assistant-ui Reasoning](https://www.assistant-ui.com/elements/reasoning),
[Claude streaming messages](https://platform.claude.com/docs/en/build-with-claude/streaming).

### 조회·표시 한도와 Composer 준비 중 제어 (2026-09-16, 표시 한도 대체)

SQL 조회·Result Store 저장 상한은 500행에서 1,000행으로 확장한다. Frontend 표
표시 한도는 이 데이터 한도와 분리해 10행으로 고정한다. 공용 `DataTable`과 최종
답변 Markdown `tbody`가 모두 처음 10개 데이터 행만 렌더링하고, 나머지 건수를
안내한다. Agent에도 최종 Markdown 표를 10행 이내로 작성하도록 지시한다.

Composer 왼쪽 아래에는 첨부, 모델 `GLM-5.3-Flash`, 추론 강도 `Low`를 표시한다.
현재 attachment adapter와 per-run 모델·추론 설정 계약이 없으므로 세 제어는
준비 중인 비활성 UI다. 사용자가 실제로 설정이 적용된 것으로 오해하지 않도록
접근 가능한 이름에 준비 중 상태를 포함한다.

근거: [계획 이력 요약](History.md).

위 결정의 조회 1,000행과 Composer 제어는 유지한다. 표 표시 10행 정책만 아래
대화형 표 결정의 100행 정책으로 대체됐다.

### 중첩 Tool 실행 과정 (2026-09-16, 활성)

한 assistant 턴의 업무 Tool 호출은 assistant-ui `MessagePrimitive.GroupedParts`와
`ToolGroup` 요소로 최종 답변 위에 모은다. 실행 중에는 전체 그룹이 열리고 응답이
완료되면 자동으로 닫힌다. 사용자가 그룹을 펼치면 Tool 목록, 개별 Tool을 다시
펼치면 공개 Parameters와 Result가 보이는 두 단계 disclosure를 사용한다.

Backend `AgentEvent`는 선택 필드 `tool_call_id`를 추가했으며 `tool_call.data.args`에
업무 Tool의 공개 입력만 싣는다. 동일 호출의 call/status/result는 같은 ID를 써서
같은 이름의 반복 호출도 정확히 연결한다. 내부 access scope, SDK thinking과
built-in Tool 입력은 계속 노출하지 않는다.

Tool 사이의 안내 텍스트는 실행 과정과 최종 답변을 두 덩어리로 만들지 않도록
본문에서 제외한다. 마지막 Tool 뒤에 스트리밍된 텍스트만 최종 응답으로 렌더링하며,
Tool이 없는 응답은 전체 텍스트를 유지한다.

첫 공개 Tool 호출 전에는 빈 assistant 메시지에 `요청 분석 중` indicator를
즉시 표시한다. 첫 content part가 도착하면 indicator는 실제 ToolGroup 또는
스트리밍 답변으로 교체된다. 준비 중인 Composer 제어는 비활성 상태를 유지하되
금지 커서를 표시하지 않는다.

Tool 실행 단계는 assistant-ui가 계산한 그룹 `part.status`를 따른다. 회전
아이콘은 메시지 전체 실행 상태를 따라 요청 분석, Tool 실행, 최종 답변 작성
동안 유지한다. Tool이 끝난 뒤 최종 텍스트가 스트리밍되는 동안 그룹은 열린
상태에서 `응답 작성 중`으로 바뀌고, 완료되면 완료 아이콘과 `응답 작성 완료`를
표시한 뒤 접힌다. Tool 호출과 연결되지 않은 공개 `status` 이벤트는 metadata로 전달해
같은 실행 과정 블록의 `AgentPlan`에 표시한다. Tool-linked status는 개별 Tool
행이 이미 표현하므로 중복 렌더링하지 않는다. 최종 상태에서는 실행 과정 전체를
자동으로 접고, 다시 펼치면 공개 단계 → Tool 목록 → Parameters/Result 순으로
확인할 수 있다.

근거: [계획 이력 요약](History.md).

### 검증된 차트 Tool UI (2026-09-16, 활성)

`prepare_visualization`은 Backend에서 계속 실행하고, assistant-ui toolkit에는
같은 이름의 렌더링 전용 backend Tool UI만 등록한다. 성공 payload의 32자
`visualization_id`를 기존 조회 API와 런타임 검증을 거쳐 Recharts에 전달한다.

차트 Tool은 `display: "standalone"`으로 실행 과정 disclosure에서 분리해 최종
설명 다음에 둔다. 같은 `result_id`의 실패 호출을 Agent가 후속 성공으로 보정하면
앞선 실패 UI는 숨기며, 모두 실패한 경우에는 안전한 오류를 표시한다. 기존
`chart` marker renderer는 과거 메시지 호환용으로 유지하고 같은 ID의 Tool UI가
있으면 중복 렌더링하지 않는다. 새 Agent 응답은 marker를 작성하지 않는다.

FastAPI SSE, `useExternalStoreRuntime`, Result Store와 시각화 API 계약은 변경하지
않았다. Generative UI, AI SDK transport, 프론트 실행 Tool과 새 패키지도 추가하지
않았다.

근거: [계획 이력 요약](History.md),
[assistant-ui Tool UI](https://www.assistant-ui.com/docs/tools/tool-ui).

### 대화형 표 Tool UI와 표시 100행 (2026-09-16, 활성)

공용 `DataTable`과 답변 Markdown 표는 데이터 행을 최대 100개까지 렌더링하고,
세로 높이를 제한한 내부 스크롤로 다음 메시지가 밀리지 않게 한다.

Backend의 `prepare_table(result_id, columns?, title?)`은 Result Store에서 scope,
TTL과 선택 컬럼을 검증하고 앞쪽 최대 100행을 반환한다. 모델은 행 배열을 입력으로
보내지 않는다. Frontend는 같은 이름의 render-only backend Tool UI를
`display: "standalone"`으로 등록해 최종 설명 다음에 표시한다.

대화형 표는 전달된 최대 100행 범위에서 전체 셀 검색, 열 오름차순·내림차순 정렬,
페이지 크기 10·25·50·100과 이전·다음 이동을 제공한다. payload의 열·행 길이,
스칼라 타입, 행 수와 Result Store ID가 계약과 다르면 안전한 오류로 닫는다.

명시적인 표 요청이나 Result Store 조회 뒤 Markdown 표 응답에서 모델이
`prepare_table`을 빠뜨리면 Backend가 마지막 접근 가능한 `result_id`로 Tool 이벤트를
보완한다. 이 이벤트가 답변 텍스트 뒤에 도착해도 Frontend는 설명을 보존하고 표를
답변 아래에 둔다. 성공한 표 Tool UI와 같은 응답의 GFM 표 블록만 제거해 데이터가
두 번 표시되지 않게 한다.

근거: [계획 이력 요약](History.md),
[assistant-ui Tool UI](https://www.assistant-ui.com/docs/tools/tool-ui).

### assistant-ui Primitives Overview·Composer 점검 (2026-09-16, 활성)

Primitives는 runtime 상태·접근성·키보드 동작을 제공하고 스타일은 제공하지 않는다.
따라서 공통 채팅 UI는 공식 Elements를 우선 사용하고, 프로젝트 전용 레이아웃이나
동작이 필요한 부분만 Primitive를 직접 조합하는 현재 경계를 유지한다. 모든
Primitive는 루트 `AssistantRuntimeProvider` 아래에서 기존 FastAPI SSE 기반
`useExternalStoreRuntime`을 사용한다.

현재 새 메시지와 인라인 편집은 각각 Thread와 Message 문맥 안의
`ComposerPrimitive.Root`를 사용한다. `Input`, `Send`, `Cancel`이 입력 상태,
전송 가능 여부, 실행 취소와 편집 취소를 runtime에 연결하며, 전송·중단 버튼은
`asChild`로 프로젝트 버튼 스타일만 합성한다. deprecated `ComposerPrimitive.If`나
`submitOnEnter`는 사용하지 않는다. 제품의 키보드 정책은 `submitMode="enter"`로
명시해 Enter 전송과 Shift+Enter 줄바꿈을 유지한다.

현재 Composer는 모델·추론 표시를 포함한 두 줄 레이아웃이므로 `compact` 모드를
적용하지 않는다. Headless input도 현재 textarea로 충분해 도입하지 않는다.
첨부와 dropzone은 attachment adapter·Backend payload 계약이 마련된 뒤 활성화하고,
음성 입력은 폐쇄망에서 사용할 DictationAdapter가 정해진 뒤 검토한다. Quote는
메시지 인용 계약, Queue는 후속 입력 실행 정책, unstable trigger popover는 멘션·
명령의 의미와 안정 API가 확정될 때까지 보류한다.

근거: [assistant-ui Primitives](https://www.assistant-ui.com/docs/primitives),
[assistant-ui Composer](https://www.assistant-ui.com/docs/primitives/composer).

### assistant-ui Thread·Message Primitive 점검 (2026-09-16, 활성)

Thread는 `Root` 아래의 실제 스크롤 컨테이너에 `Viewport`를 두고, 메시지는
`Messages` children render function으로 편집·사용자·assistant 역할을 나눈다.
빈 상태와 실행 상태는 deprecated `Empty`·`If` 대신 `AuiIf`를 사용하고,
Composer는 `ViewportFooter`, 이동 버튼은 `ScrollToBottom`에 연결한다. 현재 제품은
새 답변의 끝을 따라가는 전통적인 채팅 흐름으로 검증됐으므로 상단 turn anchor로
바꾸지 않는다. `turnAnchor="bottom"`과 `autoScroll`을 명시해, 사용자가 위로
스크롤한 경우에는 위치를 보존하면서 새 실행과 스트리밍의 하단 추적을 유지한다.

시작 화면 예시는 런타임이 생성한 suggestion 목록이 아니라 제품에 고정된
예시 질문이다. 정적 `Suggestions` scope와 `ThreadPrimitive.Suggestions`
iterator, `SuggestionPrimitive`를 사용한다. `ViewportProvider`,
`MessageByIndex`와 experimental `Unstable_MessageById`는 현재 표준 목록 렌더링에
필요하지 않다.

Message는 `Root`가 제공하는 문맥과 hover 상태를 ActionBar가 사용한다. 사용자
메시지는 현재 계약상 text만 `Parts` children renderer로 표시한다. Assistant는
인접한 일반 Tool을 `GroupedParts`와 `groupPartByType`으로 묶고, globally registered
Tool UI가 해석된 `part.toolUI`를 우선한 뒤 프로젝트 fallback을 사용한다. text는
Markdown과 `MessagePartPrimitive.InProgress`, 오류는 `MessagePrimitive.Error`와
`ErrorPrimitive.Message`로 표시한다. deprecated `components`, `Content`,
`MessagePrimitive.If`와 unstable grouping API는 사용하지 않는다.

현재 메시지 변환 계약은 text와 tool-call만 생성한다. image·file·attachment,
quote, reasoning/source/data part는 해당 Backend·adapter 계약을 도입할 때 렌더러와
함께 추가한다. Generative UI는 기존 Tool UI 결정을 유지하며 도입하지 않는다.

근거: [assistant-ui Thread](https://www.assistant-ui.com/docs/primitives/thread),
[assistant-ui Message](https://www.assistant-ui.com/docs/primitives/message).

### assistant-ui ActionBar·BranchPicker Primitive 점검 (2026-09-16, 활성)

ActionBar는 모든 메시지의 `MessagePrimitive.Root` 안에 두고 `hideWhenRunning`과
`autohide="not-last"`를 사용한다. 마지막 메시지의 액션은 바로 보이고, 이전
메시지의 액션은 hover 시 나타나며, 실행 중에는 숨긴다. 사용자 메시지는
`Copy`·`Edit`, assistant 메시지는 `Copy`·`Reload`를 제공한다. 각 버튼의 실행
가능 여부와 disabled 상태는 Primitive가 runtime capability에서 계산하고,
프로젝트는 `asChild`로 아이콘 버튼 스타일과 접근 가능한 이름만 합성한다.
복사 완료 상태도 runtime의 `message.isCopied`로 안내한다.

현재 ActionBar가 차지하는 메시지 footer 공간은 안정적으로 유지하므로 floating
전환과 전용 CSS를 추가하지 않는다. `Speak`·`StopSpeaking`은 폐쇄망용
SpeechSynthesisAdapter, feedback은 저장 API와 FeedbackAdapter가 필요해 보류한다.
`ExportMarkdown`과 `ActionBarMore`는 동작할 수 있지만 현재 복사와 겹치며 별도
내보내기 요구가 없어 추가하지 않는다. 요구가 생기면 보조 액션을 overflow
메뉴에 묶어 키보드·focus 동작을 함께 적용한다.

BranchPicker는 현재 도입하지 않는다. External Store runtime에서 `setMessages`와
branch adapter를 의도적으로 제공하지 않아 `switchToBranch` capability가 없고,
편집·재생성은 선택한 지점 이후의 화면 메시지를 새 실행 결과로 교체한다.
Backend의 `fork_from_turn_id`는 재실행 시작점을 지정할 뿐, 이전 답변을 탐색 가능한
대안으로 보존하는 branch repository 계약이 아니다. Picker만 추가하면 1/1을
표시하거나 비활성 제어가 생겨 실제 기능을 과장하게 된다.

향후 BranchPicker 도입은 부모·대안 message id를 보존하는 저장 구조, branch 목록
조회·전환, 세션 재접속 후 복원, Frontend branch adapter를 한 작업에서 설계한다.
그때 사용자와 assistant 메시지 footer에 `hideWhenSingleBranch`를 적용해 대안이
두 개 이상일 때만 Previous·Number·Count·Next를 표시한다.

근거: [assistant-ui ActionBar](https://www.assistant-ui.com/docs/primitives/action-bar),
[assistant-ui BranchPicker](https://www.assistant-ui.com/docs/primitives/branch-picker).

### assistant-ui ThreadList·Suggestion Primitive 점검 (2026-09-16, 활성)

현재 왼쪽 목록은 저장된 대화가 아니라 `SESSIONS` 예시 데이터를 표시하는 props
기반 standalone ThreadList다. 새 대화와 항목 선택도 assistant-ui thread를
생성·전환하지 않고 현재 한 개의 External Store runtime을 초기화한다. 화면에
`예시 세션 · 현재 대화만 유지됩니다`를 표시해 영속 기능으로 오해하지 않게 한다.

실제 `ThreadListPrimitive`는 thread list runtime과 함께 생성·선택·제목·보관·
삭제 상태를 소유한다. 현재 설치 버전의 `ExternalStoreThreadListAdapter`에서
thread 전환 API는 여전히 active development로 표시되며, 더 안정적인
`RemoteThreadListAdapter` 경로도 list·initialize·fetch·rename·archive·delete,
제목 생성과 thread별 message hydration이 모두 필요하다. Backend에 이 계약이
없으므로 현재 목록을 Primitive로 감싸거나 비활성 Archive/Delete 메뉴를 추가하지
않는다. 실제 세션 API와 권한·식별자·복원 정책이 준비되면 공식 Elements 소스를
연결하고 `Items` children renderer, `data-active`·`aria-current`, 기본 키보드 탐색과
`sharedFocusGroup` 메뉴를 함께 사용한다.

고정 시작 질문(`lib/dummy.ts`의 개발용 예시)은 `AuiConfig`의 `Suggestions(EXAMPLE_QUESTIONS)`로 등록하고,
`ThreadPrimitive.Suggestions` iterator 안에서 `SuggestionPrimitive.Trigger`와
`Title`을 렌더링한다. 클릭 즉시 실행하는 제품 동작은 `send`로 유지한다. 이로써
정적 제안의 데이터 소유권과 화면 반복·trigger 동작이 공식 scope 경계를 따른다.

동적 후속 제안은 `thread.suggestions`가 생길 때 직접 그 배열을 읽고 각 prompt를
self-contained `ThreadPrimitive.Suggestion`으로 렌더링하는 경로가 맞다. 정적
Suggestions scope가 동적 값을 가리기 때문에 공식 문서도 이 조합을 사용한다.
현재 Backend는 후속 제안을 보내지 않으므로 설치된 follow-up 컴포넌트는 활성
화면에 연결하지 않는다. deprecated `autoSend`·`method`는 사용하지 않는다.

근거: [assistant-ui ThreadList](https://www.assistant-ui.com/docs/primitives/thread-list),
[assistant-ui Suggestion](https://www.assistant-ui.com/docs/primitives/suggestion).

### assistant-ui ChainOfThought·Error Primitive 점검 (2026-09-16, 활성)

`ChainOfThoughtPrimitive`와 `components.ChainOfThought`는 기존 코드 유지용 legacy
API이므로 도입하지 않는다. Assistant 메시지는 권장 API인
`MessagePrimitive.GroupedParts`와 stable fingerprint를 제공하는
`groupPartByType`으로 인접한 일반 Tool 호출만 묶는다. globally registered
standalone Tool UI는 그룹 밖에 두고, 그룹·text·tool-call은 children renderer가
각각 표시한다. synthetic indicator는 프로젝트의 공개 실행 상태 UI와 중복되므로
`indicator="never"`를 유지한다.

Backend `status` 이벤트는 모델 reasoning token이나 비공개 chain-of-thought가
아니라 사용자에게 공개하기로 한 업무 진행 단계다. 따라서 message reasoning
part로 변환하지 않고 metadata의 `statuses`와 `AgentPlan`으로 표시한다. Claude SDK
thinking block은 계속 폐기하며, 향후 공개 reasoning part 계약을 별도로 도입하는
경우에만 `GroupedParts`의 reasoning 경로를 추가한다.

메시지 오류 블록은 `MessagePrimitive.Error`로 전체 UI를 조건부 렌더링하고,
`ErrorPrimitive.Message`로 `incomplete/error` 상태의 안전한 오류 문구를 자동
추출한다. 공용 `ErrorState`의 루트가 이미 단일 `role="alert"`를 제공하므로
`ErrorPrimitive.Root`를 다시 중첩하지 않는다. 이 구성은 Root가 제공하는 접근성
역할과 Message의 자동 문구 추출을 분리해 같은 경고를 스크린 리더가 두 번
알리지 않게 한다. 오류 재실행은 `ActionBarPrimitive.Reload`를 사용해 다른 실행
중에는 runtime이 자동으로 비활성화한다.

근거: [assistant-ui ChainOfThought](https://www.assistant-ui.com/docs/primitives/chain-of-thought),
[assistant-ui Error](https://www.assistant-ui.com/docs/primitives/error).


### 표·차트 문맥 보존 (2026-09-16, 활성)

일반 Tool은 실행 과정 그룹으로 모으되, standalone 표·차트를 포함한 도입·해석
구간은 이후 추가 조회가 있어도 보존한다. 마지막 일반 Tool 뒤 답변도 유지한다.
이는 중첩 Tool 결정의 중간 준비 문구 생략 정책을 표·차트 문맥에 한해 보완한다.
중복 Markdown 표 제거는 코드 펜스를 건드리지 않는다. 결과 없이 끝난 Tool은
완료로 추정하지 않고 미완료로 표시한다.

근거: [계획 이력 요약](History.md).

### 공개 실행 안내의 가독성과 수명 (2026-09-16, 활성)

`요청 분석 중`과 실행 중 헤더는 13px `text-ui`, `text-ink-2` 이상의 고정 대비로
표시한다. 회전 아이콘이 이미 진행 상태를 전달하므로 텍스트 shimmer에 의존하지 않는다.
독립 공개 status의 단계 본문도 같은 크기 계열로 표시한다.

일반 Tool 직전의 공개 `AgentEvent.text`는 해당 Tool이 실행되는 동안 metadata의
`progressText`로 유지한다. ToolGroup 상단에 강조 블록으로 배치하지 않고,
이전 Tool 행 뒤와 현재 실행 Tool 행 사이에 일반 본문 스타일로 표시한다.
Tool 결과 또는 다음 공개 텍스트가 도착하거나 메시지가 종료되면 제거한다.
실행 중 헤더의 좌측 아이콘은 동작 상태가 유지되는 동안 계속 회전한다.
이는 Backend adapter를 통과한 공개 문구에만 적용한다. Claude SDK의
thinking/signature/tool input delta는 계속 폐기하며 reasoning UI로 변환하지 않는다.

근거: [계획 이력 요약](History.md).

### 지식 관리와 조회 패널 (2026-09-16, 활성)

좌측 상단 전역 메뉴에 새 채팅·지식 관리를 두고 그 아래 최근 대화 목록을
배치한다. 중앙 관리 화면은 텍스트 등록·검토·
활성화·이력을 제공하고 구조화 YAML은 읽기 전용으로 표시한다. 우측은 도구·스킬·지식
조회 탭이며 Metadata·Prompt 예시 패널과 더미 값은 제거했다. 지식 탭은 제목·유형·
검토 상태와 짧은 설명을 간결한 목록으로 함께 제공한다. 출처와 관리 화면 이동은 우측
패널에서 제거했다.

라우터나 신규 패키지는 도입하지 않았다. 루트 AssistantRuntimeProvider와 useAgentChat을
유지하고 Thread를 언마운트하지 않는다. 관리 화면에서는 채팅 viewport의 크기를 보존한
채 숨기고 자동 추적을 중지한다. display:none은 SDK가 viewport를 하단으로 오인해 스크롤
위치를 잃게 하므로 채팅 영역에 사용하지 않는다. 지식 관리에서 중앙 헤더의 별도
복귀 버튼과 별도 `채팅` 메뉴는 두지 않는다. 현재로 표시된 최근 대화 항목으로
복귀하며 스크롤과 진입 요소 포커스를 복원한다. `새 채팅`은 현재 대화를 초기화하고
현재 실행 동안 최근 목록에 `새 대화` 항목을 추가한다. 영속 세션 계약은 아직 없으며
문서 인용은 document_id와 version으로 보존된 본문을 연다.

입력은 일반 텍스트이며 임의 HTML을 렌더링하지 않는다. 관리 API 응답은 런타임 검증하고
실패해도 편집 내용을 보존한다. 변경 후 목록·패널을 갱신하되 열린 편집본을 자동으로
덮어쓰지 않는다. 동시 변경은 서버 revision 충돌 후 수동 새로고침으로 해결한다.

근거: [계획 이력 요약](History.md).

### 지식 관리 구조화 상세 표현 (2026-09-16, 활성)

구조화 YAML 상세는 raw JSON 대신 값의 의미에 맞는 UI로 표시한다. 최상위는
사용자용 필드 라벨과 값의 2열 구조로 통일하고, 태그·grain은 wrap 가능한 chip,
문장 배열은 불릿 목록, 컬럼 배열은 이름·형식·설명의 반복 행, 중첩 객체는 작은
정의 목록, SQL 예시는 질문·SQL 블록을 사용한다. 원본 값은 변경하거나
추측하지 않는다. 최상위 빈 값은 `없음`으로 알리되 컬럼마다 반복되는 선택적
빈 필드는 생략해 비교 밀도를 유지한다.

좌측 지식 목록은 유형과 상태를 같은 행에 두고 제목·요약을 아래로 정렬한다.
현재 선택은 색상만이 아니라 accent 좌측 룰과 `aria-current`로 함께 표현한다.

근거: [계획 이력 요약](History.md).

### Agent Workbench 감사 후속 정책 (2026-09-16, 활성)

기존 assistant-ui primitives·Elements와 ExternalStoreRuntime/SSE 소유권을 유지한다.
이 결정은 앞선 완료 이력을 취소하지 않고 다음 표시 정책만 보완한다.

- 성공한 standalone 표의 존재만으로 다른 Markdown 표를 지우지 않는다.
  검증된 payload의 컬럼·전체 행과 일치하는 단순 표만 중복 처리하고 서식·의미가 모호하면 남긴다.
- ActionBar의 hover 기반 unmount를 사용하지 않는다. 기존 Copy/Edit/Reload는
  키보드 접근 가능한 DOM으로 유지한다. 교체·재생성 전 브라우저 기본 확인창으로
  대화/초안 손실·후속 메시지 수·복원 불가를 안내하며 취소는 상태를 바꾸지 않는다.
- 턴 종료와 Tool 성공을 구별해 그룹에 오류·미완료 개수를 남긴다.
  빈 응답, 0행 성공, 결과 누락은 별도 문구로 표시한다. 자동 접힘은 유지하되
  숨겨질 상세에 포커스가 있으면 보이는 trigger로 돌리고 외부 포커스는 유지한다.
- 실행 단계는 안정적인 polite 상태 영역으로 알린다. 오류 alert와 중복하지 않고
  토큰·타이머는 알림에 포함하지 않는다. 2026-09-22부터 reduced-motion에서도 실행 중 아이콘 회전은 유지한다(진행 신호).
- 경과 시간은 performance.now로 관측한 프론트 로컬 metadata다.
  요청 시작→종료/오류/취소, 동일 Tool 호출 수신→결과 수신만 측정하며 과거 값은 합성하지 않는다.
  서버 시간과 별개이며 작은 표시 컴포넌트만 초 단위로 갱신한다.
- 기존 860/1180px 임계값 아래 재개방은 같은 DOM을 쓰는 비모달 overlay로 처리한다.
  Escape/닫기는 trigger로 복귀하고 Tab 이탈은 패널을 닫되 외부 포커스를 유지한다.
  확대 시 패널을 자동으로 펼치지 않는다.
- 핵심 메타·표 헤더는 ink-2, 긴 본문은 overflow-wrap:anywhere,
  SQL/CTE는 max-h-96 내부 스크롤을 쓴다. main·명명된 aside·답변 h2와 내용 h3~h6으로
  의미를 전달하되 글자 크기는 기존 dense type scale을 유지한다.
- 차트에는 기존 chart.data의 축/단위/값을 읽는 접이식 표를 제공한다.
  Inspector 탭은 숨김 상태로 mount를 유지해 필터·스크롤을 보존한다.
  모델·추론 제어는 실제 설정으로 표시하지 않고 준비 중·미연결임을 명시한다.

새 라이브러리나 API는 추가하지 않았다. 서버 timing·모델 설정 API·대화 영속 저장은
별도 계약 검토로 보류한다. 실제 스크린리더·대규모 대화 성능은
브라우저 DOM/키보드·fixture 통과와 구분해 운영 인수에서 확인한다.

근거: [계획 이력 요약](History.md),
[assistant-ui ActionBar](https://www.assistant-ui.com/docs/primitives/action-bar),
[assistant-ui Message timing](https://www.assistant-ui.com/docs/guides/message-timing).

### 대화 화면 전환 확인창 제거 (2026-09-16, 활성)

사용자가 현재 비영속 세션의 한계를 알고 있으며 DB 세션 관리는 추후 연결하기로 했다.
따라서 앞선 감사 후속 정책 중 새 채팅·예시 세션 교체의 기본 확인창만 제거한다.
전환 시 기존 초기화 동작과 Sidebar의 비영속 안내는 유지한다. 지식 편집의 미저장
변경 보호·답변 재생성 확인은 제거 대상이 아니다. 저장 API나 로컬 persistence는 추가하지 않는다.
일반적인 확인창 권고보다 명시적인 사용자 요청을 우선하며 반복 전환을 막지 않는다.

근거: [계획 이력 요약](History.md).

### Inspector 도구·Skills 가독성 (2026-09-16, 활성)

도구 상세는 사용자가 탐색에 필요한 설명과 결과 형태만 남기고 입력 JSON Schema를
표시하지 않는다. API 계약과 Agent의 tool schema는 변경하지 않는다.

Skills 탭은 각 절차를 다시 펼치는 버튼을 제거하고 등록된 절차 본문을 바로 보여준다.
원문 Markdown은 HTML 제목·번호/불릿 목록·강조·인라인 코드로 안전하게 렌더링하며
임의 HTML은 무시한다. Skill 이름 h3 아래 본문 제목은 h4부터 시작한다. 항목 간 구분선,
본문 좌측 룰, 기존 semantic token과 type scale로 긴 절차의 읽기 흐름을 구분한다.
1280px 이상에서는 Inspector를 23rem으로 넓히고, 그 아래 및 작은 화면 overlay는
기존 20rem을 유지해 Chat 작업 폭을 보호한다.

기존 `@assistant-ui/react-markdown`이 사용하는 `react-markdown` 10.1.0을 직접 의존성으로
명시해 정적 Skill 본문에도 같은 GFM 파서를 재사용한다. 신규 디자인 라이브러리나
Backend payload는 추가하지 않는다.

근거: [계획 이력 요약](History.md).

### Skills disclosure 복원 (2026-09-16, 활성)

사용자 요청에 따라 Skills 항목의 disclosure를 복원한다. 이름·상태·요약은 접힌
상태에서도 보이고, 상세 절차는 사용자가 선택한 항목만 펼친다. 앞선 결정의 Markdown
HTML 렌더링, 제목 위계, 여백, 23rem 데스크톱 폭은 유지한다. trigger는 네이티브
button과 `aria-expanded`·`aria-controls`를 사용하고, 펼친 항목만 상세 API를 호출한다.

근거: [계획 이력 요약](History.md).

### Disclosure·Inspector 레이아웃 안정화 (2026-09-17, 활성)

완료된 실행 과정의 ToolGroup은 펼침·접힘 때 높이, blur, slide와 자식 stagger
애니메이션을 적용하지 않는다. disclosure 내용 아래의 최종 답변과 표가 여러 프레임에
걸쳐 이동해 중앙 채팅이 흔들리는 것처럼 보이지 않게 즉시 최종 레이아웃을 적용한다.
상태를 알리는 chevron 회전과 접근 가능한 `aria-expanded` 계약은 유지한다.

Inspector의 각 탭 스크롤 영역은 `scrollbar-gutter: stable`로 세로 스크롤바 공간을
항상 예약한다. Skill 상세가 길어져 스크롤바가 생겨도 기존 설명의 가용 폭과 줄바꿈이
바뀌지 않는다. 이 예약 공간은 도구·스킬·지식 탭에 동일하게 적용한다. 좁은 화면의
Inspector는 `absolute` overlay만 적용해 중앙 Chat의 grid 폭을 소비하지 않는다.

## 모바일 환경 비지원 (2026-09-21, 활성)

이 앱은 모바일 환경에서 구동하지 않는다. 휴대폰·태블릿 폭(~400px) 검증, 터치 조작,
모바일 device emulation과 가상 키보드 확인을 검증·테스트 항목으로 두지 않는다. 기존
문서의 "~400px까지 가로 스크롤 없음"과 "모바일 가상 키보드" 검증 요구를 삭제했다.
브라우저 확인은 1280px 이상 데스크톱 폭에서 한다. 데스크톱 창을 줄였을 때의 패널
접힘 임계값(Sidebar 860px, Inspector 1180px)은 모바일 지원이 아니라 창 크기 대응이므로
제품 동작과 회귀 테스트로 유지한다.

## 구조화 지식 편집·검토·승인 화면 (2026-09-21, 활성)

구조화 YAML(table·KPI·recipe·simulation·용어·시나리오)을 이 화면에서 수정하고, 작성자가
검토를 요청하면 승인 권한자가 승인해 검색·Tool에 반영한다. 직접 수정 API는 없고 변경
요청만 존재한다. 이전 결정(구조화 상세 읽기 전용)은 이 항목으로 대체한다. 상세 조회
화면(`StructuredDetail`)은 그대로 읽기 전용이며 편집은 별도 편집기에서만 한다.

- 라우터와 새 패키지 없이 기존 `KnowledgeManager` 안에서 편집기(`knowledge/editor/`)를
  연다. 폼 라이브러리·YAML 파서·코드 편집기·diff 라이브러리는 도입하지 않는다(폐쇄망 반입
  부담). 프론트는 YAML을 파싱하지 않고 서버 `validate`에 위임한다.
- 입력 폼은 서버가 내려주는 가이드 명세(`GET /api/knowledge/guides/{kind}`)로 그린다.
  구조(필수·타입·enum)는 백엔드 모델이, 라벨·도움말·예시는 가이드가 소유하므로 종류가
  늘어도 화면 코드는 늘지 않는다. 폼과 원문 YAML은 같은 내용의 두 표현이며 전환은
  서버 변환으로 한다. YAML 문법 오류가 있으면 폼 전환을 막고 오류를 보여준다.
- 검증은 입력을 멈춘 뒤 서버 dry-run(모델 + 참조 정합성)으로 하고 필드 경로별로 인라인
  표시한다. 검증을 통과해야 검토를 요청할 수 있다. 저장·전이 실패 시 입력은 지우지
  않고, 서버 문구는 노출하지 않으며 상태 코드별 한국어 문구로만 안내한다.
- 변경 검토는 자체 줄 단위 diff로 현재 승인본과 비교한다. 추가·삭제는 색과 기호(+/−),
  스크린 리더용 텍스트를 함께 쓴다. 이전 줄이 이후 줄 위에 온다.
- 권한은 `GET /api/me`의 `permissions`·`knowledge_management`만 보고 버튼을 켜고 끈다.
  화면에 역할 이름 분기를 두지 않아 실제 인증이 연결돼도 화면은 바뀌지 않는다.
  자기 승인이 막힌 경우 승인 버튼을 비활성화하고 이유를 밝힌다.
- 인증 전(`mode: "stub"`)에만 임시 사용자 선택기를 보이고, 실제 인증이 아니며 작성자·승인자를
  구분해 기록할 뿐이라고 화면에 밝힌다. 선택값은 localStorage에 보관하되 접근 실패에도
  동작하며 `X-User-Id` 헤더로 보낸다. 인증이 붙으면 선택기와 `lib/knowledge-user.ts`를 제거한다.
- 승인은 되돌리기 어려운 공용 변경이므로 `window.confirm` 대신 Dialog로 근거 메모를 필수로
  받고 "이후 모든 대화의 검색·Tool에 바로 반영"됨을 명시한다.
- 미저장 변경 보호(`requestLeave`, `beforeunload`, 저장 후 이동·변경 취소 후 이동·계속 편집)는
  텍스트 지식과 같은 경로를 쓴다.

근거: 백엔드가 초안·검토 이력은 SQLite에, 최종 내용은 `knowledge/` YAML에 두어 단일 기준을 유지한다.


## assistant-ui 디자인 적용 범위 (2026-09-22, 활성)

공식 디자인 원문은 `assistant-ui-design.md`에 폐쇄망 사본으로 보관하고, 프로젝트별
결정만 이 문서에 남긴다. 상세 token 값은 `globals.css`와 `tailwind.config.ts`가 기준이다.

- 라이트 테마와 시스템 Sans/Mono font만 사용한다. 외부 font·CDN은 도입하지 않는다.
- Chat이 primary인 3-pane 데스크톱 UI를 유지한다. 모바일 전용 UX는 지원하지 않는다.
- 모델 thinking은 표시하지 않으며 공개 `status`는 업무 진행 단계로만 표현한다.
- 원격 image·attachment·voice·Assistant Cloud는 Backend 계약이 생기기 전까지 도입하지 않는다.
- radius는 document(6px), control(8px), surface(10px), floating card(12px),
  thread(16px), capsule 체계를 사용한다. thread radius는 Composer 등 제품 surface에만 쓴다.
- blue accent는 streaming·running·connected·selected와 focus에 사용하고, CTA는 ink 계열을 쓴다.
  기존 텍스트 링크와 pane resize affordance의 accent는 범위를 넓히지 않는 조건으로 유지한다.
  (2026-09-23 결정으로 대체, "accent를 signature color로 확장" 참고.)
- 장식적 gradient·glass·과도한 shadow와 전면 카드화를 피하고 상태는 색만으로 전달하지 않는다.

## assistant-ui 통합 전환 (2026-09-22, 활성)

`present` Generative UI 결과 전환과 LocalRuntime 전환을 한 계획으로 수행했다. Backend `/api/chat` SSE 계약은
바뀌지 않는다.

### 결정

- **Runtime**: `useExternalStoreRuntime`(직접 소유한 메시지 상태)을 `useRemoteThreadListRuntime` + thread별
  `useLocalRuntime`으로 바꿨다. `lib/chat-model-adapter.ts`의 async generator가 기존 `sendChatMessage`·
  `applyAgentEvent`·`convertMessage`를 그대로 쓰고, 메시지 저장·취소·편집·재생성·분기는 runtime이 맡는다.
  `hooks/use-agent-chat.ts`와 `ConnectionBanner`, 재생성 `window.confirm`은 삭제했다(연결 실패 재시도는
  `MessageError`의 Reload).
- **fork 규칙**(`planTurn`): 분기 경로에서 가장 가까운 성공 assistant의 `turnId`가 anchor다. 대화 head(마지막 성공
  turn)와 같으면 `fork_from_turn_id`를 생략(이어쓰기), 다르면 anchor에서 fork, anchor가 없고 head가 있으면 `""`.
  head는 성공 종료 상태를 yield하는 순간 갱신한다(마무리 대기 중 다음 질문이 시작돼도 어긋나지 않게).
- **분기·다중 thread**: 편집·재생성은 이전 내용을 지우지 않고 BranchPicker로 남긴다. thread 목록·메시지는
  `lib/agent-threads.ts`의 메모리 저장소(`RemoteThreadListAdapter`·`ThreadHistoryAdapter`)이며 브라우저 세션 동안만
  유지된다. 다른 thread가 응답 중이어도 전환할 수 있고 실행은 계속된다(런타임이 thread를 유지). 계획의
  `RemoteThreadList({backgroundThreads})`는 runtime hook 경로에서 옵션이 없어 쓰지 않았다. Backend 앵커는 프로세스
  메모리이므로 재시작 후 fork는 Backend `error`로 돌아올 수 있다.
- **결과 Tool UI**: Backend가 실행한 flat `present_sql_preview`·`present_chart`·
  `present_table`·`present_simulation`을 Tool 이름별 renderer로 표시한다. 각 renderer는
  snake_case args를 Zod로 검증해 기존 결과 컴포넌트 prop으로 변환한다.
- **Tool wire 경계**: 재귀 `$type` tree와 JSON 문자열 이중 인코딩은 사용하지 않는다.
  Tool args에는 scalar 설정과 `result_id`만 두며 원본 행·차트 data 배열을 싣지 않는다.
- **결과 데이터**: 트리에는 `resultId`와 표시 설정만 있다. `QueryTable`은
  `@tanstack/react-table` 9.2.4 수동 모드로 `/api/query-results/{id}/table`에 page·전체 셀 검색·
  단일 열 정렬을 보낸다. Result Store의 최대 1,000건에 서버가 먼저 검색·정렬을 적용하고
  기본 10행의 현재 page만 반환한다. 차트는 `/chart` 서버 집계 응답을 조회한다
  (요청 공유·abort·성공만 cache). 전체 행은 브라우저에 한 번에 오지 않는다.
- **Schema 계약**: FE Zod와 Backend Tool schema는 `tests/fixtures/present-vocabulary.json`
  (Backend 사본)으로 비교한다. 여러 결과는 메시지 안에 순차적으로 표시하고 관계는
  Assistant Markdown으로 설명한다. 별도 Card grouping 계약은 없다.
- **실패한 `present`**: 같은 메시지에서 이후 `present`가 성공하면 실패 호출은 숨기고, 전부 실패하면 오류 알림 표면을
  그대로 보여 준다(계획의 "ToolGroup 안 표시"에서 단순화).
- **결과 모드**: Backend는 `present` 결과 UI만 보낸다(legacy `prepare_*`/`RESULT_UI_MODE` 플래그는 제거됨).
  `DatabaseResult`·`SimulationResult`는 bounded preview(`sample_rows` 객체 배열, `statistics`)만 받는다.
- **Tool UI**: 실행 과정 그룹의 12개 도구를 toolkit에 등록하고(`RegisteredToolUI`) 표·차트·`present`는 standalone으로
  등록했다. 종류별 본문 선택(`TOOL_META`)은 `ToolResultCard`에 남겼다.
- **후속질문**: `done.data.suggestions`(2~4개·각 120자 이하·중복 제거)를 엄격히 검증해 `metadata.custom`에 싣고
  `adapters.suggestion`이 그대로 돌려준다(모델 호출 없음). Backend가 보내지 않으면 표시되지 않는다.
- **정리**: 미사용 복사 소스(image·file·attachment·reasoning·tool-fallback·thread-list 2종)와 더미 세션·시드 대화를
  삭제했다.

### 알려진 한계

- 취소된 응답은 소요 시간을 표시하지 않는다(runtime이 취소 뒤 스냅샷을 받지 않아 종료 시각을 기록할 수 없음).
- 새로고침하면 대화·분기·목록이 사라진다. 영속 대화 API가 필요하다.
- legacy `prepare_*` renderer(`table-tool-ui`·`visualization-tool-ui`·`chart-marker`)와
  `/api/visualizations` client(`visualization-api.ts`)는 2026-09-22에 삭제했다. Backend가
  더 이상 `prepare_table`/`prepare_visualization`을 호출하지 않는다(사용자 결정으로 별도
  observation gate 없이 즉시 제거).

## accent를 signature color로 확장 (2026-09-23, 활성)

**배경**: "assistant-ui 디자인 적용 범위(2026-09-22)"에서 accent를 live 상태
(streaming·running·connected·selected)와 focus 전용으로 좁히고 CTA는 ink로
되돌렸다. 이후 제품 요구로 프로젝트 전체에 드러나는 signature color가
필요해졌고, 새 색을 들이는 대신 기존 accent를 그 용도로 겸하기로 했다.

**결정**: accent(blue, `#2f5fd0`)는 이제 live 상태·focus에 더해 프로젝트
유일의 signature color를 겸한다. 1차 CTA 채움(지식 편집기 검토 요청·승인,
Composer 전송 버튼과 메시지 편집 후 "저장하고 다시 실행" 버튼), 탭 active
상태, 사이드바 로고 배지에 적용한다. 두 번째 브랜드 색은 들이지 않는다
("single accent" 원칙 유지). Composer의 중단(취소) 버튼처럼 1차 CTA가 아닌
상태 전환 액션은 계속 ink 계열을 쓴다.

**영향**: `--shadcn-primary`를 `--ink`에서 `--accent`로 바꿔 shadcn 기본
`<Button variant="default">`도 같은 정책을 따르게 했다(현재 이 variant를
쓰는 feature 코드는 없어 시각적 영향은 없음).

**대체 관계**: "assistant-ui 디자인 적용 범위(2026-09-22)"의 "CTA는 ink
계열을 쓴다" 불릿을 대체한다. 기존 텍스트 링크·pane resize affordance의
accent 유지 결정은 그대로 유효하다.

## Composer 중단(취소) 버튼도 signature color 사용 (2026-09-23, 활성)

**배경**: 바로 위 "accent를 signature color로 확장" 결정은 중단(취소) 버튼을
"1차 CTA가 아닌 상태 전환 액션"으로 보고 ink 계열 예외로 남겼다. 이후 제품
요구로 전송·중단 두 Composer 액션의 시각적 일관성이 signature color 구분보다
우선한다고 판단했다.

**결정**: Composer의 `ComposerPrimitive.Cancel`(중단) 버튼도 전송 버튼과 같은
`bg-accent text-accent-ink hover:bg-accent-hover` 채움을 쓴다. 아이콘(SquareIcon)
전환만으로 전송/중단 상태를 구분하고 배경색은 구분에 쓰지 않는다.

**영향**: 이 버튼 hover에만 쓰이던 `--ink-strong` 토큰(및 Tailwind `ink-strong`
색 매핑)은 다른 사용처가 없어 함께 제거했다. 필요해지면 다시 추가한다.

**대체 관계**: "accent를 signature color로 확장(2026-09-23)"의 "Composer의
중단(취소) 버튼처럼 1차 CTA가 아닌 상태 전환 액션은 계속 ink 계열을 쓴다"
문장을 대체한다.


## present_table 사용 시 Markdown 표 숨김 (2026-09-26, 활성)

성공한 `present_table`과 모델이 작성한 Markdown 표가 같은 답변에 함께 보이면
같은 결과를 두 번 읽게 된다. 유효한 인자의 성공 호출이 있는 assistant 답변에서는
모든 GFM Markdown 표를 숨기고 결과 표 Tool을 표시한다. 다른 내용의 Markdown 표도
별도 예외 없이 같은 정책을 적용한다.

숨김은 파싱된 table 노드에만 적용한다. 설명·결론·근거와 코드 블록은 유지하고,
원문 데이터와 복사 내용은 변경하지 않는다. Tool이 성공하기 전이나 실패한 경우에는
Markdown 표를 유지한다. 차트의 데이터 표 대안과 지식 관리 표에는 적용하지 않는다.

과거 legacy 결과 모드 제거 시 없앴던 텍스트 변환 방식의 표 제거를 다시 도입하지 않고,
현재 flat `present_table` 성공 결과와 메시지별 renderer 정책으로 처리한다.

## Frontend 폐쇄망 반입 점검 이력

## 2026-09-22 반입 항목: 결과 Tool UI

- `zod@4.6.5`를 결과 Tool 인자 검증용 직접 의존성으로 고정한다.
- `@assistant-ui/react-generative-ui`는 flat `present_*` Tool 전환 후 제거했다.
- 사내 registry에는 현재 `package-lock.json`의 정확한 버전과 전이 의존성만 반입한다.
  `npm view <package>@<version> dependencies peerDependencies`와 `dist` URL grep 절차를 따른다.

## 2026-09-16 Elements 반입

공식 registry의 Thread, ThreadList, ToolCall, AgentPlan, TooltipIconButton을
준비 환경에서 검토해 `src/components/assistant-ui/elements`에 조정 소스로
포함했다. 출처·수정 범위는 같은 폴더의 `README.md`, MIT 고지는 상위
`LICENSE`에 있다. 기존 MarkdownText도 이 디렉터리로 이동했다.
package.json과 lockfile은 변경하지 않았고 신규 npm 의존성은 없다.
`components.json`의 registry URL은 개발 시 소스 생성용이며 앱이 호출하지 않는다.


### 공식 CLI 설치 후속

사용자 요청으로 tw-shimmer 0.4.13과 zustand 5.0.15를 직접 의존성에 고정했다.
신규 tarball은 tw-shimmer 하나이며 zustand는 이미 잠긴 전이 의존성과 동일하다.
두 패키지에 설치 스크립트·런타임 외부 fetch는 없고 tw-shimmer는 로컬 CSS다.
사내 registry 확보 여부는 이 환경에서 확인할 수 없으므로 반입 시 위 준비 절차에
따라 정확한 버전을 미러링해야 한다. 기존 package 버전은 변경하지 않았다.

## 2026-09-16 TanStack Table·Recharts 점검

대화형 표는 `@tanstack/react-table` 9.2.4, 차트는 `recharts` 3.8.0을 사용한다.
두 직접 의존성은 `package.json`과 lockfile에 정확한 버전으로 고정했다. TanStack
Table의 잠긴 전이 의존성은 `@tanstack/table-core` 9.2.4,
`@tanstack/react-store` 0.11.1, `@tanstack/store` 0.11.1이다.

두 프로젝트는 MIT 라이선스다. 사내 업무, 상업적 사용, 수정과 재배포가 가능하며,
복사본 또는 중요한 부분에 저작권 및 허가 고지를 보존해야 한다. 무보증 조건도
함께 적용된다. 앱은 두 라이브러리를 번들에 포함하며 CDN이나 외부 runtime API를
호출하지 않는다. 배포물에 포함되는 전문은
`public/table-chart-license-notices.txt`에서 관리한다. 회사의 별도 오픈소스 승인
절차가 있으면 이 기술·라이선스 점검과 별도로 따른다.

현재 개발 환경의 npm registry는 공개 npm을 가리키므로 사내 Nexus에 패키지가
있는지는 여기서 확인하지 못했다. Nexus에 접근할 수 있는 준비 환경에서 실제 주소를
환경 변수로만 주입한 뒤 정확한 버전을 조회한다.

```bash
cd frontend
export INTERNAL_NPM_REGISTRY='<NEXUS_NPM_REGISTRY>'

npm view @tanstack/react-table@9.2.4 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/table-core@9.2.4 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/react-store@0.11.1 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/store@0.11.1 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view recharts@3.8.0 version license dependencies optionalDependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
```

각 명령이 요청한 버전을 출력하면 직접 패키지는 조회 가능한 상태다. Nexus의 group
repository가 외부 proxy를 허용하는 환경이라면 조회 성공만으로 사전 반입 완료를
뜻하지 않을 수 있다. Nexus UI에서 artifact가 hosted 또는 cache에 실제 저장됐는지
함께 확인한다.

모든 전이 의존성과 OS별 optional package까지 확인하려면 깨끗한 checkout에서 빈
cache로 lockfile 설치를 실행한다. 이 검증이 성공해야 폐쇄망 설치 가능 판정을 내린다.

```bash
cd frontend
NPM_AUDIT_CACHE="$(mktemp -d)"
npm ci --registry="$INTERNAL_NPM_REGISTRY" --cache="$NPM_AUDIT_CACHE" --prefer-online
npm ls @tanstack/react-table @tanstack/table-core @tanstack/react-store \
  @tanstack/store recharts
npm run build
rm -rf "$NPM_AUDIT_CACHE"
```

인증 token과 실제 Nexus URL은 `.npmrc`, shell history, 빌드 로그와 저장소에 남기지
않는다. `npm ci`가 404로 실패하면 오류에 나온 정확한 package와 버전을 Nexus에
미러링한 뒤 빈 cache 검증을 다시 수행한다.
