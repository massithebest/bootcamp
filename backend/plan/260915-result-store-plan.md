# Result Store 1차 실행 계획 (백엔드)

**상태: 완료.** 상위 요구사항은 [Result Store 통합 계획](../../plan/260915-result-store-plan.md)을 따른다. 이 문서는 1차 백엔드 구현의 상세 실행·결정 기록이다.

[차트 시각화 통합 계획](../../plan/260915-chart-visualization-plan.md)은 이 계획의 완료를 전제로 한다.

## 실행 세션 시작 방법

```bash
cd backend
claude --model sonnet
```

첫 프롬프트: "`plan/260915-result-store-plan.md`를 Task 0부터 순서대로 진행해줘. 설계 문서에 없던 판단을 내릴 때마다 문서 끝 '결정 기록' 절에 무엇을 왜 그렇게 정했는지 바로 남겨줘 — 다른 세션이 이력을 추적할 수 있어야 해."

이 지시는 실행 에이전트가 Claude Code가 아니어도(Codex 등) 동일하게 적용한다 — `plan/AGENTS.md`의 저장소 관례다.

## 실행 규칙

- 각 Task 끝의 "검증"을 통과해야 다음 Task로 넘어간다.
- mock/real 계약(함수 시그니처, 반환 dict 키)은 항상 동일하게 유지한다 — `backend/AGENTS.md` 참고. `services/real/*`는 현재 `NotImplementedError` 상태이므로 이번 작업은 mock 경로만 구현한다.
- 새 환경변수는 `core/config.py`에서만 읽는다. `.env.example`도 같은 커밋에서 갱신한다.
- `backend/agent/sdk_tools.py`의 `TOOL_NAMES`에 tool을 추가하면 `backend/tests/test_prompt_consistency.py`가 `agent/agent_sdk/CLAUDE.md`의 "Tool 사용 규칙" 표와의 일치를 강제한다 — Task 5에서 둘을 같은 커밋으로 갱신한다.
- 각 Task는 관련 있는 기존 테스트 파일(`test_services.py`/`test_tools.py`/`test_prompt_consistency.py`)에 이어 붙인다. 새 파일이 필요하면 해당 Task에 명시했다.

## Task 목록

### Task 0. `pyarrow` 의존성 추가

**파일**: `backend/requirements.txt`

**스펙**:
- `pandas==3.0.5` 다음 줄(`requests==2.34.2` 앞)에 `pyarrow==<현재 설치된 버전>`을 추가한다. 버전은 아래 명령으로 확인한다.

```bash
python -c "import pyarrow; print(pyarrow.__version__)"
```

- 이미 `pandas`의 전이 의존으로 설치돼 있으므로 새로 설치할 필요는 없다 — `requirements.txt`에 명시만 한다.

**검증**:
```bash
pip install -r requirements.txt   # 변경 없음(이미 설치돼 있음)을 확인
python -c "import pyarrow"
```

**완료 기준**: `requirements.txt`에 `pyarrow==X.Y.Z` 줄이 존재하고 위 명령이 오류 없이 끝난다.

---

### Task 1. `ResultStore` 인터페이스 + `LocalParquetResultStore`

**파일**: `backend/services/result_store.py`(신규), `backend/core/config.py`, `backend/.env.example`

**스펙** (설계 §2~§4):

1. `core/config.py`에 `SAMPLE_DB_PATH` 패턴(29~31번째 줄 부근)을 따라 상수를 추가한다:

```python
#: 조회 결과(parquet) 저장 디렉터리. git 미추적.
RESULT_STORE_DIR = Path(os.getenv("RESULT_STORE_DIR") or BACKEND_DIR / "data" / "results")
```

   `.env.example`에도 `SAMPLE_DB_PATH` 항목 형식을 따라 같은 절에 추가:

```
# 조회 결과(parquet) 저장 디렉터리. 비워두면 backend/data/results 를 쓴다.
RESULT_STORE_DIR=
```

2. `services/result_store.py`에 다음을 정의한다.

```python
@dataclass(frozen=True)
class ResultColumn:
    name: str
    dtype: str
    role: str | None   # "category" | "measure" | "time" | None

@dataclass(frozen=True)
class ResultMeta:
    result_id: str
    row_count: int
    columns: list[ResultColumn]
    created_at: datetime
    expires_at: datetime
    source: str                  # "execute_sql" | "run_simulation:<simulation_type>"
    conversation_id: str | None
    path: Path                   # 저장소 내부용 — tool 반환 payload에 절대 넣지 않는다

@dataclass(frozen=True)
class ResultPage:
    result_id: str
    offset: int
    limit: int
    rows: list[list]
    row_count: int   # 전체 행 수 (이 페이지 크기가 아니라)

class ResultStore(ABC):
    @abstractmethod
    def save(self, columns: list[str], rows: list[list], *,
             source: str, conversation_id: str | None) -> ResultMeta: ...
    @abstractmethod
    def get_meta(self, result_id: str) -> ResultMeta | None: ...
    @abstractmethod
    def get_page(self, result_id: str, offset: int, limit: int) -> ResultPage | None: ...
    @abstractmethod
    def load(self, result_id: str) -> "pandas.DataFrame": ...
    @abstractmethod
    def delete(self, result_id: str) -> None: ...
```

3. `LocalParquetResultStore(ResultStore)` 구현:
   - `save()`: `uuid4().hex`로 `result_id` 발급 → `columns`/`rows`로 `pandas.DataFrame` 생성 → `<RESULT_STORE_DIR>/<result_id>.parquet`에 `to_parquet(engine="pyarrow")`로 저장 → `columns[].role`을 dtype+컬럼명 휴리스틱으로 1차 추정(아래 4번) → `<result_id>.meta.json` 사이드카에 `ResultMeta`를 JSON으로 직렬화(경로는 상대/절대 중 일관되게, `datetime`은 ISO 8601 문자열) → `ResultMeta` 반환.
   - `get_meta()`: 사이드카 JSON을 읽어 `ResultMeta`로 역직렬화. 없으면 `None`.
   - `get_page()`: `get_meta()`로 존재 확인 후 parquet을 읽어(`pandas.read_parquet`) `iloc[offset:offset+limit]` 슬라이스 → `ResultPage`. `result_id` 없으면 `None`.
   - `load()`: parquet 전체를 `DataFrame`으로 반환.
   - `delete()`: parquet + 사이드카 둘 다 삭제. 파일 없어도 예외 없이 조용히 통과(TTL 정리 중 경합 대비).
   - `RESULT_STORE_DIR`가 없으면 `save()` 시점에 생성한다(`mkdir(parents=True, exist_ok=True)`).

4. `role` 추정 휴리스틱(간단하게):
   - dtype이 `datetime64` 계열이거나 컬럼명이 `_date`/`_at`/날짜 패턴을 포함하면 `"time"`.
   - dtype이 숫자(`int64`/`float64`)이면 `"measure"`.
   - 그 외(`object` 등)는 `"category"`.
   - 이 로직은 별도 함수(`_infer_role(name: str, dtype: str) -> str | None`)로 분리해 테스트 가능하게 만든다.

5. 모듈 끝에서 `SERVICE_MODE` 분기 없이 항상 `LocalParquetResultStore` 인스턴스를 export한다 (설계 §2 "구현 전환" — mock/real 스위칭과 무관):

```python
_store = LocalParquetResultStore(RESULT_STORE_DIR)

def get_result_store() -> ResultStore:
    return _store
```

**검증**: `backend/tests/test_result_store.py`(신규)에 다음을 작성하고 통과시킨다.
- `save()` 후 `get_meta()`가 같은 `row_count`/`columns`를 돌려준다.
- `get_page(offset=1, limit=1)`이 올바른 부분 행을 돌려준다.
- `load()`가 저장한 것과 동일한 DataFrame을 돌려준다(행 수·컬럼 일치).
- `delete()` 후 `get_meta()`가 `None`.
- 존재하지 않는 `result_id`에 대해 `get_meta`/`get_page`가 예외 없이 `None`.
- `_infer_role`이 `int64`→`measure`, `object` 컬럼명 `line_cd`→`category`, `work_date`(object, 컬럼명에 `date` 포함)→`time`을 올바르게 판정한다.

```bash
cd backend && python -m pytest tests/test_result_store.py -q
```

**완료 기준**: 위 테스트 전부 통과. `RESULT_STORE_DIR`를 `tmp_path`로 monkeypatch해서 테스트가 실제 `backend/data/`를 오염시키지 않는다(기존 `seeded_db` fixture의 monkeypatch 패턴을 따른다).

---

### Task 2. `mock_sql_service.execute_sql`이 결과를 저장하고 `result_id`/`type` 반환

**파일**: `backend/services/mock/mock_sql_service.py`

**스펙** (설계 §1, §5):

1. `MAX_ROWS`(현재 500, `sql_guard.py`)와는 별개로 **inline/large_result 분기 임계값 200행** 상수를 이 파일 또는 `core/config.py`에 둔다. 설계 §1의 "초기 임계값: 200행"을 그대로 코드 상수화한다 — `INLINE_ROW_THRESHOLD = 200` (이름은 자유, `sql_guard.MAX_ROWS`와 혼동되지 않게 다른 이름을 쓴다).
2. 기존 `truncated` 계산·필드는 제거한다(설계 §5 "truncated는 더 이상 쓰지 않는다"). 대신 `fetchmany(MAX_ROWS + 1)` → `MAX_ROWS`로 자르는 기존 로직(가드레일 상한)은 그대로 둔다 — 이건 SQL 가드레일이지 표시 임계값이 아니다.
3. 쿼리 성공 시:
   - `get_result_store().save(columns, rows, source="execute_sql", conversation_id=None)`을 호출해 `ResultMeta`를 받는다. (`conversation_id`는 1차 범위에서 `execute_sql` 시그니처에 없으므로 `None`으로 둔다 — 시그니처를 넓히는 건 이번 범위 밖. 열린 질문으로 설계 문서에 이미 있음.)
   - `row_count <= INLINE_ROW_THRESHOLD`면 기존처럼 `type: "inline"`, `table: {columns, rows}` 포함, `result_id` 추가.
   - `row_count > INLINE_ROW_THRESHOLD`면 `type: "large_result"`, `table` 필드 제거, 대신 `columns`(각 `{name, dtype, role}`), `sample_rows`(앞 5행 정도), `summary`(숫자 컬럼별 `min`/`max`/`mean`/`null_count` — `pandas.DataFrame.describe()` 또는 수동 계산)를 포함한다. 설계 §5의 JSON 예시를 그대로 따른다.
   - 두 분기 모두 `status: "ok"`, `kind: "database"`, `sql`, `purpose`, `row_count`, `result_id`를 공통으로 포함한다.
4. `chart = infer_chart(columns, rows)` 호출은 그대로 유지한다(§7 "차트는 이 절과 무관" — 건드리지 않는다). `large_result`일 때도 `rows`가 이미 메모리에 있으므로 `infer_chart`는 그대로 호출 가능하다.

**검증**: `backend/tests/test_services.py`에 이어 붙인다.
- `test_mock_execute_sql_returns_result_id(seeded_db)`: 소량 결과에 `result_id`(uuid4 hex 형식)와 `type == "inline"`, `table.rows`가 존재.
- `test_mock_execute_sql_large_result_omits_rows(seeded_db)`: `INLINE_ROW_THRESHOLD`를 monkeypatch해 낮춘 뒤(예: 1) 결과가 `type == "large_result"`, `table` 키 없음, `sample_rows`/`summary`/`columns` 존재.
- `test_mock_execute_sql_result_retrievable_via_store(seeded_db)`: 반환된 `result_id`로 `get_result_store().get_meta()`가 성공.
- 기존 `test_mock_execute_sql_truncates_over_max_rows`는 `truncated` 필드 검증이었다면 삭제하거나 `MAX_ROWS` 가드레일 자체(행 수가 잘리는지)만 검증하도록 수정한다 — `truncated` 키 자체를 assert하지 않게 고친다.

```bash
cd backend && python -m pytest tests/test_services.py -q
```

**완료 기준**: 위 테스트 통과. `tests/test_sql_guard.py`(가드레일, 이번 범위 밖)는 영향받지 않는다 — 실행해서 회귀 없는지만 확인.

---

### Task 3. `mock_simulation_service.run_simulation`도 배열 결과에 동일 처리

**파일**: `backend/services/mock/mock_simulation_service.py`

**스펙** (설계 §5 "run_simulation도 배열 결과에 대해 같은 구조를 따른다"):

1. `run_simulation()`에서 `result.get("results")`가 리스트이고 비어있지 않으면(기존 `infer_chart_from_records` 호출 조건과 동일한 위치, `records = result.get("results")` 직후):
   - `columns = list(records[0].keys())`, `rows = [[r[c] for c in columns] for r in records]`로 변환.
   - `get_result_store().save(columns, rows, source=f"run_simulation:{simulation_type}", conversation_id=None)` 호출.
   - Task 2와 동일한 200행 임계값 분기: 임계값 이하면 `result["result_id"]`/`result["type"] = "inline"`만 추가(기존 `results` 필드는 그대로 유지 — 프론트가 이미 이 형태를 읽는다). 임계값 초과면 `result["type"] = "large_result"`로 표시하고 `results`를 `sample_rows`(앞 5개)로 축소하며 `summary`를 추가한다.
2. `실적_조회` 외 다른 `simulation_type`(`MP_확정조회`, `MP_최신조회`, `SWAP_결과조회`)은 `results` 배열이 없으므로 이 로직에 걸리지 않는다 — 조건문이 이미 `isinstance(records, list) and records`로 걸러준다.

**검증**: `backend/tests/test_services.py`에 이어 붙인다.
- `test_mock_run_simulation_performance_lookup_gets_result_id(seeded_db)`: `실적_조회` 결과에 `result_id`/`type` 존재, 기존 `results` 필드 내용은 변화 없음(소량이라 `inline`).
- 기존 `test_mock_run_simulation_performance_lookup`은 `results` 필드 assertion이 그대로 통과하는지 확인(회귀 없음).

```bash
cd backend && python -m pytest tests/test_services.py -q
```

**완료 기준**: 위 테스트 통과.

---

### Task 4. `get_result_summary` / `get_result_page` tool 등록

**파일**: `backend/tools/result_tool.py`(신규), `backend/agent/sdk_tools.py`, `backend/agent/agent_sdk/CLAUDE.md`, `backend/agent/agent_sdk/.claude/skills/sql-analysis/SKILL.md`

**스펙** (설계 §6):

1. `backend/tools/result_tool.py` 신규 — 기존 `tools/sql_tool.py` 패턴을 따라 얇은 wrapper로 작성:

```python
from services.result_store import get_result_store

async def get_result_summary(result_id: str) -> dict:
    meta = get_result_store().get_meta(result_id)
    if meta is None:
        return {"status": "error", "message": f"result_id를 찾을 수 없습니다(만료되었을 수 있음): {result_id}"}
    # meta.columns 로 요약 통계 계산 (load() 후 describe()) 또는 save 시점 계산값 재사용
    ...
    return {"status": "ok", "result_id": result_id, "row_count": meta.row_count,
            "columns": [...], "summary": {...}}

async def get_result_page(result_id: str, offset: int, limit: int) -> dict:
    page = get_result_store().get_page(result_id, offset, limit)
    if page is None:
        return {"status": "error", "message": f"result_id를 찾을 수 없습니다(만료되었을 수 있음): {result_id}"}
    return {"status": "ok", "result_id": result_id, "offset": offset, "limit": limit,
            "row_count": page.row_count, "rows": page.rows}
```

   `ResultMeta.path`는 여기서도 반환 payload에 절대 넣지 않는다(설계 §2 "인터페이스 설계 시 주의").

2. `backend/agent/sdk_tools.py`:
   - `from tools.result_tool import get_result_summary, get_result_page` 추가.
   - `TOOL_NAMES`에 두 항목 추가(기존 `list_recipes`/`get_recipe` 다음).
   - `@tool("get_result_summary", "...", {"result_id": str})`, `@tool("get_result_page", "...", {"result_id": str, "offset": int, "limit": int})` 등록. 설명 문구는 §6 표의 용도("메타데이터 + 요약 통계. 대용량 결과의 성격 파악용" / "해당 구간 행. 특정 구간을 직접 봐야 할 때")를 참고해 작성.
   - `build_planning_mcp_server()`의 `tools=[...]` 배열에 두 함수 추가.

3. `backend/agent/agent_sdk/CLAUDE.md` "Tool 사용 규칙" 표에 두 행 추가(기존 `get_recipe` 다음):

```
| `get_result_summary` | 대용량 조회 결과(`large_result`)의 메타데이터·요약 통계 확인 |
| `get_result_page` | 대용량 조회 결과의 특정 구간(offset/limit) 조회 |
```

   그리고 마지막 불릿 `- execute_sql 결과의 truncated 가 true 면...`을 다음으로 교체(설계 §5):

```
- `execute_sql` 결과가 `type: "large_result"`면 `get_result_summary`로 성격을 파악하고, 필요한 구간만 `get_result_page`로 조회한다.
```

4. `sql-analysis` SKILL.md 6단계(`backend/agent/agent_sdk/.claude/skills/sql-analysis/SKILL.md`)의 "`truncated` 가 true 면 집계 수준을 올리거나 조건을 좁힌다" 문구를 다음으로 교체(설계 §6):

```
6. **검증**: `status` 가 error 면 메시지를 읽고 SQL 을 고쳐 재시도(최대 2회). `row_count` 가 0 이면 조건이 맞는지 `describe_table` 의 예시와 비교한다. 결과가 `large_result` 면 `get_result_summary` 로 성격을 파악하고, 필요한 구간만 `get_result_page` 로 본다.
```

**검증**:
```bash
cd backend && python -m pytest tests/test_prompt_consistency.py tests/test_tools.py -q
```
- `test_claude_md_tool_table_matches_tool_names`가 통과한다(표와 `TOOL_NAMES` 완전 일치).
- `test_skill_mentions_only_existing_tools`가 통과한다.
- `tests/test_tools.py`에 `test_get_result_summary_unknown_id_is_error()`, `test_get_result_page_returns_slice(seeded_db)` 추가(먼저 `execute_sql`로 저장 후 조회) — 기존 `ALL_TOOLS` 튜플에 두 tool 추가하고 `test_tool_names_cover_every_tool`이 계속 통과하는지 확인.

**완료 기준**: 위 두 테스트 파일 전부 통과.

---

### Task 5. 프론트엔드 계약 정리 확인 (백엔드 측 메모만)

이 Task는 코드 변경이 아니라 **프론트 계획 문서와의 인터페이스 확정**이다. Task 2~4까지 끝나면 다음 payload 형태가 확정된다 — [frontend/plan/260915-result-store-plan.md](../../frontend/plan/260915-result-store-plan.md)가 이를 전제로 작업을 시작할 수 있다.

- `execute_sql` 결과: `type: "inline" | "large_result"`, `result_id` 필드 추가. `truncated` 필드 제거.
- `large_result`일 때 `table` 필드 없음, 대신 `columns`/`sample_rows`/`summary`.

**완료 기준**: 아래 curl로 두 케이스를 직접 확인하고, 실제 응답 JSON을 이 절 아래에 "결정 기록"으로 남긴다.

```bash
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000 &
# 소량 조회와 대량 조회(200행 초과 결과가 나오는 질의) 각각 curl 또는 채팅으로 확인
```

---

### Task 6. TTL 정리 태스크

**파일**: `backend/main.py`, `backend/services/result_store.py`(또는 신규 `backend/services/result_cleanup.py`), `backend/core/config.py`

**스펙** (설계 §8):

1. `ResultMeta`에 이미 `expires_at`이 있다 — Task 1에서 `save()` 시점에 `created_at + timedelta(hours=RESULT_STORE_TTL_HOURS)`로 채운다. `RESULT_STORE_TTL_HOURS = 24`를 `core/config.py`에 환경변수로 노출한다(`.env.example`에도 추가, 기본값 24).
2. `services/result_store.py`(또는 별도 모듈)에 `cleanup_expired() -> int`(삭제 건수 반환) 함수 추가: `RESULT_STORE_DIR`의 `*.meta.json`을 스캔해 `expires_at < now()`인 것을 `delete()`한다.
3. `backend/main.py`의 lifespan TODO(41~43번째 줄) 자리에 `@asynccontextmanager` lifespan을 구현하고 `FastAPI(lifespan=lifespan)`로 연결한다. lifespan 안에서 `asyncio.create_task`로 주기 루프(예: 1시간마다 `cleanup_expired()` 호출, `asyncio.sleep`)를 돌리고, `yield` 이후(shutdown) 그 task를 취소한다.
4. 디스크 상한(설계 §8 "총량이 상한을 넘으면 오래된 것부터 지운다")은 1차 범위에 포함한다 — `RESULT_STORE_MAX_BYTES` 환경변수(기본값, 예: 500MB)를 추가하고, `cleanup_expired()`와 같은 주기 태스크에서 총 용량 초과 시 `created_at` 오름차순으로 삭제하며 `logger.warning`으로 남긴다.

**검증**: `backend/tests/test_result_store.py`에 이어 붙인다.
- `test_cleanup_expired_removes_only_expired(...)`: `expires_at`을 과거로 monkeypatch한 항목만 삭제되고 미래 항목은 남는다.
- `test_cleanup_respects_max_bytes(...)`: 여러 개 저장 후 상한을 낮춰 오래된 것부터 삭제되는지 확인.
- lifespan 자체는 통합 테스트로 검증하기보다 `cleanup_expired()` 단위 테스트로 충분 — `main.py`의 asyncio task 등록은 수동으로 서버 기동해 로그 확인.

```bash
cd backend && python -m pytest tests/test_result_store.py -q
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000   # 기동 시 에러 없는지, 로그에 정리 태스크 시작 메시지가 있는지 확인 후 Ctrl-C
```

**완료 기준**: 새 테스트 통과, 서버가 lifespan 오류 없이 기동/종료된다.

---

## 최종 검증

```bash
cd backend
python -m pytest -q
```

전체 테스트(mock e2e 시나리오 `pytest -m e2e` 제외 기본 스위트)가 통과해야 한다. 그리고:

```bash
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
```

으로 기동해 채팅에서 대량 결과가 나오는 질의를 보내고, SSE에 `tool_result.data.type == "large_result"`가 오는지, `get_result_summary`/`get_result_page`를 에이전트가 후속 호출하는지 수동 확인한다.

## 이후

- **2차 (차트)**: [상위 차트 계획](../../plan/260915-chart-visualization-plan.md) — 백엔드 실행 이력은 [plan/260915-chart-v2-plan.md](260915-chart-v2-plan.md).
- **3차 (재사용 연산)**: `filter_result`/`aggregate_result` — 설계 §9. 이번 범위 아님, `ResultStore` 인터페이스에 자리만 비워둔다(이미 Task 1에서 추상 메서드로 구현하지 않음).

## 결정 기록

- 2026-09-15: 활성 Python(3.13)에는 계획의 전제와 달리 `pyarrow`와 `pandas`가 설치돼 있지 않았다. `pip install -r requirements.txt`로 환경을 맞춘 뒤 설치된 `pyarrow==25.0.1`을 고정했다. 폐쇄망 반입 시에는 기존 가이드대로 Python 3.11용 wheel을 별도 준비해야 한다.
- 2026-09-15: `PLANNING_AGENT_FAKE=1` 서버를 기동해 lifespan 시작/종료와 `/health`, `/api/chat` SSE를 확인했다. 8000 포트가 이미 사용 중이어서 동일 앱을 8011 포트에서 검증했다. Fake Runner는 고정된 88행 쿼리만 실행하므로 소량 SSE 계약을 확인하고, 200행 초과 계약은 같은 mock service를 직접 호출해 확인했다.

소량 실제 응답:

```json
{
  "status": "ok",
  "kind": "database",
  "type": "inline",
  "result_id": "a30f90f8da934a35a931ba694e130a65",
  "sql": "SELECT line_cd, line_nm FROM LINE_MASTER ORDER BY line_cd LIMIT 2",
  "purpose": "소량 결과 계약 확인",
  "row_count": 2,
  "table": {
    "columns": ["line_cd", "line_nm"],
    "rows": [["A", "1라인"], ["B", "2라인"]]
  }
}
```

대량 실제 응답:

```json
{
  "status": "ok",
  "kind": "database",
  "type": "large_result",
  "result_id": "7fdfa3dae9814ff8b72457ac6aa58cfa",
  "sql": "SELECT work_date, line_cd, product_id, inbound_qty FROM FGS_INBOUND_RESULT ORDER BY work_date, line_cd, product_id",
  "purpose": "대량 결과 계약 확인",
  "row_count": 500,
  "columns": [
    {"name": "work_date", "dtype": "str", "role": "time"},
    {"name": "line_cd", "dtype": "str", "role": "category"},
    {"name": "product_id", "dtype": "str", "role": "category"},
    {"name": "inbound_qty", "dtype": "int64", "role": "measure"}
  ],
  "sample_rows": [
    ["2026-06-01", "A", "P-1001", 450],
    ["2026-06-01", "A", "P-1002", 410],
    ["2026-06-01", "B", "P-1002", 399],
    ["2026-06-01", "B", "P-1003", 219],
    ["2026-06-01", "C", "P-1004", 527]
  ],
  "summary": {
    "inbound_qty": {"min": 158, "max": 676, "mean": 381.69, "null_count": 0}
  }
}
```
