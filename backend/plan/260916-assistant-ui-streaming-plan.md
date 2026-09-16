# 답변 delta 스트리밍 Backend 실행 계획

**상태: 완료. 마지막 갱신: 2026-09-16.**

- 상위: [공통 계획](../../plan/260916-assistant-ui-streaming-plan.md)
- 상대 파트: [Frontend 계획](../../frontend/plan/260916-assistant-ui-streaming-plan.md)

## Tasks

1. `ClaudeAgentOptions.include_partial_messages`를 활성화한다.
2. `StreamEvent`의 `content_block_delta/text_delta`만 공개 `text` 이벤트로
   변환하고 같은 UUID의 최종 TextBlock은 중복 전송하지 않는다.
3. thinking/signature/tool-input delta 및 알 수 없는 이벤트를 공개하지 않는다.
4. adapter 단위 테스트와 전체 pytest로 기존 tool/session/fork 계약을 검증한다.

## 실행·검증 기록

- `_build_options`에서 `include_partial_messages=True`를 활성화했다.
- `StreamEvent`의 text delta만 AgentEvent text로 변환하고 UUID를 기록해 최종
  AssistantMessage TextBlock 중복을 막았다. tool use 등 최종 block 처리는 유지한다.
- thinking/signature/input JSON/알 수 없는 delta는 공개하지 않는다.
- 신규 adapter 회귀 2개와 options 검증을 추가했다.
- 관련 테스트 28 passed, 전체 `python -m pytest -q` 219 passed, 5 deselected.
