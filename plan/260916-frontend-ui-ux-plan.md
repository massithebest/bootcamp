# Frontend UI/UX 개선 (frontend-design Skill) 계획

- 상태: 완료
- 작성일: 2026-09-16
- 상위 기준: [프로젝트 요구사항 및 Todo](Todo.md)
- 실행 계획: [frontend/plan/260916-frontend-ui-ux-plan.md](../frontend/plan/260916-frontend-ui-ux-plan.md)

## 목표

3-pane Agent Workspace(Sidebar/Chat/Inspector)의 UI/UX를 실제 업무 흐름
기준으로 개선한다 — 사용자가 생산계획 데이터를 질문하고, Agent 실행 진행
상황을 이해하고, SQL·시뮬레이션 결과와 최종 답변을 검토하는 흐름 전체가
대상이다. 색상 등 표면적 변경이 아니라 정보 위계·progressive disclosure·
오해를 유발하는 미연결 affordance를 대상으로 한다.

## 범위

- Chat Workspace(메시지 가독성, 진행 상태 표현, Tool 결과 progressive
  disclosure), Composer, 3-pane 공간 배분/collapse, Sidebar, Context
  Inspector의 실제 코드 개선.
- `frontend/CLAUDE.md`에 최종 구현과 일치하는 디자인 가이드 추가.
- Claude Code `frontend-design` Skill을 실제로 호출해 반영.

## 비범위

- Backend 변경, `AgentEvent`/Result Store/시각화 계약 변경.
- Sidebar 영속 thread, Prompt 저장 API 등 실제 연결 계약이 없는 기능의 신규
  구현(대신 미연결 상태를 정직하게 표현하는 것까지만 다룬다).
- 모바일 최적화(비범위 유지, 단 ~400px 가로 스크롤 방지는 확인).
- 좁은 화면 전용 Sheet/overlay 레이아웃 전환(§6 후속 참고, 이번 범위 제외).
- `backend/agent/agent_sdk/CLAUDE.md` 수정.

## 공유 계약 유지 여부

변경 없음. `AgentEvent`(text/status/tool_call/tool_result/error/done),
`done.data.turn_id`/`fork_from_turn_id`, `pp_session_scope`, Result Store,
`visualization_id` 차트 marker, `useExternalStoreRuntime` 기반 상태 소유권을
모두 그대로 유지했다. 새 패키지도 추가하지 않았다.

## 파트별 할당

전량 프론트엔드 단독 작업. Backend 파트 없음(공유 계약 미변경이므로
`backend/plan` 항목 없음).

## 완료 조건

- [x] 실제 코드 기준 UI/UX 문제를 P0/P1/P2로 분류하고 근거를 남긴다.
- [x] `frontend-design` Skill을 호출하고 적용 판단을 기록한다.
- [x] P0(오해 유발 affordance)와 핵심 P1(진행 상태 위계, 표 높이, 리사이즈
      충돌)을 실제로 구현한다.
- [x] `frontend/CLAUDE.md`에 최종 구현과 일치하는 디자인 가이드를 추가한다.
- [x] `npm test`, `npm run build`, `npm run lint`이 기준선 대비 회귀 없이
      통과한다.
- [x] `plan/Todo.md`의 관련 항목 상태를 갱신한다.

실행 세부(대상 파일, 검증 결과, 브라우저 확인, 보류 항목)는
[frontend/plan/260916-frontend-ui-ux-plan.md](../frontend/plan/260916-frontend-ui-ux-plan.md)
참고.
