# TanStack Table·메시지 순서 — Frontend

**상태: 완료. 상위 계획: [TanStack Table·메시지 순서 계획](../../plan/260916-tanstack-table-message-order-plan.md).**

## Task

- [x] `@tanstack/react-table` 정확한 버전을 package/lockfile에 추가한다.
- [x] 대화형 표를 TanStack의 필터·정렬·페이지 row model로 전환한다.
- [x] standalone 표·차트를 답변 하단으로 모으지 않고 원래 text/tool 순서로 렌더링한다.
- [x] MIT 라이선스와 Nexus/폐쇄망 확인 절차를 문서화한다.
- [x] unit test, build, lint와 실제 브라우저 동작을 검증한다.

## 검증 기록

- `npm test`: 45 passed
- `npm run build`: 성공, 라이선스 고지 asset 포함
- `npm run lint`: 오류 없음, 기존 Fast Refresh 경고 13건
- 브라우저: 검색, 숫자 정렬 asc/desc/none, 페이지당 100 선택, TanStack 표와
  Recharts SVG, 표·차트 전후 설명 순서를 확인

## 완료 조건

- 최대 100행 payload와 현재 디자인·키보드 접근성·한국어 숫자 정렬을 유지한다.
- 일반 Tool 실행 과정 그룹과 실패 보정 숨김 규칙은 유지한다.


## 통합 검토 후속 (2026-09-16)

- 후속 일반 Tool 때문에 앞선 standalone 결과와 설명이 사라지던 문제를 수정했다.
  표·차트가 포함된 구간과 마지막 답변을 보존한다.
- 중복 표 제거 시 fenced code를 보존하고, 같은 결과 표의 페이지 크기 레이블은
  useId로 구분한다. 결과 전에 종료한 일반 Tool은 미완료로 표시한다.
- 전체 Frontend 테스트 49개, build/lint 및 Chromium 11개 lifecycle과 실제 화면
  검증 결과는 [통합 검토](../../plan/260916-uncommitted-review-plan.md)에 기록했다.
