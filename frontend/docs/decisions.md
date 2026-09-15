# Frontend 기술 결정 기록

이 문서는 지속적으로 유효한 결정과 대체된 결정의 이유만 보존한다. 구현 Task와
검증 이력은 `frontend/plan`에 둔다.

## 결정 요약

| 날짜 | 결정 | 상태 |
| --- | --- | --- |
| 2026-09-08 | 3-pane 워크벤치 | 활성 |
| 2026-09-11 | Tailwind v4와 shadcn/ui | 활성 |
| 2026-09-14 | AI Elements를 복사 소스로 제한해 사용 | 활성 |
| 2026-09-14 | Next.js에서 Vite SPA로 이전 | 활성 |
| 2026-09-14 | assistant-ui를 UI plumbing 계층으로 도입 | 활성 |
| 2026-09-15 | 차트를 최종 답변의 `visualization_id` marker로 전환 | 활성 |

## 3-pane 워크벤치

사이드바, 대화, context inspector를 한 화면에 둔다. 대화와 Skills는 실제 API,
세션 목록·사용자·Metadata·Prompt는 아직 로컬 데이터다. 실제 연결되지 않은
패널을 영속 기능으로 설명하지 않는다.

현재 왼쪽 sidebar는 `components/chat/app-sidebar.tsx`의 커스텀 구현이다.
설치된 shadcn Sidebar는 사용하지 않는다. 교체할 때는 provider, mobile sheet와
기존 토큰·layout 충돌을 먼저 검토한다.

## Tailwind v4와 shadcn/ui

UI primitive는 shadcn 소스를 저장소에 복사해 관리한다. registry CLI는 인터넷이
되는 준비 환경에서 실행하고 생성 파일을 함께 반입한다. 컴포넌트는 프로젝트의
semantic CSS token을 사용하며 shadcn 기본 팔레트를 독립적으로 유지하지 않는다.

초기 스캐폴드의 “custom Tailwind 컴포넌트만 사용” 결정은 이 결정으로 대체됐다.

## AI Elements

`chain-of-thought`, `tool`, `task` 컴포넌트 소스만 사용한다. 복사된 코드는 프로젝트
코드와 같은 기준으로 수정한다. `ai`, `@ai-sdk/react`, `useChat`, `streamdown`과
AI SDK streaming protocol은 사용하지 않는다. 이유는 Backend SSE 계약과 맞지 않고
불필요한 의존성·외부 endpoint 가능성을 늘리기 때문이다.

## Next.js에서 Vite로 이전

Frontend는 router 없는 Vite SPA다. `src/app` 이름은 CSS와 asset 경로 호환을 위해
남은 디렉터리일 뿐 Next.js App Router가 아니다. Browser가 FastAPI를 직접 호출하고
dev·preview 포트는 CORS 계약과 맞춘 3000으로 고정한다.

## assistant-ui

assistant-ui는 thread, viewport, composer, message, action bar와 Markdown rendering을
담당한다. 애플리케이션 메시지 상태와 SSE transport는
`hooks/use-agent-chat.ts`가 소유하고 `useExternalStoreRuntime`으로 연결한다.

- 어시스턴트 메시지는 text와 tool의 도착 순서를 보존하는 `MessagePart[]`다.
- status/progress는 메시지 metadata에 연결한다.
- edit와 regenerate는 Backend의 `turn_id`/`fork_from_turn_id` 계약을 사용한다.
- Runtime이나 transport를 바꾸려면 공유 계약을 포함한 새 상위 계획이 필요하다.
- External Store adapter는 실제로 지원하는 capability만 노출한다. 선형 대화만
  유지하는 동안 `setMessages`(branch switch/delete)는 제거했다.
- 메시지 종료 상태는 공식 `MessageStatus`(`complete`/`incomplete(cancelled,error)`)로
  정규화하고 오류 표시는 `MessagePrimitive.Error`를 사용한다.
- Tool UI toolkit/`GroupedParts`와 thread-list adapter는 Backend에 stable
  `tool_call_id`와 세션 persistence 계약이 생기기 전까지 보류한다.

감사 결과와 후속 작업은
[assistant-ui 감사 계획](../plan/260915-assistant-ui-audit-plan.md)에 둔다.

## 차트 v2 marker

도구 카드의 v1 자동 차트는 폐기했다. 최종 답변의 `chart` 코드 펜스에는
`visualization_id`만 허용하며, marker가 `/api/visualizations/{id}` 응답을 런타임
검증한 뒤 Recharts에 전달한다.

동일 ID의 진행 중 요청은 공유하고 마지막 구독자가 사라지면 취소한다. 프론트는
수치를 집계·정렬·피벗하지 않으며 Backend가 검증한 payload를 렌더링한다. 네트워크
재시도는 같은 조회만 반복하고 Agent tool을 자동으로 다시 실행하지 않는다.

공유 요구사항과 완료 조건은
[차트 시각화 계획](../../plan/260915-chart-visualization-plan.md)을 따른다.

## 폐쇄망 공통 결정

외부 font, CDN, script, telemetry와 브라우저의 외부 LLM 호출을 금지한다. 패키지
버전과 전이 의존성을 사내 registry에서 확인하고 오프라인 build를 검증한다.
세부 절차는 [폐쇄망 운영 원칙](closed-network.md)을 따른다.
