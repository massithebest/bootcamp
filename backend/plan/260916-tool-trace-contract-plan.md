# Tool trace 공유 계약 실행 계획

**상위 계획:** `../../plan/260916-nested-tool-reasoning-plan.md`

**상태:** 완료

- [x] `AgentEvent.tool_call_id` 선택 필드를 추가한다.
- [x] 실제 SDK adapter에서 업무 Tool 호출 ID와 공개 입력을 전달한다.
- [x] Fake Runner도 같은 호출 ID·입력 계약을 사용한다.
- [x] adapter/API 회귀 테스트와 전체 Backend 테스트를 실행한다.

검증: `python -m pytest -q` — 220 passed, 5 deselected.
