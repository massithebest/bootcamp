---
name: simulation
description: 생산계획 Agent 전용. 시뮬레이션(실적 조회, MP 조회, SWAP 결과 등)을 선택·실행·해석할 때 사용.
---

# 시뮬레이션 절차

1. **종류 확인**: `list_simulation` 으로 종류와 `when_to_use`, `params`, `output_schema` 를 본다. 질의의 표현이 `aliases` 에 있는지로 종류를 고른다.
2. **선행 조건**: `follows` 에 적힌 시뮬레이션이 있으면 먼저 실행한다.
3. **파라미터 구성**: `params` 의 `required: true` 는 전부 채운다. 형식은 `description` 과 `example` 을 따른다(예: 월은 yyyyMM). 모르는 값은 사용자에게 묻고, 선택 파라미터는 생략한다.
4. **실행**: `run_simulation(simulation_type, params)`. `status` 가 error 면 메시지대로 파라미터를 고쳐 1회 재시도.
5. **해석**: `output_schema` 의 필드 설명에 따라 읽는다. 다른 Tool 결과와 비교할 때는 집계 단위(월/일, 라인/품목)를 맞춘 뒤 비교한다.
6. **인용**: 어떤 시뮬레이션의 어떤 필드인지 밝힌다.

## 규칙

- 시뮬레이션 결과와 SQL 결과가 어긋나면 어느 쪽이 맞는지 단정하지 말고 둘 다 제시한다.
- 시뮬레이션은 조회 수단이다. 결과를 근거로 원인을 단정하려면 `kpi-shortfall-analysis` 절차의 가설 검증 안에서 쓴다.
