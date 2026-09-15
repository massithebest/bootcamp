# Result Store — 조회 결과 저장과 참조

**상태: 구현 중. 백엔드 1차 완료, 프론트엔드 연동 대기.** 백엔드/프론트엔드 양쪽에 걸친 결정이라 최상위 `docs/`에 둔다.
[chart-visualization.md](chart-visualization.md)의 v2 차트 설계가 이 문서를 전제로 하므로 **이쪽을 먼저 구현한다.**

## 배경

### 지금 일어나는 일

`execute_sql`은 조회 결과를 통째로 tool 결과 dict에 담아 에이전트에게 돌려준다. 행 수는 `MAX_ROWS = 500`(`backend/services/sql_guard.py`)에서 잘리고, 잘렸다는 사실만 `truncated: true`로 알린다.

```python
# backend/services/mock/mock_sql_service.py
truncated = len(fetched) > MAX_ROWS
rows = [list(row) for row in fetched[:MAX_ROWS]]
```

여기서 세 가지 문제가 생긴다.

1. **잘린 데이터는 영영 접근할 수 없다.** 에이전트가 할 수 있는 건 "집계 수준을 올려 다시 조회하라"(`sql-analysis` Skill 6단계)뿐이다. 같은 쿼리의 501번째 행을 보는 방법이 없다.
2. **LLM 컨텍스트에 500행이 그대로 들어간다.** 라인·품목·일자 3차원 분해 결과는 쉽게 수백 행이 되고, 그게 전부 토큰이 된다. 대화가 길어질수록 앞선 조회 결과가 컨텍스트를 잠식한다.
3. **후속 질의가 원본 데이터를 재사용하지 못한다.** "방금 결과에서 B라인만 다시 보여줘"는 SQL을 다시 짜서 DB를 다시 치는 수밖에 없다.

### 방향

조회 결과를 **파일로 저장하고 `result_id`로 참조**한다. LLM은 전체 행 대신 요약(행 수, 컬럼, 샘플 몇 행, 기초 통계)과 `result_id`만 들고 다니고, 전체 데이터가 필요한 백엔드 작업(차트 집계, 후속 필터)은 `result_id`로 저장소를 직접 읽는다. **프론트엔드는 저장소에 직접 접근하지 않는다** — 항상 에이전트가 `AgentEvent`로 보낸 응답만 받는다(§7).

## 1. 저장 정책 — 전부 저장한다

**건수와 무관하게 모든 조회 결과를 저장하고 `result_id`를 발급한다.**

임계값은 "저장할지"가 아니라 **"LLM에게 보내는 payload에 행을 실을지"**만 가른다.

| 행 수       | 저장                            | LLM payload                                       |
| ----------- | ------------------------------- | ------------------------------------------------- |
| 임계값 이하 | parquet 저장,`result_id` 발급 | `type: "inline"` — 행 전체 포함                |
| 임계값 초과 | parquet 저장,`result_id` 발급 | `type: "large_result"` — 행 제외, 샘플·요약만 |

이렇게 하는 이유: 차트 집계·`get_result_page` 구간 조회·후속 질의가 전부 `result_id` 하나로 동작한다. "소량이면 A 경로, 대량이면 B 경로" 같은 이중 분기가 생기지 않는다. 특히 차트는 결과 크기와 무관하게 필요하므로, 소량 결과에만 `result_id`가 없으면 차트 로직이 두 갈래가 된다.

parquet 쓰기 비용은 수백 행 기준 무시할 수준이고, 이 애플리케이션은 사용자 질의당 몇 번의 조회만 일어난다.

**임계값: 100행(2026-09-15, 200행에서 하향 조정).** 조정 근거는 "LLM이 이 표를 실제로 읽고 판단해야 하는가"다. 라인 4개 × 월 3개 = 12행처럼 에이전트가 직접 수치를 인용해야 하는 결과는 inline이어야 하고, 일자별 상세 수백 행처럼 "요약만 알면 되는" 결과는 굳이 컨텍스트에 넣을 이유가 없다. 실제 질의 패턴을 보고 조정한다. `sample_rows`는 앞 10행(200행 임계값과 함께 도입했던 5행에서 상향).

## 2. `ResultStore` 인터페이스

`backend/services/result_store.py`(신규)에 추상 베이스와 로컬 구현을 둔다.

```python
class ResultStore(ABC):
    @abstractmethod
    def save(self, columns: list[str], rows: list[list], *,
             source: str, conversation_id: str | None) -> ResultMeta: ...

    @abstractmethod
    def get_meta(self, result_id: str) -> ResultMeta | None: ...

    @abstractmethod
    def get_page(self, result_id: str, offset: int, limit: int) -> ResultPage: ...

    @abstractmethod
    def load(self, result_id: str) -> "pandas.DataFrame": ...

    @abstractmethod
    def delete(self, result_id: str) -> None: ...
```

`load()`가 DataFrame을 돌려주는 것은 차트 집계·필터·요약 통계가 전부 그 위에서 이뤄지기 때문이다. 이 메서드만 저장 포맷에 의존하고 나머지는 그 위에 쌓인다.

향후 추가(1차 범위 아님):

```python
    def filter(self, result_id: str, expr: str) -> ResultMeta: ...     # 새 result_id 발급
    def aggregate(self, result_id: str, spec: AggSpec) -> ResultMeta: ...
```

필터·집계 결과도 **새 `result_id`를 발급**한다. 그래야 "필터 결과를 다시 차트로" 같은 연쇄가 같은 경로로 동작한다.

### 구현 전환

Result Store는 `backend/services/__init__.py`의 `SERVICE_MODE` mock/real 스위칭과 **성격이 다르다** — DB나 시뮬레이션 서버처럼 "사내 시스템 연결 여부"가 갈리는 게 아니라 **저장 경로**만 다르다. **mock과 real 모두 같은 `LocalParquetResultStore`를 쓰고**, 저장 디렉터리만 환경변수(`RESULT_STORE_DIR`, 예: mock 기본값 `backend/data/results/`)로 구분한다. `services/result_store.py`가 `SERVICE_MODE` 분기 없이 이 클래스 하나를 그대로 export한다.

**추후 RDB로 전환 예정이다.** 이 전환이 이번 설계에 영향을 주는 지점은 하나뿐이어야 한다 — `save`/`get_meta`/`get_page`/`load`/`delete`가 저장 백엔드를 완전히 추상화하고 있으므로, RDB 전환 시 `RdbResultStore` 구현체 하나만 추가하면 되고 호출부(`tools/sql_tool.py`, `tools/simulation_tool.py`, `get_result_page`/`get_result_summary` tool, 향후 차트 집계 API)는 무수정이어야 한다. 이 무수정 목표가 `ResultStore`를 추상 베이스로 두는 이유다 — 인터페이스 설계 시 "parquet 파일 경로"가 호출부에 새지 않도록 주의한다(`ResultMeta.path`는 저장소 내부용으로만 쓰고, tool 반환 payload에는 넣지 않는다).

## 3. 저장 포맷과 경로

- **포맷: parquet.** 컬럼 타입이 보존되고(문자열로 뭉개지지 않는다), 컬럼 단위 읽기가 가능해 "이 두 컬럼만 차트로"가 전체 로드 없이 된다.
- **경로: `backend/data/results/<result_id>.parquet`.** `backend/data/`는 이미 시드 SQLite가 사는 곳이고 gitignore 대상이다. `results/`도 같은 규칙으로 추가한다.
- **`result_id`: uuid4 hex.** 사용자에게 노출되고 LLM이 인용하므로 짧을수록 좋지만, 충돌 회피와 추측 불가능성이 우선이다.

### 의존성 — 폐쇄망 주의

`pyarrow`는 현재 `pandas`의 전이 의존으로 설치돼 있을 뿐 **`backend/requirements.txt`에 명시돼 있지 않다.** 이대로 두면 [CLOSED_NETWORK_SETUP.md](../backend/docs/CLOSED_NETWORK_SETUP.md)의 `pip download -r requirements.txt` 번들에 포함될지가 pandas 버전에 좌우된다.

**`pyarrow`를 `requirements.txt`에 명시적으로 추가한다.** 폐쇄망 반입 wheel 목록에서 빠지면 저장소 전체가 동작하지 않는다.

## 4. 메타데이터

각 결과에 대해 데이터와 별개로 메타데이터를 유지한다.

```python
@dataclass(frozen=True)
class ResultColumn:
    name: str
    dtype: str          # "int64" | "float64" | "object" | "datetime64[ns]" 등
    role: str | None    # "category" | "measure" | "time" — 차트 결정에 쓴다 (§7)

@dataclass(frozen=True)
class ResultMeta:
    result_id: str
    row_count: int
    columns: list[ResultColumn]
    created_at: datetime
    expires_at: datetime
    source: str                      # "execute_sql" | "run_simulation:<type>"
    conversation_id: str | None
    path: Path
```

**저장 위치: `<result_id>.meta.json` 사이드카.** 단일 인덱스 파일은 동시 쓰기 시 경합이 생기고, 파일 하나가 깨지면 전체를 잃는다. 사이드카는 정리(TTL) 시 디렉터리 스캔이 필요하지만 이 규모에서는 문제되지 않는다.

`columns[].role`은 저장 시점에 dtype과 컬럼명으로 1차 추정해 넣는다. 차트 결정(§7, [chart-visualization.md](chart-visualization.md))이 이 값을 출발점으로 쓴다.

## 5. Tool 반환 구조

기존 `AgentEvent`(`backend/api/schemas.py`) 계약은 바꾸지 않는다 — `data`가 자유형 `dict[str, Any]`이므로 pydantic 모델 변경이 필요 없다.

`execute_sql` 결과에 `result_id`와 `type`을 추가한다.

```jsonc
// 소량 — 행 포함
{
  "status": "ok",
  "kind": "database",
  "type": "inline",
  "result_id": "a3f2...",
  "sql": "...",
  "purpose": "...",
  "table": { "columns": ["line_nm", "qty"], "rows": [["1라인", 18427], ...] },
  "row_count": 4
}
```

```jsonc
// 대용량 — 행 제외, 샘플과 요약만
{
  "status": "ok",
  "kind": "database",
  "type": "large_result",
  "result_id": "b7c1...",
  "sql": "...",
  "purpose": "...",
  "row_count": 3480,
  "columns": [
    { "name": "work_date", "dtype": "object", "role": "time" },
    { "name": "line_cd", "dtype": "object", "role": "category" },
    { "name": "inbound_qty", "dtype": "int64", "role": "measure" }
  ],
  "sample_rows": [["2026-08-01", "A", 412], ["2026-08-01", "B", 388]],
  "summary": {
    "inbound_qty": { "min": 0, "max": 980, "mean": 421.3, "null_count": 0 }
  }
}
```

`truncated`는 더 이상 쓰지 않는다 — 데이터가 잘리지 않고 전부 저장되기 때문이다. 기존 필드를 읽는 프론트(`frontend/src/components/chat/tool-results/database-result.tsx`)와 Skill 문구(`sql-analysis` SKILL.md 6단계 "truncated 가 true 면 집계 수준을 올리거나")를 함께 정리해야 한다.

`run_simulation`도 배열 결과(`실적_조회`의 `results`)에 대해 같은 구조를 따른다.

## 6. 조회 Tool

에이전트가 저장된 결과를 다시 볼 수 있어야 한다.

| Tool                   | 입력                           | 출력                                              |
| ---------------------- | ------------------------------ | ------------------------------------------------- |
| `get_result_summary` | `{result_id}`                | 메타데이터 + 요약 통계. 대용량 결과의 성격 파악용 |
| `get_result_page`    | `{result_id, offset, limit}` | 해당 구간 행. 특정 구간을 직접 봐야 할 때         |

향후: `filter_result`, `aggregate_result` — 새 `result_id`를 돌려준다.

### 등록 시 함께 고쳐야 하는 것

`backend/agent/sdk_tools.py`의 `TOOL_NAMES`에 추가하면 **`backend/tests/test_prompt_consistency.py`가 깨진다.** 이 테스트는 `TOOL_NAMES`와 `backend/agent/agent_sdk/CLAUDE.md`의 도구 표가 정확히 일치할 것을 강제한다:

```python
def test_claude_md_tool_table_matches_tool_names() -> None:
    assert set(rows) == SHORT_TOOL_NAMES
```

따라서 tool 추가 시 `agent/agent_sdk/CLAUDE.md`의 "Tool 사용 규칙" 표도 같은 커밋에서 갱신한다. 이 드리프트 방지는 의도된 설계다.

`sql-analysis` SKILL.md에도 "결과가 `large_result`면 `get_result_summary`로 성격을 파악하고, 필요한 구간만 `get_result_page`로 본다"는 절차를 추가한다.

## 7. 프론트엔드 연동

### 원칙 — 프론트는 에이전트 응답만 받는다

프론트엔드는 저장소(parquet)에 직접 접근하지 않는다. `result_id`로 원본 데이터를 조회하는 것은 **백엔드(tool 실행 시점)와 에이전트뿐**이고, 프론트는 항상 `AgentEvent`(`tool_result`)로 보내온 것만 렌더링한다. 이는 기존 아키텍처(`backend/CLAUDE.md`: `Frontend → FastAPI(/api/chat, SSE) → Agent Runner`, Browser가 직접 호출하는 경로는 `/api/chat`과 `/api/knowledge/*` 뿐)와 일치시키는 방향이다. `result_id`를 반환하는 raw 조회용 엔드포인트(`GET /api/results/{id}` 같은)는 만들지 않는다.

### `large_result`의 표시

`database-result.tsx`가 `data.type === "large_result"`를 보면 표 대신 요약 카드를 렌더한다 — 행 수, 샘플 몇 행(`sample_rows`)을 작은 미리보기 표로, 요약 통계(`summary`)를 곁들인다. 페이지네이션이나 "더 보기" 같은 추가 조회 UI는 두지 않는다.

### 전체 데이터를 보고 싶을 때

사용자가 "전체 다 보여줘"/"B라인만 다시" 같은 후속 질의를 하면, **에이전트가 `get_result_page`(또는 §9의 `filter_result`)를 호출해 필요한 구간을 다시 `AgentEvent`로 스트리밍한다.** 즉 "더 보기"는 UI 기능이 아니라 대화의 연장이다 — §9 "후속 질의에서의 재사용"과 같은 경로.

### 차트와의 관계

차트는 이 절과 무관하다. [chart-visualization.md](chart-visualization.md) §4가 설계한 `GET /api/results/{id}/chart`는 raw 행이 아니라 **차트를 그리기 위해 이미 집계된 소량 데이터**를 반환하는 API라, 여기서 제거한 raw 페이지네이션 엔드포인트와는 성격이 다르다 — 그 API는 그대로 유지한다.

## 8. TTL과 삭제

디스크가 무한하지 않고, 조회 결과에는 업무 데이터가 들어 있다.

- **TTL: 기본 24시간.** `expires_at`을 메타데이터에 박아둔다.
- **정리 시점**: FastAPI `lifespan`에서 주기 태스크로 만료분을 지운다. `main.py`에 이미 lifespan TODO가 적혀 있다.
- **세션 종료 시 삭제**: 하지 않는다. 대화를 닫았다가 다시 열어 이전 결과를 참조하는 흐름이 막힌다. TTL로만 정리한다.
- **디스크 상한**: 총량이 상한을 넘으면 오래된 것부터 지운다. 상한 초과는 로그로 남긴다 — 조용히 지우면 "방금 본 결과가 사라지는" 현상의 원인을 못 찾는다.

`conversation_id`를 메타데이터에 넣는 이유가 여기 있다 — 나중에 "이 대화의 결과만 정리" 같은 정책이 필요해질 때 근거가 된다.

## 9. 후속 질의에서의 재사용

`result_id`가 대화 컨텍스트에 남아 있으면 다음이 가능해진다.

- **필터**: "방금 결과에서 B라인만" → `filter_result(result_id, "line_cd == 'B'")` → 새 `result_id`
- **재집계**: 일자별 결과를 월별로 → `aggregate_result`
- **시뮬레이션 입력**: 조회 결과를 시뮬레이션 파라미터로 넘길 때 값을 옮겨 적지 않고 `result_id`로 참조
- **비교**: SQL 결과와 시뮬레이션 결과를 같은 집계 단위로 맞춰 비교 (`simulation` SKILL.md 5단계가 지금은 에이전트에게 수동으로 시키는 일)

이 셋은 1차 범위가 아니다. 다만 `ResultStore` 인터페이스를 설계할 때 이 연산들이 나중에 얹힐 자리를 비워둔다.

## 10. 단계별 도입

**1차 (이 문서의 구현 범위)**

1. `pyarrow`를 `requirements.txt`에 추가
2. `services/result_store.py` — `ResultStore` ABC + `LocalParquetResultStore`
3. `mock_sql_service.execute_sql`이 결과를 저장하고 `result_id`/`type`을 반환
4. `mock_simulation_service.run_simulation`도 배열 결과에 대해 동일 처리
5. `get_result_summary`/`get_result_page` tool + `TOOL_NAMES` + `agent_sdk/CLAUDE.md` 표 + `sql-analysis` SKILL.md 절차
6. 프론트 `database-result.tsx`가 `type: "large_result"`를 요약 카드로 렌더 (페이지네이션 없음)
7. TTL 정리 태스크

**2차 (차트)** — [chart-visualization.md](chart-visualization.md)

**3차 (재사용 연산)** — `filter_result` / `aggregate_result`

## 열린 질문

- **임계값 100행이 맞는가.** 실제 질의 로그를 보고 조정한다. inline 기준이 너무 낮으면 에이전트가 수치를 인용하려고 `get_result_page`를 계속 호출해 왕복이 늘어난다.
- **`columns[].role` 추정을 어디까지 할 것인가.** 저장 시점에 dtype만 보고 넣을지, 카탈로그 YAML(`knowledge/catalog/tables/*.yaml`)의 컬럼 정의를 참조할지. 후자가 정확하지만 SQL 결과의 컬럼이 항상 카탈로그 컬럼과 1:1로 대응하지는 않는다(집계·별칭).
- **RDB 전환 시점과 마이그레이션 방법.** 기존에 쌓인 parquet 파일을 RDB로 일괄 이관할지, 전환 시점 이후 신규 저장분부터 RDB로 갈지(구 parquet은 TTL로 자연 소멸). 전환 시 어떤 RDB(SQLite/PostgreSQL 등)를 쓸지와 스키마(행 단위 테이블 vs JSON 컬럼)도 미정.
- **동시성.** 같은 대화에서 병렬 tool 호출이 일어나면(Claude가 `AssistantMessage` 하나에 `ToolUseBlock`을 여러 개 담을 수 있다 — `backend/agent/event_adapter.py` 참고) 저장이 동시에 일어난다. uuid4 경로라 충돌은 없지만 TTL 정리와의 경합은 확인이 필요하다.

## 관련 문서

- [chart-visualization.md](chart-visualization.md) — 이 저장소를 전제로 한 차트 설계 (2차)
- [todo.md](todo.md) — 이 설계의 출발점이 된 TODO 항목
- [domain-knowledge.md](domain-knowledge.md) — 지식 YAML 구조와 Tool 계약
- [backend/docs/CLOSED_NETWORK_SETUP.md](../backend/docs/CLOSED_NETWORK_SETUP.md) — 폐쇄망 의존성 반입 절차
- [backend/CLAUDE.md](../backend/CLAUDE.md) — 백엔드 작업 지침
