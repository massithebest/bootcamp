# 차트 v2 연동 계획 (프론트엔드)

**상태: 백엔드 계약 대기.** 기준 설계는
[docs/chart-visualization.md](../../docs/chart-visualization.md)이고,
백엔드 구현 순서는 [backend 차트 v2 계획](../../backend/plan/260915-chart-v2-plan.md)을 따른다.

프론트는 LLM이 만든 HTML이나 원시 축 명세를 실행하지 않는다.
최종 답변의 chart 마커에서 visualization_id만 읽고,
검증된 렌더링 payload를 백엔드에서 조회해 기존 Recharts 컴포넌트로 표시한다.

~~~text
최종 답변의 visualization_id
  → GET /api/visualizations/{visualization_id}
  → 검증된 ChartSpec
  → ChartBlock
~~~

기존 계획의 GET /api/results/{id}/chart 호출과 result_id + type/x/y 마커는 폐기한다.
차트의 집계·컬럼 선택은 브라우저가 수행하지 않는다.

## 착수 조건

백엔드 계획 Task 0~6이 완료되고 다음 계약이 실제 API와 테스트로 고정되어야 한다.

- prepare_visualization이 성공한 visualization_id를 반환한다.
- GET /api/visualizations/{visualization_id}가 아래 payload를 반환한다.
- 접근 scope의 브라우저 전달 방식과 credentials 설정이 정해져 있다.
- 오류 상태, 표시 한도, schema_version, TTL이 확정되어 있다.
- inline/large SQL 및 표형 시뮬레이션 결과가 동일한 컬럼 메타데이터를 제공한다.

~~~json
{
  "visualization_id": "b8c19235da17461ab3e8ec82a942f017",
  "result_id": "a30f90f8da934a35a931ba694e130a65",
  "schema_version": 1,
  "expires_at": "2026-09-16T00:00:00+00:00",
  "chart": {
    "type": "line",
    "x": "work_month",
    "series": [
      {"key": "series_0", "label": "actual"}
    ],
    "categories": ["2026-07", "2026-08"],
    "data": [
      {"work_month": "2026-07", "series_0": 100}
    ],
    "title": null,
    "x_label": "work_month",
    "y_label": null,
    "unit": null
  },
  "warnings": [
    {"code": "SOURCE_TRUNCATED", "message": "조회 결과가 저장 한도에서 잘렸습니다."}
  ]
}
~~~

백엔드 예시와 한 필드라도 다르면 프론트 타입을 추측해서 만들지 않고
두 계획과 기준 설계를 먼저 맞춘다.

## 실행 세션 시작 방법

frontend 디렉터리에서 시작한다. 첫 요청에는 다음 내용을 포함한다.

> plan/260915-chart-v2-plan.md의 착수 조건을 실제 백엔드 응답으로 확인한 뒤
> Task 0부터 순서대로 실행해 줘. 설계에 없던 판단을 내릴 때마다 문서 끝
> 실행 기록에 무엇을 왜 정했는지 즉시 남겨 줘.

새 패키지는 추가하지 않는다. custom fetch/ReadableStream SSE,
애플리케이션 소유 메시지 상태, useExternalStoreRuntime 구조를 유지한다.

## Task 0. assistant-ui 마크다운 확장 방식 확인

**파일:** 이 계획의 실행 기록, 필요 시 frontend/docs/decisions.md

**스펙:**

구현을 시작할 때 assistant-ui markdown Skill을 읽고 현재 설치 버전의 타입 선언을 확인한다.
MarkdownTextPrimitive의 code/pre override로 fenced chart block을 가로채는 방식,
메시지 실행 상태를 읽는 방식, 스트리밍 중 컴포넌트 수명주기를 확인한다.

이 확인은 API나 런타임 교체를 위한 것이 아니다. 기존 components override 안에서
chart 전용 렌더러로 위임할 수 있는 최소 변경을 선택한다.
공식 패턴과 현재 코드가 충돌할 때만 frontend/docs/decisions.md에 결정을 추가한다.

**검증:**

- 확인한 Skill·설치 버전·선택한 확장 지점을 실행 기록에 남긴다.
- useExternalStoreRuntime과 기존 SSE transport를 바꾸지 않는지 확인한다.

**완료 기준:** chart marker가 어느 컴포넌트에서 실행 상태를 읽고 렌더러로 위임할지 확정된다.

---

## Task 1. API 계약과 안전한 파서

**파일:** src/types/chat.ts, src/lib/visualization-api.ts(신규),
src/components/chat/tool-result-card.tsx, 필요 시 .env.example

**스펙:**

1. VisualizationWarning, VisualizationChartSpec, VisualizationResponse 타입을
   백엔드 Task 0의 schema_version 1 계약과 동일하게 추가한다.
2. 기존 ChartSpec은 렌더링 타입으로 정리한다.
   title, x_label, y_label, unit의 null/생략 규칙과 warnings의 위치를 계약대로 반영한다.
   v1의 truncated/hiddenCount는 전환 기간에만 호환하고 Task 5에서 제거한다.
3. parseVisualizationResponse를 작성해 unknown payload를 검증한다.
   type, x, series, categories, data, schema_version과 ID 형태를 확인하며
   JSON을 곧바로 타입 단언하지 않는다.
4. fetchVisualization(id, options)를 추가한다.
   API_BASE_URL을 재사용하고 Task 0에서 정한 credentials/access scope를 포함한다.
   AbortSignal을 받고 404·410·접근 불가·기타 오류를 사용자용 상태로 정규화한다.
5. prepare_visualization tool 카드에는 명확한 레이블을 추가한다.
   성공 ID는 디버깅 가능한 접힌 generic 결과로 둘 수 있지만,
   tool 카드 안에 차트를 렌더링하지 않는다.

외부 provider나 parquet에 직접 접근하지 않는다. type/x/y query parameter를 만들지 않는다.

**검증:**

현재 프론트에는 자동 테스트 명령이 없으므로 순수 파서는 별도 의존성 없이 테스트 가능한
함수로 두고, 테스트 기반이 추가되지 않았다면 build/lint와 수동 malformed payload로 확인한다.

~~~bash
cd frontend
npm run build
npm run lint
~~~

필수 확인:

- 유효한 schema_version 1 payload만 통과한다.
- 잘못된 ID, 알 수 없는 차트 type, 비정상 series/data를 거부한다.
- access scope 불일치와 존재하지 않는 ID의 상세 정보를 과도하게 노출하지 않는다.
- fetch 취소는 일반 오류 메시지로 표시되지 않는다.

**완료 기준:** 컴포넌트가 검증되지 않은 API 값을 ChartBlock에 전달하지 않는다.

---

## Task 2. ID 전용 chart 마커 렌더러

**파일:** src/components/chat/markdown-text.tsx,
src/components/chat/tool-results/chart-marker.tsx(신규),
필요 시 src/lib/chart-marker.ts(신규)

**스펙:**

최종 답변에서 다음 fenced block만 시각화 마커로 인정한다.

~~~~text
```chart
{"visualization_id":"b8c19235da17461ab3e8ec82a942f017"}
```
~~~~

- JSON 객체는 visualization_id 하나만 허용한다.
  result_id, kind, x, y, group_by, data, HTML 같은 필드가 있으면 거부한다.
- visualization_id는 백엔드와 같은 형식으로 검증한다.
- MarkdownText의 Code 분기에서 language-chart만 ChartMarker로 위임한다.
- Pre는 chart code child일 때 코드블록 셸을 씌우지 않고 child를 그대로 반환한다.
  다른 fenced code와 inline code의 현행 스타일은 유지한다.
- ChartMarker는 현재 assistant 메시지의 running/terminal 상태를 읽는다.
  불완전 JSON이면서 running이면 로딩 상태, complete/cancelled/error면 잘못된 마커 오류로 바꾼다.
  JSON.parse 성공만으로 fetch하지 않고 전체 스키마 검증 후 호출한다.
- 유효한 ID는 Task 1의 조회 계층에 전달하고 성공 시 ChartBlock을 렌더한다.
- 생성 HTML이나 JavaScript를 삽입하는 경로, dangerouslySetInnerHTML은 추가하지 않는다.

파싱을 순수 함수로 분리해 완전·불완전·금지 필드·잘못된 ID 케이스를 재현 가능하게 한다.

**검증:**

- 일반 코드펜스와 inline code 렌더링에 회귀가 없다.
- streaming 중 부분 JSON은 스켈레톤이고 터미널 상태에서는 오류가 된다.
- raw spec 또는 임의 data가 포함된 마커는 네트워크 요청을 만들지 않는다.
- 완성된 유효 ID만 정확히 한 번 조회된다.
- 차트가 다크 코드블록 배경 안에 들어가지 않는다.

**완료 기준:** 최종 답변에서 검증된 visualization_id만 API 조회로 연결된다.

---

## Task 3. 조회 상태·중복 요청·재시도

**파일:** src/lib/visualization-api.ts,
src/components/chat/tool-results/chart-marker.tsx,
필요 시 src/hooks/use-visualization.ts(신규)

**스펙:**

상태를 loading, success, unavailable, forbidden/not-found, error로 명시한다.

- 같은 visualization_id의 동시 요청은 하나의 in-flight 요청으로 합친다.
- 각 구독자가 ID 변경 또는 언마운트되면 결과 반영을 중단한다.
  마지막 구독자가 사라지면 AbortController로 실제 요청도 취소한다.
- 성공 응답은 명세가 불변이고 expires_at이 있으므로 해당 시각까지만 메모리 캐시할 수 있다.
  access scope가 바뀌면 캐시를 비우며 다른 scope 간 응답을 공유하지 않는다.
- 네트워크 오류에는 UI 재시도 버튼을 제공한다. 이 재시도는 같은 GET만 다시 수행하며
  LLM이나 prepare_visualization을 재호출하지 않는다.
- 410 또는 원본 만료는 새 조회가 필요하다는 설명을 표시한다.
- 404·접근 불가 응답은 ID 존재 여부를 구분해 노출하지 않는다.
- 원본 표가 현재 메시지에 남아 있다고 단정하지 않는다.
  안내는 표가 있으면 확인하고, 없거나 만료됐으면 새 조회를 요청하라는 수준으로 둔다.
- 상태 변화는 screen reader가 이해할 수 있게 짧은 status/alert 문구를 제공한다.

**검증:**

- 동일 ID 마커 두 개가 네트워크 호출 하나를 공유한다.
- 한 컴포넌트 언마운트가 남은 구독자의 요청을 취소하지 않는다.
- 마지막 구독자 제거와 ID 변경이 stale state update를 만들지 않는다.
- UI 재시도가 대화 메시지나 tool call을 추가하지 않는다.
- 취소된 스트림의 불완전 마커가 무한 로딩으로 남지 않는다.

**완료 기준:** 조회 실패와 LLM 명세 보정이 분리되고 모든 터미널 상태가 화면에 남는다.

---

## Task 4. ChartSpec과 bar/line 렌더러 보완

**파일:** src/components/chat/tool-results/chart-block.tsx,
src/components/chat/tool-results/charts/bar-chart-view.tsx,
src/components/chat/tool-results/charts/line-chart-view.tsx,
src/components/ui/chart.tsx, src/types/chat.ts

**스펙:**

- 기존 Recharts와 --chart-1부터 --chart-5 팔레트를 재사용한다.
- bar와 line 모두 여러 series를 렌더하고 두 개 이상이면 범례를 표시한다.
- backend가 만든 내부 series key를 dataKey로, label을 사용자 표시 이름으로 사용한다.
  표시 이름이 같아도 series가 사라지거나 덮어써지지 않아야 한다.
- title, x_label, y_label, unit이 있을 때만 표시한다.
  알 수 없는 단위를 추정해서 붙이지 않는다.
- warnings를 차트 아래의 짧은 안내로 렌더한다.
  SOURCE_TRUNCATED는 저장된 결과 범위라는 점을 분명히 한다.
- null 값을 0으로 변환하지 않고 Recharts에 결측으로 전달한다.
- line categories는 서버가 준 시간 순서를 유지한다.
  프론트에서 재정렬·top N·downsample·재집계를 하지 않는다.
- 지원하지 않는 schema/type은 표 또는 오류 상태로 폴백하고 빈 차트 영역을 남기지 않는다.
- 좁은 폭에서 가로 스크롤이나 잘린 범례가 생기지 않게 확인한다.

**검증:**

- 단일/다중 y, group별 series, 동명 label, 5개 초과 series 색상 반복을 확인한다.
- null 구간이 0으로 연결되지 않는다.
- title/축/단위가 null일 때 빈 레이블이 없다.
- 400px, tablet, desktop 폭과 키보드·screen reader 안내를 확인한다.
- 사용자에게 표시된 값이 API payload와 일치한다.

**완료 기준:** 백엔드가 검증한 bar/line payload를 의미 변경 없이 읽을 수 있게 표시한다.

---

## Task 5. v1 tool 카드 차트 제거

**의존성:** 백엔드 v2 조회, Task 1~4, 통합 시나리오가 모두 성공해야 한다.
백엔드 계획 Task 7과 같은 변경 단위에서 수행한다.

**파일:** src/components/chat/tool-results/database-result.tsx,
src/components/chat/tool-results/simulation-result.tsx,
src/components/chat/tool-results/shared.ts, src/types/chat.ts,
관련 chart 컴포넌트 사용처

**스펙:**

- DatabaseResult와 SimulationResult의 data.chart 파싱 및 ChartBlock 렌더 분기를 제거한다.
- asChart가 다른 곳에서 사용되지 않으면 제거한다.
- v1 전용 truncated/hiddenCount 타입과 문구는 사용처 확인 후 제거한다.
- ChartBlock과 bar/line 렌더러는 최종 답변 마커에서 계속 사용하므로 삭제하지 않는다.
- 표·요약·SQL 펼쳐보기는 그대로 유지한다.
- marker/tool 미호출 시 tool 카드에 infer_chart 결과를 자동 표시하는 폴백을 만들지 않는다.
- 백엔드가 v1 chart 필드를 먼저 제거해 배포 중 차트가 사라지는 중간 상태를 만들지 않는다.

**검증:**

~~~bash
cd frontend
rg -n "asChart|data\\.chart|truncated|hiddenCount|/api/results/.*/chart|ChartRule|applicable_chart" src
npm run build
npm run lint
~~~

검색 결과에는 v2에서 의도한 호환 코드만 있어야 하며 최종 전환 후에는 폐기 용어가 없어야 한다.

**완료 기준:** 차트는 최종 답변 visualization_id 마커에서만 렌더되고 tool 카드에는 중복되지 않는다.

---

## Task 6. 통합·스트리밍 검증

**의존성:** 백엔드 계획 전체와 프론트 Task 1~5 완료

**스펙:**

실제 chat SSE 흐름으로 다음을 확인한다.

1. Knowledge를 참고한 집계 SQL → result_id → prepare_visualization →
   최종 chart 마커 → GET 조회 → 차트 표시
2. 같은 result_id에서 수량 비교와 비율 추이 두 시각화 표시
3. 잘못된 컬럼을 LLM이 보정한 뒤 성공
4. 보정 2회 실패, 빈 결과, table-only 요청에서 차트 생략
5. 원본 잘림 경고와 표시 한도 초과 오류 구분
6. 스트림 취소·불완전 마커·잘못된 JSON·없는 ID·만료·접근 불가
7. 재시작 후 유효 명세 조회와 만료 뒤 410
8. 도구 카드에는 표/요약만, 최종 답변에는 요청된 차트만 표시

~~~bash
cd frontend
npm run build
npm run lint
~~~

백엔드도 함께 실행한다.

~~~bash
cd backend
python -m pytest -q
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
~~~

수동 UI 확인은 narrow(약 400px), tablet, desktop에서 수행하고
composer submit/cancel, 편집/재생성, 복사, 자동 스크롤, tool 카드 접기 동작도 회귀 확인한다.

**완료 기준:** 로딩·성공·오류·취소가 무한 대기 없이 끝나고,
브라우저가 명세를 재해석하거나 데이터 값을 변경하지 않는다.

## 범위 밖

- pie와 Gantt 렌더러
- HTML 사전 생성, LLM HTML·JavaScript 실행
- 프론트의 SQL·집계·비율 계산
- raw result_id로 차트를 만드는 API
- 원시 kind/x/y/group_by 마커
- 자동 top N과 downsampling
- assistant-ui runtime 또는 SSE protocol 교체
- 새 차트 패키지 도입

## 실행 기록

*(실행 세션이 설계에 없던 판단을 내릴 때마다 여기에 남긴다.)*
