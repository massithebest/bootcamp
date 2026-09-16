# 중첩 Tool Reasoning UI 계획

**상태: 완료 · 2026-09-16**

## 문제

공개 실행 상태와 Tool 결과가 서로 다른 영역에 렌더링되고, Tool 사이의 설명
텍스트까지 답변 본문에 남아 최종 답변이 여러 덩어리처럼 보인다. 현재
`AgentEvent`에는 Tool 호출 ID와 입력 인자가 없어 같은 Tool을 여러 번 실행하면
상태와 결과를 정확히 연결할 수도 없다.

## 공유 계약

- `AgentEvent`에 선택 필드 `tool_call_id`를 추가한다.
- 업무 Tool의 `tool_call` 이벤트는 `data.args`에 모델이 호출한 공개 입력
  파라미터를 담는다. 내부 scope, SDK reasoning과 built-in Tool은 계속 숨긴다.
- 같은 호출의 `tool_call`, `status`, `tool_result`는 동일한 `tool_call_id`를 쓴다.
- 기존 이벤트 종류와 `tool_result.data` 결과 payload는 유지한다.

## UI 동작

- assistant-ui `ToolGroup`으로 한 턴의 Tool을 최종 답변 위에 한 그룹으로 모은다.
- Tool과 독립적인 공개 `status` 이벤트는 같은 실행 과정 안의 `AgentPlan`으로
  표시하고, Tool-linked status는 개별 Tool 행과 중복 표시하지 않는다.
- ToolGroup의 Tool 실행 단계는 그룹 `part.status`를 따른다. 메시지 상태는
  실행 아이콘과 실행 과정 전체의 자동 펼침, 최종 상태의 자동 접힘에 사용한다.
- 실행 아이콘은 요청 분석부터 Tool 실행과 최종 답변 작성까지 회전하며, Tool
  단계는 `part.status`, 전체 실행 여부는 메시지 상태로 구분한다. Tool이 끝난
  뒤에는 `응답 작성 중`, 최종 상태에는 완료 아이콘과 `응답 작성 완료`를 표시한다.
- 실행 중에는 그룹을 열고, 최종 응답 완료 시 그룹과 개별 Tool을 모두 접는다.
- 그룹을 한 번 펼치면 Tool 목록만 보인다. Tool 행을 추가로 펼치면 Parameters와
  Result 상세가 보인다.
- Tool 사이의 중간 설명은 최종 답변 본문에서 제외하고 마지막 Tool 이후의 텍스트만
  최종 답변으로 렌더링한다. Tool이 없는 답변은 기존처럼 전체 텍스트를 렌더링한다.

## 완료 조건

- 동일 Tool의 반복 호출도 호출 ID로 별도 표시된다.
- 완료 직후 ToolGroup과 모든 Tool 상세가 닫힌다.
- 두 단계 disclosure와 최종 답변 단일 본문이 데스크톱·좁은 화면에서 검증된다.
- Backend 전체 테스트와 Frontend test/build/lint가 통과한다.

## 완료 기록

- Backend `AgentEvent.tool_call_id`와 공개 `data.args` 계약을 실제 adapter와 fake
  runner에 적용했다.
- Frontend는 호출 시점에 Tool part를 만들고 ID로 결과를 갱신하며, 마지막 Tool
  이후 text만 최종 답변으로 렌더링한다.
- assistant-ui GroupedParts/ToolGroup/ToolCall로 두 단계 disclosure와 완료 후 자동
  접힘을 구현했다.
- 독립 공개 status와 Tool을 한 실행 과정에 통합하고, Tool 완료 뒤 최종 텍스트가
  스트리밍되는 구간에는 `part.status`에 따라 Tool 활성 표시만 종료한다.
- Backend 220개 테스트, Frontend 35개 테스트·build·lint를 통과했다. lint에는
  registry 혼합 export의 기존 Fast Refresh 경고 13개만 남는다.
- agent-browser 회귀 harness에서 초기 진행 표시, 독립 공개 status, Tool
  실행/완료 전환, 최종 자동 접힘, Tool 목록과 Parameters/Result 상세를 자동
  검증했다. 기존 데스크톱·400px 가로 넘침 검증도 유지한다.
