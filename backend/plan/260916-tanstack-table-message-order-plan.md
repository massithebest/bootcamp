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
