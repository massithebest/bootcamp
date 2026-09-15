# 에이전트 응답 차트 시각화

**상태: v1 구현 완료(bar/line). v2 설계, 구현 착수 전.**
v2는 [result-store.md](result-store.md)를 전제로 한다 — **Result Store를 먼저 구현한 뒤 착수한다.**

## 1. v1 — 현재 구현된 것

2026-09-15에 bar/line 차트를 구현해 동작 중이다.

| 구성 요소 | 파일 | 역할 |
| --- | --- | --- |
| 추론 | `backend/services/chart_inference.py` | `infer_chart(columns, rows)` — 결정론적 규칙으로 차트 스펙 조립 |
| 백엔드 연결 | `services/mock/mock_sql_service.py`, `mock_simulation_service.py` | 결과 조립 직후 `chart` 필드 첨부 |
| 타입 | `frontend/src/types/chat.ts` | `ChartSpec` |
| 렌더 | `tool-results/chart-block.tsx`, `charts/bar-chart-view.tsx`, `line-chart-view.tsx` | Recharts (shadcn `chart` 컴포넌트 경유) |
| 색상 | `src/app/globals.css` | `--chart-1` ~ `--chart-5` 전용 팔레트 |

동작 방식: LLM을 거치지 않고 서비스 레이어가 `columns`/`rows` 형태만 보고 차트를 만든다. `line_cd`+`line_nm` 코드·명 쌍은 자동으로 `_nm`만 남기고, 항목이 20개를 넘으면 상위 N개 + `truncated`로 자른다.

### v1의 한계 — v2를 만드는 이유

**(1) 차트가 도구 호출 카드 안에만 뜬다.**
`execute_sql` 결과 카드(접었다 펴는 UI) 안에 렌더된다. 사용자가 실제로 읽는 것은 에이전트의 **최종 답변**인데, 거기에는 차트가 없다. "표를 만들었으면 차트도 같이 보여달라"는 요구를 지금 구조로는 만족시킬 수 없다.

**(2) 숫자 컬럼이 2개 이상이면 차트가 통째로 사라진다.**
`infer_chart`는 숫자 컬럼이 정확히 1개일 때만 동작한다:

```python
if len(numeric_cols) != 1 or not non_numeric_cols:
    return None
```

"계획 대비 실적 달성률"처럼 `plan_qty`, `actual_qty`, `achievement_rate`가 함께 나오는 — 이 도메인에서 가장 흔한 — 조회는 차트가 나오지 않는다. 어떤 컬럼으로 그릴지 지정할 방법도 없다.

**(3) 규칙만으로는 의도를 못 읽는다.**
"추이를 보고 싶다"와 "라인별로 비교하고 싶다"는 같은 컬럼 구성에서도 다른 차트를 원한다. 컬럼 shape만 보는 규칙은 이 차이를 알 수 없다.

### v2에서 재사용 / 폐기

- **재사용**: 렌더 계층 전체(`chart-block.tsx`, `charts/*`, 팔레트, `ChartSpec` 타입의 뼈대). Recharts 채택과 폐쇄망 검증 결과도 유효하다.
- **유지**: `infer_chart`는 3단 폴백의 마지막 단계로 남긴다(§3).
- **폐기**: 서비스 레이어가 tool 결과에 `chart`를 무조건 첨부하던 방식. v2에서는 차트 스펙의 출처가 셋으로 늘고, 데이터는 `result_id`에서 온다.

## 2. v2의 전제 — Result Store

[result-store.md](result-store.md)가 구현되면 상황이 바뀐다.

- 모든 조회 결과가 parquet에 저장되고 `result_id`를 갖는다.
- LLM은 **전체 행을 들고 있지 않다.** 대신 컬럼 목록(이름·dtype·role), 샘플 몇 행, 요약 통계를 본다.
- 전체 데이터가 필요한 쪽은 `result_id`로 저장소를 직접 읽는다.

이것이 v2 설계의 핵심 제약이자 기회다. **LLM은 숫자를 옮겨 적을 수 없다**(애초에 갖고 있지 않으니까). 그러므로 LLM에게 차트 결정을 맡겨도 v1 설계가 우려했던 transcription 오류가 원천적으로 발생하지 않는다.

> v1 문서 §3은 "차트 생성 전용 tool을 만들지 않는다"고 했고, 근거는 *LLM이 `execute_sql`이 반환한 숫자를 tool 인자로 다시 옮겨 적어야 해서*였다. v2에서 LLM이 다루는 것은 **`result_id`와 컬럼명뿐**이다. 따라서 그 원칙의 근거가 해소되고, LLM이 차트를 지정하는 설계가 안전해진다.

## 3. 차트 스펙 결정 — 3단 폴백

차트 스펙(타입 + 축 컬럼)을 누가 정하는가. 우선순위대로 셋을 둔다.

```
1. Knowledge 명세  — knowledge YAML 의 charts: 블록에 해당하는 패턴이 있는가?
2. LLM 판단        — 없으면 LLM 이 컬럼 메타데이터를 보고 마커로 지정
3. 규칙 폴백       — LLM 도 지정 안 했으면 infer_chart (v1 로직)
```

### 3.1 Knowledge 명세 (우선)

테이블·시뮬레이션마다 "이런 결과가 나오면 이렇게 그려라"를 미리 선언한다. 도메인 담당자가 한 번 정해두면 LLM 판단의 흔들림 없이 항상 같은 형태가 나온다.

`knowledge/catalog/tables/<table>.yaml`에 `charts:` 추가:

```yaml
table: FGS_INBOUND_RESULT
# ... 기존 필드 ...
charts:
  - name: 라인별_실적_비교
    when:                            # 결과 컬럼이 이 조건을 만족하면 적용
      has_columns: [line_cd, inbound_qty]
      absent_columns: [work_date]    # 시계열이 아닐 때만
    spec:
      type: bar
      x: line_cd                     # line_nm 이 함께 있으면 자동으로 명 우선
      y: [inbound_qty]
      sort: desc
  - name: 일자별_실적_추이
    when:
      has_columns: [work_date, inbound_qty]
    spec:
      type: line
      x: work_date
      y: [inbound_qty]
      group_by: line_cd              # 있으면 라인별 시리즈로 분리
```

`knowledge/simulations/<type>.yaml`도 동일하게:

```yaml
type: 실적_조회
# ... 기존 필드 ...
charts:
  - name: 라인별_월별_추이
    when:
      has_columns: [line, workMonth, qty]
    spec:
      type: line
      x: workMonth
      y: [qty]
      group_by: line
```

계획 대비 실적처럼 **숫자 컬럼이 여럿인 경우**(v1 한계 2)가 여기서 풀린다:

```yaml
charts:
  - name: 계획_대비_실적
    when:
      has_columns: [work_date, plan_qty, actual_qty]
    spec:
      type: bar
      x: work_date
      y: [plan_qty, actual_qty]      # 다중 시리즈 — 나란히 비교
  - name: 달성률_추이
    when:
      has_columns: [work_date, achievement_rate]
    spec:
      type: line
      x: work_date
      y: [achievement_rate]          # 비율은 스케일이 달라 별도 차트로
```

수량과 비율은 축 스케일이 달라 한 차트에 섞으면 읽히지 않는다. 이런 도메인 판단이 YAML에 담기는 것이 이 방식의 핵심 가치다.

**구현**: `backend/services/knowledge_service.py`의 `KnowledgeTable`/`KnowledgeSimulation` pydantic 모델에 `charts: list[ChartRule] = []` 추가. `when` 매칭은 결과 컬럼 집합에 대한 단순 포함 검사이므로 결정론적이고 테스트 가능하다.

### 3.2 LLM 판단 (폴백 1)

명세에 해당 패턴이 없으면 LLM이 정한다. LLM은 tool 결과로 이미 컬럼 메타데이터를 받고 있다:

```jsonc
"columns": [
  { "name": "work_date", "dtype": "object", "role": "time" },
  { "name": "line_cd",   "dtype": "object", "role": "category" },
  { "name": "inbound_qty","dtype": "int64", "role": "measure" }
]
```

이걸 보고 **컬럼 이름만 골라** 마커를 쓴다(§4). 값은 쓰지 않는다.

### 3.3 규칙 폴백 (폴백 2)

1·2 모두 없으면 v1의 `infer_chart`가 동작한다. 단일 카테고리 + 단일 숫자처럼 명백한 경우를 자동 처리해, 명세를 아직 안 쓴 테이블도 최소한의 시각화를 얻는다.

## 4. 차트를 최종 응답에 — 마커 방식

**LLM이 답변 본문에 마커를 쓰면 프론트가 그 자리에 차트를 렌더한다.**

### 마커 형식

```chart
{ "result_id": "a3f2c8...", "type": "bar", "x": "line_nm", "y": ["actual_qty"] }
```

코드펜스의 언어 태그를 `chart`로 쓰고 본문에 JSON 스펙을 담는다. 이 형식을 고른 이유:

- **마크다운 파서가 이미 처리한다.** `frontend/src/components/chat/markdown-text.tsx`의 `Code` 컴포넌트가 이미 `language-*` 클래스 유무로 인라인/블록을 가르고 있다. 여기에 `language-chart` 분기를 추가하면 된다.
- **`MessagePart` 유니온을 늘리지 않아도 된다.** 차트는 텍스트 파트 안의 한 블록이므로 `frontend/src/types/chat.ts`의 파트 구조와 `chat-runtime.ts`의 `convertMessage` 매핑을 건드리지 않는다.
- **LLM이 위치를 통제한다.** "표 다음에 차트", "결론 앞에 추이 그래프" 같은 배치가 자연스럽게 나온다.
- **실패해도 안전하다.** 프론트가 마커를 이해 못 하면 그냥 코드 블록으로 보인다. 깨진 화면이 아니라 읽을 수 있는 JSON이 남는다.

### 렌더 흐름

```
LLM 답변 텍스트 (마커 포함)
  └─ MarkdownText (markdown-text.tsx)
       └─ pre/code 슬롯에서 language-chart 가로채기
            └─ 스펙 JSON 파싱
                 └─ GET /api/results/{result_id}/chart?type=bar&x=line_nm&y=actual_qty
                      └─ 백엔드가 parquet 에서 집계해 데이터 포인트 반환
                           └─ ChartBlock (v1 컴포넌트 재사용)
```

**데이터는 마커에 없다.** 마커는 "무엇을 어떻게 그릴지"만 말하고, 실제 값은 프론트가 `result_id`로 조회한다. LLM은 숫자를 만지지 않는다.

### 집계 API

```
GET /api/results/{result_id}/chart?type=bar&x=line_nm&y=actual_qty&group_by=&limit=20
  → { type, x, categories, series, data, truncated?, hiddenCount? }
```

응답 형태는 v1의 `ChartSpec`과 같게 유지한다 — 렌더 컴포넌트를 그대로 재사용하기 위해서다. 상위 N개 자르기(`MAX_CHART_ITEMS`)와 코드·명 쌍 처리도 v1 로직을 여기로 옮긴다.

### 스트리밍 중 처리

마커는 텍스트 스트림에 섞여 들어오므로, 코드펜스가 닫히기 전의 부분 텍스트가 잠시 화면에 보인다.

```
```chart
{ "result_id": "a3f2
```

`MarkdownTextPrimitive`는 매 델타마다 다시 파싱하므로 이 상태에서는 닫히지 않은 코드 블록으로 렌더된다. 대응:

- **JSON 파싱 실패 시 조용히 대기.** 차트 컴포넌트가 스펙을 못 읽으면 스켈레톤(로딩 자리)을 보여주고, 다음 델타에서 완성되면 렌더한다. 에러를 띄우지 않는다 — 스트리밍 중에는 미완성이 정상이다.
- **완성된 뒤에만 API 호출.** 파싱 성공 + `result_id` 존재를 확인한 뒤 조회한다. 부분 문자열로 요청하지 않는다.

### Skill 연동

"표가 있으면 차트도" 요구는 Skill 규칙으로 유도한다. `sql-analysis` SKILL.md에 추가:

> **시각화**: 조회 결과를 표로 제시할 때, 비교·추이가 드러나는 결과면 차트 마커를 함께 쓴다. 마커에는 `result_id`와 컬럼명만 쓰고 수치는 쓰지 않는다. 어떤 차트가 적절한지는 tool 결과의 `columns[].role`을 본다.

`simulation` SKILL.md에도 동일 취지의 문구를 넣는다.

**주의**: `backend/tests/test_prompt_consistency.py`의 `test_skill_does_not_copy_schema`가 SKILL.md에 실제 테이블명이 들어가는 것을 금지한다. 위 문구처럼 **구체적 테이블·컬럼명 없이** 절차만 서술해야 한다.

## 5. 구현 순서

Result Store 완료가 전제다.

1. **집계 API** — `GET /api/results/{id}/chart`. v1 `infer_chart`의 코드·명 처리와 상위 N개 자르기를 이쪽으로 이동.
2. **마커 렌더** — `markdown-text.tsx`에 `language-chart` 분기 + 스켈레톤/파싱 실패 처리. `ChartBlock`은 그대로 재사용하되 데이터를 props가 아니라 API에서 받도록 변경.
3. **Skill 문구** — `sql-analysis`/`simulation` SKILL.md에 시각화 절차 추가. LLM이 마커를 쓰기 시작한다.
4. **Knowledge 명세** — `ChartRule` pydantic 모델, `charts:` 블록 파싱, `when` 매칭. tool 결과에 "이 결과에 적용 가능한 차트 명세"를 실어 LLM이 그대로 쓰게 한다.
5. **v1 경로 정리** — 서비스 레이어의 무조건 `chart` 첨부 제거, tool 카드 내 차트를 유지할지 결정(§열린 질문).

3까지 하면 사용자가 요구한 "최종 응답에 차트"가 동작한다. 4는 품질·일관성 개선이다.

## 6. 열린 질문

- **tool 카드의 차트를 남길 것인가.** 최종 답변에 차트가 생기면 도구 카드의 차트는 중복이다. 다만 "에이전트가 무엇을 봤는지" 확인하는 용도로는 여전히 쓸모가 있다. 제거하면 v1 코드가 단순해지고, 남기면 같은 차트를 두 번 보게 된다.
- **`when` 매칭 규칙의 표현력.** `has_columns`/`absent_columns`만으로 부족한 경우(행 수 조건, 값 범위 조건)가 나올 수 있다. 처음부터 복잡하게 만들지 말고 실제 부족한 사례가 나올 때 늘린다.
- **LLM이 마커를 남발하거나 안 쓰는 경우.** Skill 문구만으로 빈도가 통제될지는 실제로 돌려봐야 안다. 너무 안 쓰면 명세 기반 자동 첨부(§3.1의 결과를 답변 끝에 자동으로)를 보조로 둘 수 있다.
- **`role` 추정 정확도.** `columns[].role`(`category`/`measure`/`time`)이 LLM 판단의 입력인데, 이 값이 틀리면 차트도 틀린다. [result-store.md](result-store.md)의 같은 이름 열린 질문과 연결된다.
- **pie·간트.** 여전히 범위 밖이다. 간트는 구간(시작~종료) 데이터를 가진 조회가 실제로 생긴 뒤에 다시 본다.

## 관련 문서

- [result-store.md](result-store.md) — **선행 구현 대상.** `result_id`·컬럼 메타데이터·저장 구조
- [domain-knowledge.md](domain-knowledge.md) — 지식 YAML 구조. `charts:` 블록이 여기 스키마에 추가된다
- [frontend/docs/decisions.md](../frontend/docs/decisions.md) — Recharts 채택, assistant-ui 구조
- [frontend/docs/closed-network.md](../frontend/docs/closed-network.md) — 폐쇄망 의존성 체크리스트
- [frontend/CLAUDE.md](../frontend/CLAUDE.md) · [backend/CLAUDE.md](../backend/CLAUDE.md) — 작업 지침
