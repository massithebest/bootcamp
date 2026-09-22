---
name: simulation
description: 생산계획 Agent 전용. 등록된 시뮬레이션 또는 입력 검증 도구를 선택·실행·해석할 때 사용.
---

# 시뮬레이션 절차

1. **종류 확인**: `list_simulation` 으로 종류와 `when_to_use`, `params`, `output_schema`, `aggregation_rules`, `visualization_hints` 를 본다. 질의의 표현이 `aliases` 에 있는지로 종류를 고른다.
2. **선행 조건**: `follows` 에 적힌 시뮬레이션이 있으면 먼저 실행한다.
3. **파라미터 구성**: `params` 의 `required: true` 는 전부 채운다. 형식은 `description` 과 `example` 을 따른다(예: 월은 yyyyMM). 모르는 값은 사용자에게 묻고, 선택 파라미터는 생략한다.
4. **실행**: `run_simulation(simulation_type, params)`. `status` 가 error 면 메시지대로 파라미터를 고쳐 1회 재시도.
5. **해석**: `output_schema` 의 필드 설명에 따라 읽는다. `aggregation_rules` 가 있으면 합산·비교 범위를 그대로 따른다. 다른 Tool 결과와 비교할 때는 집계 단위(월/일, 라인/품목)를 맞춘 뒤 비교한다.
6. **표현 준비**: 결과는 전체 행이 아니라 `result_id`, `scenario`, `summary`, `kpis`와 preview다. 보여 줄 결과가 있으면 실제 `columns`와 grain을 확인하고(`visualization_hints` 는 권고로만 쓴다) `present(tree)`를 한 번 호출한다. `tree`에 root UI node 하나를 JSON 문자열로 직렬화해 넣는다. JSON 문자열 안의 각 node는 assistant-ui 표준 `$type`으로 종류를 지정하고 선택적 `$key`와 props를 같은 객체에 넣으며 하위 node는 `children`으로 중첩한다. `$type`·`children`을 Tool의 최상위 인자로 따로 보내거나 root를 JSON 배열로 보내지 않는다. 시나리오·요약·KPI는 `SimulationSummary`, 사용자가 표를 요청했거나 표형 결과에서 2행 이상을 나열하려면 같은 `resultId`의 `QueryTable`, 비교·추이가 유용하거나 사용자가 차트를 요청하면 `QueryChart`를 `SimulationSummary`의 자식으로 조합한다. 트리에는 `resultId`와 표시 설정만 넣고 행·차트 data 배열은 넣지 않는다. 오류는 `code`와 `details.path`를 읽고 지원 파라미터 변경 또는 명세 수정으로 최대 2회 보정한다.
7. **인용**: 결과 UI는 사용자에게 공개할 짧은 `도입 설명 → present 호출 → 결과 해석` 순서로 배치한다. 도입과 해석에는 해당 결과의 범위·핵심 수치·주의점만 쓰고 내부 추론은 쓰지 않는다. 호출 뒤의 해석에서는 `위·아래·다음 표/차트`처럼 화면 위치를 가리키지 말고 `표에는…`, `차트에서는…`처럼 대상 자체를 지칭한다. 성공한 결과 UI를 Markdown 표나 `chart` 코드 펜스로 다시 쓰지 않고 `resultId`도 최종 답변에 반복하지 않는다. 빈 결과·보정 실패·지원하지 않는 표현은 텍스트로 설명한다. 어떤 시뮬레이션의 어떤 필드인지 밝힌다.

## 규칙

- 시뮬레이션 결과와 SQL 결과가 어긋나면 어느 쪽이 맞는지 단정하지 말고 둘 다 제시한다.
- 시뮬레이션은 조회 수단이다. 결과를 근거로 원인을 단정하려면 `kpi-shortfall-analysis` 절차의 가설 검증 안에서 쓴다.
- 입력 검증 simulation은 입력 table count와 JOIN 관계만 확인한다. 이 결과에서 실제
  완료량, throughput, 병목, 가동률 또는 납기 달성 여부를 추론하지 않는다.
