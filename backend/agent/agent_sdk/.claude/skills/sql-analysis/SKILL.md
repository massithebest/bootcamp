---
name: sql-analysis
description: 생산계획 Agent 전용. 실적·계획·재고 등 데이터를 SQL 로 조회할 때 사용. 카탈로그 확인 → SQL 작성 → 실행 → 검증 절차.
---

# SQL 조회 절차

1. **테이블 찾기**: 어떤 테이블인지 모르면 `list_tables(keyword=...)`. KPI 조회면 `get_kpi` 의 `sources` 와 `sql_template` 를 출발점으로 쓴다.
2. **재사용 패턴 확인**: 여러 테이블을 조인·집계하는 쿼리라면 새로 쓰기 전에 `list_recipes(keyword=...)` 로 같은 목적의 재사용 가능한 CTE 가 있는지 확인한다. 있으면 `get_recipe` 의 `cte_sql` 을 `WITH` 절로 그대로 조합해 쓴다.
3. **스키마 확인**: 쓰려는 테이블마다 `describe_table`. `columns` 의 코드값(`codes`), `joins`, `caveats` 를 읽는다. caveats 의 필터 조건(예: 취소 제외)은 반드시 WHERE 에 반영한다.
4. **SQL 작성**: SELECT 만. 조인은 `joins` 에 적힌 키를 쓴다. 날짜는 `time_column` 을 쓰고 ISO 문자열(YYYY-MM-DD)로 비교한다. 집계 결과는 정렬한다.
5. **실행**: `execute_sql(sql, purpose)`. `purpose` 에는 이 쿼리로 확인하려는 것을 한 줄로.
6. **검증**: `status` 가 error 면 메시지를 읽고 SQL 을 고쳐 재시도(최대 2회). `row_count` 가 0 이면 조건이 맞는지 `describe_table` 의 예시와 비교한다. `truncated` 가 true 면 집계 수준을 올리거나 조건을 좁힌다.
7. **인용**: 답변에 수치를 쓸 때 어떤 쿼리(purpose)의 결과인지 밝힌다.

## 규칙

- 카탈로그에 없는 테이블·컬럼을 추측하지 않는다.
- 한 번에 하나의 목적만 가진 쿼리를 쓴다. 복잡하면 여러 번 나눠 조회한다.
- 데이터 변경 SQL 은 작성하지 않는다.
