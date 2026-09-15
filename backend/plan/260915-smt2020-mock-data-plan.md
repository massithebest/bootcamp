# SMT2020 SQLite 및 Mock 전환 실행 계획 (백엔드)

**상태: 완료. 마지막 갱신: 2026-09-15.**

상위 계약은 [SMT2020 SQLite 및 Mock 전환 계획](../../plan/260915-smt2020-mock-data-plan.md)을
따른다. 프론트엔드 관통 검증은
[프론트엔드 실행 계획](../../frontend/plan/260915-smt2020-mock-data-plan.md)과 연결한다.

## 실행 규칙

- Task는 번호 순서대로 수행하고 각 Task의 검증을 통과한 뒤 다음으로 이동한다.
- 원본 `datasets/SMT2020_*` 파일은 읽기만 하며 값 보정이나 원본 덮어쓰기를 하지 않는다.
- SQLite 생성에는 Python 표준 라이브러리만 사용한다.
- mock SQL과 mock simulation은 같은 `SMT2020_DB_PATH`를 조회한다.
- mock/real service 함수 시그니처와 Result Store 반환 계약은 유지한다.
- 공유 계약 변경이 필요하면 구현 전에 상위 계획을 먼저 갱신한다.
- 계획 밖 판단과 실제 실행 결과는 문서 끝의 결정·실행 기록에 남긴다.

## Task 0. 실제 파일 계약 고정

**대상**: `datasets/SMT2020_HVLM`, `datasets/SMT2020_LVHM`, 변환기 테스트 fixture

**요구 동작**:

- 필수 고정 파일은 `part.txt`, `order.txt`, `WIP.txt`, `tool.txt.1l`,
  `setup.txt`, `setupgrp.txt`, `downcal.txt`, `pmcal.txt`, `attach.txt`,
  `fromto.txt`다.
- 각 데이터셋에 `route_*.txt`가 하나 이상 있어야 한다.
- 파일별 예상 원본 헤더를 코드 상수로 두고 순서까지 검증한다. route 파일끼리도
  헤더가 완전히 같아야 한다.
- 데이터셋 폴더 이름은 정확히 `SMT2020_HVLM`, `SMT2020_LVHM`만 받으며
  SQLite `dataset` 값은 각각 `HVLM`, `LVHM`으로 만든다.
- 짧은 행은 누락분이 모두 행 끝에 있을 때만 `NULL`로 pad한다. 긴 행은 오류로
  처리한다. 오류에는 dataset, 파일명, 1-based 원본 행 번호를 포함한다.

**검증/완료 조건**:

- 실제 파일 전부가 헤더 검증을 통과한다.
- HVLM `WIP.txt` 첫 행이 10개 컬럼으로 보존되고 `hotlot`, `trace`가 `NULL`이 된다.
- 임의로 헤더를 바꾸거나 필드를 추가한 임시 fixture가 명확한 오류로 실패한다.

## Task 1. 원자적 SQLite 변환기 구현

**변경 대상**: `scripts/build_smt2020_db.py`(신규), `scripts/__init__.py`, `.gitignore`

**요구 동작**:

- `python -m scripts.build_smt2020_db`로 기본 입력 `backend/datasets`, 기본 출력
  `backend/datasets/smt2020.db`를 사용한다.
- CLI에 `--source-root PATH`, `--output PATH`를 제공하고 Python 호출용
  `main(source_root: Path | None = None, db_path: Path | None = None) -> Path`를
  제공한다.
- table/file mapping과 컬럼명 override는 상위 계약에 고정된 명시 상수로 둔다.
- 각 테이블의 전체 입력을 먼저 읽어 타입을 판정한다. 빈 값은 판정에서 제외한다.
  - 정수 후보가 모두 정수면 `INTEGER`
  - 실수 후보가 모두 유한한 숫자면 `REAL`
  - `start`, `due`가 모두 `%m/%d/%y %H:%M:%S`면 ISO `TEXT`
  - 후보 중 하나라도 실패하면 변환하지 않고 해당 컬럼 전체를 원문 `TEXT`로 저장
- 임시 DB는 출력과 같은 디렉터리에 만들고 schema, insert, index, count 검증과
  commit이 끝난 뒤 `Path.replace()`로 기존 DB를 원자적으로 교체한다. 예외 시
  임시 파일만 정리하고 기존 출력은 유지한다.
- 생성 인덱스는 상위 계획의 9개 키를 모두 포함하며 unique 대상은
  `part(dataset, part)`, `route_step(dataset, route, step)`,
  `tool(dataset, stnfam)`이다.
- 성공 시 출력 경로, 데이터셋별/테이블별 row count를 출력한다.
- `.gitignore`에는 `/backend/datasets/smt2020.db`만 추가한다.

**검증/완료 조건**:

- 두 번 연속 실행한 DB의 schema, index 이름과 row count가 같다.
- 두 번째 실행 중 잘못된 fixture로 실패시켜도 첫 DB의 checksum과 조회 결과가 같다.
- 실제 row count는 상위 계획의 11개 테이블 기준값과 일치한다.

## Task 2. 기존 합성 DB와 설정 제거

**변경 대상**: `scripts/seed_sample_db.py`(삭제), `data/sample.sqlite`(로컬 삭제),
`core/config.py`, `.env.example`, `services/mock/_sqlite.py`

**요구 동작**:

- `SAMPLE_DB_PATH`를 제거하고 `SMT2020_DB_PATH`를 추가한다. 환경변수가 비면
  `BACKEND_DIR / "datasets" / "smt2020.db"`를 사용한다.
- 연결 helper는 호출 시점에 `core.config.SMT2020_DB_PATH`를 읽어 테스트
  monkeypatch가 동작하게 한다.
- DB 존재 여부를 확인한 뒤 URI `mode=ro`로 연결하여 mock 내부에서도 쓰기를
  막고 `sqlite3.Row`를 사용한다.
- 누락 오류는 내부 절대경로 없이
  `python -m scripts.build_smt2020_db` 실행을 안내한다.
- `data/results`, `data/visualizations`와 그 안의 산출물은 건드리지 않는다.

**검증/완료 조건**:

- `rg 'SAMPLE_DB_PATH|seed_sample_db|sample.sqlite'` 결과가 완료 계획 이력을
  제외한 실행 코드·현재 운영 문서·테스트에서 0건이다.
- 없는 DB, 정상 DB와 읽기 전용 연결을 각각 테스트한다.

## Task 3. SMT2020 도메인 지식으로 교체

**변경 대상**: `knowledge/catalog`, `knowledge/kpi`, `knowledge/recipes`,
`knowledge/scenarios`, `knowledge/simulations`, `knowledge/glossary.yaml`,
`services/knowledge_service.py`

**요구 동작**:

- 기존 FGS/MP 전용 table YAML 6개, `plan_vs_actual` recipe,
  `fgs_inbound` KPI, 합성 원인 scenario와 기존 simulation YAML 4개를 제거한다.
- SQLite 11개 테이블 각각의 catalog YAML을 추가한다. 실제 SQLite 컬럼·타입,
  `dataset`을 포함한 grain/join, 값 단위와 집계 주의사항, 실행 가능한 sample SQL을
  기록한다.
- `joins.yaml`에 다음 관계를 등록한다.
  - `part(dataset, route) → route_step(dataset, route)`
  - `route_step(dataset, stnfam) → tool(dataset, stnfam)`
  - `wip(dataset, part) → part(dataset, part)`
  - `orders(dataset, part) → part(dataset, part)`
- `initial_wip` KPI는 `dataset, part` grain에서 `COUNT(*) AS lot_count`,
  `SUM(pieces) AS piece_count`를 정의하고 입력 검증 simulation을 diagnostic으로
  연결한다.
- glossary는 WIP, Route, STNFAM, HVLM, LVHM을 실제 catalog에 연결한다.
- simulation YAML은 `SMT2020_입력검증` 하나로 교체하며 필수 `dataset`과 출력
  `kpis`, `table`, `results`, `summary`를 문서화한다.
- 합성 시드에만 사용된 `Scenario` 모델, loader와 `list_scenarios`를 제거한다.
  일반 catalog/KPI/recipe/simulation tool 계약은 유지한다.

**검증/완료 조건**:

- 모든 YAML이 로드되고 column ref, join, KPI source와 diagnostic ref가 실제
  항목을 가리킨다.
- catalog에 선언된 테이블·컬럼·SQLite affinity가 생성 DB와 일치한다.
- 모든 sample SQL과 `initial_wip` SQL이 SQL guard를 통과해 실행된다.
- HVLM/LVHM을 함께 조회하더라도 sample JOIN에 dataset 조건이 누락되지 않는다.

## Task 4. Mock SQL과 입력 검증 simulation 전환

**변경 대상**: `services/mock/mock_sql_service.py`,
`services/mock/mock_simulation_service.py`, `services/simulation_registry.py`,
`services/real/simulation_service.py`

**요구 동작**:

- mock SQL은 새 read-only 연결 helper와 SMT catalog allow-list를 사용한다.
  `execute_sql`의 입력/출력, Result Store 저장, 100행 inline 기준과 500행 guard는
  변경하지 않는다.
- `SMT2020_입력검증`은 `dataset`을 strip/uppercase한 뒤 `HVLM`, `LVHM`만
  허용한다. 다른 값은 허용값을 포함한 안전한 error payload를 반환한다.
- 입력 검증 결과는 다음 SQL 기반으로 계산한다.
  - 11개 테이블의 dataset별 `COUNT(*)`
  - part의 route가 route_step에 존재하는지
  - 각 route step의 stnfam이 tool에 존재하는지
  - wip/orders의 part가 part master에 존재하는지
  - wip의 curstep이 해당 part route의 route_step에 존재하는지
- 관계별 `source_rows`, `matched_rows`, `unmatched_rows`를 `results`에 넣고,
  `matched_rows + unmatched_rows == source_rows`를 보장한다.
- `results` 배열은 기존 로직대로 Result Store에 저장하고 `result_id`, `columns`,
  `type`을 받는다. `kpis`와 table count는 기존 simulation renderer가 읽는 형태로
  유지한다.
- real service는 같은 registry를 노출하되 실행은 기존처럼 구현되지 않은 상태를
  유지한다.

**검증/완료 조건**:

- HVLM/LVHM 모두 모든 관계의 `unmatched_rows == 0`이다.
- 소문자 dataset 입력이 정상화되고, 잘못된 값과 DB 누락은 error payload가 된다.
- SQL과 simulation 결과의 access scope 및 Result Store 조회가 유지된다.

## Task 5. Fake Runner와 런타임 지침 전환

**변경 대상**: `agent/fake_runner.py`, `agent/agent_sdk/CLAUDE.md`,
`agent/agent_sdk/.claude/skills/sql-analysis/SKILL.md`,
`agent/agent_sdk/.claude/skills/simulation/SKILL.md`, prompt consistency 테스트

**요구 동작**:

- Fake Runner는 `initial_wip` 정의 확인 후 LVHM 제품별 WIP lot 수 SQL을 실행하고,
  `SMT2020_입력검증`을 호출한다.
- SQL JOIN과 집계에는 `dataset = 'LVHM'`을 넣는다.
- SQL 결과의 `part`를 x, `lot_count`를 y로 쓰는 bar visualization을 등록한다.
- 답변은 조회 건수와 입력 관계 검증 결과만 설명하며 throughput, 병목, 생산 가능량
  같은 미계산 수치를 만들지 않는다.
- 런타임 지침에 dataset을 먼저 확정하고 모든 cross-table JOIN에 dataset을 함께
  사용하는 규칙, 입력 검증 mock을 실제 DES로 해석하지 않는 규칙을 추가한다.

**검증/완료 조건**:

- Fake Runner 이벤트가 catalog→execute_sql→run_simulation→prepare_visualization
  순으로 발생하고 error 없이 `done`으로 끝난다.
- tool 목록과 CLAUDE.md 표, skill에서 언급한 tool 이름 정합성 테스트가 통과한다.

## Task 6. 테스트와 운영 문서 마이그레이션

**변경 대상**: `tests/`, 루트·백엔드 `README.md`, `backend/AGENTS.md`,
`docs/CLOSED_NETWORK_SETUP.md`, `docs/domain-knowledge-management.md`

**요구 동작**:

- 공통 pytest fixture는 실제 raw dataset을 임시 출력 DB로 변환하고
  `SMT2020_DB_PATH`와 Result Store를 `tmp_path`로 격리한다.
- 기존 FGS/MP seed에 결합된 service/tool/scenario/E2E/aggregation 테스트를
  SMT2020 count, join, initial WIP와 입력 검증 시나리오로 교체한다.
- 로더 자체를 검증하는 단위 fixture도 오래된 FGS 명칭 대신 SMT table 예시를 쓴다.
- README와 작업 지침의 초기화 명령을 `python -m scripts.build_smt2020_db`로 바꾸고
  `SERVICE_MODE=mock`이 생성 DB를 읽는다고 명시한다.
- 폐쇄망 문서에는 raw dataset 반입, 변환, checksum/row count 확인과 DB 재생성
  절차를 기록한다.

**검증/완료 조건**:

```bash
cd backend
python -m scripts.build_smt2020_db
python -m scripts.build_smt2020_db
python -m pytest -q
```

- `sqlite_master`, `PRAGMA table_info`, `PRAGMA index_list` 검증이 통과한다.
- 상위 계획의 row count와 다섯 JOIN 관계가 모두 맞는다.
- 제공된 제품별 WIP/공정 Step 수 SQL과 dataset-safe 변형이 실행된다.
- 실제 provider 인증이 있을 때 E2E 질의가 catalog, SQL, 입력 검증을 사용하고
  계산하지 않은 simulation 수치를 주장하지 않는다.

## 최종 검증

```bash
cd backend && python -m pytest -q
cd .. && git diff --check
```

프론트엔드 계획의 lint/build와 Fake Runner 화면 검증까지 완료되어야 상위 계획을
완료로 전환한다.

## 결정·실행 기록

- 2026-09-15: 두 benchmark의 식별자 충돌을 확인해 모든 테이블과 JOIN에
  `dataset`을 포함하기로 결정했다.
- 2026-09-15: 실제 simulator가 없으므로 이번 mock은 입력 count·관계 검증만
  반환하고 예측 지표는 만들지 않기로 결정했다.
- 2026-09-15: 표준 라이브러리 변환기, 원자적 DB 교체, 11개 catalog와
  `initial_wip` KPI, 입력 검증 mock, Fake Runner 전환을 완료했다. 기존
  `seed_sample_db.py`와 로컬 `data/sample.sqlite`는 제거했고 Result Store와
  visualization 산출물은 유지했다.
- 2026-09-15: 실제 DB를 연속 두 번 생성한 결과 모든 기준 row count가 일치했고,
  다섯 JOIN의 unmatched가 모두 0이었다. catalog 컬럼·SQLite affinity와 인덱스도
  자동 테스트로 확인했다.
- 2026-09-15: `python -m pytest -q` 결과 189 passed, 5 deselected다. deselected
  항목은 실 provider 인증이 필요한 E2E이며 mock 관통 검증과 무관하다.
- 2026-09-15: 후속 작업으로 SMT2020 집계 recipe 2개와 HVLM/LVHM 입력 검증
  scenario를 추가했다. scenario는 원본을 변경하는 합성 시드가 아니라 고정 row
  count와 관계 검사를 보존하는 QA 계약으로 정의했다.
