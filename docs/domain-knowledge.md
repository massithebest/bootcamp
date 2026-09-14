# 도메인 지식 관리 및 주입 아키텍처

**상태: Phase 1 구현 완료 (2026-09-14).** Phase 2·3은 미착수. 백엔드(지식 저장·tool·프롬프트)와 프론트엔드(지식 조회 UI·결과 카드) 양쪽에 걸친 결정이라 최상위 `docs/`에 둔다. 각 하위 프로젝트 docs에 반영할 항목은 섹션 끝에 `→ backend` / `→ frontend`로 표시했다.

## 배경

현업 질의 예: **"FGS 입고 실적이 부진한 원인을 찾아줘."**

이 질의에 답하려면 에이전트는 다음을 알아야 한다.

- 어떤 테이블·컬럼을 봐야 하는지, 어떻게 조인하는지
- "입고 실적"이라는 KPI를 어떻게 집계하는지, 무엇과 비교해 "부진"이라 판정하는지
- 원인을 찾기 위해 어떤 순서로 무엇을 조회하고, 어떤 시뮬레이션을 언제 돌리는지
- 시뮬레이션의 종류·파라미터·응답값이 무엇인지

이 지식은 아직 문서로 정의돼 있지 않고, 에이전트를 개발하면서 함께 쌓아가야 한다. 시스템 프롬프트에 전부 넣을 수 없으므로 **"어디에 저장하고, 언제, 어떤 채널로 에이전트에게 주입할지"**를 정한다. 이 문서 전체에서 위 질의를 관통 예제로 쓴다.

### 현재 상태 (2026-09-14 기준)

| 항목                     | 상태                                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 주입 채널                | `SYSTEM_PROMPT` → `agent_sdk/CLAUDE.md` → `.claude/skills/*` 3계층으로 설계됨 ([backend-scaffold-instructions.md §8](../backend/backend-scaffold-instructions.md)). Skills 3개는 전부 `<!-- TODO -->` 빈 껍데기. |
| 구조화 카탈로그          | [simulation_registry.py](../backend/services/simulation_registry.py) 하나. `PARAM_SCHEMA`는 `list_simulation_types()`에 합쳐지지 않아 에이전트에게 전달되지 않음.                                                       |
| 테이블 사전·KPI·용어집 | 없음. 저장소 전체에서`FGS`/`입고`/KPI 공식 0건.                                                                                                                                                                        |
| SQL 조회                 | `query_database(question)` — 서비스 내부 Text-to-SQL 블랙박스. 실서비스는 `NotImplementedError`.                                                                                                                      |
| 에이전트 권한            | [agent.py](../backend/agent/agent.py) `allowed_tools`가 MCP 4개뿐. `Skill` 도구 미허용.                                                                                                                                 |
| 드리프트                 | [agent_sdk/CLAUDE.md](../backend/agent/agent_sdk/CLAUDE.md)가 삭제된 `simulate_*` 3개 도구를 안내 중.                                                                                                                     |
| RAG                      | `pymilvus`/`langchain`은 requirements에만 있고 코드 참조 0건.                                                                                                                                                          |
| 프론트                   | `context-inspector.tsx`에 Skills/Metadata/Prompt 탭이 더미로 존재. 백엔드 API 대기 중.                                                                                                                                   |

### 결정 사항

| 질문                                           | 결정                                        | 근거                                                                                                                                                        |
| ---------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQL은 누가 작성하나                            | **에이전트가 직접 작성**              | "어떤 테이블·컬럼을 보고 어떻게 조인할지"를 에이전트가 판단하려면 스키마 지식이 에이전트 추론에 직접 쓰여야 한다. Text-to-SQL 블랙박스는 그 판단을 숨긴다. |
| 지식 저장 방식                                 | **repo 파일(git) + RAG(Milvus) 병행** | 구조화 지식(카탈로그·KPI·시뮬레이션)은 백엔드 검증에도 쓰이므로 코드와 함께 버전 관리. 매뉴얼·보고서 같은 대용량 산문만 RAG.                             |
| 에이전트에게 파일 도구(`Read`/`Glob`) 개방 | **하지 않음**                         | 지식 접근 경로를 MCP tool 하나로 통일해 모든 조회가`tool_call` 이벤트로 프론트에 관측되게 한다.                                                           |
| 편집 UI                                        | **보류**                              | 개발 초기에는 git으로 축적. 프론트 Skills 탭은 읽기 전용 조회만 연결.                                                                                       |

## 1. 지식 분류 — 무엇을 관리하나

| 지식 종류           | 관통 예제에서의 예                                                   | 성격                                                       | 저장 위치                   |
| ------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------- |
| 용어집(glossary)    | FGS, 입고, MP, SWAP                                                  | 짧은 정의·동의어·관련 KPI/테이블 링크                    | repo YAML                   |
| 데이터 카탈로그     | 입고 실적 테이블, 계획 테이블, 라인 마스터                           | 테이블·컬럼·키·조인·집계 단위(grain)·코드값·주의사항 | repo YAML                   |
| KPI 정의            | `fgs_inbound` = 기간별 입고 수량, 계획 대비 달성률, 부진 판정 규칙 | 공식·원천·집계 단위·비교 기준·원인 후보(diagnostics)   | repo YAML                   |
| 분석 절차(playbook) | "실적 부진 원인 분석" 단계                                           | 절차형 산문                                                | Skill (`SKILL.md`)        |
| 시뮬레이션 카탈로그 | `실적_조회`, `MP_확정조회` …                                    | 종류·파라미터·출력 스키마·사용 시점·선후 관계          | repo YAML (registry가 로드) |
| 쿼리 레시피         | 검증된 "월별 라인별 입고 실적" SQL                                   | few-shot 예제                                              | repo MD + RAG 색인          |
| 비정형 문서         | 공정 매뉴얼, 계획 정책, 과거 분석 보고서                             | 대용량 산문                                                | Milvus RAG                  |

핵심 구분: **구조화 가능한 것은 YAML, 절차는 Skill, 산문은 RAG.** 하나의 사실이 두 곳에 있으면 불일치가 생기므로 각 지식은 정확히 한 곳에만 둔다(§2 경계 규칙).

## 2. 주입 채널 5개와 역할 분담

Claude Agent SDK가 제공하는 채널을 "항상 로드"와 "필요할 때 로드"로 나눈다. 항상 로드되는 채널에는 **인덱스만**, 실제 내용은 필요할 때 로드되는 채널에 둔다.

| 채널                                                                       | 로드 시점                              | 담는 것                                                                                                                                                                 | 토큰 원칙                                                                       |
| -------------------------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `SYSTEM_PROMPT` ([system_prompt.py](../backend/agent/system_prompt.py))   | 항상                                   | 역할, 응답 원칙, 금지사항                                                                                                                                               | 30줄 이내. 도구 목록·절차 넣지 않음                                            |
| `CLAUDE.md` ([agent_sdk/CLAUDE.md](../backend/agent/agent_sdk/CLAUDE.md)) | 항상 (`setting_sources=["project"]`) | 공통 규칙 +**지식 인덱스** — "실적 부진·원인 분석 → `kpi-shortfall-analysis` Skill", "테이블을 모르면 `list_tables`", "용어를 모르면 `search_knowledge`" | 인덱스만. 스키마·공식·절차 본문 금지                                          |
| Skills (`.claude/skills/*/SKILL.md`)                                     | 에이전트가`description`을 보고 선택  | 절차·플레이북 (무엇을 어떤 순서로 조회하고 판단하는지)                                                                                                                 | 절차만. 테이블·컬럼 복사 금지, 대신 "`describe_table`로 확인"                |
| 지식 tool (in-process MCP)                                                 | 에이전트가 호출                        | 카탈로그·KPI·시뮬레이션 정의                                                                                                                                          | 2단계 progressive disclosure:`list_*`는 요약, `describe_*`/`get_*`는 상세 |
| RAG (`search_knowledge`)                                                 | 에이전트가 호출                        | 비정형 문서, 쿼리 레시피                                                                                                                                                | top-k 청크, 출처 메타데이터 포함                                                |

### 경계 규칙

- 카탈로그·KPI·시뮬레이션 정의의 **source of truth는 YAML**이다. 같은 내용을 RAG에 넣지 않는다. 이유: 두 곳의 내용이 어긋나면 에이전트가 어느 쪽을 믿을지 판단할 수 없다.
- RAG에는 YAML로 표현할 수 없는 산문만 넣는다. 예외로 쿼리 레시피 MD는 RAG에도 색인한다 (유사 질문 검색이 목적이라 벡터 검색이 적합).
- Skill 본문이 길어지면 `references/` 파일로 쪼개지 않고 **Skill을 분할**한다. `Read` 도구를 열지 않기로 했으므로 참조 파일은 에이전트가 읽을 수 없다.
- CLAUDE.md의 도구 표는 [sdk_tools.py](../backend/agent/sdk_tools.py) `TOOL_NAMES`와 항상 일치해야 한다. 현재 드리프트는 §8 Phase 1에서 제거한다.

`→ backend` 채널별 책임 표를 backend/README.md 계층 표에 추가. `SYSTEM_PROMPT` 재작성 원칙.

## 3. 저장 구조

```
backend/
├── knowledge/                        # 데이터(YAML/MD). 코드 아님. git으로 축적.
│   ├── glossary.yaml
│   ├── catalog/
│   │   ├── tables/<table_name>.yaml
│   │   └── joins.yaml                # 자주 쓰는 조인 경로
│   ├── kpi/<kpi_id>.yaml
│   ├── simulations/<type>.yaml       # SIMULATION_TYPES + PARAM_SCHEMA 통합
│   ├── scenarios/<name>.yaml         # 합성 DB에 심을 이상치 정의 (§6-1). 시드와 테스트가 공유
│   └── recipes/<slug>.md
├── data/sample.sqlite                # 시드 스크립트 산출물. gitignore
├── scripts/seed_sample_db.py         # 카탈로그 YAML → DDL → 기준 데이터 → 시나리오 적용
├── services/knowledge_service.py     # 로더(pydantic 검증) + 키워드/태그 검색 + 프론트 API용 조회
├── tools/knowledge_tool.py           # list_tables / describe_table / list_kpis / get_kpi
└── agent/agent_sdk/
    ├── CLAUDE.md                     # 재작성: 드리프트 제거, 지식 인덱스
    └── .claude/skills/
        ├── sql-analysis/SKILL.md
        ├── simulation/SKILL.md
        └── kpi-shortfall-analysis/SKILL.md
```

`knowledge/`를 `agent_sdk/` 밖에 두는 이유: 이 데이터는 에이전트만 쓰는 게 아니라 백엔드 서비스(`execute_sql` 테이블 허용 목록, 시뮬레이션 파라미터 검증)와 프론트 API도 읽는다. 에이전트는 tool을 통해서만 접근하므로 `cwd` 안에 있을 필요가 없다.

### 공통 메타데이터

모든 YAML 항목은 다음 필드를 가진다.

```yaml
status: draft        # draft | verified
owner: "생산계획팀 OOO"
updated: 2026-09-14
source: "9/12 현업 인터뷰"   # 어디서 얻은 지식인지
```

`draft` 항목은 tool 응답에 `"verified": false`로 실린다. 에이전트는 CLAUDE.md 규칙에 따라 미검증 정의로 집계한 수치에는 그 사실을 답변에 밝힌다. 개발 중 지식을 빠르게 쌓으면서도 신뢰도를 구분하기 위한 장치다.

### 스키마 예시

`catalog/tables/<table_name>.yaml`

```yaml
table: FGS_INBOUND_RESULT          # 실제 테이블명은 현업 확인 후 기입
description: FGS 창고 입고 실적 (일 단위)
grain: [work_date, line_cd, product_id]
time_column: work_date
tags: [실적, 입고, FGS]
columns:
  - {name: work_date, type: date, desc: 작업일}
  - {name: line_cd, type: varchar, desc: 라인 코드, ref: LINE_MASTER.line_cd}
  - {name: product_id, type: varchar, desc: 품목 ID}
  - {name: inbound_qty, type: number, desc: 입고 수량}
  - {name: status_cd, type: varchar, desc: 상태, codes: {C: 완료, P: 대기, X: 취소}}
joins:
  - {to: LINE_MASTER, on: line_cd, kind: many-to-one}
  - {to: PRODUCTION_PLAN, on: [work_date, line_cd, product_id], kind: one-to-one, note: 계획 대비 비교용}
caveats:
  - status_cd = 'X' 는 실적에서 제외
  - work_date 는 계획월 기준이 아니라 실제 작업일
sample_sql: |
  SELECT work_date, line_cd, SUM(inbound_qty) FROM FGS_INBOUND_RESULT
  WHERE status_cd <> 'X' GROUP BY work_date, line_cd
status: draft
owner: ""
updated: 2026-09-14
source: ""
```

`kpi/<kpi_id>.yaml`

```yaml
kpi_id: fgs_inbound
name: FGS 입고 실적
aliases: [입고 실적, FGS 입고량, 완제품 입고]
definition: 기간 내 FGS 창고에 입고 완료된 수량. 계획 수량 대비 달성률로 부진 여부를 판단한다.
formula: SUM(inbound_qty) WHERE status_cd <> 'X'
sources: [FGS_INBOUND_RESULT, PRODUCTION_PLAN]
grain: [work_date, line_cd, product_id]
baseline: PRODUCTION_PLAN.plan_qty   # 비교 기준
shortfall_rule: 달성률 < 0.9 이면 부진. 3일 연속이면 구조적 부진으로 본다.
sql_template: |
  SELECT r.work_date, r.line_cd,
         SUM(r.inbound_qty) AS actual, SUM(p.plan_qty) AS plan
  FROM FGS_INBOUND_RESULT r JOIN PRODUCTION_PLAN p USING (work_date, line_cd, product_id)
  WHERE r.status_cd <> 'X' AND r.work_date BETWEEN :from AND :to
  GROUP BY r.work_date, r.line_cd
diagnostics:                        # 부진일 때 확인할 가설. 에이전트가 순서대로 검토
  - {hypothesis: 계획 자체가 변경됨, how: simulation, ref: MP_확정조회}
  - {hypothesis: 특정 라인·품목에 집중, how: sql, ref: recipes/inbound-by-line-product}
  - {hypothesis: 생산 실적 자체가 부족, how: simulation, ref: 실적_조회}
  - {hypothesis: 자재 부족, how: sql, ref: MATERIAL_SHORTAGE}
status: draft
owner: ""
updated: 2026-09-14
source: ""
```

`simulations/<type>.yaml` — 기존 `SIMULATION_TYPES`/`PARAM_SCHEMA`를 합치고 세 필드를 추가한다.

```yaml
type: MP_확정조회
name: 확정 MP 조회
aliases: [확정 MP, 확정된 버전]
when_to_use: 계획 수량이 바뀌었는지 확인할 때. 실적 부진 원인 분석의 첫 가설 검증에 사용.
params:
  fixedPlanMonth: {required: false, description: "확정 MP 조회 연월 (yyyyMM), 누락시 당월", example: "202609"}
output_schema:
  version: {type: string, desc: 확정 MP 버전}
  items: {type: array, desc: "[{product_id, line_cd, plan_qty}]"}
follows: []                          # 이 시뮬레이션 전에 실행해야 하는 것
status: verified
```

`recipes/<slug>.md`

```markdown
---
question: 월별 라인별 FGS 입고 실적과 계획 대비 달성률
kpi: fgs_inbound
tables: [FGS_INBOUND_RESULT, PRODUCTION_PLAN]
verified: 2026-09-14
---
```sql
...
```
설명: status_cd 'X' 제외. 달성률은 actual / NULLIF(plan, 0).
```

`→ backend` `knowledge/` 디렉터리 규약, pydantic 모델(`KnowledgeTable`, `KnowledgeKpi`, `KnowledgeSimulation`), `simulation_registry.py`를 YAML 로더로 전환.

## 4. Tool 계약

| Tool                 | 상태                              | 입력                                                             | 출력 요지                                                                                    |
| -------------------- | --------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `list_tables`      | 신규                              | `{keyword?: str, tag?: str}`                                   | `[{table, description, grain, tags, verified}]` 요약. 인자 없으면 전체                     |
| `describe_table`   | 신규                              | `{table: str}`                                                 | 컬럼·키·조인·코드값·주의사항·sample_sql 전체                                            |
| `list_kpis`        | 신규                              | `{keyword?: str}`                                              | `[{kpi_id, name, aliases, verified}]`                                                      |
| `get_kpi`          | 신규                              | `{kpi_id: str}`                                                | 정의·공식·원천·baseline·shortfall_rule·sql_template·diagnostics                        |
| `execute_sql`      | **`query_database` 대체** | `{sql: str, purpose: str}`                                     | `{kind: "database", sql, table: {columns, rows}, row_count, truncated, chart?}`            |
| `search_knowledge` | 유지, 인자 확장                   | `{query: str, doc_type?: "manual"\|"policy"\|"report"\|"recipe"}` | `[{text, source, doc_type, tables?}]`                                                      |
| `list_simulation`  | 개선                              | `{}`                                                           | `params` 상세(`PARAM_SCHEMA` 병합), `when_to_use`, `output_schema`, `follows` 포함 |
| `run_simulation`   | 유지                              | `{simulation_type, params}`                                    | 기존과 동일                                                                                  |

### `execute_sql` 가드레일

서비스 계층(`services/*/sql_service.py`)에서 강제한다. SDK 훅이 아니다 — 훅은 SDK에 종속되지만 서비스 계층 검증은 mock/real 양쪽과 테스트에서 동일하게 동작한다.

- `SELECT`(및 `WITH … SELECT`)만 허용. DML/DDL 거부.
- `FROM`/`JOIN`에 등장하는 테이블은 카탈로그에 등록된 것만 허용. 미등록 테이블은 오류 메시지에 "`list_tables`로 확인하라"를 포함.
- 행 수 상한(기본 500)과 timeout. 상한을 넘으면 `truncated: true`.
- `purpose`는 실행 전 로그에 남긴다. 에이전트가 "무엇을 확인하려는 쿼리인지"를 한 줄로 쓰게 강제해 프론트 진행 표시와 사후 감사에 쓴다.
- mock 모드는 더미 행을 만들지 않고 **합성 SQLite**(`backend/data/sample.sqlite`)를 실제로 조회한다. 시드 방식은 §6-1. 실제 DB 없이도 지식 → SQL → 결과 → 원인 판정 흐름을 끝까지 시험할 수 있어야 한다.

### 결과 payload

`execute_sql` 결과는 [chart-visualization.md §2](chart-visualization.md)의 `"database"` kind를 그대로 따른다. `chart` 필드는 선택이며 백엔드 `_infer_chart`가 붙인다.

지식 tool 결과에는 `kind: "catalog"`를 붙인다. `"knowledge"`는 프론트가 이미 `search_knowledge`(RAG) 결과 렌더링에 쓰고 있어 충돌하므로 쓰지 않는다.

```jsonc
{ "kind": "catalog", "catalog_type": "table" | "kpi" | "table_list" | "kpi_list", "verified": true, "data": { ... } }
```

`→ backend` tools/knowledge_tool.py, sql_tool.py 시그니처 변경, sdk_tools.py `TOOL_NAMES` 갱신, test_tools.py 추가.
`→ frontend` `tool_result.data.kind = "catalog"` 렌더링 (§7).

## 5. 관통 예제 실행 흐름

"FGS 입고 실적이 부진한 원인을 찾아줘"

| 단계 | 에이전트 동작                                                                                                                                                                                                         | 사용된 채널 / 지식                                                                  |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 1    | 질의에서 "실적 부진 · 원인"을 읽고`kpi-shortfall-analysis` Skill 선택                                                                                                                                              | CLAUDE.md 지식 인덱스 → Skill description                                          |
| 2    | Skill 절차 1단계:`list_kpis("입고")` → `get_kpi("fgs_inbound")`                                                                                                                                                  | 지식 tool →`kpi/fgs_inbound.yaml` (공식·baseline·shortfall_rule·diagnostics)  |
| 3    | 기간이 없으면 사용자에게 확인하거나 Skill 기본값(최근 1개월) 적용                                                                                                                                                     | Skill 본문                                                                          |
| 4    | `describe_table("FGS_INBOUND_RESULT")`, `describe_table("PRODUCTION_PLAN")` → `sql_template` 참고해 SQL 작성 → `execute_sql(sql, purpose="기간 내 계획 대비 입고 달성률")`                                  | 지식 tool → 카탈로그 YAML,`sql-analysis` Skill의 SQL 작성 규칙                   |
| 5    | `shortfall_rule`로 부진 여부·구간 판정. 부진이면 라인·품목·일자별 분해 쿼리 `execute_sql`                                                                                                                      | KPI YAML +`sql-analysis` Skill                                                    |
| 6    | `diagnostics`를 순서대로 검증: `run_simulation("MP_확정조회")`로 계획 변경 확인 → 분해 결과로 집중 라인 확인 → `run_simulation("실적_조회", …)`로 생산 부족 확인 → 필요 시 `execute_sql`로 자재 부족 확인 | KPI YAML diagnostics,`simulation` Skill(파라미터·출력 해석), `list_simulation` |
| 7    | 뒷받침되는 가설과 근거 수치(어떤 tool 결과에서 나왔는지)를 인용해 결론. 미검증(`draft`) 정의를 썼으면 명시                                                                                                          | CLAUDE.md 결과 검증 원칙                                                            |

모든 단계가 `tool_call`/`tool_result` 이벤트로 프론트에 노출된다. 에이전트가 파일을 직접 읽지 않으므로 "어떤 지식을 참조했는지"가 빠짐없이 보인다.

이 흐름이 §4의 tool 계약만으로 완결되는지가 설계의 검증 기준이다. 새로운 질의 유형이 이 흐름으로 풀리지 않으면 tool을 늘리기 전에 **Skill 또는 YAML 필드 추가로 해결되는지** 먼저 본다.

## 6. 지식 작성·성장 워크플로

지식은 개발 중 계속 쌓인다. 다음 루프를 기본으로 한다.

1. 현업 질의를 에이전트에 던진다.
2. 실패하거나 부정확하면 어느 채널의 지식이 부족했는지 식별한다 (테이블 몰랐음 → 카탈로그, 판정 기준 없음 → KPI, 순서를 몰랐음 → Skill).
3. 해당 YAML/Skill을 `status: draft`로 보강한다.
4. 현업이 확인하면 `verified`로 올린다.
5. 성공한 분석의 SQL은 `recipes/`에 저장한다 (초기엔 수동, 이후 에이전트가 제안하고 개발자가 승인하는 admin tool 검토).

### 6-1. 합성 시드 DB와 시나리오

공개 데이터셋 중 사내 스키마(계획 대비 실적, MP, FGS 입고)를 닮은 것은 없다. 그리고 mock 개발이 어려운 진짜 이유는 데이터가 없어서가 아니라 **찾아낼 원인이 없어서**다. 그래서 카탈로그 정의에서 직접 데이터를 생성하고, 이상치를 의도적으로 심는다.

- `backend/scripts/seed_sample_db.py`: `knowledge/catalog/tables/*.yaml`에서 DDL을 만들고, 기준 데이터(라인·품목 마스터, 일별 계획·실적, MP 버전)를 고정 random seed로 생성한 뒤 시나리오를 적용해 `backend/data/sample.sqlite`에 저장한다. 카탈로그 YAML이 바뀌면 시드도 따라간다. 지식과 데이터의 source of truth가 하나로 유지된다.
- `knowledge/scenarios/<name>.yaml`: 심을 이상치와 그 원인. 예:

  ```yaml
  name: fgs_line_b_material_shortage
  description: 9월 3주차 B라인 P-1002 입고가 자재 결품으로 40% 부족
  period: [2026-09-15, 2026-09-21]
  line_cd: B
  product_id: P-1002
  drop_ratio: 0.4
  cause: material_shortage        # MATERIAL_SHORTAGE 에 같은 기간 결품 행을 삽입
  unchanged: [MP_VERSION]         # 기각돼야 할 가설의 흔적은 남기지 않음
  expected_diagnosis: 자재 부족    # E2E 테스트가 에이전트 답변에서 찾는 문구
  ```

- 시나리오 파일은 시드와 테스트가 공유한다. `tests/test_scenarios.py`는 시나리오별로 KPI `sql_template`를 SQLite에 실행해 부진 구간이 실제로 생성됐는지(달성률 < `shortfall_rule`) 확인한다. E2E 테스트는 관통 질의를 에이전트에 보내 답변에 `expected_diagnosis`가 포함되는지 확인한다. 정답이 있으므로 Skill이나 KPI 정의를 고칠 때 회귀 테스트가 된다.
- mock 시뮬레이션 서비스의 `실적_조회`·`MP_확정조회`도 같은 SQLite를 읽는다. SQL 결과와 시뮬레이션 결과가 모순되면 에이전트가 잘못된 가설을 채택하므로, 두 경로가 한 데이터를 봐야 한다.
- 시나리오를 늘려가는 것이 곧 "에이전트가 풀 수 있는 원인 유형"을 늘리는 일이다. 시나리오 하나가 KPI `diagnostics` 항목 하나에 대응한다.

### 정합성 검사 (pytest)

- 모든 YAML이 pydantic 모델을 통과한다.
- KPI의 `sources`·`formula`·`sql_template`에 등장하는 테이블·컬럼이 카탈로그에 존재한다.
- `diagnostics[].ref`가 실제 시뮬레이션 type, 테이블, 또는 레시피를 가리킨다.
- Skill 본문에 언급된 tool 이름이 `TOOL_NAMES`에 있고, KPI id가 존재한다.
- CLAUDE.md 도구 표가 `TOOL_NAMES`와 일치한다 (드리프트 재발 방지).

### RAG 색인

`backend/scripts/ingest_knowledge.py`가 비정형 문서 디렉터리와 `recipes/`를 Milvus에 색인한다. 청크는 heading 단위, 메타데이터에 `doc_type`, `tables[]`, `kpi`를 붙여 `search_knowledge(doc_type=…)` 필터에 쓴다. YAML은 색인하지 않는다(§2 경계 규칙). 폐쇄망 Milvus 버전·임베딩 모델은 [closed-network.md](../frontend/docs/closed-network.md) 원칙에 따라 도입 전 확인한다.

### 알려진 부작용

`backend/agent/agent_sdk/.claude/skills`는 에이전트용 Skill인데, 개발자가 이 저장소에서 Claude Code를 열면 Claude Code도 이 Skill들을 자기 것으로 인식한다(이번 설계 세션에서 관찰). 개발 편의상 무시해도 되지만, 에이전트 Skill을 개발 작업에 잘못 적용하지 않도록 Skill description 첫 줄에 "생산계획 Agent 전용"을 명시한다.

`→ backend` tests/test_knowledge.py, scripts/ingest_knowledge.py, `.env`에 `MILVUS_*` 키 ([CLOSED_NETWORK_SETUP.md](../backend/docs/CLOSED_NETWORK_SETUP.md) Part 2 명명 규칙).

## 7. 프론트엔드 연동 계약

기존 `AgentEvent` 계약은 바꾸지 않는다.

### 읽기 전용 지식 API

| 엔드포인트                     | 응답                                              | 용도                                  |
| ------------------------------ | ------------------------------------------------- | ------------------------------------- |
| `GET /api/knowledge/skills`  | `[{name, description, status}]`                 | context-inspector Skills 탭 더미 대체 |
| `GET /api/knowledge/catalog` | `[{table, description, grain, tags, verified}]` | 테이블 목록 조회                      |
| `GET /api/knowledge/kpis`    | `[{kpi_id, name, aliases, verified}]`           | KPI 목록 조회                         |

Skills 탭의 per-skill 토글은 보류한다. 켜고 끄는 의미(`allowed_tools`? Skill 비활성화?)가 아직 정해지지 않았다.

### `tool_result` 렌더링

- `kind: "database"` — 기존 DataTable + 선택적 chart. 변경 없음.
- `kind: "knowledge"` — 기존 `search_knowledge` RAG 결과 카드. 변경 없음.
- `kind: "catalog"` — 컴팩트 "참조한 지식" 카드. `catalog_type`에 따라 테이블명·KPI명과 `verified` 배지만 표시하고 본문은 접는다. 분석 한 번에 지식 조회가 4~6회 발생하므로 결과 영역을 차지하지 않게 한다.
- `execute_sql`의 `purpose`는 `tool_call` 진행 표시(`agent-progress.tsx`)에 한 줄로 노출한다.

`→ frontend` types/workspace.ts `Skill` 타입을 API 응답에 맞춤, tool-results에 `knowledge-result.tsx` 추가, agent-progress에 `purpose` 표시.

## 8. 단계별 도입

| Phase | 범위                                                                                                                                                                                                                                                        | 완료 기준                                                                              |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1 | `knowledge/` 로더 + 지식 tool 4개 + `execute_sql`(SQLite) + 시드 스크립트 + 시나리오 1개 + 시뮬레이션 registry → YAML + CLAUDE.md/SYSTEM_PROMPT 재작성 + `allowed_tools`에 `Skill` 추가 + 지식 읽기 API + **수직 슬라이스 1개**: `fgs_inbound` KPI, 원천 테이블 6개, `kpi-shortfall-analysis`·`sql-analysis`·`simulation` Skill. 실행 계획: [backend/plan/domain-knowledge-plan.md](../backend/plan/domain-knowledge-plan.md) | 시나리오 `fgs_line_b_material_shortage`에 대해 에이전트가 §5 흐름대로 tool을 호출하고 **자재 부족을 원인으로 지목** |
| 2 | 시나리오 추가(계획 변경, 생산 부족, 라인 집중) + diagnostics 보강 + 프론트 지식 렌더링([frontend/plan/domain-knowledge-plan.md](../frontend/plan/domain-knowledge-plan.md)) | 시나리오 4개 전부 E2E 통과, Skills 탭이 실제 Skill을 표시 |
| 3 | RAG 색인 스크립트, recipes, `search_knowledge` 실서비스 | `search_knowledge`가 레시피를 반환 |

Phase 1의 `production-planning` Skill은 `kpi-shortfall-analysis`로 대체한다. "생산계획 업무 수행법" 같은 범용 Skill은 description이 모호해 선택 기준이 되지 못한다. Skill은 **질의 유형 하나에 하나씩** 만든다.

## 9. 확인 필요 사항

- **`Skill` 도구 노출 여부**: claude-agent-sdk 0.2.152에서 `system_prompt`를 문자열로 주면 Claude Code preset이 대체된다. `setting_sources=["project"]`로 Skill 파일은 로드되지만 `Skill` 도구 안내가 preset에 있어 빠질 수 있다. Phase 1 첫 작업으로 확인하고, 안 되면 `system_prompt={"type": "preset", "preset": "claude_code", "append": SYSTEM_PROMPT}`로 전환한다.
- **실제 테이블명·컬럼명**: 이 문서의 `FGS_INBOUND_RESULT` 등은 자리표시자다. 현업 확인 후 카탈로그에 `draft`로 기입한다.
- **폐쇄망 Milvus·임베딩**: Phase 3 착수 전 사내 가용 버전 확인.
- **`query_database` 제거 시점**: Phase 1에서 `execute_sql`로 대체하되, pntfp Text-to-SQL 이식이 필요해지면 `search_knowledge`처럼 별도 보조 tool로 되살릴 수 있다. 지금은 YAGNI.
- **2차 검증 데이터**: 합성 DB는 사내 스키마를 흉내 내므로 Skill이 그 스키마에 과적합될 수 있다. Phase 3 이후 Microsoft AdventureWorks(`Production.WorkOrder`에 계획·실제 일정과 스크랩 수량이 있음)를 별도 카탈로그로 등록해 "낯선 스키마에서도 카탈로그만 보고 SQL을 쓰는가"를 확인한다.

## 참고

- [chart-visualization.md](chart-visualization.md) — `execute_sql` 결과 스키마의 기준
- [backend/backend-scaffold-instructions.md §8, §25](../backend/backend-scaffold-instructions.md) — 3계층 프롬프트 설계 원안
- [backend/docs/CLOSED_NETWORK_SETUP.md](../backend/docs/CLOSED_NETWORK_SETUP.md) Part 2 — 실서비스 이식·env 명명 규칙
- [frontend/docs/decisions.md#3-pane-워크벤치-리디자인](../frontend/docs/decisions.md#3-pane-워크벤치-리디자인) — context-inspector Skills 탭
