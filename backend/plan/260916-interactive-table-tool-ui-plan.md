# 대화형 표 Tool UI — Backend

**상태: 완료. 상위 계획: [대화형 표 계획](../../plan/260916-interactive-table-tool-ui-plan.md).**

Frontend는 `prepare_table` 성공 payload를 standalone Tool UI로 렌더링한다.

## Task

- [x] Result Store 결과의 scope·TTL·컬럼을 검증하고 최대 100행을 직렬화하는
  표 서비스와 Tool wrapper를 추가한다.
- [x] Claude Agent SDK Tool 목록·입력 스키마와 Agent/Skill 지침을 갱신한다.
- [x] Fake Runner에 SQL 결과 표 준비 호출을 추가한다.
- [x] 모델이 표 요청 또는 Markdown 표 응답에서 호출을 빠뜨리면 마지막 Result Store
  결과로 `prepare_table` 이벤트를 자동 보완한다.
- [x] 성공·컬럼 투영·100행 상한·만료/다른 scope/손상 오류와 Tool 등록을 테스트한다.
- [x] 전체 Backend pytest 결과를 기록한다.

## 완료 조건

- 모델은 `result_id`와 선택 컬럼·제목만 전달하고 행 데이터는 Backend가 읽는다.
- Tool payload에 내부 파일 경로가 포함되지 않으며 모든 오류는 안전하게 닫힌다.

## 결정·실행 기록

- 성공 payload는 상위 계획 계약을 그대로 따르고 새 API endpoint나 저장소를
  만들지 않았다. 표 payload는 기존 SSE Tool 결과로 전달한다.
- 다른 scope, 만료, 손상 metadata/parquet, 없는 컬럼과 중복 컬럼을 안전한
  업무 오류로 변환한다.
- Agent 지침은 Result Store 행을 Markdown 표로 작성하지 않고 2행 이상 또는 명시적
  표 요청이면 `prepare_table`을 반드시 호출하도록 강화했다.
- `python -m pytest -q`: 234개 통과, 5개 선택 해제.


## 통합 검토 후속 (2026-09-16)

- 목표·지표·대표 등의 단어를 표 요청으로 오인하지 않도록 자동 보완 조건을 좁혔다.
- 모델이 이미 표 준비에 성공하면 fallback을 다시 실행하지 않는 테스트를 추가했다.
- 폐쇄망 가이드에 mock DB 생성과 Tool 성공 payload 확인 절차를 보완했다.
- 전체 pytest 240 passed, 5 deselected. 상세는
  [통합 검토](../../plan/260916-uncommitted-review-plan.md)를 따른다.
