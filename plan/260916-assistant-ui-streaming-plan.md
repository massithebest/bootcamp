# assistant-ui 홈페이지형 Composer와 공개 실행 스트리밍

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 목표

assistant-ui 홈페이지의 중앙 Composer·suggestion 배치를 현재 3-pane에 맞게
적용하고, Backend의 공개 실행 상태와 답변 delta를 assistant-ui Reasoning 및
Message UI로 자연스럽게 스트리밍한다.

## 계약과 경계

- 공개 `AgentEvent` 6종과 FastAPI SSE 형식은 바꾸지 않는다.
- Claude Agent SDK의 partial `text_delta`만 기존 `text` 이벤트로 변환한다.
  최종 `AssistantMessage`의 누적 본문은 중복 전송하지 않는다.
- `thinking_delta`와 `ThinkingBlock`은 계속 폐기한다. UI의 Reasoning은 모델의
  비공개 chain-of-thought가 아니라 `status` 이벤트로 받은 공개 업무 단계다.
- 질문 모음 popover와 키 안내 문구는 제거한다. 시작 화면의 기존 예시 질문은
  홈페이지처럼 Composer 아래의 간결한 suggestion pill로 유지한다.
- 신규 npm/Python 의존성, 외부 asset·런타임 API는 추가하지 않는다.

## 할당과 완료 조건

1. [Backend 실행 계획](../backend/plan/260916-assistant-ui-streaming-plan.md):
   SDK partial text 활성화, 중복 방지, thinking 차단 회귀.
2. [Frontend 실행 계획](../frontend/plan/260916-assistant-ui-streaming-plan.md):
   Composer·empty layout, 단일 focus 테두리, Reasoning UI와 답변 delta 표시.
3. Backend pytest, Frontend test/build/lint, lifecycle 및 실제 브라우저에서
   desktop·400px·focus·status/text/tool 순서·중단·스크롤을 검증한다.

## 완료 결과

- 질문 모음과 키 안내를 제거하고 시작 화면을 제목 → Composer → suggestion
  pill 순으로 재구성했다. 대화 중 Composer 하단 고정은 유지한다.
- Composer textarea의 내부 focus outline을 제거해 외곽 focus 테두리 하나만
  표시한다. 전역 접근성 focus 규칙은 그대로다.
- 공개 status를 assistant-ui Reasoning disclosure로 교체했다. 실행 중 자동
  펼침·shimmer·단계 추가, 완료 후 접힘, 오류·취소 상태를 검증했다.
- 실 SDK 경로에서 partial text delta를 기존 text 이벤트로 즉시 전달하며 같은
  UUID의 최종 TextBlock 중복을 차단한다. thinking delta는 계속 폐기한다.
- Backend 전체 219 passed, 5 deselected. Frontend 30 tests, build, lifecycle
  10개와 Chromium UI 회귀를 통과했다. lint 오류 0, 기존 경고 13개다.
- desktop·400px, focus, 답변 delta 누적·cursor, tool/chart, 중단·재시도,
  사용자 scroll 보존, 외부 요청·page error 0을 확인했다.
- 서버를 재시작하고 frontend 3000/backend 8000의 HTTP 200을 확인했다.
