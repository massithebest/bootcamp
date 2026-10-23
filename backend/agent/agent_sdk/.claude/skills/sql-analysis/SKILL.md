---
name: sql-analysis
description: 생산계획 Agent 전용. 실적·계획·재고 등 데이터를 SQL 로 조회할 때 사용. 집계 가이드·카탈로그 확인 → SQL 작성 → 실행 → 검증 절차.
---

# SQL 조회 절차

## 적용할 질의

- 사용자가 "DB/데이터베이스/SQL에서 조회해 줘"라고 명시하거나 저장된 계획·실적·제품 행과 수치를 묻는 요청에 적용한다. "알려줘/보여줘" 같은 표현은 경로 판단 기준이 아니다.
- "차월 계획제품", "잔여 계획수량이 남지 않은 제품"처럼 조건이 분명한 조회는 SQL 경로다. 기준 날짜·월이 생략되면 직전 대화나 카탈로그 규칙에서 확인하고, 근거가 없으면 임의 날짜를 적용하지 않는다.
- "DB에 저장된 simulation 결과를 조회"하는 요청은 저장값 조회이므로 SQL로 처리한다. 새 simulation 실행 요청은 이 절차 대신 `simulation` Skill로 보낸다.
- 직전 조회나 simulation 결과를 가리키는 후속 질문이면 원래 결과의 출처를 유지한다. 직전 SQL `result_id`가 있으면 해당 결과의 summary/page를 사용하고, 결과를 특정할 수 없을 때만 되묻는다.

1. **테이블 찾기**: 어떤 테이블인지 모르면 `list_tables(keyword=...)`. KPI 조회면 `get_kpi` 의 `sources`, `aggregation_rules`, `recipe_refs`, `sql_template` 를 확인한다.
2. **집계 레시피 확인**: KPI 의 `recipe_refs` 가 있으면 `get_recipe` 로 조회한다. 그 외 집계·비교·추이 요청도 `list_recipes(keyword=...)` 로 적용 가능한 가이드를 찾는다. `when_to_use`, `output_grain`, `output_columns`, `query_rules`, `aggregation_rules` 를 읽고 요청한 기간·차원·비교 대상에 맞는지 확인한다. 맞으면 `cte_sql` 을 `WITH` 절로 조합한다. 레시피에 없는 차원을 이미 집계된 결과에서 복원하려 하지 않는다.
3. **스키마 확인**: 쓰려는 테이블마다 `describe_table`. `grain`(원본 한 행의 의미), `columns` 의 코드값(`codes`), `joins`, `caveats`, `query_rules`, `aggregation_rules` 를 읽는다. 사용자가 다른 조건을 지정하지 않았다면 `query_rules`의 기본 날짜·필터 조건을 SQL에 반영한다. 필수 필터(명시된 WHERE 조건 규칙)를 반영한다. "~를 필수로 포함한다"는 컬럼 규칙은 그 컬럼을 결과에 넣으라는 뜻이므로 `IS NOT NULL` 같은 제외 필터로 바꾸지 않고, 질문이나 규칙에 없는 필터를 덧붙이지 않는다. 반대로 "~는 명시적으로 요청했을 때만 포함한다"는 기본 제외 조건이므로, 요청이 없으면 해당 코드값 행을 WHERE 필터로 반드시 제외한다(NULL 코드값 행은 남긴다). 조인 키 유일성·집계 단위·수량 단위 호환성을 확인한다. KPI·카탈로그·레시피가 충돌하면 임의로 선택하지 말고 확인이 필요한 기준을 밝힌다.
4. **SQL 작성**: SELECT 만. 먼저 최종 결과 한 행의 의미를 정하고 필요한 필터·집계·비율 계산을 DB 에서 끝낸다. 조인으로 수량이 반복되지 않게 원천의 키 유일성을 확인하거나 공통 키로 사전 집계한다. 비율은 가이드에 따라 분자·분모에서 재계산한다. 시간은 `time_column` 의 형식에 맞게 비교하고 월별 그룹에는 연도를 포함한다. 원본을 LIMIT 으로 자른 뒤 합산하지 않는다. 집계 결과는 정렬한다.
5. **실행**: `execute_sql(sql, purpose)`. `purpose` 에는 이 쿼리로 확인하려는 것을 한 줄로.
6. **검증**: `status` 가 error 면 메시지를 읽고 SQL 을 고쳐 재시도(최대 2회). `row_count` 가 0 이면 조건이 맞는지 `describe_table` 의 예시와 비교한다. 조건이 맞는데도 사용자가 지정한 기간·대상에 데이터가 없으면, 다른 기간·대상으로 바꿔 집계하지 말고 조회 가능한 범위만 확인해 알린 뒤 어느 기준으로 볼지 묻고 멈춘다. 선택지는 데이터가 있음을 확인한 범위 안에서만 제시한다. 결과는 전체 행이 아니라 `result_id`와 preview(`sample_rows` 최대 5행, `statistics`, `top_groups` 등)다. 값을 확인해야 하면 `get_result_summary` 로 성격을 파악하고, 필요한 구간만 `get_result_page` 로 본다. 최종 그룹별 중복·NULL·비교 대상 누락을 확인하고 요약 평균을 KPI 값으로 대신 쓰지 않는다. 반환 행이 제한될 수 있으므로 전체 기간·차원을 포함한다고 단정하지 않는다.
7. **표현 준비**: 보여 줄 결과가 있으면 실제 `columns`(name·dtype·role)와 결과 grain을 확인하고 관련 `present_*` Tool을 scalar 인자로 직접 호출한다. 행·차트 data 배열은 어떤 Tool에도 넣지 않는다. 실행한 SQL은 `present_sql_preview(sql, title?)`, 사용자가 표를 요청했거나 2행 이상을 나열하려면 `present_table(result_id, columns?, title?)`, 비교·추이가 유용하거나 사용자가 차트를 요청하면 `present_chart(result_id, chart_type, x_column, y_column, group_by_column?, aggregation?)`를 호출한다. 여러 지표를 한 차트로 비교하려면 SQL을 처음부터 `지표 이름, 값` long 형식으로 만든다(예: `SELECT <차원>, '<지표 A>' AS metric, SUM(<값 A>) AS qty ... GROUP BY <차원> UNION ALL SELECT <차원>, '<지표 B>', SUM(<값 B>) ... GROUP BY <차원>`). 지표별 합계는 각자 집계 규칙대로 따로 계산하고, 차트는 `group_by_column`=metric으로 한 번만 호출한다. 단위가 다른 지표(예: 건수와 수량)는 한 결과·한 차트에 섞지 말고 지표별 SQL·차트로 나눈다. 숫자 컬럼이 없거나 차트 명세를 확정할 수 없으면 `present_chart` 없이 표와 설명만 쓴다. 오류는 `code`와 `details.path`를 읽고 인자를 수정해 최대 2회 보정한다. `visualization_hints`는 사용자 의도와 함께 권장 표현으로만 참고한다.
8. **표현·인용**: 결과 UI는 사용자에게 공개할 짧은 `도입 설명 → present_* 호출 → 결과 해석` 순서로 배치한다. 도입과 해석에는 해당 결과의 범위·핵심 수치·주의점만 쓰고 내부 추론은 쓰지 않는다. 호출 뒤의 해석에서는 `위·아래·다음 표/차트`처럼 화면 위치를 가리키지 말고 `표에는…`, `차트에서는…`처럼 대상 자체를 지칭한다. 성공한 결과 UI를 Markdown 표나 `chart` 코드 펜스로 다시 쓰지 않고 `result_id`도 최종 답변에 반복하지 않는다. 빈 결과·보정 실패·지원하지 않는 표현은 텍스트로 설명하고 차트를 약속하지 않는다. 표와 차트의 수치는 동일한 `result_id`의 집계 결과를 기준으로 한다. 작업 구간 표현에는 실제 시작·종료 데이터가 필요하다. 답변에는 쿼리(purpose), 집계 단위, 필터·비교 범위를 밝히고 `verified: false` 인 지식은 미검증 정의 기준임을 알린다.

## 규칙

- 카탈로그에 없는 테이블·컬럼을 추측하지 않는다.
- 한 번에 하나의 목적만 가진 쿼리를 쓴다. 복잡하면 여러 번 나눠 조회한다.
- 데이터 변경 SQL 은 작성하지 않는다.
- catalog에 세그먼트 구분 키(예: dataset)가 있는 테이블은 먼저 그 값을 확정한다.
  JOIN에는 업무 키뿐 아니라 양쪽의 구분 키 동등 조건도 반드시 넣어 같은 ID의
  교차 결합을 막는다.
