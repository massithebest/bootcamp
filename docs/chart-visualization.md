# 에이전트 응답 차트/그래프 시각화 검토

**상태: 설계 논의 완료, 구현 착수 전.** 백엔드/프론트엔드 양쪽에 걸친 결정이라 최상위 `docs/`에 둔다. 각 하위 프로젝트에서 실제 구현에 들어갈 때 이 문서를 출발점으로 삼는다.

## 배경

에이전트 응답 결과(`query_database`, `run_simulation` 등 tool 결과)를 표뿐 아니라 그래프/도표/간트차트로도 표현하고, 에이전트가 어떤 tool을 호출하고 어떤 계획을 진행 중인지 보여주는 요구사항이 나왔다. 이 문서는 전자(데이터 시각화)를 다룬다. 후자(진행상태 표시)는 이미 결론이 나 있다 — [frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토](../frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토) 및 `frontend/src/components/chat/agent-progress.tsx`의 기존 커스텀 구현(`AgentEvent`의 `status`/`tool_call`/`tool_result`) 유지, 신규 패키지 도입 불필요로 결론.

## 1. 차트 라이브러리 선택

프론트엔드 기존 스택: Next.js 14 · React 18 · Tailwind v4 · shadcn/ui (자세한 배경은 [frontend/CLAUDE.md](../frontend/CLAUDE.md), [frontend/docs/decisions.md#shadcnui-도입](../frontend/docs/decisions.md#shadcnui-도입)). 폐쇄망 배포 원칙([frontend/docs/closed-network.md](../frontend/docs/closed-network.md)) 적용 대상.

| 후보 | 결론 | 근거 |
| --- | --- | --- |
| **Recharts** | **채택** | shadcn/ui 공식 `chart` 컴포넌트가 이를 감싸는 래퍼 — CLI로 `add chart` 시 소스 복사, 기존 shadcn 토큰(`--shadcn-*` 매핑) 위에서 그대로 동작. `npm view recharts` 확인 결과 React 18 peer dep 지원(`^18.0.0` 포함), 런타임 의존성(Redux Toolkit, immer, d3 벤더 번들 등) 전부 순수 연산 라이브러리라 하드코딩된 외부 URL 없음 — 폐쇄망 체크리스트 통과. v3부터 `sideEffects: false` + ESM으로 트리셰이킹 지원. |
| visx | 보류 | 번들 최소(~15KB)지만 D3 원시 API 수준이라 조립 비용 큼. 지금 요구사항엔 과함 — 커스텀 시각화가 실제로 필요해지면 재검토. |
| Nivo | 제외 | 자체 스타일 시스템이 강해 shadcn 토큰과 이중화 위험 (Chatscope 때와 같은 패턴의 문제). |
| **SVAR React Gantt** | **간트 전용으로 채택** | 오픈소스 코어 MIT 라이선스, React 18/19 지원, 활발히 유지보수. 단 critical path·baseline·export 등 고급 기능은 유료 PRO 티어 — 지금은 무료 코어 범위(기본 일정 바 표시)로 충분하다고 판단, 고급 기능 필요 시 별도 라이선스 검토. |
| gantt-task-react | 제외 | MIT지만 4년간 미유지보수. |
| AI Elements / assistant-ui / CopilotKit / Chatscope 등 | 해당 없음 | 이들은 채팅/tool-call UI 라이브러리로, 데이터 시각화와는 무관한 카테고리. [frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토](../frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토) 참고. |

## 2. 백엔드 응답 스키마

기존 `AgentEvent`(`backend/api/schemas.py`) 계약은 바꾸지 않는다. `tool_result` 이벤트의 `data`(자유형 `dict[str, Any]`) 안에 **선택적** `chart` 필드를 추가하는 방식 — 표 렌더링을 대체하지 않고 병렬로 얹는다.

```jsonc
// query_database 결과 예시
{
  "kind": "database",
  "sql": "...",
  "table": { "columns": [...], "rows": [...] },
  "chart": {
    "type": "bar",            // "bar" | "line" | "pie" | "gantt"
    "x": "line_name",
    "series": [{ "key": "output_qty", "label": "생산량" }]
  }
}
```

```jsonc
// 간트 예시 (simulate_* 결과 등)
{
  "kind": "simulation",
  "chart": {
    "type": "gantt",
    "tasks": [
      { "id": "L1", "label": "1라인", "start": "2026-09-01", "end": "2026-09-05" }
    ]
  }
}
```

`chart`는 optional이다 — 시각화할 가치가 없는 결과(컬럼이 너무 많거나 row가 과도하게 많은 경우 등)는 채우지 않고 표만 남긴다.

## 3. 차트 생성 위치 — 별도 tool 불필요

**결론: "차트 생성" 전용 tool은 만들지 않는다.**

- 차트 `chart` 필드는 실제 렌더링과 무관한 순수 메타데이터(타입 + 축 매핑)이므로 새 tool 호출로 왕복시킬 이유가 없다.
- LLM이 별도 tool에 데이터를 다시 자연어로 옮겨 넘기게 하면 숫자 transcription 오류나 스키마 임의 변경 위험이 생긴다.
- `sql_service.generate_and_query()` / `simulation_service.run_simulation()`이 이미 갖고 있는 실제 결과(`table.rows`, `kpis`)를 그 자리에서 그대로 보고 `chart`를 조립하면 데이터 왕복 없이 결정론적으로 일치한다.

적용 위치: `backend/services/*/sql_service.py`, `backend/services/*/simulation_service.py`의 결과 조립부. `backend/tools/sql_tool.py`, `backend/tools/simulation_tool.py` 자체는 지금처럼 얇은 패스스루로 유지.

## 4. 차트 타입 판단 로직

**우선순위: LLM 힌트 → 없으면 데이터 shape 규칙 → 그래도 없으면 차트 생략.**

### 4.1 LLM 힌트 (override, optional)

`query_database` / `run_simulation` tool signature에 optional 파라미터 추가:

```python
async def query_database(
    question: str,
    chart_type_hint: Literal["bar", "line", "pie", "gantt", "none"] | None = None,
) -> dict:
    """...
    chart_type_hint: 사용자가 특정 시각화(추이=line, 비교=bar, 일정=gantt 등)를
    명시적으로 요청했을 때만 지정. 불확실하면 생략 — 데이터 형태로 자동 판단됨.
    """
```

docstring에 "불확실하면 생략"을 명시해 LLM이 애매한 케이스에서 억지로 고르지 않게 한다.

### 4.2 데이터 shape 기반 규칙 (힌트 없을 때 폴백, 서비스 레이어의 결정론적 함수)

```python
def _infer_chart(columns: list[str], rows: list[list]) -> ChartSpec | None:
    ...
```

- 컬럼이 `[카테고리, 숫자]` 1~2개 → **bar**
- 컬럼에 날짜/월 축 + 숫자 시계열 → **line**
- 컬럼이 `[카테고리, 비율]`이고 합이 100%에 가까움 → **pie** (오용되기 쉬워 지원 자체를 재검토할 수 있음)
- `start`/`end`(또는 `기간`) 필드를 가진 작업/라인 목록 → **gantt**
- 숫자 컬럼 3개 이상이거나 row가 과도하게 많음(예: 50+) → 생략, 표만

### 4.3 힌트와 shape 충돌 시 처리

```
chart_type_hint 있음
  └─ 해당 타입에 필요한 컬럼(예: line/bar면 카테고리+숫자, gantt면 start/end)이 있는가?
       ├─ 있음 → 그 타입으로 생성
       └─ 없음 → 생략 (규칙 기반 폴백으로 다른 타입을 자동 선택하지 않음 —
                 사용자가 요청한 타입과 다른 게 나오면 더 혼란스럽다)
hint 없음
  └─ shape 규칙으로 추론 → 매칭 없으면 생략
```

hint는 "타입 선택권"만 주고, "그릴 수 있는 축이 실제로 있는가"는 항상 shape 검증을 통과해야 한다. 즉 판단/검증 로직 자체는 항상 서비스 레이어(결정론적 코드)에 있어 테스트 가능하다.

## 5. 프론트엔드 렌더링 파이프라인

`frontend/src/components/chat/tool-result-card.tsx`의 기존 kind 분기 패턴을 그대로 따른다. 2026-09-14부터 이 카드는 AI Elements `Tool`/`ToolOutput`으로 감싸져 있고([frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토](../frontend/docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토) §적용 범위), `ToolOutput`의 `output`은 ReactNode 슬롯이라 차트도 같은 자리에 들어간다.

```
ToolResultCard (AI Elements Tool > ToolHeader + ToolContent > ToolOutput)
 └─ (kind별 결과 컴포넌트: DatabaseResult / SimulationResult / ...)
      └─ data.chart 있으면 → <ChartBlock chart={data.chart} />
```

`ChartBlock`은 `chart.type`으로 다시 분기하는 얇은 스위치:

```tsx
function ChartBlock({ chart }: { chart: ChartSpec }) {
  switch (chart.type) {
    case "bar": return <BarChartView {...chart} />;
    case "line": return <LineChartView {...chart} />;
    case "pie": return <PieChartView {...chart} />;
    case "gantt": return <GanttView {...chart} />;
  }
}
```

- bar/line/pie: Recharts (shadcn `chart` 컴포넌트 기반)
- gantt: SVAR React Gantt 무료 코어
- 각 View는 `DatabaseResult`/`SimulationResult`가 이미 하듯 `table.rows`/`chart.tasks`를 그대로 받아 그리기만 한다 — 데이터 변환/집계는 백엔드 책임, 프론트는 순수 렌더러로 유지.

구현 시 추가될 파일(예상):
- `frontend/src/types/chat.ts` — `ChartSpec` 유니온 타입 추가
- `frontend/src/components/chat/tool-results/chart-block.tsx` — 타입 분기 스위치
- `frontend/src/components/chat/tool-results/charts/` — `bar-chart-view.tsx`, `line-chart-view.tsx`, `pie-chart-view.tsx`, `gantt-view.tsx`

## 열린 질문 / 다음 단계

- pie 차트를 실제로 지원할지 — 오용 위험이 커서 bar/line/gantt 3종만으로 시작하고 필요성이 명확해지면 추가하는 방안도 있음.
- `_infer_chart` shape 규칙의 임계값(컬럼 수, row 수 등)은 실제 데이터로 튜닝 필요 — 지금은 추정치.
- `chart_type_hint`가 tool signature에 추가되면 `backend/agent/system_prompt.py`에 사용 가이드를 반영해야 함 (언제 지정하고 언제 생략할지).
- SVAR React Gantt 무료 코어의 실제 기능 범위(드래그, 의존성 표시 등)를 구현 전에 한 번 더 확인 — 지금은 문서 조사 수준.
- 구현 순서: (1) 백엔드 `ChartSpec` pydantic 모델 + `_infer_chart` 규칙 함수 + `sql_service`/`simulation_service` 연동 → (2) 프론트 `ChartSpec` 타입 + `ChartBlock` + Recharts 3종 → (3) 간트(SVAR) 별도 스파이크.

## 관련 문서

- [frontend/docs/decisions.md](../frontend/docs/decisions.md) — 결정 사항 기록 전체 (ai SDK/채팅 UI 라이브러리 검토, shadcn 도입 경위·토큰 네임스페이싱 포함)
- [frontend/docs/closed-network.md](../frontend/docs/closed-network.md) — 폐쇄망 원칙, 신규 의존성 체크리스트
- [frontend/CLAUDE.md](../frontend/CLAUDE.md) — 프론트엔드 작업 지침 전반
