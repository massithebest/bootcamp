---
name: simulation
description: 생산계획 Agent 전용. 등록된 시뮬레이션 또는 SMT2020 입력 검증 mock을 선택·실행·해석할 때 사용.
---

# 시뮬레이션 절차

1. **종류 확인**: `list_simulation` 으로 종류와 `when_to_use`, `params`, `output_schema` 를 본다. 질의의 표현이 `aliases` 에 있는지로 종류를 고른다.
2. **선행 조건**: `follows` 에 적힌 시뮬레이션이 있으면 먼저 실행한다.
3. **파라미터 구성**: `params` 의 `required: true` 는 전부 채운다. 형식은 `description` 과 `example` 을 따른다(예: 월은 yyyyMM). 모르는 값은 사용자에게 묻고, 선택 파라미터는 생략한다.
4. **실행**: `run_simulation(simulation_type, params)`. `status` 가 error 면 메시지대로 파라미터를 고쳐 1회 재시도.
5. **해석**: `output_schema` 의 필드 설명에 따라 읽는다. 다른 Tool 결과와 비교할 때는 집계 단위(월/일, 라인/품목)를 맞춘 뒤 비교한다.
6. **표현 준비**: 사용자가 표를 요청했거나 표형 결과에서 2행 이상을 나열하려면 실제 `columns`를 확인하고 반드시 `prepare_table(result_id, columns?, title?)`을 호출한다. 비교·추이가 유용하거나 사용자가 차트를 요청하면 실제 `columns`와 grain을 확인하고 `prepare_visualization(result_id, kind, x, y, group_by?)`을 호출한다. 오류는 지원 파라미터 변경 또는 명세 수정으로 최대 2회 보정한다.
7. **인용**: 표와 차트는 각각 사용자에게 공개할 짧은 `도입 설명 → Tool UI → 결과 해석` 순서로 배치한다. 둘을 함께 제공하면 표 한 묶음 다음에 차트 한 묶음을 둔다. 도입과 해석에는 해당 결과의 범위·핵심 수치·주의점만 쓰고 내부 추론은 쓰지 않는다. 표 준비가 성공하면 Tool UI가 최대 100행을 검색·정렬·페이지 이동 가능한 표로 표시한다. Result Store 데이터를 Markdown 표로 작성하지 않는다. 시각화 등록이 성공하면 Tool UI가 반환된 `visualization_id`를 자동으로 표시한다. 최종 답변에 ID나 `chart` 코드 펜스를 반복하지 않는다. 빈 결과·보정 실패·지원하지 않는 표현은 텍스트로 설명한다. 어떤 시뮬레이션의 어떤 필드인지 밝힌다.

## 규칙

- 시뮬레이션 결과와 SQL 결과가 어긋나면 어느 쪽이 맞는지 단정하지 말고 둘 다 제시한다.
- 시뮬레이션은 조회 수단이다. 결과를 근거로 원인을 단정하려면 `kpi-shortfall-analysis` 절차의 가설 검증 안에서 쓴다.
- `SMT2020_입력검증`은 입력 table count와 JOIN 관계만 확인한다. 이 결과에서 실제
  완료량, throughput, 병목, 가동률 또는 납기 달성 여부를 추론하지 않는다.
