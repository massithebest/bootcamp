# assistant-ui Tool UI 기반 차트 표시

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 목표와 범위

`prepare_visualization`의 검증된 Tool 결과를 assistant-ui Tool UI로 렌더링해,
Agent가 최종 답변에 별도 `chart` 마커를 작성하지 않아도 차트가 표시되게 한다.
기존 Result Store, 시각화 검증·저장, 조회 API와 Recharts는 그대로 사용한다.

## 공유 계약과 결정

- `prepare_visualization` 성공 payload의 `visualization_id`를 유일한 차트 참조로
  사용하며 데이터·축 명세를 Tool UI에 직접 전달하지 않는다.
- `AgentEvent`, Tool payload와 `/api/visualizations/{id}` 계약은 변경하지 않는다.
- 새 응답은 `chart` 마커를 생성하지 않는다. 기존 마커 파서와 renderer는 과거
  메시지 호환을 위해 유지한다.
- Tool UI는 `display: "standalone"`으로 실행 과정 disclosure 밖에 표시하고,
  최종 설명 다음에 배치한다.
- Generative UI, AI SDK transport, 프론트 실행 Tool과 새 npm 의존성은 도입하지
  않는다.

## 파트별 할당

1. [Frontend 실행 계획](../frontend/plan/260916-assistant-ui-tool-ui-plan.md):
   렌더링 전용 toolkit 등록, 차트 조회 UI 공통화, standalone 그룹·순서 및 상태 처리.
2. [Backend 실행 계획](../backend/plan/260916-assistant-ui-tool-ui-plan.md):
   Agent·Skill·Fake Runner의 신규 마커 생성을 중단하고 계약 회귀를 갱신한다.

## 완료 조건

- 성공한 `prepare_visualization` Tool 결과가 검증된 시각화 API를 통해 차트로 표시된다.
- 준비 중, 업무 오류, 런타임 오류와 중단 상태가 안전한 사용자 메시지로 표시된다.
- SQL·검색·시뮬레이션 Tool은 기존 접힌 실행 과정에 남는다.
- 새 응답은 마커를 쓰지 않고 기존 마커만 계속 렌더링된다.
- Backend pytest와 Frontend test/build/lint가 통과하고 관련 계획·결정이 일치한다.

## 완료 결과

- 렌더링 전용 toolkit과 standalone `prepare_visualization` UI를 연결했다.
- 최종 설명 다음에 검증된 차트를 표시하고 같은 결과의 보정된 실패는 숨긴다.
- 새 마커 생성을 중단하고 기존 marker renderer와 중복 방지를 유지했다.
- Frontend 39개 테스트·build·lint, Backend 220개 테스트와 실제 브라우저의
  LLM→SQL→시각화 관통 흐름을 통과했다. 브라우저 최종 상태는 차트 1개, 경고 0개,
  marker 코드 0개이며 오류 overlay와 page error가 없었다.
