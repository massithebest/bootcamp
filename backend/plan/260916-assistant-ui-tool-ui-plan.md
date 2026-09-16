# assistant-ui Tool UI 기반 차트 표시 — Backend

**상태: 완료. 상위 계획: [Tool UI 차트 계획](../../plan/260916-assistant-ui-tool-ui-plan.md).**

Frontend는 기존 `prepare_visualization` 성공 payload의 `visualization_id`를 Tool UI로
렌더링한다. Backend API와 Tool 반환 형태는 바꾸지 않는다.

## Task

- Agent 공통 지침과 SQL·시뮬레이션 Skill에서 신규 `chart` 마커 작성을 제거한다.
- 시각화 성공 여부와 오류 보정 규칙은 유지한다.
- Fake Runner가 Tool 결과 뒤에 마커를 추가하지 않도록 갱신한다.
- prompt·API 회귀 테스트와 전체 pytest를 실행한다.

## 완료 조건

- 새 응답은 마커 없이도 `prepare_visualization` 결과를 전달한다.
- 시각화 조회 API와 Tool payload 계약은 이전과 동일하다.

## 결정·실행 기록

- 공통 Agent 지침과 SQL·시뮬레이션 Skill은 성공한 시각화를 Tool UI가 자동으로
  표시한다고 안내하며 ID·코드 펜스를 최종 답변에 반복하지 않는다.
- Fake Runner도 Tool 결과만 보내고 marker text를 생성하지 않는다.
- Tool·시각화 API 계약 변경 없이 전체 pytest 220개 통과(선택 해제 5개).
