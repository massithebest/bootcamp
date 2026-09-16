# 카탈로그 Tool 선택 인자 스키마 수정 — Backend

**상태: 완료. 상위 계획: [카탈로그 Tool 선택 인자 스키마 수정](../../plan/260916-optional-catalog-tool-schema-plan.md).**

## Task

- [x] SDK dict 스키마가 선택 필터를 필수로 변환하는 원인을 재현한다.
- [x] `list_tables`, `list_kpis`, `list_recipes`에 선택 필드 TypedDict를 적용한다.
- [x] 실제 MCP 광고 스키마와 keyword 단독 호출을 회귀 테스트한다.
- [x] 전체 Backend 테스트를 실행한다.

검증: `python -m pytest -q` — 235 passed, 5 deselected.
