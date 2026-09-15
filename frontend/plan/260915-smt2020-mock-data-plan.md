# SMT2020 Mock 연동 실행 계획 (프론트엔드)

**상태: 완료. 마지막 갱신: 2026-09-15.**

상위 계약은 [SMT2020 SQLite 및 Mock 전환 계획](../../plan/260915-smt2020-mock-data-plan.md)을
따른다. 백엔드 의존 작업은
[백엔드 실행 계획](../../backend/plan/260915-smt2020-mock-data-plan.md)에 정의한다.

## 착수 조건

- `backend/datasets/smt2020.db`가 상위 계획의 schema와 row count로 생성된다.
- mock `execute_sql`이 SMT2020 테이블을 조회하고 기존 database payload를 반환한다.
- `run_simulation("SMT2020_입력검증", {"dataset": "LVHM"})`이 `kpis`,
  `table`, `results`, `summary`를 반환한다.
- Fake Runner가 LVHM WIP SQL, 입력 검증과 bar visualization 이벤트를 방출한다.

## 실행 규칙

- 새 API, 패키지와 데이터셋 선택 UI를 추가하지 않는다.
- `AgentEvent`, `ToolResult`, database/simulation/visualization payload 타입은
  기존 계약을 유지한다.
- benchmark 입력 검증 결과를 실제 생산성·capacity simulation처럼 표현하지 않는다.
- 계획 밖 UI 변경이 필요하면 원인과 계약 차이를 문서 끝 실행 기록에 남긴다.

## Task 1. SMT2020 기반 정적 콘텐츠 교체

**변경 대상**: `src/lib/dummy.ts`

**요구 동작**:

- 기존 A/B라인 생산실적, KRA/MDF 자재, MP와 임의 capacity 수치를 모두 제거한다.
- 세션 제목과 예시 질문을 아래 범주로 교체한다.
  - 제품별 초기 WIP lot/piece 수
  - 특정 part의 route와 공정 step
  - Dry Etch 계열 `stngrp`/`stnfam`별 설비 수량
  - 제품별 전체 step 수
  - 납기가 빠른 order/WIP lot
  - HVLM/LVHM 입력 관계 정합성
- system prompt에는 다음을 명시한다.
  - 질문의 대상 dataset을 HVLM/LVHM 중 하나로 확정한다.
  - 테이블 JOIN에는 `dataset`을 포함한다.
  - `SMT2020_입력검증`은 입력 관계 mock이며 생산 결과 예측이 아니다.
  - 데이터에 없는 completion, throughput, 병목, 납기 달성률을 추정하지 않는다.
- metadata의 데이터 기준을 SMT2020 공개 benchmark와 simulation 시작 시점으로
  표시하고 simulation 상태는 입력 검증 mock임을 드러낸다.
- 초기 대화에는 실제 tool 이름 `execute_sql`, `run_simulation`을 사용한다.
  - database 결과: LVHM 제품별 WIP lot 수
  - simulation 결과: LVHM KPI 4개, 11개 table count, 관계 검증 results
  - 최종 텍스트: 조회 사실과 unmatched 0만 설명

**검증/완료 조건**:

- `rg 'KRA-|MDF-|FGS|MP-|자재 부족|최대 생산 가능' frontend/src/lib/dummy.ts`
  결과가 0건이다.
- 초기 대화의 tool result가 `DatabaseResult`, `SimulationResult`에서 예외 없이
  렌더된다.

## Task 2. 기존 결과 컴포넌트 계약 검증

**확인 대상**: `src/components/chat/tool-result-card.tsx`,
`tool-results/database-result.tsx`, `tool-results/simulation-result.tsx`,
`tool-results/result-summary.tsx`

**요구 동작**:

- `execute_sql` 결과는 기존 표와 실행 SQL disclosure로 표시한다.
- `run_simulation`의 `kpis`, `summary`, `results`, `table`은 기존 simulation 카드로
  표시한다. 100행을 넘는 결과가 생기면 기존 large-result 요약 경로를 사용한다.
- Fake Runner의 `prepare_visualization` 결과와 chart fence는 기존 bar chart 경로를
  사용한다.
- 실제 백엔드 payload가 기존 계약과 일치하므로 이 Task에서는 컴포넌트와 공유
  타입을 선제 변경하지 않는다. 실제 관통 검증에서 렌더 누락이 확인될 때만 최소
  수정하고 백엔드 계약 변경 없이 해결한다.

**검증/완료 조건**:

- database 표에 `part`, `lot_count`가 표시된다.
- simulation 카드에 KPI, 관계별 matched/unmatched와 table count가 표시된다.
- bar chart가 LVHM 제품별 WIP lot 수를 렌더한다.
- error payload는 내부 경로나 stack trace 없이 기존 error UI로 표시된다.

## Task 3. Fake Runner 관통 및 반응형 검증

**대상**: 실제 백엔드 Fake Runner와 프론트 dev/preview 서버

**검증 시나리오**:

1. 새 대화에서 제품별 WIP 예시 질문을 보낸다.
2. catalog, SQL, simulation, chart 순서의 status/tool card가 표시되는지 확인한다.
3. SQL 카드의 LVHM 제품별 lot 수와 simulation KPI의 WIP lot 수가 같은 DB 기준인지
   비교한다.
4. simulation 관계 검증에서 unmatched가 모두 0인지 확인한다.
5. 최종 답변이 입력 검증 결과를 실제 생산 simulation으로 과장하지 않는지 확인한다.
6. 400px 폭과 desktop에서 표는 내부 스크롤되고 세 pane 스크롤 체인이 깨지지
   않는지 확인한다.

**완료 조건**:

```bash
cd frontend
npm run lint
npm run build
```

- 두 명령과 수동 시나리오가 모두 통과한다.
- 새 패키지, AgentEvent/parser 변경과 데이터셋 선택 UI가 추가되지 않는다.

## 결정·실행 기록

- 2026-09-15: dataset 선택은 자연어→Agent 파라미터로 처리하고 별도 UI는 두지
  않기로 결정했다.
- 2026-09-15: 새 mock payload가 기존 고정 renderer 계약에 맞으므로 정적 콘텐츠
  교체와 관통 검증을 우선하고 선제적인 타입·컴포넌트 변경은 하지 않기로 결정했다.
- 2026-09-15: 더미 세션, 예시 질문, prompt, metadata와 입력 안내를 SMT2020
  기준으로 교체했다. 공유 `ToolResult`와 결과 renderer 계약은 변경하지 않았다.
- 2026-09-15: 격리된 Fake Runner 관통에서 `execute_sql`, 입력 검증 table,
  `prepare_visualization` bar 차트와 최종 답변이 모두 표시되었고, 콘솔 오류와
  error overlay는 없었다. 400px viewport에서도 페이지 수평 overflow가 없었다.
- 2026-09-15: `npm run lint && npm run build`가 성공했다. 기존 Fast Refresh 경고
  4건과 Vite 번들 크기 경고만 남았으며 오류는 없다.
