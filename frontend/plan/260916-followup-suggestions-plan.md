# 후속질문 동적 생성 — Frontend

**상태: 진행 예정. 상위 계획: [후속질문 동적 생성](../../plan/260916-followup-suggestions-plan.md).**
**Backend 의존: [Backend 실행 계획](../../backend/plan/260916-followup-suggestions-plan.md)의
`done.data.follow_up_questions` 계약이 준비된 뒤 통합 검증한다. 타입·상태 배선은
계약 형태(`list[str]`, 키 이름)가 고정되어 있으므로 Backend 구현과 병행 착수
가능.**

## Task

- [ ] `types/chat.ts`의 `ChatMessage`에 `followUpQuestions?: string[]`를
  추가한다(`turnId?: string`과 동일 패턴).
- [ ] `lib/chat-state.ts`의 `applyAgentEvent` `"done"` 케이스에서
  `event.data?.follow_up_questions`를 문자열 배열로 안전 파싱해
  `followUpQuestions`에 반영한다(값이 없으면 기존 값 유지, 순수 함수 원칙
  유지 — 별도 `useState` 도입하지 않는다).
- [ ] `hooks/use-agent-chat.ts`에 `messages`에서 파생되는 `suggestions`를
  계산하는 작은 순수 함수를 추가한다(테스트 가능하도록 export, 예:
  `deriveSuggestions(messages): {prompt: string}[]`):
  - `messages.length === 0` → `EXAMPLE_QUESTIONS.map(prompt => ({ prompt }))`.
  - 아니면 가장 최근의 `role === "assistant" && runState.type === "complete"`
    메시지의 `followUpQuestions ?? []`를 `{prompt}[]`로 매핑.
  - `useMemo`로 감싸 `useExternalStoreRuntime({ ..., suggestions })`에 전달한다.
  - `EXAMPLE_QUESTIONS` import를 `App.tsx`에서 이 파일로 옮긴다.
  - 주의: `useExternalStoreRuntime`의 `suggestions`는 `ThreadSuggestion[]`
    타입이라 `AuiConfig`의 `Suggestions()` 헬퍼와 달리 순수 문자열 배열을
    받지 않는다 — 반드시 `{prompt}` 객체로 매핑한다.
- [ ] `App.tsx`의 `AuiConfig`에서 `suggestions: Suggestions(EXAMPLE_QUESTIONS)`를
  제거한다(runtime-level suggestions를 항상 가리는 문제 해결). 이제 안 쓰는
  `Suggestions`, `EXAMPLE_QUESTIONS` import를 제거한다.
- [ ] `components/chat/empty-state.tsx`는 변경하지 않는다 — `ExampleSuggestions`는
  이미 `ThreadPrimitive.Suggestions`(runtime-level `s.thread.suggestions`)를
  읽으므로 `AuiConfig`의 가리기만 없어지면 자동으로 동적 목록을 받는다.
- [ ] `components/assistant-ui/elements/thread.aui.tsx`에서 기존
  `ThreadFollowupSuggestions`를 import해 `ViewportFooter` 안,
  `ScrollToBottom`과 `Composer` 사이에 마운트한다(내부에서 이미
  `!isEmpty && !isRunning && suggestions.length > 0` 조건을 처리하므로 추가
  조건 분기는 불필요).
- [ ] `lib/chat-runtime.ts`(`convertMessage`)는 변경하지 않는다(`suggestions`는
  thread-scope라 `ThreadMessageLike`와 무관).
- [ ] 테스트:
  - `tests/chat-state.test.mjs`: `done` 이벤트에 `follow_up_questions`가
    있을 때/없을 때 `followUpQuestions` 처리를 검증한다.
  - `deriveSuggestions`를 기존 `.mjs` 테스트 패턴(`ssrLoadModule`)으로 커버한다.
  - 수동 검증: `npm run dev` + fake runner(`PLANNING_AGENT_FAKE=1`)로 빈 대화
    정적 예시 → 첫 응답 후 동적 chip row 전환 → 스트리밍 중 마커 원문이 화면에
    잠깐도 노출되지 않는지 육안 확인. 제안 칩 클릭 시 실제 전송되는지 확인.
  - `npm run build && npm run lint` 통과.

## 완료 조건

- 빈 대화에는 정적 예시질문이, 첫 응답 완료 이후에는 최신 assistant 메시지의
  동적 후속질문이 Composer 위 chip row로 표시된다.
- 스트리밍 중 마커 텍스트가 화면에 한순간도 노출되지 않는다.
- 제안 칩 클릭 시 해당 텍스트가 그대로 사용자 메시지로 전송된다.

## 결정·실행 기록

_구현 후 기록._
