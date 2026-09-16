# 표·차트 문맥 배치 — Backend

**상태: 완료. 상위 계획: [TanStack Table·메시지 순서 계획](../../plan/260916-tanstack-table-message-order-plan.md).**

## Task

- [x] Agent 공통 지침과 SQL·시뮬레이션 Skill에 `도입 → Tool UI → 해석` 순서를 명시한다.
- [x] Fake Runner가 표와 차트 각각의 전후 설명을 독립 text part로 전달하게 한다.
- [x] 지침 일관성과 공개 이벤트 순서를 테스트한다.

## 검증 기록

- `python -m pytest -q`: 234 passed, 5 deselected
- Fake SSE에서 표 이전 text, 표와 차트 사이 text, 차트 이후 text 순서를 검증

## 완료 조건

- 표·차트 payload 계약과 Result Store 접근 범위는 변경하지 않는다.
- 모델 내부 추론이 아니라 사용자에게 공개할 짧은 설명만 Tool UI 앞뒤에 둔다.

## 후속 보완 (2026-09-16)

- `prepare_table` Tool 설명의 “답변 아래” 표현이 Tool 호출 뒤 모델 응답에도 반복될
  수 있어 제거했다.
- 공통 지침과 SQL·시뮬레이션 Skill, 표·차트 Tool 설명에 후속 해석은 화면 위치가
  아닌 대상 자체를 지칭하도록 명시하고 prompt consistency 테스트로 고정했다.
