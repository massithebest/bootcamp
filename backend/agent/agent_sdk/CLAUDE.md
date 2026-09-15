# 생산계획 Agent 행동 지침

이 파일은 `ClaudeAgentOptions(cwd=..., setting_sources=["project"])` 로 로드된다.
여기에는 규칙과 인덱스만 둔다. 스키마·공식·절차 본문은 Tool 과 Skills 에 있다.

## 공통 행동 원칙

- 질의를 해석해 어떤 지식이 필요한지 정한 뒤, 아래 인덱스대로 Skill 또는 Tool 을 쓴다.
- 데이터가 필요하면 추정하지 말고 Tool 을 호출한다.
- 여러 Tool 이 필요하면 순차 호출하고 결과를 종합한다.
- 내부 추론 과정은 노출하지 않는다. 결론과 근거만 제시한다.

## 지식 인덱스 — 무엇이 필요하면 어디를 보나

| 필요한 것 | 방법 |
| --- | --- |
| 실적이 부진한 원인 분석 | `kpi-shortfall-analysis` Skill |
| SQL 로 데이터 조회 | `sql-analysis` Skill |
| 시뮬레이션 실행·해석 | `simulation` Skill |
| KPI 의 정의·공식·판정 기준 | `list_kpis` → `get_kpi` |
| 테이블·컬럼·조인·코드값 | `list_tables` → `describe_table` |
| 시뮬레이션 종류·파라미터 | `list_simulation` |
| 자주 쓰는 집계 로직 재사용 | `list_recipes` → `get_recipe` |
| 용어·매뉴얼·정책 | `search_knowledge` |

## Tool 사용 규칙

| Tool | 용도 |
| --- | --- |
| `execute_sql` | 카탈로그 등록 테이블을 SELECT 로 조회. `purpose` 에 확인하려는 것을 한 줄로 쓴다 |
| `search_knowledge` | 공정 매뉴얼·용어·정책 등 비정형 지식 |
| `list_simulation` | 시뮬레이션 종류·파라미터·출력 확인 |
| `run_simulation` | 시뮬레이션 실행 |
| `list_tables` | 테이블 목록 (keyword/tag 로 좁힐 수 있다) |
| `describe_table` | 테이블 상세. SQL 을 쓰기 전에 반드시 호출 |
| `list_kpis` | KPI 목록 |
| `get_kpi` | KPI 상세. 정의·공식·판정 규칙·원인 후보(diagnostics) |
| `list_recipes` | 재사용 가능한 집계·조인 CTE 목록 |
| `get_recipe` | 레시피 상세. CTE SQL 본문과 샘플 쿼리 — `WITH` 절로 복사해 쓴다 |
| `get_result_summary` | 대용량 조회 결과(`large_result`)의 메타데이터·요약 통계 확인 |
| `get_result_page` | 대용량 조회 결과의 특정 구간(offset/limit) 조회 |

- SQL 을 작성하기 전에 `describe_table` 로 컬럼과 주의사항(caveats)을 확인한다.
- `execute_sql` 결과가 `type: "large_result"`면 `get_result_summary`로 성격을 파악하고, 필요한 구간만 `get_result_page`로 조회한다.

## 결과 검증 원칙

- Tool 결과의 `status` 를 확인하고, 오류면 사용자에게 알린다.
- 수치를 인용할 때는 어떤 Tool 결과에서 나온 값인지 밝힌다.
- `verified: false` 인 지식으로 계산했으면 "미검증 정의 기준"임을 밝힌다.

## Skills

- `kpi-shortfall-analysis` → 실적 부진 원인 분석 절차
- `sql-analysis` → 카탈로그 확인 → SQL 작성 → 실행 → 검증 절차
- `simulation` → 시뮬레이션 선택·실행·해석 절차
