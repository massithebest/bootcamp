# Result Store 연동 계획 (프론트엔드)

**상태: 완료 (2026-09-15).** 설계는 [docs/result-store.md](../../docs/result-store.md) §5, §7. 백엔드 실행 계획은 [backend/plan/260915-result-store-plan.md](../../backend/plan/260915-result-store-plan.md)(완료). 실행 세부는 문서 끝 "실행 기록" 참고.

**assistant-ui 검토 완료 (2026-09-15):** `frontend/CLAUDE.md`의 "assistant-ui 작업 원칙"에 따라 `assistant-ui:tools`, `assistant-ui:generative-ui` Skill로 사전 확인함 — 둘 다 이 작업과 무관하다는 결론. `tools`(`defineToolkit`/`render`)와 `generative-ui`(`present` tool)는 모두 `"use generative"` 컴파일러 + `AISDKToolkit` + AI SDK v7 라우트를 전제로 하는데, 이 프로젝트는 AI SDK를 도입하지 않고 `useExternalStoreRuntime` + 자체 SSE(`AgentEvent`)를 쓴다. `large_result` 요약 카드는 백엔드가 고정 스키마로 보낸 데이터를 프론트가 고정된 방식으로 렌더하는 케이스라, 기존 `database-result.tsx`의 `data.table`/`data.chart` 분기 패턴을 그대로 확장하면 된다 — 아래 작업 목록은 이 결론을 반영해 변경 없이 유지한다.

## 왜 기다리나

프론트 몫은 전부 백엔드가 `execute_sql`(그리고 `run_simulation`) 결과에 새로 싣는 `type`/`result_id`/`sample_rows`/`summary` 필드에 의존한다. 이 계약은 백엔드 Task 2~3에서 코드로 굳는다. 그 전에 만들면 형태를 추측한 더미를 만들고 나중에 다시 맞추게 된다 — 도메인 지식 연동 때 `database-result.tsx`의 `table.{columns,rows}` 형태가 계획과 실제가 달랐던 사례([frontend/plan/domain-knowledge-plan.md](domain-knowledge-plan.md) 실행 기록 참고)가 반복될 수 있다.

## 착수 조건

다음이 전부 성립하면 시작한다.

```bash
cd backend
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
# 소량 결과 질의 → tool_result.data 에 result_id, type: "inline" 확인
# 대량 결과 질의(200행 초과) → tool_result.data 에 type: "large_result",
#   table 필드 없음, columns/sample_rows/summary 확인, truncated 필드는 더 이상 없음
```

백엔드 계획 Task 5(결정 기록)에 실제 응답 JSON 예시가 남아 있으면 그것을 1차 기준으로 삼는다 — 이 문서의 JSON 스니펫과 실제가 다르면 실제를 따르고 그 차이를 이 문서 끝 "실행 기록"에 남긴다.

## 작업 목록

실행 세션은 `frontend/`에서 `claude --model sonnet`으로 열고 [frontend/CLAUDE.md](../CLAUDE.md) 규칙을 따른다(특히 폐쇄망 원칙, 디자인 토큰 규칙). 새 패키지는 없다.

설계 문서에 없던 판단을 내릴 때마다 이 문서 끝 "실행 기록" 절에 무엇을 왜 그렇게 정했는지 바로 남긴다 — 다른 세션이 이력을 추적할 수 있어야 한다(`plan/CLAUDE.md` 관례). 실행 에이전트가 Claude Code가 아니어도(Codex 등) 동일하게 적용한다.

### 1. `database-result.tsx` — `large_result` 요약 카드 분기

[database-result.tsx](../src/components/chat/tool-results/database-result.tsx)가 현재 `data.table.{columns,rows}`(없으면 최상위 `columns`/`rows`로 폴백)를 읽고 `truncated === true`면 안내 문구를 붙인다. 이 파일을 다음과 같이 고친다.

- `data.type === "large_result"`인 경우: 기존 표 렌더링 경로를 타지 않는다. 대신
  - 헤더에 `row_count`(전체 행 수)를 표시.
  - `sample_rows`(대개 5행)를 작은 미리보기 표로 렌더 — 기존 표 컴포넌트를 그대로 재사용하되 "샘플" 배지를 붙인다.
  - `summary`(컬럼별 `{min, max, mean, null_count}`)를 정의 목록 또는 작은 통계 카드로 렌더.
  - 페이지네이션이나 "더 보기" 버튼은 두지 않는다(설계 §7 "추가 조회 UI는 두지 않는다" — 후속 질의는 대화로 처리된다, §9).
- `data.type === "inline"`(또는 `type` 필드가 없는 과거 형태와의 호환은 고려하지 않는다 — 백엔드가 항상 새 계약으로 응답하므로): 기존 표 렌더링 경로를 그대로 유지.
- `truncated` 관련 안내 문구(있다면)를 제거한다 — 더 이상 백엔드가 이 필드를 보내지 않는다.
- `result_id`는 이번 범위에서 화면에 노출하지 않는다(설계 §7 "프론트는 저장소에 직접 접근하지 않는다" — 사용자가 `result_id`를 직접 조작할 UI는 없다). 필요하면 개발자 디버깅용으로만 작게(예: 툴팁) 남긴다.

`run_simulation` 결과(`실적_조회`의 `results` 배열)도 같은 `type`/`result_id` 필드를 받는다(백엔드 Task 3) — 이 결과를 렌더하는 컴포넌트(`simulation-result.tsx` 등 `tool-results/` 내 시뮬레이션 카드)가 있으면 같은 방식으로 `large_result` 분기를 추가한다. 대상 파일은 착수 시점에 `frontend/src/components/chat/tool-results/`를 확인해 정확히 특정한다 — 이 문서 작성 시점 기준 `simulation-result.tsx`로 추정된다.

### 2. `shared.ts` 타입/헬퍼 정리

[shared.ts](../src/components/chat/tool-results/shared.ts)에 `database`/`simulation` kind의 payload 형태를 좁혀 쓰는 타입이나 헬퍼가 있으면, `type: "inline" | "large_result"` 판별을 위한 타입 가드나 공용 헬퍼(예: `isLargeResult(data)`)를 추가해 `database-result.tsx`와 시뮬레이션 결과 컴포넌트가 같은 판별 로직을 중복 작성하지 않게 한다. `frontend/src/types/chat.ts`의 `ToolResult.data`는 여전히 자유형 `Record<string, unknown>`으로 유지한다(백엔드 `AgentEvent.data`가 자유형이므로 pydantic/TS 모델 변경이 필요 없다 — 설계 §5) — `chat.ts`는 건드리지 않는다.

### 3. `agent-progress.tsx` — 대용량 결과 후속 조회 표시(선택)

[agent-progress.tsx](../src/components/chat/agent-progress.tsx)가 `execute_sql` 뒤에 오는 `tool_result.data.purpose`를 표시하는 것과 같은 방식으로, `get_result_summary`/`get_result_page` tool 호출이 진행 표시에 뜨는지 확인한다. 별도 라벨이 없으면(백엔드가 `TOOL_META`류 매핑 없이 일반 tool 호출로만 처리한다면) `tool-result-card.tsx`의 `TOOL_META`에 두 항목을 추가한다.

| tool_name | label | kind |
| --- | --- | --- |
| `get_result_summary` | 결과 요약 조회 | `database` |
| `get_result_page` | 결과 구간 조회 | `database` |

`get_result_page` 응답(`{result_id, offset, limit, row_count, rows}`)은 이번 범위에서 기존 표 컴포넌트(`database-result.tsx`의 inline 표 렌더 경로)를 그대로 재사용해 표시한다 — 별도 컴포넌트를 만들지 않는다.

## 검증

```bash
cd frontend && npm run lint && npm run build
```

- `PLANNING_AGENT_FAKE=1` 백엔드에 소량 조회 질의를 보내면 기존과 동일하게 표가 뜬다(회귀 없음).
- 200행 초과 대량 조회 질의를 보내면 표 대신 요약 카드(샘플 몇 행 + 통계)가 뜨고, `truncated` 관련 문구가 보이지 않는다.
- "방금 결과에서 B라인만 다시" 같은 후속 질의를 보내면 에이전트가 `get_result_page`(또는 필터링된 새 `execute_sql`)를 호출하고 그 결과가 새 `AgentEvent`로 렌더된다 — UI에 별도 "더 보기" 버튼이 없다는 것을 확인한다.
- 폭 400px에서 요약 카드가 가로 스크롤을 만들지 않는다.

## 이후

3차(재사용 연산: `filter_result`/`aggregate_result`)와 2차(차트, [docs/chart-visualization.md](../../docs/chart-visualization.md))는 이 계획 범위 밖이다. 차트는 `GET /api/results/{id}/chart`를 쓰는 별도 API라 이 문서가 다루는 raw 조회 요약 카드와 무관하다(설계 §7 "차트와의 관계").

## 실행 기록

**상태: 완료 (2026-09-15).**

- 백엔드 계획(`backend/plan/260915-result-store-plan.md`) Task 0~6 전부 완료 확인. `pyarrow` 의존성, `ResultStore`/`LocalParquetResultStore`, `execute_sql`/`run_simulation`의 `result_id`/`type` 반환, `get_result_summary`/`get_result_page` tool 등록, TTL 정리까지 실제 코드에 반영되어 있고 `pytest -q` 156개 전부 통과.
- 착수 조건도 재확인: mock service(`execute_sql`)를 직접 호출해 이 문서의 JSON 스니펫이 백엔드 결정 기록의 실제 응답과 정확히 일치함을 확인(`type: "large_result"`, `columns[].{name,dtype,role}`, `sample_rows`, `summary[col].{min,max,mean,null_count}`).
- **공용 헬퍼 위치**: `isLargeResult`/`asResultColumns`/`asResultSummary`를 계획대로 `shared.ts`에 추가했다. 요약 카드 자체는 `database-result.tsx`/`simulation-result.tsx` 양쪽에서 재사용해야 해서 계획에 없던 새 파일 `tool-results/result-summary.tsx`(`ResultSummaryCard`)를 만들었다 — 계획 Task 1은 "기존 표 컴포넌트를 재사용"만 언급했지 요약 카드 자체를 어디 둘지는 정하지 않았음.
- **`get_result_page` 표 재사용 이슈**: 계획 Task 3은 "`get_result_page` 응답을 `database-result.tsx`의 inline 표 렌더 경로로 재사용"이라고만 적었는데, 실제 `tools/result_tool.py`의 `get_result_page` 반환값에는 `columns` 필드가 없다(`{result_id, offset, limit, row_count, rows}`뿐). 컬럼명이 없으면 기존 inline 경로가 `columns.length === 0`로 `null`을 반환해 아무것도 안 보였다. `database-result.tsx`에 `declaredColumns`가 없을 때 `rows[0]`의 인덱스를 문자열 헤더(`"0"`, `"1"`, ...)로 쓰는 폴백을 추가해 표가 항상 보이게 했다 — 별도 컴포넌트는 만들지 않았다(계획 취지 유지).
- **`run_simulation` 시뮬레이션 컴포넌트 특정**: 계획이 "추정"이라 적어둔 대로 실제로 `simulation-result.tsx`가 맞았다. `results` 배열이 `isLargeResult(data)`면 기존 `DataTable` 렌더 대신 `ResultSummaryCard`로 분기했다(`data.table` 상세 접기 블록은 그대로 유지 — 그건 별개 필드).
- **`truncated` 필드 제거**: `database-result.tsx`에 있던 `truncated === true` 안내 문구를 완전히 제거했다(백엔드가 더 이상 이 필드를 보내지 않음). `MAX_ROWS` 가드레일 자체와는 무관하므로 그 로직은 건드리지 않았다.
- **`agent-progress.tsx`(Task 3 선택 항목)**: 실제로 확인해보니 진행 단계 `status` 이벤트의 `label`은 `agent-progress.tsx`가 아니라 백엔드 `event_adapter.py`가 `f"{tool_name} 실행"`/`f"{tool_name} 완료"` 형태로 항상 자동 생성한다(도구별 한글 라벨을 프론트가 개입할 지점이 없음). 계획 표는 사실 `tool-result-card.tsx`의 `TOOL_META`(결과 카드 헤더 라벨)를 가리키는 것이었고, 그쪽에 `get_result_summary`/`get_result_page` 두 항목을 계획대로 추가했다. `agent-progress.tsx` 자체는 수정하지 않았다(별도 라벨 매핑 지점이 아니므로).
- **검증**: `npm run lint && npm run build` 통과. 시각 검증은 Fake Runner가 고정 88행 쿼리만 실행해 대량 케이스를 못 만들기 때문에, mock `execute_sql`을 직접 호출해 얻은 실제 대량 응답을 dummy 대화에 임시로 대입 → Playwright로 데스크톱/400px 폭 양쪽에서 요약 카드(전체 500행 배지, 샘플 5행 표, 컬럼별 역할 배지, min/max/평균 통계) 렌더링과 가로 스크롤 없음을 스크린샷으로 확인 → 검증 후 `git checkout`으로 `dummy.ts` 원상복구(이 변경은 계획 범위 밖이라 커밋에 남기지 않음).
- 3번(선택, `agent-progress.tsx` 라벨 확인)을 제외한 계획 전 항목을 반영했다.
- **임계값·샘플 행 수 조정 (사용자 요청, 커밋 직전)**: `INLINE_ROW_THRESHOLD`를 200→100행, `sample_rows` 슬라이스를 5→10행으로 낮췄다(`backend/services/mock/mock_sql_service.py`, `backend/services/mock/mock_simulation_service.py` 양쪽에 중복 정의된 상수 모두 수정, `SAMPLE_ROW_COUNT` 상수로 명명). `docs/result-store.md` §1과 "열린 질문"의 "200행" 서술도 100행으로 갱신했다. 완료된 백엔드 실행 계획(`backend/plan/260915-result-store-plan.md`)은 저장소 관례상 소급 수정하지 않았다 — 그 문서는 Task 실행 당시(200/5) 이력으로 남긴다. 프론트 쪽은 `ResultSummaryCard`가 이미 `sampleRows.length`를 동적으로 배지에 쓰고 있어 코드 변경이 필요 없었다. `backend/pytest -q` 156개 재확인, mock `execute_sql` 직접 호출로 `sample_rows` 길이 10 확인.
