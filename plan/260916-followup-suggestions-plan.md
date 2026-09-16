# 후속질문 동적 생성

**상태: 진행 예정. 마지막 갱신: 2026-09-16.**

## 목표와 범위

에이전트가 매 턴 응답을 마친 뒤, 그 턴에서 실제로 확인한 내용에 근거해 2~4개의
후속질문을 동적으로 생성하고 클릭 가능한 제안 칩으로 보여준다. 별도 백엔드
후처리 LLM 호출 없이 에이전트(Claude) 자신이 응답 생성과 함께 만든다. 도메인
지식(KPI/recipe)에 후속질문 힌트가 있으면 이번 턴 맥락에 맞을 때만 참고한다.

비범위: 메시지별 개별 suggestions(assistant-ui는 thread 전체에 하나의 목록만
지원), 새 `AgentEventType` 도입, Result Store·시각화·표 Tool 계약 변경, 기존
KPI/recipe YAML 전체에 힌트 채우기(메커니즘 증명용 예시 1건만 포함), pie·간트
차트·모바일·인증 등 프로젝트 전역 비범위 항목.

## 배경

`ThreadFollowupSuggestions`(assistant-ui 공식 Elements 컴포넌트)가 프론트엔드에
이미 구현돼 있었으나 어디에도 마운트되지 않은 죽은 코드였다. `knowledge/scenarios/*.yaml`은
이미 QA 회귀 테스트 픽스처로 쓰이고 있어 "질문 시나리오"라는 이름으로 재사용하지
않는다.

## 공유 계약과 결정

- **`done` 이벤트 확장**: 성공한 턴의 마지막 `AgentEvent(type="done")`의
  `data`에 `follow_up_questions: list[str]`를 추가한다(기존 `turn_id`와 함께).
  실패로 조기 종료되는 `done`(현재 `data=None`)에는 추가하지 않는다. 프론트엔드는
  `follow_up_questions`가 없거나 빈 배열이면 "이번 턴에 제안 없음"으로 처리한다.
  스키마 변경은 없다 — `AgentEvent.data: dict[str, Any] | None`가 이미 허용.
- **마커 포맷(백엔드 프롬프트 계약)**: 에이전트는 최종 답변 본문 뒤에 아래
  형식을 그대로 덧붙인다. 화면에는 노출되지 않고 백엔드가 파싱해 제거한다.

  ```
  <!--FOLLOWUP_QUESTIONS
  - 후속 질문 1
  - 후속 질문 2
  -->
  ```

  HTML 주석 구분자를 쓰는 이유: 파싱이 실패해도 CommonMark 렌더러가 `<!-- -->`
  내용을 렌더링하지 않으므로 최악의 경우에도 원문이 화면에 노출되지 않는다.
  이 문자열(`<!--FOLLOWUP_QUESTIONS`, `-->`)은 `backend/agent/agent.py`의 상수와
  `backend/agent/agent_sdk/CLAUDE.md`의 프롬프트 문구가 공유하는 계약이며, 어느
  한쪽만 바뀌면 안 된다 — `test_prompt_consistency.py`가 두 값의 일치를 강제한다.
- **스트리밍 분리**: `event_adapter.py`는 변경하지 않는다. `agent.py::run_agent`의
  기존 스트리밍 루프 안에서 tail-buffer 방식으로 마커를 분리해, 마커 시작이
  확정되기 전까지는 기존과 동일하게 실시간으로 `text` 이벤트를 스트리밍하고,
  마커 이후 텍스트는 별도로 모아 `done` 생성 시점에만 파싱한다. 닫히지 않은
  마커(모델이 형식을 못 지킨 경우)는 조용히 버려 원문이 노출되지 않게 한다.
- **도메인 지식 힌트**: `KnowledgeKpi`, `KnowledgeRecipe`에
  `follow_up_hints: list[str] = []`를 추가한다(`visualization_hints`,
  `diagnostics`와 동일한 선택적 리스트 패턴). `get_kpi`/`get_recipe` Tool 결과에
  자동으로 포함되며 별도 Tool·API 변경은 없다.
- **프론트엔드 suggestions 배선**: assistant-ui의 `suggestions`는 thread
  전체에 하나뿐인 스코프다. `App.tsx`의 `AuiConfig({ suggestions: ... })`(정적
  예시질문)는 runtime-level suggestions를 항상 가리므로 제거하고, 빈 대화에는
  정적 예시질문을, 첫 응답 이후에는 최신 완료된 assistant 메시지의
  `followUpQuestions`를 `useExternalStoreRuntime({ suggestions })`로 공급한다.
  기존 `ThreadFollowupSuggestions` 컴포넌트를 `thread.aui.tsx`의
  `ViewportFooter`(Composer 위)에 마운트한다.
- mock(`fake_runner.py`)과 real 경로의 `done` 결과 형태를 동일하게 유지한다
  (repo 공통 원칙).

## 파트별 할당

1. [Backend 실행 계획](../backend/plan/260916-followup-suggestions-plan.md):
   마커 tail-buffer 파싱, `done` 확장, `follow_up_hints` 스키마, CLAUDE.md 지침,
   Fake Runner, 테스트.
2. [Frontend 실행 계획](../frontend/plan/260916-followup-suggestions-plan.md):
   `ChatMessage`/`chat-state.ts` 확장, `suggestions` 파생·배선, `AuiConfig` 정리,
   `ThreadFollowupSuggestions` 마운트, 테스트.

## 완료 조건

- 성공한 턴의 `done.data.follow_up_questions`에 에이전트가 그 턴 내용에 근거해
  만든 2~4개(또는 0~1개, 강제 최소치 없음) 질문이 담긴다.
- 마커 텍스트가 스트리밍 중이든 최종 렌더링이든 어떤 경우에도 사용자에게 노출되지
  않는다(파싱 실패 시에도).
- `follow_up_hints`가 있는 KPI/recipe를 참조한 턴에서, 맥락에 맞을 때만 힌트가
  후속질문에 반영된다(무조건 복사하지 않음).
- 빈 대화에는 정적 예시질문이, 첫 응답 이후에는 동적 후속질문 chip row가
  Composer 위에 표시되고 클릭 시 그대로 전송된다.
- Backend pytest와 Frontend test/build/lint가 통과하고 계획·Todo 문서가 현재
  구현과 일치한다.
