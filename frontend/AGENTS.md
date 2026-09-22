# Frontend 작업 지침

Vite 7, React 18, strict TypeScript 기반의 데스크톱 SPA다. 작업 전
`plan/Todo.md`, `docs/decisions.md`와 대상 폴더의 더 가까운 `AGENTS.md`를 확인한다.

## 구조와 계약

- `src/App.tsx`가 앱과 `AssistantRuntimeProvider`를 조립한다. 공용 primitive는
  `components/ui`, assistant-ui 반입 소스는 `components/assistant-ui/elements`,
  기능 UI는 `components/chat`·`components/knowledge`, 통신·adapter는 `lib`에 둔다.
- `useRemoteThreadListRuntime` + thread별 `useLocalRuntime(ChatModelAdapter)` 구성을
  유지한다. 브라우저는 `lib/chat-api.ts`에서 Backend SSE를 직접 읽으며 외부 LLM
  provider를 호출하지 않는다.
- thread와 메시지는 현재 메모리 adapter에만 저장된다. 영속성을 암시하지 않으며,
  영속 API가 생기면 adapter 경계에서 교체한다.
- `AgentEvent`, `tool_call_id`, `done.data.turn_id`, 포크와 결과 payload는 Backend
  계약과 동기화한다. 준비되지 않은 값이나 기능을 UI에서 추측하지 않는다.
- 결과는 flat `present_sql_preview`·`present_chart`·`present_table`·
  `present_simulation` Tool을 이름별 renderer로 표시한다. wire의 snake_case
  schema, Zod parser와 fixture를 함께 갱신한다. 재귀 `$type` UI tree와
  `@assistant-ui/react-generative-ui`는 사용하지 않는다.

## assistant-ui와 UI

- assistant-ui 변경 전 관련 Skill, 공식 문서와 설치된 타입 선언을 함께 확인한다.
  현재 주요 버전은 `@assistant-ui/react` 0.15.19와
  `@assistant-ui/react-markdown` 0.14.15다.
- 시각·상호작용 기준은 `docs/assistant-ui-design.md`, 제품별 결정과 예외는
  `docs/decisions.md`, 현재 계약과 검증 이력은 `plan/Todo.md`를 따른다.
- `globals.css`의 semantic token과 기존 컴포넌트를 우선 사용한다. 외부 font·CDN·
  remote asset, dark theme, 근거 없는 새 UI 라이브러리를 추가하지 않는다.
- 모델 thinking은 표시하지 않는다. 공개 `status`는 업무 진행 단계로만 표현한다.
- Frontend는 모바일을 지원하지 않는다. UI는 1280px 이상 데스크톱에서 확인하고
  모바일 viewport·device emulation·터치 시뮬레이션을 테스트에 추가하지 않는다.

## 작업과 검증

- 기존 변경을 보존하고 작은 작업은 `plan/Todo.md`, 큰 작업만
  `plan/<yymmdd>-<topic>-plan.md`에 기록한다.
- 폐쇄망 반입 원칙과 패키지 검증은 `docs/closed-network.md`를 따른다.
- 기본 검증: `npm test && npm run build && npm run lint`.
- UI 변경은 loading·empty·error, keyboard·focus·label, 표·차트 fallback을
  데스크톱 브라우저에서 확인한다. 자동화 산출물은 `.playwright-mcp/` 또는
  `artifacts/`에 두고 커밋하지 않는다.
