# 도메인 지식·테이블·Recipe·Scenario 관리 지침

이 문서는 생산계획 Agent가 사용하는 구조화 지식과 비정형 지식을 개발 환경과
폐쇄망에서 같은 방식으로 관리하기 위한 운영 기준이다. 단계별 제품 범위와 상태는
[상위 도메인 지식 계획](../../plan/260914-domain-knowledge-plan.md)을 따른다.

## 지식의 단일 기준

| 지식 | 저장 위치 | 용도 |
| --- | --- | --- |
| 용어 | `knowledge/glossary.yaml` | 동의어, 정의, 관련 KPI·테이블 연결 |
| 테이블·컬럼·조인 | `knowledge/catalog/` | SQL 작성과 서버의 허용 목록·검증 |
| KPI | `knowledge/kpi/` | 공식, 기준, 판정 규칙, 원인 후보 |
| query recipe/CTE | `knowledge/recipes/` | 검증된 집계 흐름과 출력 계약 |
| 시뮬레이션 | `knowledge/simulations/` | 종류, 입력, 출력과 실행 순서 |
| 검증 시나리오 | `knowledge/scenarios/` | 고정 데이터셋을 관통하는 질문·실행 단계·기대값 |
| 분석 절차 | `agent/agent_sdk/.claude/skills/` | 어떤 지식을 어떤 순서로 조회할지 |
| 매뉴얼·정책·보고서 | 폐쇄망 RAG | YAML로 구조화하기 어려운 산문과 출처 |

같은 사실을 여러 위치에 복제하지 않는다. 구조화 가능한 정의는 YAML, 분석 순서는
Skill, 긴 산문은 RAG가 기준이다. 실행 가능한 recipe/CTE는 RAG에 중복 색인하지
않고 `list_recipes`와 `get_recipe`로 제공한다.

## 공통 메타데이터

모든 지식 항목은 다음 정보를 가진다.

```yaml
status: draft        # draft | verified
owner: ""
source: ""
updated: 2026-09-15
```

- `draft`는 구조 검증만 통과했거나 업무 담당자가 확인하지 않은 상태다.
- `verified`는 실제 테이블·업무 정의·단위와 비교 기준을 담당자가 확인한 상태다.
- 테스트 통과는 `verified`의 근거가 아니다.
- source에는 문서명이나 검토 회의처럼 다시 확인 가능한 근거를 기록하고 비밀값이나
  사내 접속 주소는 넣지 않는다.

## 테이블 카탈로그 작성

테이블 정의에는 원본 한 행의 의미를 나타내는 `grain`, 시간 컬럼, 키, 컬럼 타입과
설명, 코드값, join, caveat와 `aggregation_rules`를 기록한다.

```yaml
table: wip
description: SMT2020 초기 재공 Lot
grain: [dataset, lot]
time_column: due
columns:
  - name: part
    type: varchar
    desc: Part ID
joins:
  - to: part
    on: [dataset, part]
    kind: many-to-one
aggregation_rules:
  - Lot 수는 COUNT(*), piece 수는 SUM(pieces)로 구분한다.
caveats:
  - HVLM/LVHM을 조인할 때 dataset을 반드시 포함한다.
```

작성할 때 다음을 반드시 확인한다.

- grain의 모든 컬럼이 실제로 한 행을 식별하는지
- 스냅샷, 누적값, 이벤트 중 어떤 형태인지와 시간 기준
- nullable 값과 누락 행의 업무 의미
- join cardinality와 일대다 join으로 인한 중복 합산 가능성
- 코드와 표시 이름, 버전 키, 수량 단위
- 합산 가능한 차원과 합산하면 안 되는 식별자·비율

실제 스키마가 바뀌면 catalog YAML, `scripts/build_smt2020_db.py`와 관련 정합성
테스트를 같은 변경에서 갱신한다. 생성된 `datasets/smt2020.db`를 직접 수정하지 않는다.

## KPI 작성

KPI는 표시 이름과 동의어, 업무 정의, 공식, 원천 테이블, 기본 grain, 비교 기준,
부진 판정, diagnostics, `aggregation_rules`와 `recipe_refs`를 가진다.

| 필드 | 의미 |
| --- | --- |
| `kpi_id` | 파일명과 같은 소문자 `snake_case` 식별자 |
| `name`, `aliases` | 사용자에게 표시할 이름과 자연어 검색에 사용할 동의어 |
| `definition` | 측정 대상, 기준 시점·기간과 업무 의미 |
| `formula` | 집계 함수, 분자·분모와 단위를 포함한 계산식 |
| `sources` | `sql_template`이 직접 조회하는 catalog table |
| `grain` | KPI 결과 한 행을 식별하는 차원 |
| `baseline` | 비교 기준 데이터와 기준 시점·버전 |
| `shortfall_rule` | 정상·부진·미달을 판정하는 조건 또는 판정하지 않는다는 명시 |
| `sql_template` | KPI를 재현하는 읽기 전용 SQL과 필수 placeholder |
| `aggregation_rules` | NULL, 중복 JOIN, 재집계와 단위 처리 규칙 |
| `recipe_refs` | KPI 계산에 재사용할 `recipe_id` 목록 |
| `diagnostics` | 이상 원인을 확인할 SQL·simulation 가설과 참조 대상 |

파일명은 `<kpi_id>.yaml`로 맞춘다. 새 KPI는 구조와 SQL을 테스트했더라도 현업
정의·단위·판정 기준을 검토하기 전까지 `draft`로 둔다. SMT2020에 적용된 실제
예시는 [initial_wip.yaml](../knowledge/kpi/initial_wip.yaml)을 참고한다.

다음은 필수 필드와 연결 방식을 보여주는 작성 예다. 실제 KPI를 추가할 때는
예시의 이름과 값을 복사하지 말고 대상 catalog와 업무 정의에 맞춰 작성한다.

```yaml
kpi_id: example_lot_count
name: 예제 Lot 수
aliases: [Lot 건수, 재공 건수]
definition: 선택한 dataset의 기준 시점에 존재하는 Lot을 Part별로 집계한다.
formula: lot_count = COUNT(*)
sources: [wip]
grain: [dataset, part]
baseline: wip 원본의 simulation 시작 시점 스냅샷
shortfall_rule: 현황 지표이므로 정상·부진을 판정하지 않는다
sql_template: |
  SELECT dataset, part, COUNT(*) AS lot_count
  FROM wip
  WHERE dataset = :dataset
  GROUP BY dataset, part
  ORDER BY part
aggregation_rules:
  - dataset을 먼저 확정하고 HVLM/LVHM을 섞지 않는다
  - Lot 수는 COUNT(*), piece 수는 SUM(pieces)로 구분한다
  - route_step과 조인하기 전에 dataset과 part grain으로 먼저 집계한다
recipe_refs: [initial_wip_by_part]
diagnostics:
  - hypothesis: WIP의 Part와 현재 Step이 master 및 Route에 연결된다
    how: simulation
    ref: SMT2020_입력검증
status: draft
owner: ""
source: SMT2020 WIP.txt와 KPI 정의 검토 기록
updated: 2026-09-15
```

### 정의·공식·grain

- `definition`만 읽어도 무엇을, 언제, 어떤 단위로 측정하는지 알 수 있어야 한다.
  `formula`는 같은 내용을 SQL 집계식 수준으로 좁혀 적는다.
- `grain`은 `sql_template`의 `GROUP BY` 및 출력 식별 컬럼과 일치해야 한다.
  예를 들어 `[dataset, part]` KPI에서 `dataset`을 빼면 HVLM/LVHM의 같은 Part ID가
  한 행으로 합쳐질 수 있다.
- Lot, piece, wafer, hour처럼 단위가 다른 측정값은 하나의 합계로 섞지 않는다.
  표시용 이름이 비슷해도 각각 별도 출력 alias와 단위를 사용한다.
- 비율 KPI는 행별 비율의 평균으로 다시 계산하지 않는다. 합산 가능한 분자와
  분모를 결과에 보존한 뒤 `SUM(분자) / NULLIF(SUM(분모), 0)`로 재계산한다.
- 분모 0, NULL, 누락 행, 취소 상태를 포함할지 제외할지 정의와
  `aggregation_rules` 양쪽에 모순 없이 기록한다.
- 기간 KPI의 월 집계는 월 번호만 사용하지 않고 연도·월을 함께 사용한다. 스냅샷
  KPI는 흐름이나 기간 실적으로 해석하지 않도록 기준 시점을 명시한다.

### baseline과 shortfall 판정

- `baseline`은 비교 대상의 테이블, 버전, 기간 또는 스냅샷을 다시 찾을 수 있게
  적는다. “전월”처럼 실행 시점에 따라 달라지는 표현은 기준 timezone과 범위를
  함께 정의한다.
- `shortfall_rule`에는 비교 연산자와 경계 포함 여부를 명시한다. 예를 들어
  `actual / plan < 0.9`와 `<= 0.9`는 서로 다른 규칙이다.
- 초기 WIP처럼 현황만 보여주는 KPI에는 임의의 정상 범위를 만들지 않는다.
  `판정하지 않는다`고 명시하고 Agent가 부족·양호를 추정하지 않게 한다.
- `baseline`이 없거나 같은 단위로 비교할 수 없다면 `shortfall_rule`도 적용하지
  않는다. 계산할 수 없는 판정을 0이나 정상으로 대체하지 않는다.

### SQL template과 placeholder

- `sql_template`은 한 개의 읽기 전용 `SELECT` 또는 `WITH ... SELECT`여야 하며
  `sources`에는 `FROM`/`JOIN`에서 읽는 실제 catalog table을 모두 선언한다.
- placeholder는 `:dataset`, `:from`, `:to`처럼 의미가 드러나는 이름을 쓴다.
  현재 `execute_sql`은 바인딩 값을 별도로 받지 않으므로 placeholder가 자동으로
  치환되지 않는다. Agent 또는 호출 코드는 catalog에서 허용된 값을 확인한 뒤
  실행 SQL에 안전한 리터럴로 치환해야 한다.
- 날짜 범위는 timezone과 양 끝 포함 여부를 정한다. `BETWEEN`을 쓰면 양 끝이 모두
  포함된다는 점을 `definition` 또는 `aggregation_rules`에 기록한다.
- SQL alias는 `formula`와 일치시킨다. `formula`가 `lot_count`를 정의했다면
  `sql_template`도 같은 alias를 반환해야 후속 recipe와 시각화가 안정적이다.
- 일대다 테이블을 JOIN한 뒤 원천 수량을 합산하지 않는다. 필요한 원천 grain으로
  먼저 집계하거나 검증된 recipe를 `recipe_refs`에 연결한다.

### Recipe와 diagnostics 연결

- `recipe_refs`에는 `knowledge/recipes/*.yaml`의 `recipe_id`를 경로 접두사 없이
  기록한다. Agent는 `get_kpi` 후 해당 ID를 `get_recipe`로 조회한다.
- `diagnostics[].hypothesis`는 확인하려는 원인 가설, `how`는 `sql` 또는
  `simulation`, `ref`는 실행 근거다.
- `how: simulation`의 `ref`는 `knowledge/simulations/*.yaml`의 정확한 `type`이어야
  한다.
- `how: sql`은 catalog table 이름 또는 `recipes/<recipe_id>`를 참조한다. 단순
  table 조회보다 grain·JOIN 규칙이 필요한 진단은 recipe 참조를 권장한다.
- diagnostics는 KPI 값을 다시 계산하는 목록이 아니라 값이 예상과 다를 때 확인할
  순서 있는 원인 후보다. 근거 데이터에 없는 원인을 추가하지 않는다.

### 작성 및 검증 순서

1. `list_tables`와 `describe_table`에 해당하는 catalog YAML에서 원천 grain, 타입,
   NULL과 JOIN cardinality를 확인한다.
2. 담당자와 `definition`, 단위, `baseline`, `shortfall_rule`을 먼저 합의한다.
3. 합의한 공식을 동일한 alias의 `sql_template`로 작성하고 `sources`를 선언한다.
4. raw table과 recipe 중 어떤 경로가 중복 집계를 막는지 확인한 뒤
   `recipe_refs`와 `aggregation_rules`를 작성한다.
5. diagnostics의 모든 참조가 실제 table, recipe 또는 simulation에 존재하는지
   확인한다.
6. HVLM/LVHM 각각에서 SQL을 실행해 NULL, 0건, dataset 혼합과 합계 차이를
   점검한다.
7. 기술 검증 후에도 현업 승인 전에는 `draft`, 승인 근거가 있을 때만
   `verified`로 변경한다.

KPI와 연결된 Recipe까지 확인하는 기본 검증 명령은 다음과 같다.

```bash
cd backend
python -m pytest -q \
  tests/test_knowledge.py \
  tests/test_knowledge_integrity.py \
  tests/test_aggregation_guidance.py
```

정합성 테스트는 KPI source, SQL이 참조하는 table, `recipe_refs`, diagnostics와
catalog 컬럼 참조가 실제 항목을 가리키는지 검사한다. 새 KPI에는 경계값과 NULL,
분모 0, 중복 JOIN을 재현하는 테스트를 필요에 따라 추가한다.

## Recipe와 CTE 작성

Recipe YAML은 다음 필드로 질문을 실행 가능한 결과 계약에 연결한다.

| 필드 | 의미 |
| --- | --- |
| `when_to_use` | 이 recipe를 적용할 질문과 목적 |
| `cte_name`, `cte_sql` | 재사용할 CTE 이름과 읽기 전용 SQL |
| `sources` | 참조하는 catalog table |
| `output_grain` | CTE 결과 한 행을 식별하는 출력 컬럼 |
| `output_columns` | `category`, `measure`, `time` 역할과 단위·설명 |
| `aggregation_rules` | 필터 위치, join 전제, 재집계 가능 범위 |
| `visualization_hints` | 비교·추이에 적합한 표현 제안 |
| `sample_queries` | CTE를 사용하는 검증 가능한 SELECT 예시 |

파일명은 `<recipe_id>.yaml`로 맞추고 `recipe_id`와 `cte_name`에는 SQL 식별자로
안전한 소문자 `snake_case`를 사용한다. 새 파일은 담당자 검토 전까지 `draft`로
시작한다. 실제 예시는
[initial_wip_by_part.yaml](../knowledge/recipes/initial_wip_by_part.yaml)과
[part_route_tool_summary.yaml](../knowledge/recipes/part_route_tool_summary.yaml)을
참고한다.

다음은 필수 계약을 보여주는 최소 작성 예다. 값과 컬럼은 복사하지 말고 대상
catalog의 실제 grain과 타입에 맞춰 바꾼다.

```yaml
recipe_id: example_by_key
name: 키별 예제 집계
description: dataset과 업무 키별 원천 행을 집계한다.
cte_name: example_by_key
cte_sql: |
  SELECT dataset, business_key, COUNT(*) AS row_count
  FROM source_table
  GROUP BY dataset, business_key
sources: [source_table]
when_to_use:
  - 데이터셋 내 업무 키별 건수를 확인할 때
output_grain: [dataset, business_key]
output_columns:
  - {name: dataset, role: category, desc: 데이터셋 구분}
  - {name: business_key, role: category, desc: 업무 키}
  - {name: row_count, role: measure, unit: row, desc: 원천 행 수}
aggregation_rules:
  - 서로 다른 dataset을 섞지 않는다
visualization_hints:
  - 키별 row_count 비교에는 bar 차트를 고려한다
sample_queries:
  - description: LVHM 키별 건수
    sql: |
      SELECT * FROM example_by_key
      WHERE dataset = 'LVHM'
      ORDER BY business_key
status: draft
owner: ""
source: source_table 원본과 생성 SQLite 확인
updated: 2026-09-15
```

`cte_sql`에는 `WITH <이름> AS (`와 닫는 `)`를 넣지 않는다. Agent는
`get_recipe` 결과를 다음처럼 조합한다.

```sql
WITH example_by_key AS (
    -- cte_sql 본문
)
SELECT *
FROM example_by_key
WHERE dataset = 'LVHM';
```

작성 시 SQL 계약은 다음과 같다.

- `cte_sql`과 `sample_queries[].sql`은 읽기 전용 `SELECT`만 사용한다.
- `sources`에는 CTE의 `FROM`/`JOIN`에 나타나는 실제 catalog table을 모두 적는다.
  CTE 자신의 이름은 `sources`에 넣지 않는다.
- 모든 JOIN은 catalog의 cardinality와 키를 따르고 SMT2020 교차 테이블 JOIN에는
  `dataset`을 포함한다.
- `output_grain`의 모든 이름은 `output_columns`에 있어야 하며 출력 alias와 철자가
  같아야 한다. 수량은 `measure`, 식별 차원은 `category`, 시각은 `time`이다.
- recipe는 문자열 템플릿 엔진이 아니다. `:dataset` 같은 placeholder를 썼다면
  호출자가 실행 전에 허용 값을 명시적으로 치환해야 한다. 가능한 경우 CTE는
  dataset별로 집계하고 바깥 SELECT에서 `WHERE dataset = 'LVHM'`처럼 필터한다.
- 이미 집계된 CTE를 다시 합칠 때는 `aggregation_rules`에 재집계 함수와 보존할
  grain을 명시한다. 비율은 분자·분모 없이 평균내지 않는다.
- 각 sample query는 `WITH <cte_name> AS (<cte_sql>)` 뒤에 붙였을 때 그대로
  실행되어야 한다.

CTE를 추가할 때는 다음 순서로 검토한다.

1. catalog에서 원본 grain과 join cardinality를 확인한다.
2. KPI의 공식, 필터, 비교 모집단과 분모 정책을 확인한다.
3. CTE의 출력 grain과 모든 출력 컬럼을 선언한다.
4. 집계 전에 필요한 필터를 적용하고 join으로 늘어난 행을 점검한다.
5. 작은 고정 데이터로 중복, 누락, 0, NULL, 연월 경계를 검증한다.
6. 재집계에서 보존해야 할 분자·분모와 차원을 `aggregation_rules`에 적는다.
7. 담당자 검토 전에는 `draft`를 유지한다.

`visualization_hints`는 Agent의 제안 자료이며 차트 종류나 컬럼을 강제하지 않는다.
최종 SQL의 alias나 grain이 CTE와 달라질 수 있으므로 차트는 실제 Result Store
컬럼과 grain을 `prepare_visualization`에서 다시 검증한다.

## 검증 Scenario 작성

Scenario는 원본 데이터를 변경하거나 실제 이산사건 시뮬레이션 결과를 만들어내는
파일이 아니다. 공개 benchmark처럼 입력이 고정된 환경에서 “어떤 질문을 어떤
recipe/simulation 순서로 검증하고 무엇이 변하면 회귀인가”를 기록하는 QA 계약이다.
현재 scenario는 `KnowledgeStore`와 테스트가 읽으며 Agent에 직접 노출하는 별도
tool은 없다. 향후 runtime tool로 공개하려면 tool payload와 프론트 표시 계약을
상위 계획에서 먼저 정의한다.

| 필드 | 의미 |
| --- | --- |
| `scenario_id` | 파일명과 같은 소문자 `snake_case` 식별자 |
| `name`, `description` | 사람이 이해할 이름과 검증 목적 |
| `dataset` | 실행 대상 `HVLM` 또는 `LVHM` |
| `question` | Fake/E2E에서 사용할 수 있는 대표 자연어 질문 |
| `steps` | 순서대로 참조할 `recipe` 또는 `simulation`, 입력과 기대 설명 |
| `expected.table_counts` | 고정 원본에서 반드시 일치해야 하는 테이블별 행 수 |
| `expected.unmatched_rows` | 입력 관계 검사별 허용 미연결 행 수 |

실제 작성 샘플은
[hvlm_input_integrity.yaml](../knowledge/scenarios/hvlm_input_integrity.yaml)과
[lvhm_input_integrity.yaml](../knowledge/scenarios/lvhm_input_integrity.yaml)에 있다.
최소 형태는 다음과 같다.

```yaml
scenario_id: lvhm_example_validation
name: LVHM 예제 검증
description: 집계 recipe와 입력 검증 simulation을 관통한다.
dataset: LVHM
question: LVHM의 제품별 현황과 입력 관계를 확인해줘.
steps:
  - action: recipe
    ref: example_by_key
    params: {dataset: LVHM}
    expectation: 기대한 업무 키 수와 합계가 조회된다.
  - action: simulation
    ref: SMT2020_입력검증
    params: {dataset: LVHM}
    expectation: 핵심 관계의 unmatched_rows가 모두 0이다.
expected:
  table_counts: {part: 10, wip: 2156}
  unmatched_rows: {wip_to_part: 0}
status: draft
owner: ""
source: SMT2020 LVHM 원본과 생성 SQLite 확인
updated: 2026-09-15
```

Scenario를 추가할 때는 다음 순서로 작성한다.

1. 대상 dataset을 하나로 고정하고 SQLite에서 기준 row count와 관계 검사를 직접
   실행한다. HVLM/LVHM 식별자가 겹치므로 기대값을 합쳐 적지 않는다.
2. `steps[].ref`가 실제 `knowledge/recipes/*.yaml`의 `recipe_id` 또는
   `knowledge/simulations/*.yaml`의 `type`을 가리키는지 확인한다.
3. `params.dataset`과 최상위 `dataset`을 일치시키고 expectation에는 숫자를
   산출하는 방식과 판정 기준을 사람이 읽을 수 있게 적는다.
4. `expected.table_counts`에는 시나리오가 실제로 의존하는 입력 테이블을 기록한다.
   `expected.unmatched_rows` 키는 simulation 결과의 `check` 값과 정확히 맞춘다.
5. 원본 데이터가 공식적으로 바뀐 경우에만 기대값을 수정한다. 테스트를 통과시키기
   위해 기대값을 임의로 낮추거나 누락 관계를 허용하지 않는다.
6. 구조·SQL·기대값 테스트가 통과해도 담당자 검토 전에는 `draft`를 유지한다.

Recipe와 Scenario를 함께 검증하는 기본 명령은 다음과 같다.

```bash
cd backend
python -m scripts.build_smt2020_db
python -m pytest -q \
  tests/test_knowledge.py \
  tests/test_knowledge_integrity.py \
  tests/test_smt2020_dataset.py
```

테스트는 YAML schema, recipe 참조, CTE의 catalog table 사용, 모든 sample query의
실행 가능 여부, scenario의 table count와 입력 관계 기대값을 확인한다.

## Agent 주입 경계

- `SYSTEM_PROMPT`: 역할, 응답 원칙과 금지사항만 둔다.
- 런타임 `agent/agent_sdk/CLAUDE.md`: 지식과 tool의 인덱스만 둔다.
- Skill: 질의 유형별 절차를 두고 실제 테이블·KPI 내용을 복제하지 않는다.
- 지식 tool: list는 요약, describe/get은 상세를 반환한다.
- RAG: 출처가 있는 비정형 산문만 검색한다.

`agent/sdk_tools.py::TOOL_NAMES`, 런타임 CLAUDE의 tool 표, Skill의 tool 이름과
fake runner가 어긋나지 않게 prompt 정합성 테스트를 유지한다. Agent가 SQL을
작성하기 전 `describe_table`을 호출하고, `draft` 지식을 사용한 계산은 답변에
미검증 기준임을 표시한다.

## SMT2020 데이터와 검증

`scripts/build_smt2020_db.py`는 `datasets/SMT2020_HVLM`과
`datasets/SMT2020_LVHM`의 tab 구분 원본을 하나의 SQLite로 변환한다. 모든
테이블에 `dataset`을 추가하며 SQL 서비스와 입력 검증 mock은 같은 DB를 사용한다.
원본은 수정하지 않고 생성 DB는 완성 후 원자적으로 교체한다.

```bash
cd backend
python -m scripts.build_smt2020_db
python -m pytest -q
```

검증 항목은 YAML schema, KPI source와 column, diagnostics/recipe/scenario reference,
recipe sample SQL, Skill/tool 이름, SQLite schema/index와 row count, dataset-safe
join 및 입력 관계 unmatched 건수를 포함한다.

## 폐쇄망 반입과 운영

- YAML, Skill과 검증 테스트는 애플리케이션 소스와 같은 commit으로 반입한다.
- 반입 전에 인터넷 연결 없이 SQLite 변환과 기본 pytest를 실행해 지식 로딩을 확인한다.
- 비정형 문서 원본은 승인된 반입 절차를 따르고 문서별 owner, source와 갱신일을
  보존한다.
- Milvus와 임베딩 모델은 Phase 3 착수 전에 사내 제공 버전, wheel·이미지,
  모델 파일과 저장 용량을 확정한다. 외부 모델 다운로드를 런타임에 수행하지 않는다.
- 색인에는 `doc_type`, 관련 table·KPI와 원문 식별자를 넣고, 삭제·갱신 시 재색인
  절차와 검증 query를 함께 실행한다.
- 환경변수와 실제 endpoint는 `core/config.py`와 로컬 `.env`로 주입한다.

전체 설치와 real 서비스 이식은 [폐쇄망 배포 및 이식 가이드](CLOSED_NETWORK_SETUP.md)를
따른다.
