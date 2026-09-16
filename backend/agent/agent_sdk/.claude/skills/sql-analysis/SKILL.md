---
name: sql-analysis
description: 생산계획 Agent 전용. 실적·계획·재고 등 데이터를 SQL 로 조회할 때 사용. 집계 가이드·카탈로그 확인 → SQL 작성 → 실행 → 검증 절차.
---

# SQL 조회 절차

1. **테이블 찾기**: 어떤 테이블인지 모르면 `list_tables(keyword=...)`. KPI 조회면 `get_kpi` 의 `sources`, `aggregation_rules`, `recipe_refs`, `sql_template` 를 확인한다.
2. **집계 레시피 확인**: KPI 의 `recipe_refs` 가 있으면 `get_recipe` 로 조회한다. 그 외 집계·비교·추이 요청도 `list_recipes(keyword=...)` 로 적용 가능한 가이드를 찾는다. `when_to_use`, `output_grain`, `output_columns`, `aggregation_rules` 를 읽고 요청한 기간·차원·비교 대상에 맞는지 확인한다. 맞으면 `cte_sql` 을 `WITH` 절로 조합한다. 레시피에 없는 차원을 이미 집계된 결과에서 복원하려 하지 않는다.
3. **스키마 확인**: 쓰려는 테이블마다 `describe_table`. `grain`(원본 한 행의 의미), `columns` 의 코드값(`codes`), `joins`, `caveats`, `aggregation_rules` 를 읽는다. 필수 필터를 반영하고 조인 키 유일성·집계 단위·수량 단위 호환성을 확인한다. KPI·카탈로그·레시피가 충돌하면 임의로 선택하지 말고 확인이 필요한 기준을 밝힌다.
4. **SQL 작성**: SELECT 만. 먼저 최종 결과 한 행의 의미를 정하고 필요한 필터·집계·비율 계산을 DB 에서 끝낸다. 조인으로 수량이 반복되지 않게 원천의 키 유일성을 확인하거나 공통 키로 사전 집계한다. 비율은 가이드에 따라 분자·분모에서 재계산한다. 시간은 `time_column` 의 형식에 맞게 비교하고 월별 그룹에는 연도를 포함한다. 원본을 LIMIT 으로 자른 뒤 합산하지 않는다. 집계 결과는 정렬한다.
5. **실행**: `execute_sql(sql, purpose)`. `purpose` 에는 이 쿼리로 확인하려는 것을 한 줄로.
6. **검증**: `status` 가 error 면 메시지를 읽고 SQL 을 고쳐 재시도(최대 2회). `row_count` 가 0 이면 조건이 맞는지 `describe_table` 의 예시와 비교한다. 결과가 `large_result` 면 `get_result_summary` 로 성격을 파악하고, 필요한 구간만 `get_result_page` 로 본다. 최종 그룹별 중복·NULL·비교 대상 누락을 확인하고 요약 평균을 KPI 값으로 대신 쓰지 않는다. 반환 행이 제한될 수 있으므로 전체 기간·차원을 포함한다고 단정하지 않는다.
7. **표현 준비**: 사용자가 표를 요청했거나 결과에서 2행 이상을 나열하려면 실제 `columns`를 확인하고 반드시 `prepare_table(result_id, columns?, title?)`을 호출한다. `get_result_page`로 일부를 확인했더라도 원래 `result_id`를 사용한다. 비교·추이가 유용하거나 사용자가 차트를 요청하면 실제 `columns`와 결과 grain을 확인하고 `prepare_visualization(result_id, kind, x, y, group_by?)`을 호출한다. 오류는 명세 수정 또는 새 집계 결과로 최대 2회 보정한다. `visualization_hints`는 사용자 의도와 함께 권장 표현으로만 참고한다.
8. **표현·인용**: 표와 차트는 각각 사용자에게 공개할 짧은 `도입 설명 → Tool UI → 결과 해석` 순서로 배치한다. 둘을 함께 제공하면 표 한 묶음 다음에 차트 한 묶음을 둔다. 도입과 해석에는 해당 결과의 범위·핵심 수치·주의점만 쓰고 내부 추론은 쓰지 않는다. 표 준비가 성공하면 Tool UI가 최대 100행을 검색·정렬·페이지 이동 가능한 표로 표시한다. Result Store 데이터를 Markdown 표로 작성하지 않는다. 시각화 등록이 성공하면 Tool UI가 반환된 `visualization_id`를 자동으로 표시한다. 최종 답변에 ID나 `chart` 코드 펜스를 반복하지 않는다. 빈 결과·보정 실패·지원하지 않는 표현은 텍스트로 설명하고 차트를 약속하지 않는다. 표와 차트의 수치는 동일한 `result_id`의 집계 결과를 기준으로 한다. 작업 구간 표현에는 실제 시작·종료 데이터가 필요하다. 답변에는 쿼리(purpose), 집계 단위, 필터·비교 범위를 밝히고 `verified: false` 인 지식은 미검증 정의 기준임을 알린다.

## 규칙

- 카탈로그에 없는 테이블·컬럼을 추측하지 않는다.
- 한 번에 하나의 목적만 가진 쿼리를 쓴다. 복잡하면 여러 번 나눠 조회한다.
- 데이터 변경 SQL 은 작성하지 않는다.
- SMT2020 테이블은 먼저 HVLM/LVHM dataset을 확정한다. JOIN에는 업무 키뿐 아니라
  양쪽의 dataset 동등 조건도 반드시 넣어 같은 ID의 교차 결합을 막는다.
