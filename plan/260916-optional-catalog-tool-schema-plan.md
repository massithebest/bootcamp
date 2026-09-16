# 카탈로그 Tool 선택 인자 스키마 수정

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 문제

`list_tables` 업무 함수는 `keyword`와 `tag` 생략을 허용하지만 Claude Agent SDK
등록에는 dict 스키마를 사용했다. SDK 0.2.152는 dict의 모든 키를 JSON Schema
`required`로 변환하므로 `list_tables({"keyword":"WIP"})`가 함수 실행 전에 실패했고,
모델이 `tag:""`를 추가해 재시도했다. 같은 방식의 `list_kpis`, `list_recipes`에도
동일한 잠재 오류가 있었다.

## 완료 내용

- 세 카탈로그 목록 Tool의 선택 필터를 `NotRequired` TypedDict로 선언했다.
- MCP `tools/list`가 세 Tool에 빈 `required`를 광고하는지 검증한다.
- MCP `tools/call`로 `list_tables`에 keyword만 전달해 성공하는 회귀 테스트를 추가했다.
- 전체 Backend 테스트 235건이 통과했다(5건 deselected).

## 계약

업무 Tool 함수와 반환 payload, `AgentEvent`, Frontend 계약은 변경하지 않는다.
이 수정은 모델에 노출되는 MCP 입력 스키마를 기존의 실제 선택 인자 의미와 일치시킨다.
