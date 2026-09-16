# 도메인 지식 Phase 1 실행 계획 (백엔드)

**상태: 완료 (2026-09-14).** Task 0~10 전부 실행하고 E2E 통과. 상위 요구사항은 [도메인 지식 통합 계획](../../plan/260914-domain-knowledge-plan.md), 작성 기준은 [도메인 지식 관리 지침](../docs/domain-knowledge-management.md)을 따른다. 이 문서는 Phase 1 실행 이력이다.

## 실행 세션 시작 방법

```bash
cd backend
claude --model sonnet
```

첫 프롬프트:

```
backend/plan/260914-domain-knowledge-plan.md 를 읽고 Task 0부터 순서대로 진행해.
각 Task 는 테스트를 먼저 쓰고, 완료 시 "검증" 절의 명령을 실행해 결과를 보여줘.
설계 판단이 필요하면 상위 계획과 backend/docs/domain-knowledge-management.md를 따르고,
거기에도 없으면 멈추고 질문해.
```

- Haiku는 다중 파일 작업에 부족하다. Sonnet 5를 쓴다.
- `.env`의 `AGENT_MODEL`은 개발 중 저렴한 모델(예: `claude-haiku-4-5-20251001`)로 둔다. Task 9 E2E는 에이전트를 실제로 호출하므로 비용이 든다. 최종 검증 때만 상위 모델로 바꾼다.
- `PLANNING_AGENT_FAKE=1`은 Task 8까지 그대로 동작해야 한다.

## 실행 규칙

1. **Task 순서를 바꾸지 않는다.** 뒤 Task가 앞 Task의 산출물을 쓴다.
2. **각 Task는 테스트 먼저.** 테스트 파일을 만들고 실패를 확인한 뒤 구현한다.
3. **설계 문서와 어긋나는 결정을 내리지 않는다.** 필요하면 멈추고 사용자에게 묻는다. 결정된 내용은 이 문서 끝 "결정 기록"에 적는다.
4. **부록의 내용을 창작하지 않고 그대로 쓴다.** 테이블 정의, 시나리오, Skill 본문, CLAUDE.md는 부록에 완성본이 있다.
5. **새 패키지는 `PyYAML` 하나만 추가한다.** sqlglot, sqlalchemy 등은 도입하지 않는다 (폐쇄망, [CLOSED_NETWORK_SETUP.md](../docs/CLOSED_NETWORK_SETUP.md)).
6. 신규 환경변수는 [core/config.py](../core/config.py)에 상수로만 추가하고 서비스에서 `os.getenv`를 직접 쓰지 않는다. 키 이름은 `.env.example`에도 주석과 함께 추가한다 ([backend/CLAUDE.md](../CLAUDE.md) 설정 규칙).
7. Task 하나가 끝날 때마다 `pytest`가 전부 통과해야 다음으로 간다.
8. 커밋은 Task 단위로 한다. 메시지: `knowledge: Task N <제목>`.
9. [backend/CLAUDE.md](../CLAUDE.md)의 개발 지침을 따른다. 그 문서가 가리키는 코드가 이 계획으로 바뀌면(예: `simulation_registry.py`의 dict) 해당 Task에서 CLAUDE.md 문장도 같이 고친다.

## Task 목록

### Task 0. `Skill` 도구 노출 확인 (spike, 코드 유지 안 함)

**목적**: [agent.py](../agent/agent.py)는 `system_prompt`를 문자열로 준다. 이 경우 Claude Code preset이 대체돼 `Skill` 도구가 안 붙을 수 있다 (설계 §9). 이후 Task 7이 Skill에 의존하므로 먼저 확인한다.

**파일**: `scripts/spike_skill_tool.py` (확인 후 삭제)

**스펙**:

- `_build_options`와 같은 옵션에 `allowed_tools=TOOL_NAMES + ["Skill"]`로 `query(prompt="사용 가능한 skill 이름만 나열해", options=...)`를 실행한다.
- 첫 `SystemMessage`(subtype `init`)의 `data["tools"]`에 `Skill`이 있는지, 응답 텍스트에 `sql-analysis`가 언급되는지 출력한다.
- 없으면 `system_prompt={"type": "preset", "preset": "claude_code", "append": SYSTEM_PROMPT}`로 바꿔 한 번 더 실행한다.

**검증**: 스크립트 실행 출력을 "결정 기록"에 붙여 넣는다. 어느 방식이 됐는지가 Task 7의 `agent.py` 수정 내용을 정한다.

**완료 기준**: 결정 기록에 "문자열 system_prompt로 Skill 노출됨" 또는 "preset+append로 전환"이 적혀 있다. 스크립트는 삭제한다.

### Task 1. 지식 pydantic 모델 + 로더

**파일**: `services/knowledge_service.py`, `tests/test_knowledge.py`, `requirements.txt`(`PyYAML==6.0.2` 추가), `core/config.py`(`KNOWLEDGE_DIR` 상수, 기본 `backend/knowledge`), `.env.example`(`KNOWLEDGE_DIR` 키)

**스펙**:

```python
class KnowledgeMeta(BaseModel):
    status: Literal["draft", "verified"] = "draft"
    owner: str = ""
    updated: date | None = None
    source: str = ""

class Column(BaseModel):
    name: str; type: str; desc: str = ""
    ref: str | None = None            # "TABLE.column"
    codes: dict[str, str] | None = None

class Join(BaseModel):
    to: str; on: str | list[str]; kind: str = "many-to-one"; note: str = ""

class KnowledgeTable(KnowledgeMeta):
    table: str; description: str
    grain: list[str]; time_column: str | None = None
    tags: list[str] = []
    columns: list[Column]; joins: list[Join] = []
    caveats: list[str] = []; sample_sql: str = ""

class Diagnostic(BaseModel):
    hypothesis: str; how: Literal["sql", "simulation"]; ref: str

class KnowledgeKpi(KnowledgeMeta):
    kpi_id: str; name: str; aliases: list[str] = []
    definition: str; formula: str
    sources: list[str]; grain: list[str]
    baseline: str; shortfall_rule: str
    sql_template: str
    diagnostics: list[Diagnostic] = []

class SimulationParam(BaseModel):
    required: bool; description: str; example: str | None = None

class KnowledgeSimulation(KnowledgeMeta):
    type: str; name: str; aliases: list[str] = []
    when_to_use: str
    params: dict[str, SimulationParam] = {}
    output_schema: dict[str, Any] = {}
    follows: list[str] = []

class GlossaryEntry(KnowledgeMeta):
    term: str; definition: str; aliases: list[str] = []
    related_kpis: list[str] = []; related_tables: list[str] = []
```

`KnowledgeStore`:

- `KnowledgeStore.load(root: Path) -> KnowledgeStore` — `catalog/tables/*.yaml`, `kpi/*.yaml`, `simulations/*.yaml`, `glossary.yaml`(list) 을 읽어 검증. 잘못된 파일은 파일명을 포함한 `ValueError`.
- `list_tables(keyword: str | None = None, tag: str | None = None) -> list[dict]` — `{table, description, grain, tags, verified}`. keyword는 table·description·tags·column name에 대소문자 무시 부분일치.
- `describe_table(table: str) -> dict` — 모델 전체 + `verified`. 없으면 `{"status": "error", "message": "알 수 없는 테이블입니다: X. list_tables 로 확인하세요."}`.
- `list_kpis(keyword=None) -> list[dict]` — `{kpi_id, name, aliases, verified}`. keyword는 name·aliases·definition 부분일치.
- `get_kpi(kpi_id) -> dict` — 전체 + `verified`. 없으면 위와 같은 형식의 error.
- `list_simulations() -> list[dict]`, `get_simulation(type)`.
- `table_names() -> set[str]` — Task 4 가드레일용.
- `verified`는 `status == "verified"`.
- 모듈 레벨 `get_store()` — 최초 호출 시 `KNOWLEDGE_DIR`에서 로드해 캐시. 테스트에서는 `KnowledgeStore.load(tmp_path)`를 직접 쓴다.

**검증**:

```bash
pytest tests/test_knowledge.py -v
```

테스트 항목: 정상 로드, 필수 필드 누락 시 파일명 포함 오류, `list_tables(keyword="입고")` 필터, 미존재 id 오류 형식, `verified` 계산.

**완료 기준**: 위 테스트 통과. `tmp_path`에 최소 YAML을 써서 테스트하며 아직 `knowledge/` 디렉터리는 없어도 된다.

### Task 2. 수직 슬라이스 YAML

**파일**: `knowledge/glossary.yaml`, `knowledge/catalog/tables/{LINE_MASTER,PRODUCT_MASTER,PRODUCTION_PLAN,FGS_INBOUND_RESULT,MATERIAL_SHORTAGE,MP_VERSION}.yaml`, `knowledge/catalog/joins.yaml`, `knowledge/kpi/fgs_inbound.yaml`, `tests/test_knowledge_integrity.py`

**스펙**: 부록 A, B, C의 내용을 그대로 파일로 만든다. 전부 `status: draft`, `source: "설계 문서 자리표시자. 현업 확인 필요"`.

정합성 테스트(`tests/test_knowledge_integrity.py`, 실제 `knowledge/` 디렉터리 대상):

- 모든 YAML이 로드된다.
- 모든 `Column.ref`가 `TABLE.column` 형태이고 대상이 존재한다.
- 모든 `Join.to`가 존재하는 테이블이다.
- 모든 KPI `sources`가 존재하는 테이블이다.
- KPI `sql_template`에 등장하는 `FROM|JOIN <이름>`이 전부 `sources`에 있다.
- `Diagnostic.ref`가 `how=simulation`이면 시뮬레이션 type, `how=sql`이면 테이블명 또는 `recipes/` 경로다. (Task 6 전까지 시뮬레이션 type 검사는 `knowledge/simulations/`가 비어 있으면 skip)

**검증**:

```bash
pytest tests/test_knowledge.py tests/test_knowledge_integrity.py -v
```

**완료 기준**: 통과. `python -c "from services.knowledge_service import get_store; print(len(get_store().list_tables()))"`가 `6`.

### Task 3. 시드 스크립트 + 시나리오

**파일**: `scripts/seed_sample_db.py`, `scripts/__init__.py`, `knowledge/scenarios/fgs_line_b_material_shortage.yaml`, `tests/test_scenarios.py`, `.gitignore`에 `data/` 추가, `core/config.py`에 `SAMPLE_DB_PATH`(기본 `backend/data/sample.sqlite`), `.env.example`(`SAMPLE_DB_PATH` 키)

**스펙**:

시나리오 모델(`knowledge_service.py`에 추가):

```python
class Scenario(BaseModel):
    name: str; description: str
    period: tuple[date, date]
    line_cd: str; product_id: str
    drop_ratio: float
    cause: Literal["material_shortage", "plan_change", "production_shortfall"]
    unchanged: list[str] = []
    expected_diagnosis: str
```

`seed_sample_db.py`:

1. `KnowledgeStore.load()`로 테이블 정의를 읽고, `Column.type`을 SQLite 타입으로 매핑(`date→TEXT(ISO)`, `varchar→TEXT`, `number→REAL`, `int→INTEGER`)해 `CREATE TABLE`.
2. `random.seed(20260914)`, 기간 `2026-06-01`~`2026-09-30`.
3. 마스터: 라인 `A,B,C,D` (line_nm "1라인".."4라인"), 품목 `P-1001`~`P-1008` (product_nm "품목1".."품목8", 기준 일일 계획량 200~600 사이 고정값).
4. `PRODUCTION_PLAN`: 일별 × 라인 × 품목 중 라인당 품목 2개씩만 배정(A: 1001,1002 / B: 1002,1003 / C: 1004,1005 / D: 1006,1007,1008). 주말 제외. `plan_qty = 기준량 × U(0.9, 1.1)` 정수.
5. `FGS_INBOUND_RESULT`: 같은 키로 `inbound_qty = plan_qty × N(0.97, 0.05)` 정수, `status_cd`는 97% `C`, 2% `P`, 1% `X`.
6. `MP_VERSION`: 월별 1행, `version = "MP-{yyyyMM}-FIXED"`, `fixed_at = 전월 25일`, `changed = 0`.
7. `MATERIAL_SHORTAGE`: 기본 비어 있음.
8. 시나리오 적용(`knowledge/scenarios/*.yaml` 전부): `period`·`line_cd`·`product_id`에 해당하는 `FGS_INBOUND_RESULT.inbound_qty *= (1 - drop_ratio)`. `cause == material_shortage`이면 같은 기간·품목에 `MATERIAL_SHORTAGE` 행 삽입(`material_cd = "M-{product_id}"`, `short_qty = 계획량 - 실적량`, `reason_cd = "SUPPLIER_DELAY"`). `unchanged`에 있는 테이블은 건드리지 않는다.
9. `SAMPLE_DB_PATH` 부모 디렉터리 생성 후 저장. 기존 파일은 덮어쓴다.
10. `if __name__ == "__main__": main()`; `main(db_path: Path | None = None)`을 테스트에서 호출 가능하게.

`tests/test_scenarios.py`:

- `tmp_path`에 시드 후, 각 시나리오에 대해 KPI `sql_template`의 `:from`/`:to`를 시나리오 기간으로 치환해 실행 → 해당 `line_cd`의 `SUM(actual)/SUM(plan) < 0.9`.
- 시나리오 기간 밖(예: 2026-07 전체) 같은 라인 달성률 `≥ 0.9`.
- `MATERIAL_SHORTAGE`에 시나리오 기간 행이 존재하고, `MP_VERSION.changed`가 전부 0.
- 두 번 시드해도 같은 결과(결정성): 특정 셀 값 비교.

**검증**:

```bash
python -m scripts.seed_sample_db && pytest tests/test_scenarios.py -v
sqlite3 data/sample.sqlite "SELECT COUNT(*) FROM FGS_INBOUND_RESULT"
```

**완료 기준**: 통과. `data/sample.sqlite`가 git status에 나타나지 않는다.

### Task 4. `execute_sql` 서비스 + 가드레일

**파일**: `services/sql_guard.py`, `services/mock/mock_sql_service.py`(전면 교체), `services/real/sql_service.py`(시그니처만 교체), `tools/sql_tool.py`, `tests/test_sql_guard.py`, `tests/test_services.py`(기존 `query_database` 테스트 → `execute_sql`)

**스펙**:

`sql_guard.py`:

```python
MAX_ROWS = 500
class SqlGuardError(ValueError): ...
def check_sql(sql: str, allowed_tables: set[str]) -> str:
    """검사 통과 시 LIMIT 가 보장된 SQL 을 돌려준다."""
```

- 앞뒤 공백·세미콜론 제거 후 첫 토큰이 `SELECT` 또는 `WITH`가 아니면 거부. 세미콜론이 중간에 있으면 거부(다중 문장).
- `INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|PRAGMA` 단어가 있으면 거부(대소문자 무시, 단어 경계).
- `re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql, re.I)`로 테이블명을 뽑아 `allowed_tables`(대소문자 무시)에 없으면 `SqlGuardError("등록되지 않은 테이블입니다: X. list_tables 로 확인하세요.")`. 서브쿼리 `FROM (`는 정규식이 잡지 않으므로 통과한다(허용).
- `LIMIT`가 없으면 `LIMIT {MAX_ROWS + 1}`을 붙인다. 있으면 그대로.

`mock_sql_service.py`:

```python
async def execute_sql(sql: str, purpose: str) -> dict
```

- `check_sql(sql, get_store().table_names())` → `SqlGuardError`면 `{"status": "error", "kind": "database", "message": str(e), "sql": sql}`.
- `sqlite3.connect(SAMPLE_DB_PATH)`(없으면 `{"status":"error","message":"sample DB 가 없습니다. python -m scripts.seed_sample_db 를 실행하세요."}`), `row_factory = sqlite3.Row`.
- 결과 `MAX_ROWS`개까지만 담고 초과면 `truncated: True`.
- 반환: `{"status": "ok", "kind": "database", "sql": sql, "purpose": purpose, "table": {"columns": [...], "rows": [[...], ...]}, "row_count": n, "truncated": bool}`. `rows`는 리스트의 리스트다. 이 내용은 실행 당시 계약이며 현재 Result Store 계약은 상위 계획을 따른다.
- SQLite 오류는 `{"status":"error", "kind":"database", "message": f"SQL 실행 오류: {e}", "sql": sql}`.
- `purpose`는 `logging.getLogger(__name__).info("execute_sql purpose=%s", purpose)`.

`real/sql_service.py`: `async def execute_sql(sql, purpose)` → `NotImplementedError`, docstring에 "pntfp DB 연결 후 동일 가드레일 적용".

`tools/sql_tool.py`: `query_database` 삭제, `execute_sql(sql, purpose)` 추가. docstring에 "SELECT 전용, 카탈로그 등록 테이블만, 최대 500행".

**검증**:

```bash
pytest tests/test_sql_guard.py tests/test_services.py -v
```

테스트 항목: DELETE 거부, 다중 문장 거부, 미등록 테이블 메시지에 `list_tables` 포함, LIMIT 자동 부착, 정상 조회 형태, 501행 이상 `truncated`, DB 파일 없을 때 메시지.

**완료 기준**: 통과. `grep -rn query_database` 결과가 `agent/fake_runner.py`, `agent/sdk_tools.py`, `tests/test_tools.py`, `tests/test_api.py`에만 남는다 (Task 5·8에서 정리).

### Task 5. 지식 tool 4개 SDK 등록 + `execute_sql` 등록

**파일**: `tools/knowledge_tool.py`, `agent/sdk_tools.py`, `tests/test_tools.py`

**스펙**:

`tools/knowledge_tool.py` — 각각 `async def`, `get_store()` 호출 결과를 감싼다:

```python
async def list_tables(keyword: str | None = None, tag: str | None = None) -> dict:
    return {"status": "ok", "kind": "catalog", "catalog_type": "table_list", "data": store.list_tables(keyword, tag)}
async def describe_table(table: str) -> dict:
    # error dict 면 그대로 반환, 아니면 {"status":"ok","kind":"catalog","catalog_type":"table","verified":...,"data": {...}}
async def list_kpis(keyword: str | None = None) -> dict   # catalog_type "kpi_list"
async def get_kpi(kpi_id: str) -> dict                     # catalog_type "kpi"
```

`agent/sdk_tools.py`:

- `@tool` 4개 추가. 입력 스키마: `list_tables`의 `keyword`·`tag`와 `list_kpis`의
  `keyword`는 `NotRequired` TypedDict, `describe_table {"table": str}`,
  `get_kpi {"kpi_id": str}`. 선택 인자는 `args.get(...)`으로 읽는다. dict 스키마는
  SDK가 모든 키를 필수로 변환하므로 선택 인자에 사용하지 않는다(2026-09-16 수정).
- `query_database` @tool 삭제, `execute_sql` @tool 추가: 스키마 `{"sql": str, "purpose": str}`, 설명 "카탈로그에 등록된 테이블을 SELECT 로 조회한다. 테이블·컬럼은 describe_table 로 먼저 확인한다. purpose 에는 이 쿼리로 확인하려는 것을 한 줄로 쓴다."
- `TOOL_NAMES` 순서: `execute_sql, search_knowledge, list_simulation, run_simulation, list_tables, describe_table, list_kpis, get_kpi`.
- `build_planning_mcp_server`의 `tools=` 목록 갱신.

**검증**:

```bash
pytest tests/test_tools.py -v
python -c "from agent.sdk_tools import TOOL_NAMES; print(len(TOOL_NAMES))"   # 8
```

테스트 항목: 8개 tool 전부 async, 각 지식 tool 결과에 `kind == "catalog"`와 `catalog_type` (`"knowledge"`는 프론트가 RAG 결과에 이미 쓰므로 금지), `describe_table("없는것")`이 error, `execute_sql` 정상 호출(Task 3 시드 필요 → 테스트 fixture에서 `tmp_path` 시드 후 `SAMPLE_DB_PATH` monkeypatch).

**완료 기준**: 통과. `agent/event_adapter.py`는 수정하지 않는다 (`_coerce_tool_result`가 JSON 문자열을 dict로 복원하므로 `kind` 필드는 그대로 프론트에 간다).

### Task 6. 시뮬레이션 registry → YAML

**파일**: `knowledge/simulations/{실적_조회,MP_최신조회,MP_확정조회,SWAP_결과조회}.yaml`, `services/simulation_registry.py`, `services/mock/mock_simulation_service.py`, `tests/test_services.py`, `CLAUDE.md`(아키텍처 절의 `SIMULATION_TYPES`/`PARAM_SCHEMA` 문장을 "`knowledge/simulations/*.yaml`에 정의, `simulation_registry.py`가 로드"로 수정)

**스펙**:

- 부록 D의 YAML 4개 생성.
- `simulation_registry.py`: `SIMULATION_TYPES`·`PARAM_SCHEMA` dict 삭제. `list_simulation_types()`는 `get_store().list_simulations()`를 반환하되 각 항목이 `{type, name, aliases, when_to_use, params: {name: {required, description, example}}, output_schema, follows, verified}`. `validate_simulation_request(simulation_type, params)`는 시그니처·반환 메시지 그대로 유지하고 `params[name].required`로 검사.
- `mock_simulation_service.py`:
  - `실적_조회`: SQLite에서 `SELECT line_cd AS line, substr(work_date,1,4)||substr(work_date,6,2) AS workMonth, SUM(inbound_qty) AS qty FROM FGS_INBOUND_RESULT WHERE status_cd <> 'X' AND substr(work_date,1,4)||substr(work_date,6,2) BETWEEN :from AND :to GROUP BY 1,2` → `results`.
  - `MP_확정조회`: `MP_VERSION`에서 `fixedPlanMonth`(없으면 `202609`) 행 → `{mpVersion, fixedAt, changed}`.
  - `MP_최신조회`, `SWAP_결과조회`: 기존 하드코딩 유지.
  - DB 접근은 `mock_sql_service`의 연결 helper를 재사용(`_connect()` 하나를 `services/mock/_sqlite.py`로 빼도 된다).
- `tests/test_services.py`: `list_simulation` 항목에 `params.workMonthFrom.description`이 있음, `실적_조회` 결과가 시드 데이터와 일치(시나리오 기간 B라인 qty가 7월보다 작음), `validate_simulation_request` 기존 케이스 유지.

**검증**:

```bash
pytest tests/test_services.py tests/test_knowledge_integrity.py -v
```

Task 2의 integrity 테스트가 이제 `Diagnostic.ref → 시뮬레이션 type`을 실제로 검사한다.

**완료 기준**: 통과. `simulation_registry.py`에 dict 리터럴 데이터가 남아 있지 않다.

### Task 7. 프롬프트 계층 재작성

**파일**: `agent/system_prompt.py`, `agent/agent.py`, `agent/agent_sdk/CLAUDE.md`, `agent/agent_sdk/.claude/skills/{sql-analysis,simulation,kpi-shortfall-analysis}/SKILL.md`, `agent/agent_sdk/.claude/skills/production-planning/` 삭제, `tests/test_prompt_consistency.py`

**스펙**:

- `system_prompt.py`: 부록 E. 30줄 이내, 도구 이름을 나열하지 않는다.
- `agent.py`: `allowed_tools=TOOL_NAMES + ["Skill"]`. Task 0 결과가 "preset+append"면 `system_prompt={"type": "preset", "preset": "claude_code", "append": SYSTEM_PROMPT}`.
- `CLAUDE.md`: 부록 F.
- 세 SKILL.md: 부록 G. `description` 첫 구절은 반드시 `생산계획 Agent 전용.`.
- `production-planning/` 디렉터리 삭제.

`tests/test_prompt_consistency.py`:

- `SYSTEM_PROMPT.strip().count("\n") < 30`, 그리고 `TOOL_NAMES`의 어떤 짧은 이름(`execute_sql` 등)도 SYSTEM_PROMPT에 없다.
- CLAUDE.md 도구 표의 백틱 이름 집합 == `TOOL_NAMES`의 짧은 이름 집합.
- 각 SKILL.md에 `get_store().table_names()`의 테이블명이 등장하지 않는다 (절차만, 스키마 복사 금지).
- 각 SKILL.md `description`이 `생산계획 Agent 전용.`으로 시작.
- CLAUDE.md의 Skills 절에 나열된 skill 이름이 실제 디렉터리와 일치.

**검증**:

```bash
pytest tests/test_prompt_consistency.py -v
```

**완료 기준**: 통과. `grep -rn simulate_ agent/` 결과 없음.

### Task 8. `fake_runner` 갱신

**파일**: `agent/fake_runner.py`, `tests/test_api.py`

**스펙**: 이벤트 순서를 `status(plan)` → `tool_call/tool_result get_kpi("fgs_inbound")` → `tool_call/tool_result execute_sql(KPI sql_template를 2026-09-01~09-30로 치환, purpose="계획 대비 입고 달성률")` → `tool_call/tool_result run_simulation("MP_확정조회", {})` → `text` 청크 3개 → `done`. `test_api.py`에서 `tool_name` 순서와 `tool_result.data.kind`가 `catalog`, `database` 순으로 나오는지 확인. 기존 SSE 계약 테스트는 그대로 통과.

**검증**:

```bash
PLANNING_AGENT_FAKE=1 pytest tests/test_api.py -v
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000 &  # 프론트에서 확인 가능
```

**완료 기준**: 통과. 프론트 3-pane 화면에서 기존처럼 이벤트가 렌더링된다(`catalog` kind는 아직 일반 JSON으로 보여도 된다).

### Task 9. E2E 시나리오 테스트

**파일**: `tests/test_e2e_scenario.py`, `pytest.ini`(`markers = e2e`)

**스펙**:

- `@pytest.mark.e2e`. `ANTHROPIC_API_KEY`도 `OPENROUTER_API_KEY`도 없으면 `pytest.skip`.
- 시드 후 `run_agent("FGS 입고 실적이 부진한 원인을 찾아줘. 기간은 2026년 9월.")`를 실행해 이벤트를 모은다.
- 단언: (a) `tool_call` 이름 순서에 `get_kpi`가 `execute_sql`보다 먼저 나온다. (b) `execute_sql`이 2회 이상. (c) 마지막 `text`들을 이어붙인 문자열에 시나리오 `expected_diagnosis`("자재 부족")가 포함된다. (d) `error` 이벤트 없음.
- 실패 시 tool 순서와 최종 텍스트를 `print`해 어느 채널의 지식이 부족했는지 판단할 수 있게 한다.

**검증**:

```bash
python -m scripts.seed_sample_db && pytest -m e2e -s tests/test_e2e_scenario.py
```

**완료 기준**: 통과. 실패하면 **코드가 아니라 지식(Skill 본문·KPI diagnostics·CLAUDE.md 인덱스)을 고쳐서** 통과시킨다. 무엇을 고쳤는지 결정 기록에 적는다. 3회 수정 후에도 실패하면 멈추고 보고한다.

### Task 10. 지식 읽기 API

**파일**: `api/routes_knowledge.py`, `main.py`, `tests/test_api.py`

**스펙**:

- `GET /api/knowledge/skills` → `[{name, description, status}]`. `agent/agent_sdk/.claude/skills/*/SKILL.md` frontmatter 파싱. `status`는 `"active"`.
- `GET /api/knowledge/catalog` → `get_store().list_tables()`.
- `GET /api/knowledge/kpis` → `get_store().list_kpis()`.
- `main.py`에 `include_router(knowledge_router, prefix="/api")`.

**검증**:

```bash
pytest tests/test_api.py -v
curl -s localhost:8000/api/knowledge/skills | python -m json.tool
```

**완료 기준**: 세 엔드포인트가 200과 상위 계획의 계약 형태를 반환. 이 시점에 프론트 작업([frontend 계획](../../frontend/plan/260914-domain-knowledge-plan.md))을 시작할 수 있다.

## 최종 검증

```bash
cd backend
python -m scripts.seed_sample_db
pytest -v                      # e2e 제외 전부 통과
pytest -m e2e -s               # 키가 있을 때
git status                     # data/ 가 보이지 않음
```

## Phase 1 이후 확장: 재사용 CTE("레시피") 지식 종류 (2026-09-14)

Phase 1 완료 후 별도 요청으로 추가한 지식 종류. 자세한 설계 배경과 결정 사항은
`/home/bsy/.claude/plans/with-serialized-truffle.md` 참고(세션 로컬 계획 파일).

- `knowledge/recipes/*.yaml` — `KnowledgeRecipe`(재사용 가능 CTE) 신규 지식 종류.
  당시 설계가 `recipes/<slug>.md`로 두었으나 미구현 상태였던
  것을 순수 YAML로 구현해 대체했다 (다른 지식 종류와 동일한 저장 패턴 유지).
- 실행 연결은 자동 치환이 아니라 **에이전트가 `cte_sql`을 읽어 직접 `WITH` 절로
  조합**하는 방식 — `sql_guard.py`는 변경하지 않았다(이미 즉석 CTE를 허용).
- `TOOL_NAMES` 8개 → 10개 (`list_recipes`, `get_recipe` 추가).
- 시드 예시 `plan_vs_actual` 1개 — `fgs_inbound` KPI의 조인 로직을 추출.
- 부수 수정: `test_diagnostics_refs_resolve`가 `.md` 확장자·파일시스템 직접
  탐색을 가정하던 버그를 `store.recipes` 조회로 수정. `test_kpi_sql_template_
  tables_are_declared_sources`와 신규 레시피 테스트가 테이블 추출 정규식을
  `_referenced_tables()` 헬퍼로 공유하도록 정리.
- 검증: `pytest -q` 109 passed (5 e2e deselected). 실제 시드 SQLite에서
  `cte_sql`과 샘플 쿼리 2개 모두 수동 실행 확인(B라인 자재 결품 구간 정상 검출).

---

## 부록 A. 테이블 정의 (Task 2)

각 파일 공통 꼬리:

```yaml
status: draft
owner: ""
updated: 2026-09-14
source: "설계 문서 자리표시자. 현업 확인 필요"
```

`LINE_MASTER.yaml`

```yaml
table: LINE_MASTER
description: 생산 라인 마스터
grain: [line_cd]
tags: [마스터, 라인]
columns:
  - {name: line_cd, type: varchar, desc: 라인 코드 (A~D)}
  - {name: line_nm, type: varchar, desc: 라인명}
  - {name: plant_cd, type: varchar, desc: 공장 코드}
joins: []
caveats: []
sample_sql: SELECT line_cd, line_nm FROM LINE_MASTER
```

`PRODUCT_MASTER.yaml`

```yaml
table: PRODUCT_MASTER
description: 완제품 품목 마스터
grain: [product_id]
tags: [마스터, 품목]
columns:
  - {name: product_id, type: varchar, desc: 품목 ID (P-1001 형식)}
  - {name: product_nm, type: varchar, desc: 품목명}
  - {name: base_daily_qty, type: int, desc: 기준 일일 계획량}
joins: []
caveats: []
sample_sql: SELECT product_id, product_nm FROM PRODUCT_MASTER
```

`PRODUCTION_PLAN.yaml`

```yaml
table: PRODUCTION_PLAN
description: 일별 라인·품목 생산 계획 수량 (확정 MP 기준)
grain: [work_date, line_cd, product_id]
time_column: work_date
tags: [계획, MP]
columns:
  - {name: work_date, type: date, desc: 작업일 (YYYY-MM-DD)}
  - {name: line_cd, type: varchar, desc: 라인 코드, ref: LINE_MASTER.line_cd}
  - {name: product_id, type: varchar, desc: 품목 ID, ref: PRODUCT_MASTER.product_id}
  - {name: plan_qty, type: int, desc: 계획 수량}
  - {name: mp_version, type: varchar, desc: 계획을 낸 MP 버전, ref: MP_VERSION.version}
joins:
  - {to: FGS_INBOUND_RESULT, on: [work_date, line_cd, product_id], kind: one-to-one, note: 계획 대비 실적 비교}
  - {to: LINE_MASTER, on: line_cd, kind: many-to-one}
caveats:
  - 주말은 계획이 없다
sample_sql: SELECT work_date, line_cd, SUM(plan_qty) FROM PRODUCTION_PLAN GROUP BY 1,2
```

`FGS_INBOUND_RESULT.yaml`

```yaml
table: FGS_INBOUND_RESULT
description: FGS(완제품 창고) 일별 입고 실적
grain: [work_date, line_cd, product_id]
time_column: work_date
tags: [실적, 입고, FGS]
columns:
  - {name: work_date, type: date, desc: 작업일 (YYYY-MM-DD)}
  - {name: line_cd, type: varchar, desc: 라인 코드, ref: LINE_MASTER.line_cd}
  - {name: product_id, type: varchar, desc: 품목 ID, ref: PRODUCT_MASTER.product_id}
  - {name: inbound_qty, type: int, desc: 입고 수량}
  - {name: status_cd, type: varchar, desc: 입고 상태, codes: {C: 완료, P: 대기, X: 취소}}
joins:
  - {to: PRODUCTION_PLAN, on: [work_date, line_cd, product_id], kind: one-to-one, note: 계획 대비 비교}
  - {to: LINE_MASTER, on: line_cd, kind: many-to-one}
  - {to: PRODUCT_MASTER, on: product_id, kind: many-to-one}
caveats:
  - status_cd = 'X' 는 실적에서 제외한다
  - work_date 는 계획월이 아니라 실제 작업일이다
sample_sql: |
  SELECT work_date, line_cd, SUM(inbound_qty) AS qty
  FROM FGS_INBOUND_RESULT WHERE status_cd <> 'X' GROUP BY 1,2
```

`MATERIAL_SHORTAGE.yaml`

```yaml
table: MATERIAL_SHORTAGE
description: 자재 결품 기록. 결품이 발생한 날·품목만 행이 있다
grain: [work_date, product_id, material_cd]
time_column: work_date
tags: [자재, 결품, 원인]
columns:
  - {name: work_date, type: date, desc: 결품 발생일}
  - {name: product_id, type: varchar, desc: 영향 받은 완제품 품목, ref: PRODUCT_MASTER.product_id}
  - {name: material_cd, type: varchar, desc: 자재 코드}
  - {name: short_qty, type: int, desc: 부족 수량}
  - {name: reason_cd, type: varchar, desc: 결품 사유, codes: {SUPPLIER_DELAY: 협력사 납기 지연, QUALITY_HOLD: 품질 보류, PLAN_MISS: 소요량 계획 누락}}
joins:
  - {to: PRODUCT_MASTER, on: product_id, kind: many-to-one}
caveats:
  - 행이 없으면 결품이 없었다는 뜻이다. LEFT JOIN 으로 확인한다
sample_sql: SELECT work_date, product_id, SUM(short_qty) FROM MATERIAL_SHORTAGE GROUP BY 1,2
```

`MP_VERSION.yaml`

```yaml
table: MP_VERSION
description: 월별 확정 MP(Master Plan) 버전과 변경 여부
grain: [plan_month]
time_column: plan_month
tags: [MP, 계획, 버전]
columns:
  - {name: plan_month, type: varchar, desc: 계획월 (yyyyMM)}
  - {name: version, type: varchar, desc: 확정 MP 버전}
  - {name: fixed_at, type: date, desc: 확정일}
  - {name: changed, type: int, desc: "확정 후 변경 여부 (0: 없음, 1: 있음)"}
joins: []
caveats:
  - changed = 1 이면 PRODUCTION_PLAN 과 실제 운영 계획이 다를 수 있다
sample_sql: SELECT plan_month, version, changed FROM MP_VERSION
```

`joins.yaml`

```yaml
- name: 계획 대비 실적
  from: PRODUCTION_PLAN
  to: FGS_INBOUND_RESULT
  on: [work_date, line_cd, product_id]
  note: 실적은 status_cd <> 'X' 로 필터
- name: 실적에 결품 붙이기
  from: FGS_INBOUND_RESULT
  to: MATERIAL_SHORTAGE
  on: [work_date, product_id]
  kind: left
  note: 결품 행이 없는 날은 NULL
```

## 부록 B. 용어집 (Task 2)

`glossary.yaml`

```yaml
- term: FGS
  definition: Finished Goods Store. 완제품 창고. 생산이 끝난 제품이 입고되는 곳
  aliases: [완제품 창고]
  related_kpis: [fgs_inbound]
  related_tables: [FGS_INBOUND_RESULT]
  status: draft
- term: 입고 실적
  definition: 기간 내 FGS 에 입고 완료(status_cd = C)된 수량
  aliases: [입고량, 입고 수량]
  related_kpis: [fgs_inbound]
  related_tables: [FGS_INBOUND_RESULT]
  status: draft
- term: MP
  definition: Master Plan. 월 단위 확정 생산계획. 확정 후 변경되면 MP_VERSION.changed = 1
  aliases: [마스터플랜, 확정 MP]
  related_kpis: []
  related_tables: [MP_VERSION, PRODUCTION_PLAN]
  status: draft
- term: 부진
  definition: 계획 대비 달성률이 shortfall_rule 기준 미만인 상태
  aliases: [미달, 실적 저조]
  related_kpis: [fgs_inbound]
  related_tables: []
  status: draft
```

## 부록 C. KPI 정의 (Task 2)

`kpi/fgs_inbound.yaml`

```yaml
kpi_id: fgs_inbound
name: FGS 입고 실적
aliases: [입고 실적, FGS 입고량, 완제품 입고, 입고 달성률]
definition: 기간 내 FGS 창고에 입고 완료된 수량. 계획 수량 대비 달성률로 부진 여부를 판단한다.
formula: SUM(inbound_qty) WHERE status_cd <> 'X'
sources: [FGS_INBOUND_RESULT, PRODUCTION_PLAN]
grain: [work_date, line_cd, product_id]
baseline: PRODUCTION_PLAN.plan_qty
shortfall_rule: 달성률(actual/plan) < 0.9 이면 부진. 3 영업일 연속이면 구조적 부진으로 본다.
sql_template: |
  SELECT r.work_date, r.line_cd,
         SUM(r.inbound_qty) AS actual, SUM(p.plan_qty) AS plan,
         ROUND(1.0 * SUM(r.inbound_qty) / NULLIF(SUM(p.plan_qty), 0), 3) AS rate
  FROM FGS_INBOUND_RESULT r
  JOIN PRODUCTION_PLAN p
    ON p.work_date = r.work_date AND p.line_cd = r.line_cd AND p.product_id = r.product_id
  WHERE r.status_cd <> 'X' AND r.work_date BETWEEN :from AND :to
  GROUP BY r.work_date, r.line_cd
  ORDER BY r.work_date, r.line_cd
diagnostics:
  - {hypothesis: 확정 MP 가 변경돼 계획 자체가 달라짐, how: simulation, ref: MP_확정조회}
  - {hypothesis: 특정 라인·품목에 부진이 집중됨, how: sql, ref: FGS_INBOUND_RESULT}
  - {hypothesis: 자재 결품으로 생산이 막힘, how: sql, ref: MATERIAL_SHORTAGE}
  - {hypothesis: 생산 실적 자체가 부족함, how: simulation, ref: 실적_조회}
status: draft
owner: ""
updated: 2026-09-14
source: "설계 문서 자리표시자. 현업 확인 필요"
```

## 부록 D. 시뮬레이션 정의 (Task 6)

`simulations/실적_조회.yaml`

```yaml
type: 실적_조회
name: 실적조회
aliases: [생산실적 조회, 실적 시뮬레이션]
when_to_use: 월 단위 라인별 생산 실적 합계가 필요할 때. 일별 상세는 execute_sql 로 조회한다.
params:
  workMonthFrom: {required: true, description: "조회 시작 작업 월 (yyyyMM, 포함)", example: "202608"}
  workMonthTo: {required: true, description: "조회 끝 작업 월 (yyyyMM, 포함)", example: "202609"}
output_schema:
  results: {type: array, desc: "[{line, workMonth, qty}]"}
follows: []
status: verified
```

`simulations/MP_최신조회.yaml`

```yaml
type: MP_최신조회
name: 최신 MP 조회
aliases: [최신 MP, MP 버전]
when_to_use: 현재 운영 중인 최신 MP 버전을 알아야 할 때.
params: {}
output_schema:
  mpVersion: {type: string, desc: 최신 MP 버전}
  updatedAt: {type: string, desc: 갱신 시각}
follows: []
status: verified
```

`simulations/MP_확정조회.yaml`

```yaml
type: MP_확정조회
name: 확정 MP 조회
aliases: [확정 MP, 확정된 버전, 확정 MP 버전]
when_to_use: 계획 수량이 확정 후 바뀌었는지 확인할 때. 실적 부진 원인 분석에서 첫 번째로 검증하는 가설.
params:
  fixedPlanMonth: {required: false, description: "확정 MP 조회 연월 (yyyyMM), 누락시 당월", example: "202609"}
output_schema:
  mpVersion: {type: string, desc: 확정 MP 버전}
  fixedAt: {type: string, desc: 확정일}
  changed: {type: int, desc: "확정 후 변경 여부 (0: 없음, 1: 있음)"}
follows: []
status: verified
```

`simulations/SWAP_결과조회.yaml`

```yaml
type: SWAP_결과조회
name: SWAP 결과 조회
aliases: [SWAP 실행 결과, 단품 필요량 계획 및 실적, 계획 및 실적조회]
when_to_use: 특정 품목의 단품 필요량 계획과 실적을 비교할 때.
params:
  productId: {required: true, description: 필요량 품목 ID, example: "P-1002"}
  planYm: {required: false, description: "계획월 (yyyyMM), 누락시 당월", example: "202609"}
output_schema:
  requiredQty: {type: int, desc: 필요량}
  actualQty: {type: int, desc: 실적}
follows: []
status: verified
```

## 부록 E. SYSTEM_PROMPT (Task 7)

```python
SYSTEM_PROMPT = """
당신은 생산계획 분석 업무를 지원하는 AI Agent이다.

역할:
- 사용자 질의를 해석하고 필요한 지식과 데이터를 Tool 로 확보한 뒤 결론을 낸다.
- 추정하지 않는다. 수치는 반드시 Tool 결과에서 가져온다.
- 업무 절차와 Tool 사용 규칙은 CLAUDE.md 와 Skills 를 따른다.

응답 원칙:
- 결론을 먼저, 근거(어떤 Tool 결과의 어떤 값인지)를 다음에 쓴다.
- 미검증(verified=false) 정의로 계산한 수치는 그 사실을 밝힌다.
- 내부 추론 과정은 노출하지 않는다.
- 데이터가 없거나 Tool 이 오류를 내면 그대로 알리고 멈춘다.

금지:
- 데이터를 변경하는 SQL 을 작성하지 않는다.
- 카탈로그에 없는 테이블을 추측해 조회하지 않는다.
"""
```

## 부록 F. CLAUDE.md (Task 7)

```markdown
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

- SQL 을 작성하기 전에 `describe_table` 로 컬럼과 주의사항(caveats)을 확인한다.
- `execute_sql` 결과의 `truncated` 가 true 면 집계나 조건을 좁혀 다시 조회한다.

## 결과 검증 원칙

- Tool 결과의 `status` 를 확인하고, 오류면 사용자에게 알린다.
- 수치를 인용할 때는 어떤 Tool 결과에서 나온 값인지 밝힌다.
- `verified: false` 인 지식으로 계산했으면 "미검증 정의 기준"임을 밝힌다.

## Skills

- `kpi-shortfall-analysis` → 실적 부진 원인 분석 절차
- `sql-analysis` → 카탈로그 확인 → SQL 작성 → 실행 → 검증 절차
- `simulation` → 시뮬레이션 선택·실행·해석 절차
```

## 부록 G. Skills (Task 7)

`kpi-shortfall-analysis/SKILL.md`

```markdown
---
name: kpi-shortfall-analysis
description: 생산계획 Agent 전용. 실적·KPI 가 계획 대비 부진한 원인을 찾을 때 사용. "부진", "미달", "왜 떨어졌나", "원인" 질의에 적용.
---

# 실적 부진 원인 분석

## 절차

1. **KPI 확정**: `list_kpis` 로 질의의 KPI 를 찾고 `get_kpi` 로 정의·공식·`shortfall_rule`·`diagnostics` 를 얻는다. 질의에 KPI 가 둘 이상이면 하나씩 처리한다.
2. **기간·범위 확정**: 질의에 기간이 없으면 최근 1개월. 라인·품목 지정이 없으면 전체. 확정한 기간을 답변에 명시한다.
3. **부진 여부 판정**: `sql-analysis` 절차로 KPI 의 `sql_template` 를 기간에 맞춰 실행한다. `shortfall_rule` 로 부진 구간을 찾는다. 부진이 없으면 그렇게 답하고 끝낸다.
4. **분해**: 부진 구간을 라인·품목·일자별로 나눠 다시 조회해 어디에 집중됐는지 특정한다.
5. **가설 검증**: `diagnostics` 를 나열된 순서대로 검증한다. `how: simulation` 이면 `simulation` 절차로, `how: sql` 이면 `ref` 테이블을 `describe_table` 한 뒤 부진 구간과 같은 기간·품목으로 조회한다. 각 가설마다 "지지 / 기각 / 확인 불가" 를 근거 수치와 함께 기록한다.
6. **결론**: 지지된 가설을 원인으로 제시한다. 여러 개면 영향 크기 순. 전부 기각이면 "확인된 가설 중 원인 없음" 이라 답하고 어떤 데이터가 더 필요한지 말한다.

## 규칙

- 가설을 건너뛰지 않는다. 앞 가설이 지지돼도 나머지를 확인한다. 원인은 복합일 수 있다.
- 기각 근거도 답변에 남긴다 ("확정 MP 변경 없음" 처럼).
- `verified: false` 인 KPI 정의로 판정했으면 결론에 그 사실을 붙인다.
```

`sql-analysis/SKILL.md`

```markdown
---
name: sql-analysis
description: 생산계획 Agent 전용. 실적·계획·재고 등 데이터를 SQL 로 조회할 때 사용. 카탈로그 확인 → SQL 작성 → 실행 → 검증 절차.
---

# SQL 조회 절차

1. **테이블 찾기**: 어떤 테이블인지 모르면 `list_tables(keyword=...)`. KPI 조회면 `get_kpi` 의 `sources` 와 `sql_template` 를 출발점으로 쓴다.
2. **스키마 확인**: 쓰려는 테이블마다 `describe_table`. `columns` 의 코드값(`codes`), `joins`, `caveats` 를 읽는다. caveats 의 필터 조건(예: 취소 제외)은 반드시 WHERE 에 반영한다.
3. **SQL 작성**: SELECT 만. 조인은 `joins` 에 적힌 키를 쓴다. 날짜는 `time_column` 을 쓰고 ISO 문자열(YYYY-MM-DD)로 비교한다. 집계 결과는 정렬한다.
4. **실행**: `execute_sql(sql, purpose)`. `purpose` 에는 이 쿼리로 확인하려는 것을 한 줄로.
5. **검증**: `status` 가 error 면 메시지를 읽고 SQL 을 고쳐 재시도(최대 2회). `row_count` 가 0 이면 조건이 맞는지 `describe_table` 의 예시와 비교한다. `truncated` 가 true 면 집계 수준을 올리거나 조건을 좁힌다.
6. **인용**: 답변에 수치를 쓸 때 어떤 쿼리(purpose)의 결과인지 밝힌다.

## 규칙

- 카탈로그에 없는 테이블·컬럼을 추측하지 않는다.
- 한 번에 하나의 목적만 가진 쿼리를 쓴다. 복잡하면 여러 번 나눠 조회한다.
- 데이터 변경 SQL 은 작성하지 않는다.
```

`simulation/SKILL.md`

```markdown
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
```

---

## 결정 기록

실행 세션이 채운다. 형식: `- YYYY-MM-DD Task N: <결정 또는 계획 이탈> — <이유>`

- 2026-09-14 Task 0: **문자열 system_prompt 로 Skill 노출됨** — spike 실행 결과 `SystemMessage(subtype="init").data["tools"]` 에 `Skill` 이 있고, 응답이 `production-planning`/`simulation`/`sql-analysis` 를 나열했다. preset+append 전환은 하지 않는다. Task 7 의 `agent.py` 수정은 `allowed_tools=TOOL_NAMES + ["Skill"]` 한 줄뿐이다.
- 2026-09-14 Task 0: init 이벤트의 `tools` 는 `allowed_tools` 로 필터되기 전 목록이다 — `Read`/`Write`/`Bash` 도 함께 나열되지만 `allowed_tools` 가 실행을 막는다. 설계 §"파일 도구 미개방" 은 유지된다.
- 2026-09-14 Task 0: 에이전트가 개발자의 user-level skill(`dataviz`, `code-review` 등)까지 나열했다 — 설계 §6 "알려진 부작용" 의 반대 방향. Skill description 첫 구절 `생산계획 Agent 전용.` (Task 7) 이 이 혼선도 줄이는 역할을 한다.
- 2026-09-14 Task 1: `Join` 에 `@model_validator(mode="before")` 로 boolean `True` 키를 `on` 으로 되돌리는 처리를 추가 — YAML 1.1 이 따옴표 없는 `on:` 을 boolean 으로 읽어 부록 A 의 모든 join 정의(`{to: ..., on: ...}`)가 검증에 실패했다. 부록 YAML 을 고치는 대신 로더에서 흡수해, 이후 카탈로그 작성자가 같은 함정에 빠지지 않게 했다.
- 2026-09-14 Task 1: 계획에 없던 `list_glossary()`·`list_scenarios()`·`reset_store()` 를 추가 — 각각 용어집 로드 검증, Task 3 시드 스크립트, 테스트의 캐시 초기화에 필요하다.
- 2026-09-14 Task 2: 테이블 추출 정규식에 `(?<![:\w.])` 를 앞에 붙임 — 계획이 지정한 `\b(?:FROM|JOIN)\s+(\w+)` 는 `BETWEEN :from AND :to` 의 `:from` 을 FROM 절로 읽어 `AND` 를 테이블명으로 잡는다. Task 4 의 `sql_guard.check_sql` 에도 같은 보정을 적용한다 (그쪽에선 정상 쿼리가 "등록되지 않은 테이블 AND" 로 거부되는 버그가 된다).
- 2026-09-14 Task 4·5: `services/mock/_sqlite.py` 를 추가해 연결 helper 를 분리 — Task 6 의 mock 시뮬레이션이 같은 SQLite 를 봐야 하므로(설계 §6-1) 계획이 허용한 선택지를 택했다. `SAMPLE_DB_PATH` 는 import 시점이 아니라 호출 시점에 읽어 테스트 monkeypatch 가 듣게 했다.
- 2026-09-14 Task 5: `sql_guard.check_sql` 이 CTE 이름(`WITH x AS (...)`)을 허용 테이블에 더하도록 함 — 계획은 CTE 를 언급하지 않았으나 `WITH … SELECT` 를 허용한 이상 CTE 참조가 "등록되지 않은 테이블"로 거부되면 안 된다.
- 2026-09-14 Task 8 을 Task 5 직후로 앞당겨 실행 — `fake_runner` 가 삭제된 `query_database` 를 import 해 pytest 수집 자체가 실패했다. 실행 규칙 7("Task 마다 pytest 전부 통과")을 지키려면 순서를 바꿔야 했다. Task 6·7 은 Task 8 에 의존하지 않는다.
- 2026-09-14 Task 9: 시나리오의 `expected_diagnosis` 를 `자재 부족` → `자재 결품` 으로 수정 — 에이전트는 원인을 정확히 찾았지만(B라인 P-1002, SUPPLIER_DELAY, 부족분 900 일치) 카탈로그·KPI diagnostics 가 일관되게 쓰는 "결품" 으로 답했다. 지식이 가르치지 않는 문구를 정답으로 둔 쪽이 틀렸다. 시나리오 `description` 도 원래 "자재 결품"이라 파일 내부에서도 어긋나 있었다.
- 2026-09-14 Task 9: E2E 단언에 라인·품목 특정과 기각 가설(MP) 언급 확인을 추가하고, 원인 문구는 결품/부족 둘 다 허용 — 한 문구 완전일치로 묶으면 지식이 아니라 표현을 맞추는 테스트가 된다.
- 2026-09-14 Task 9: `pytest.ini` 에 `addopts = -m "not e2e"` 를 넣어 기본 실행에서 e2e 를 제외 — 계획은 marker 등록만 지시했으나, 그것만으로는 `pytest` 가 매번 실제 LLM 을 호출해 비용이 든다.
- 2026-09-14 Task 10: 검증용 uvicorn 을 8123 포트로 띄움 — 8000·8010 을 이미 다른 프로세스가 점유 중이었다. 기본 포트 설정은 바꾸지 않았다.
