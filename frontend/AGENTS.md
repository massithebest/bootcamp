# Frontend 작업 지침

Vite 7, React 18, strict TypeScript 기반의 라우터 없는 SPA다. 코드 변경 전
상위 `../AGENTS.md`, [프론트 결정 기록](docs/decisions.md)과 관련 상위 계획을
확인한다.

## 구조와 상태 소유권

- `src/App.tsx`가 앱과 루트 `AssistantRuntimeProvider`를 조립한다. shadcn
  primitive는 `components/ui`, assistant-ui Elements 복사·조정 소스는
  `components/assistant-ui/elements`, 기능 UI는 `components/chat`, 동작과
  상태는 `hooks`, 통신·adapter는 `lib`, 계약은 `types`에 둔다.
- assistant-ui는 thread, composer, viewport, action bar와 Markdown UI를 맡는다.
  애플리케이션 메시지와 SSE·retry·cancel·edit·regenerate 상태는
  `hooks/use-agent-chat.ts`가 소유하고 `useExternalStoreRuntime`으로 노출한다.
- `@ai-sdk/react`, `useChat`, `streamdown`, AI SDK streaming protocol을 도입하지
  않는다. 브라우저 통신은 `lib/chat-api.ts`의 `fetch`/`ReadableStream` SSE를
  유지하고 외부 LLM provider를 직접 호출하지 않는다.
- assistant-ui 구조를 바꿀 때는 해당 공식 Skill과 문서를 확인하고 설치된
  패키지의 타입 선언으로 호환성을 검증한다.

## assistant-ui 적용 범위

- 현재 설치 기준은 `@assistant-ui/react` 0.15.19와
  `@assistant-ui/react-markdown` 0.14.15다. 변경 전 공식 문서와 설치된 타입 선언을
  함께 확인한다. 문서: <https://www.assistant-ui.com/llms-full.txt>
- 앱 루트의 `AssistantRuntimeProvider`, 전체 화면 `Thread`,
  `useExternalStoreRuntime` 조합을 유지한다. `useChatRuntime`과 AI SDK transport로
  전환하려면 별도 상위 계획과 Backend streaming 계약 변경이 필요하다.
- floating `AssistantModal`은 현재 제품 구조가 아니며 3-pane에 중복 채팅 UI를
  추가하지 않는다.
- 공통 UI는 공식 Elements를 우선 사용하고 도메인 기능은 슬롯으로 확장한다.
  standalone `ThreadList`는 예시 세션 UI이며 영속 저장 기능을 의미하지 않는다.
- MCP·Skill·registry는 개발 참고 도구다. 실행 앱에 원격 MCP·Cloud·CDN 연결을
  추가하지 않는다. 반입 소스와 변경 이유는 [전환 결정](docs/decisions.md)에 남긴다.

## UI와 공유 계약

- Tailwind v4와 `globals.css`의 semantic CSS 변수를 사용한다. 컴포넌트 색상
  하드코딩과 dark theme를 추가하지 않는다. shadcn 변수는 기존 프로젝트
  토큰에 매핑한다.
- `--chart-1`부터 `--chart-5`는 차트 시리즈에만 사용한다.
- 현재 sidebar 셸은 `app-sidebar.tsx`, 목록은 assistant-ui standalone ThreadList다.
  shadcn Sidebar provider와 섞으려면 먼저 결정 기록을 추가한다.
- 원본 어시스턴트 이벤트는 도착 순서의 `MessagePart[]`로 저장한다. 화면 변환 시
  일반 Tool은 실행 과정 그룹 앞으로 모으고, standalone 표·차트가 포함된 문맥과
  마지막 답변 구간은 원래 순서를 보존한다. 중간 준비 문구를 숨기는 과정에서
  앞선 표·차트와 해석을 버리지 않는다. 일반 Tool 직전의 공개 `text`는 해당
  Tool이 실행 중인 동안만 `progressText`로 유지하고, ToolGroup 상단이 아닌
  현재 Tool 행 바로 위에 표시한다. 결과·다음 공개 출력·종료에서 제거한다.
  SDK thinking은 이 경로에 넣지 않는다.
  `AgentEvent`, `done.data.turn_id`, `fork_from_turn_id`와 tool result kind는
  백엔드 계약과 동기화한다.
- `prepare_visualization`의 standalone Tool UI는 성공 결과의 `visualization_id`만
  읽고 `/api/visualizations/{id}` 응답을 검증한 뒤 bar/line으로 렌더링한다.
  기존 `chart` fence는 과거 메시지 호환용이며 새 응답에는 생성하지 않는다.
- `prepare_table`의 standalone Tool UI는 Backend가 Result Store에서 검증해 보낸
  최대 100행만 읽는다. 표 안의 검색·정렬·페이지 이동은 이 범위에서 수행하며
  원본 행 배열을 Tool 입력이나 Markdown 표로 반복하지 않는다.
- 성공한 `prepare_table`이 텍스트 뒤에 도착해도 설명을 유지하고, 같은 응답의
  중복 GFM 표 블록만 제거한다. fenced code 안의 표 예시는 제거하지 않는다.
- 구조화 지식 상세는 `query_rules`를 조회 규칙, `aggregation_rules`를 집계 규칙,
  `visualization_hints`를 시각화 안내로 표시한다. table/recipe의
  `sample_queries`는 질문과 SQL만 렌더링하며 존재하지 않는 답변 값을 만들지 않는다.
- 세 pane의 스크롤 체인에 필요한 `min-h-0`, `overflow-hidden`, `shrink-0`을
  유지한다.

## 폐쇄망과 통신

- 패키지, 폰트, CDN, remote asset을 추가하기 전에
  [폐쇄망 운영 원칙](docs/closed-network.md)을 따른다.
- 패키지는 정확한 버전과 전이 의존성이 사내 Nexus에 있는지 확인하고
  registry CLI가 필요한 소스는 외부에서 생성해 저장소에 포함한다.
- backend 접근은 `lib`의 API 모듈에만 두고 transport 오류를 사용자에게 안전한
  상태로 변환한다. live SSE 응답은 캐시하지 않는다.
- Playwright·브라우저 자동화 산출물은 루트 `.playwright-mcp/` 또는 `artifacts/`에
  두고 Git에 포함하지 않는다.

## 명령과 검증

`frontend/`에서 실행한다.

```bash
npm ci
cp .env.example .env.local
npm run dev
npm test
npm run build
npm run lint
npm run preview
```

- `npm run build`가 type check를 포함한다. `npm test`는 Node 내장 실행기로
  SSE·상태 전이·결과 렌더 회귀를 검증한다. 브라우저 lifecycle 검증은
  개발 서버의 `/tests/chat-browser.html`, `/tests/knowledge-browser.html`,
  `/tests/workbench-browser.html`을 목적에 맞게 사용한다. formatter는 아직 없다.
- UI 변경은 loading·empty·error, 키보드·focus·label, tool card와 chart/table
  fallback, 좁은 화면부터 desktop까지 수동 확인한다.
