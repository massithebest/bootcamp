# Frontend 작업 지침

Vite 7, React 18, strict TypeScript 기반의 라우터 없는 SPA다. 코드 변경 전
상위 `../AGENTS.md`, [프론트 결정 기록](docs/decisions.md)과 관련 상위 계획을
확인한다.

## 구조와 상태 소유권

- `src/App.tsx`가 앱을 조립한다. shadcn primitive는 `components/ui`, 복사한
  AI Elements는 `components/ai-elements`, 기능 UI는 `components/chat`, 동작과
  상태는 `hooks`, 통신·adapter는 `lib`, 계약은 `types`에 둔다.
- assistant-ui는 thread, composer, viewport, action bar와 Markdown UI를 맡는다.
  메시지·SSE·retry·cancel·edit·regenerate 상태는
  `hooks/use-agent-chat.ts`와 `useExternalStoreRuntime`이 소유한다.
- `@ai-sdk/react`, `useChat`, `streamdown`, AI SDK streaming protocol을 도입하지
  않는다. 브라우저 통신은 `lib/chat-api.ts`의 `fetch`/`ReadableStream` SSE를
  유지하고 외부 LLM provider를 직접 호출하지 않는다.
- assistant-ui 구조를 바꿀 때는 해당 공식 Skill과 문서를 확인하고 설치된
  패키지의 타입 선언으로 호환성을 검증한다.

## UI와 공유 계약

- Tailwind v4와 `globals.css`의 semantic CSS 변수를 사용한다. 컴포넌트 색상
  하드코딩과 dark theme를 추가하지 않는다. shadcn 변수는 기존 프로젝트
  토큰에 매핑한다.
- `--chart-1`부터 `--chart-5`는 차트 시리즈에만 사용한다.
- 현재 sidebar는 `app-sidebar.tsx`의 커스텀 구현이다. shadcn Sidebar provider와
  섞으려면 먼저 결정 기록을 추가한다.
- 어시스턴트 메시지는 도착 순서가 보존되는 `MessagePart[]`를 사용한다.
  `AgentEvent`, `done.data.turn_id`, `fork_from_turn_id`와 tool result kind는
  백엔드 계약과 동기화한다.
- 최종 답변의 `chart` fence는 `visualization_id`만 허용하고
  `/api/visualizations/{id}` 응답을 검증한 뒤 bar/line으로 렌더링한다.
  tool 카드에는 자동 차트를 넣지 않는다.
- 세 pane의 스크롤 체인에 필요한 `min-h-0`, `overflow-hidden`, `shrink-0`을
  유지한다.

## 폐쇄망과 통신

- 패키지, 폰트, CDN, remote asset을 추가하기 전에
  [폐쇄망 운영 원칙](docs/closed-network.md)을 따른다.
- 패키지는 정확한 버전과 전이 의존성이 사내 Nexus에 있는지 확인하고
  registry CLI가 필요한 소스는 외부에서 생성해 저장소에 포함한다.
- backend 접근은 `lib`의 API 모듈에만 두고 transport 오류를 사용자에게 안전한
  상태로 변환한다. live SSE 응답은 캐시하지 않는다.

## 명령과 검증

`frontend/`에서 실행한다.

```bash
npm install
cp .env.example .env.local
npm run dev
npm test
npm run build
npm run lint
npm run preview
```

- `npm run build`가 type check를 포함한다. `npm test`는 Node 내장 실행기로
  SSE·상태 전이·결과 렌더 회귀를 검증한다. 브라우저 lifecycle 검증은
  개발 서버의 `/tests/chat-browser.html`을 사용한다. formatter는 아직 없다.
- UI 변경은 loading·empty·error, 키보드·focus·label, tool card와 chart/table
  fallback, 좁은 화면부터 desktop까지 수동 확인한다.
