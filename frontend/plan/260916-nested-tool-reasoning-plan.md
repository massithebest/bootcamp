# 중첩 Tool Reasoning UI 실행 계획

**상위 계획:** `../../plan/260916-nested-tool-reasoning-plan.md`

**상태:** 완료

- [x] SSE·상태·runtime 타입에 `tool_call_id`와 args를 연결한다.
- [x] Tool part를 결과 도착 전부터 만들고 호출 ID로 결과를 갱신한다.
- [x] Tool part를 최종 텍스트 앞에 모아 assistant-ui ToolGroup으로 렌더링한다.
- [x] ToolGroup → Tool → Parameters/Result의 두 단계 disclosure를 구현한다.
- [x] 완료 전환 시 전체와 개별 disclosure를 닫는다.
- [x] test/build/lint와 agent-browser 화면 검증을 실행한다.

검증: 35 tests passed, production build passed, lint 0 errors(기존 registry
Fast Refresh 경고 13개), agent-browser 데스크톱·400px 화면과 실제 SSE 완료 전환,
실행 과정 DOM 회귀 harness 통과.

## 후속 조정

- [x] 첫 공개 Tool 이벤트를 기다리는 동안 빈 화면이 보이지 않도록 실행 중인 빈
  assistant 메시지에 `요청 분석 중` indicator를 즉시 표시한다.
- [x] 첨부·모델·추론 강도 준비 중 제어는 비활성 상태를 유지하면서 금지 커서 대신
  기본 커서를 사용한다.
- [x] ToolGroup의 Tool 실행 단계는 그룹 `part.status`를 사용하고, 메시지 상태는
  실행 아이콘과 실행 과정 전체의 자동 펼침·완료 후 접힘에 사용한다.
- [x] Tool 단계는 `part.status`로 구분하되 회전 아이콘은 메시지 실행이 끝날
  때까지 유지하고, Tool 완료 뒤에는 `응답 작성 중`, 최종 상태에는 완료
  아이콘과 `응답 작성 완료`를 표시한다.
- [x] Tool과 독립적인 공개 `status`를 같은 실행 과정 안의 `AgentPlan`에 표시한다.
  Tool-linked status는 개별 Tool 행과 중복 표시하지 않는다.
- [x] 초기 표시, 공개 status, Tool 실행/완료, 최종 자동 접힘, 두 단계 상세 펼침을
  실제 AssistantMessage DOM으로 검증하는 브라우저 회귀 케이스를 추가한다.

## 2026-09-17 disclosure 레이아웃 안정화

- [x] 완료된 실행 과정의 높이·blur·slide·stagger 애니메이션과 animation 기반
  scroll lock을 제거해 최종 답변 영역이 여러 프레임에 걸쳐 이동하지 않게 한다.
- [x] trigger의 `aria-expanded`, 키보드 조작과 chevron 상태 표시는 유지한다.
- [x] 실제 브라우저에서 펼침 후 첫 프레임부터 320ms까지 위치가 고정되고
  content `animation-name`이 `none`임을 확인한다.
