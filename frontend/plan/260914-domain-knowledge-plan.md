# 도메인 지식 연동 계획 (프론트엔드)

**상태: 완료 (2026-09-14).** 백엔드 Phase 1 완료 후 작업 1~4 전부 실행. 상위 요구사항은 [도메인 지식 통합 계획](../../plan/260914-domain-knowledge-plan.md), 백엔드 실행 이력은 [백엔드 계획](../../backend/plan/260914-domain-knowledge-plan.md)을 따른다.

## 왜 기다리나

프론트 몫은 전부 백엔드 계약(지식 API 3개, `tool_result.data.kind = "catalog"` payload, `execute_sql`의 `purpose`)에 의존한다. 이 계약은 백엔드 Task 5·8·10에서 코드로 굳는데, 그 전에 프론트를 만들면 더미를 또 만들고 나중에 다시 맞추게 된다. 지금 `context-inspector.tsx`의 Skills 탭이 더미로 남아 있는 것과 같은 상황이 반복된다. 프론트 작업량은 하루 안쪽이라 기다리는 비용이 작다.

## 착수 조건

다음이 전부 성립하면 시작한다.

```bash
cd backend
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
curl -s localhost:8000/api/knowledge/skills      # [{name, description, status}] 반환
# 채팅 한 번 보내면 SSE 에 tool_result data.kind 가 "catalog" 인 이벤트가 온다
```

## 작업 목록

실행 세션은 `frontend/`에서 `claude --model sonnet`으로 열고 [frontend/CLAUDE.md](../CLAUDE.md) 규칙을 따른다. 새 패키지는 없다.

### 1. `tool-result-card.tsx`의 도구 매핑 갱신

[tool-result-card.tsx](../src/components/chat/tool-result-card.tsx)의 `TOOL_META`가 삭제된 도구(`query_database`, `simulate_*`)를 아직 가리킨다. 백엔드 `TOOL_NAMES` 8개에 맞춘다.

| tool_name | label | kind |
| --- | --- | --- |
| `execute_sql` | 데이터 조회 | `database` |
| `search_knowledge` | 공정 문서 검색 | `knowledge` |
| `list_simulation` | 시뮬레이션 목록 | `simulation` |
| `run_simulation` | 시뮬레이션 실행 | `simulation` |
| `list_tables` | 테이블 목록 | `catalog` |
| `describe_table` | 테이블 상세 | `catalog` |
| `list_kpis` | KPI 목록 | `catalog` |
| `get_kpi` | KPI 정의 | `catalog` |

`Kind` 타입에 `"catalog"` 추가. `resolveKind`의 `dataKind` 분기에도 `"catalog"` 추가.

### 2. `catalog-result.tsx` 접힘 카드

`src/components/chat/tool-results/catalog-result.tsx` 신규. 기존 [knowledge-result.tsx](../src/components/chat/tool-results/knowledge-result.tsx)는 RAG 결과용이므로 건드리지 않는다.

payload:

```jsonc
{ "kind": "catalog", "catalog_type": "table" | "kpi" | "table_list" | "kpi_list", "verified": true, "data": { ... } }
```

- 분석 한 번에 지식 조회가 4~6회 발생하므로 **기본 접힘**. `Tool`의 `defaultOpen`을 `catalog`일 때 false로.
- 헤더 한 줄: `catalog_type`별로 `table` → `data.table`, `kpi` → `data.name`, `*_list` → `n건`. `verified === false`면 "미검증" 배지(`shared.ts`의 `ResultTone` `warn`).
- 펼치면 `table`은 컬럼 목록(name·type·desc)을 [primitives.tsx](../src/components/chat/primitives.tsx)의 `DataTable`로, `kpi`는 definition·formula·shortfall_rule을 정의 목록으로, `*_list`는 이름·설명 목록으로. 나머지 필드는 표시하지 않는다.
- `database` kind는 변경 없음. `execute_sql` 결과의 `table.columns`/`table.rows` 형태가 [database-result.tsx](../src/components/chat/tool-results/database-result.tsx)가 기대하는 형태와 같은지 확인만 한다.

### 3. `agent-progress.tsx`에 `purpose` 표시

[agent-progress.tsx](../src/components/chat/agent-progress.tsx)에서 `tool_call`이 `execute_sql`이면 그 뒤에 오는 `tool_result.data.purpose`를 진행 항목 라벨 옆에 한 줄로 붙인다. `purpose`가 없으면 기존 표시 그대로.

### 4. Skills 탭을 API에 연결

- [types/workspace.ts](../src/types/workspace.ts)의 `Skill`을 API 응답 `{name, description, status}`에 맞춘다. `toolName`·`enabled`·`lastCalledAt`은 제거한다. `enabled` 토글은 켜고 끄는 의미가 정해지지 않아 보류(설계 §7).
- `src/lib/api.ts`(또는 기존 fetch helper)에 `fetchKnowledgeSkills()` 추가. 백엔드 주소는 기존 chat 호출과 같은 설정을 쓴다.
- [context-inspector.tsx](../src/components/chat/context-inspector.tsx) Skills 탭이 `dummy.ts` 대신 이 결과를 그린다. 토글 UI 제거. 로딩·오류 상태는 [connection-banner.tsx](../src/components/chat/connection-banner.tsx)와 같은 톤으로.
- `catalog`·`kpis` 엔드포인트는 이번에 쓰지 않는다. Metadata 탭 확장은 별도 결정.

## 검증

```bash
cd frontend && npm run lint && npm run build
```

- `PLANNING_AGENT_FAKE=1` 백엔드에 채팅을 보내 `get_kpi` → `execute_sql` → `run_simulation` 순으로 카드가 뜨고, `get_kpi` 카드가 접힌 채 "FGS 입고 실적 · 미검증"으로 보인다.
- Skills 탭에 `kpi-shortfall-analysis`, `sql-analysis`, `simulation` 3개가 API에서 온다.
- 폭 400px에서 카드가 가로 스크롤을 만들지 않는다.

## 이후

백엔드 Phase 2에서 시나리오가 늘어나도 프론트 계약은 바뀌지 않는다. `catalog`·`kpis` 엔드포인트를 쓰는 지식 브라우저 UI는 필요가 확인되면 별도 문서로 결정한다.

## 실행 기록 (2026-09-14)

- 작업 1~4 완료. `npm run lint` · `npm run build` 통과, 폭 400px 가로 넘침 0px, 콘솔 에러 없음.
- **계획에 없던 수정 — `database-result.tsx` payload 형태**: 백엔드 `execute_sql` 은 컬럼·행을
  `data.table.{columns,rows}` 에 담는데 기존 컴포넌트는 최상위 `data.columns`/`data.rows` 를
  읽고 있었다. 계획 2번의 "형태가 같은지 확인만 한다"는 확인 결과 **달랐고**, 그대로 두면 표가
  비어 렌더된다. `table` 우선, 없으면 최상위로 폴백하게 고쳤다. `truncated` 안내도 함께 추가.
- **`purpose` 중복 표시 방지**: `detail` 이 step `label` 과 같은 문구면 반복 출력하지 않는다.
  fake_runner 가 purpose 를 label 로도 쓰고 있어 "계획 대비 입고 달성률"이 두 번 보였다.
- **백엔드 `fake_runner` step 키 정리(프론트 검증 중 발견)**: 완료 `status` 이벤트의 `step` 이
  `tool_call` 이 만든 항목 키(`run_simulation`)와 달라(`simulation`) 진행 표시에 완료되지 않는
  단계가 남았다. `plan` 단계도 완료 이벤트가 없었다. 둘 다 백엔드에서 수정.
- Skills 탭 토글 UI 제거, `dummy.ts` 의 `SKILLS` 삭제. `catalog`·`kpis` 엔드포인트는 계획대로 미사용.
