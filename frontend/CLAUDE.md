@AGENTS.md

# Frontend 디자인 가이드

2026-09-16 `frontend-design` Skill 기반 UI/UX 개선(3-pane 워크벤치)에서 확정한
규칙과 최종 token 기준. 2026-09-16 assistant-ui Elements 전환으로 공통 UI
구현 경로를 갱신했으며 아래 token과 정보 위계는 유지한다. 클래스명을 모두
나열하지 않고, 이후 작업자가 새 화면·컴포넌트를 만들 때 일관된 판단을
내릴 수 있는 기준만 남긴다. 구현
근거와 검증 결과는
[frontend-ui-ux-plan](plan/260916-frontend-ui-ux-plan.md)을 따른다.

## 제품 UX 원칙

- **Chat Workspace가 Primary다.** 중앙 대화 컬럼이 항상 가장 넓고 시각
  우선순위가 가장 높다. Sidebar/Inspector는 그 다음이다.
- **실행 과정은 Secondary다.** Tool 실행·진행 상태는 실행 중에는 펼쳐서
  보여주고, 완료되면 접어 최종 답변보다 낮은 위계로 내려간다. 완료 후 접힌
  카드도 헤더 한 줄로 결과 종류·상태·행 수/핵심 수치를 알 수 있어야 한다
  (raw JSON·payload를 기본 화면의 중심 정보로 남기지 않는다).
- **Context Inspector는 Progressive Disclosure다.** 탭 진입 시 가장 중요한
  정보(Skills)부터 보여주고, 나머지는 필요할 때 펼친다.
- **정확성과 밀도를 장식보다 우선한다.** 카드·그림자·그라디언트로 꾸미지
  않는다. 구분은 1px 룰과 배경 톤 한 단계 차이로 만든다.
- **실제로 연결되지 않은 기능을 동작하는 것처럼 표현하지 않는다.** 버튼을
  누르면 정말 무언가 바뀌어야 한다. 저장·설정처럼 아직 백엔드 계약이 없는
  기능은 읽기 전용으로 보여주거나 명시적으로 비활성화하고 이유를 밝힌다
  (`context-inspector.tsx`의 Prompt 패널, `app-sidebar.tsx`의 설정 버튼 참고).
- **비공개 chain-of-thought를 노출하지 않는다.** `status` 이벤트는 모델의
  내부 reasoning이 아니라 사용자용 업무 진행 단계(질문 분석→데이터 확인→
  SQL 조회→시뮬레이션→결과 분석→답변)다. Tool과 독립적인 공개 단계는
  실행 과정 안의 `AgentPlan`으로만 표현한다.

## Layout 기준

- 3-pane 구조: `Sidebar(15.5rem) | Chat(1fr) | Inspector(20rem/w-80)`.
  Chat이 항상 남은 공간을 모두 갖는다. 폭을 더 좁히거나 넓히지 않는다.
- 대화 읽기 폭은 `max-w-reading`(47.5rem/760px)로 고정한다. 메시지, 진행
  블록, Composer 모두 이 폭 안에서 `mx-auto`로 정렬한다.
- Sidebar/Inspector는 폭 0으로 접힌다(언마운트하지 않음). 접힌 pane을 다시
  여는 버튼은 헤더 좌/우 끝에 두고, 아이콘 방향으로 "펼쳐질 방향"을 알려준다.
- 좁은 화면 자동 접힘 임계값: Inspector `< 1180px`, Sidebar `< 860px`.
  **임계값을 아래로 통과하는 순간에만** 접는다(리사이즈마다 재적용하지
  않는다) — 그래야 사용자가 임계값 아래에서 직접 펼친 pane을 창 드래그 중
  발생하는 연속 resize 이벤트가 다시 강제로 닫지 않는다
  (`chat-window.tsx`의 `prevWidthRef` 패턴 참고).
- 모바일 최적화는 비범위이지만, ~400px까지 가로 스크롤이나 잘리는 컨트롤이
  없어야 한다. Sidebar/Inspector가 접힌 상태에서 Chat 컬럼과 Composer만으로
  구성이 성립해야 한다.
- 각 pane은 독립적으로 스크롤한다. `min-h-0`/`min-w-0`/`overflow-hidden`/
  `shrink-0`으로 만든 스크롤 체인을 건드리지 않는다.
- 100행 이하 inline 표(도구 결과 표, Markdown 표)는 가로 스크롤에 더해
  세로 높이도 `max-h-96`(24rem)로 제한하고 그 안에서만 스크롤한다. 최종
  답변이나 다음 메시지가 큰 표 때문에 화면 밖으로 밀리지 않게 한다.

## Typography 기준

`tailwind.config.ts`의 `fontSize` 스케일을 그대로 쓴다. 새 크기를 추가하지
않는다.

| 용도 | 클래스 | 크기/행간 |
| --- | --- | --- |
| 보조 정보·metadata·상태 표식 | `text-2xs` | 11px / 16px |
| 표·SQL·코드·숫자(mono) | `text-data` (+ `font-mono`) | 12px / 18.4px |
| 기본 UI 본문 | `text-ui`(기본값, body) | 13px / 21.6px |
| Assistant 장문 본문·소제목 | `text-ui-lg` | 14px / 24px, `leading-[1.6]` |
| 진행 블록/문서 제목(h3 대응) | `text-ui-lg font-semibold` | 위와 동일 |

- 산문은 `--font-sans`(시스템 폰트 + Noto Sans KR/맑은 고딕), 데이터는
  `--font-mono`. 섞어 쓰지 않는다 — 값·SQL·식별자는 항상 mono.
- 한글 본문은 `font-semibold`(600) 이상을 굵기로 쓰고 `font-bold`는 쓰지
  않는다. 시스템 한글 폰트가 bold에서 자간이 깨지는 경우가 있다.
- 숫자는 표·KPI·metadata 어디서나 `tabular-nums`.

## Color 기준

`globals.css`의 semantic 변수만 쓴다. 컴포넌트에 hex를 새로 하드코딩하지
않는다(코드 블록 배경 `#1c2530`/`#d7dce4`처럼 다크 트레이 전용 예외는
유지되어 온 기존 패턴이며 새로 늘리지 않는다).

| 역할 | 변수 | 값 |
| --- | --- | --- |
| 대화 배경(가장 밝음) | `--canvas` | `#ffffff` |
| Sidebar/Inspector 배경 | `--surface` | `#f6f7f9` |
| hover/중첩 배경 | `--surface-2` | `#eceef1` |
| 기본 텍스트 | `--ink` | `#17202b` |
| 보조 텍스트 | `--ink-2` | `#55606d` |
| 최약 텍스트(메타) | `--ink-3` | `#8b939e` |
| 선 | `--line` / `--line-strong` | `#e4e7eb` / `#d3d8de` |
| 강조(활성 세션·포커스·주요 액션 한정) | `--accent` / `--accent-hover` / `--accent-weak` | `#2f5fd0` / `#2650b4` / `#eef2fc` |
| 정상 | `--ok-ink` / `--ok-weak` | `#1a7a49` / `#e9f4ee` |
| 주의 | `--warn-ink` / `--warn-weak` | `#9a6416` / `#f8f0e1` |
| 차단/오류 | `--block-ink` / `--block-weak` | `#bb3a30` / `#f9ebe9` |
| 차트 전용(다계열 구분) | `--chart-1`…`--chart-5` | 파랑·청록·주황·보라·적갈 |

- `--chart-*`는 차트 시리즈에만 쓴다. 상태 표시에 절대 재사용하지 않는다.
- 상태는 색상만으로 전달하지 않는다. `StatusDot`(색) + 텍스트(대기/진행/
  완료/오류) 또는 아이콘(`CheckIcon`/`AlertCircleIcon`류) + 텍스트를 함께
  쓴다(`assistant-ui/elements/tool-call.tsx`와
  `assistant-ui/elements/agent-plan.tsx`의 상태 아이콘·라벨 참고).
- 다크 테마는 추가하지 않는다. 이 프로젝트는 라이트 전용이다.

## Spacing과 shape

- Border radius는 `rounded`(기본값 0.3125rem/5px) 하나로 통일한다. 카드마다
  다른 radius를 쓰지 않는다.
- Panel 헤더: `px-4 py-2.5` (Sidebar/Inspector 헤더는 `px-2~3 py-2~3`로 더
  좁음). Composer: `px-4 py-3`. 메시지 컬럼 세로 간격: `gap-6 py-6`.
- 카드로 감싸는 대신 좌측 룰(`border-l`)과 배경 톤 한 단계 차이로 구분한다.
  카드(둥근 테두리 박스)는 차트, 대용량 결과 요약(`ResultSummaryCard`)처럼
  화면 안에서 독립된 시각 단위로 다뤄야 하는 콘텐츠에만 쓴다. Tool 결과·
  진행 블록·지식 카드는 좌측 룰만 쓴다.
- 그림자는 쓰지 않는다(ScrollToBottom 버튼의 `shadow-sm` 등 최소 예외만
  기존 유지). 그라디언트·glassmorphism은 쓰지 않는다.
- Compact 컨트롤(아이콘 버튼, 탭, 태그) 높이는 `text-2xs` 기준 `py-1~1.5`.

## Component별 규칙

- **User message**: 오른쪽 정렬, `border border-line-strong bg-surface`
  말풍선. 카드 그림자 없음.
- **Assistant message**: 왼쪽 정렬, 말풍선 없이 컬럼 전체 폭 사용. 진행
  블록 → 최종 본문 → 액션바 순서를 유지한다.
- **실행 과정**(`thread-messages.tsx`): 독립적인 공개 `status`는 `AgentPlan`,
  Tool 호출은 `MessagePrimitive.GroupedParts`와 `ToolGroup`으로 한 블록에
  표시한다. Tool 실행 단계는 그룹의 `part.status`로 판별하고, 회전 아이콘은
  메시지 전체가 실행 중인 동안 유지한다. 헤더는 `요청 분석 중` → `툴 N개
  실행 중` → `응답 작성 중` → `응답 작성 완료` 단계를 구분한다. 메시지가
  실행 중인 동안 블록을 펼치고 최종 상태가 되면 자동으로 접는다. 완료 후
  사용자가 다시 펼치면 공개 단계와 Tool 목록이 보인다.
- **Tool 결과**(`tool-result-card.tsx`): 개별 Tool 상세는 종류와 관계없이
  기본 접힘이며 ToolGroup 안에서 두 번째 disclosure 단계가 된다. 접힌 헤더는
  `label · 요약`(예: "데이터 조회 · 10행", "시뮬레이션 실행 · 지표 4개")
  형식을 유지한다 — 새 tool_name을 추가하면 `resultHeaderSummary`에 요약
  규칙을 함께 추가한다.
- **Standalone 표**(`interactive-data-table.tsx`): `prepare_table`이 검증해 보낸
  최대 100행 안에서 검색·열 정렬·페이지 크기 10/25/50/100과 이전/다음 이동을
  제공한다. 원본 건수와 실제 포함 건수를 함께 표시하고 잘린 결과를 알린다.
- **Markdown**: `AssistantText`의 `leading-[1.6]`, 표/코드/SQL은 항상 mono +
  `tabular-nums` + 가로/세로 스크롤 캡(`max-h-96`). 헤딩은 실제 문서
  위계보다 한 단계 낮춰(`h1/h2`→`text-ui-lg`) 채팅 안에서 과도하게 크지
  않게 한다.
- **Data table**(`primitives.tsx` `DataTable`, `assistant-ui/elements/markdown-text.tsx` `Table`):
  동일한 스크롤 래퍼(`thin-scroll max-h-96 overflow-x-auto overflow-y-auto`)
  를 공유한다. 둘 중 하나만 고치고 다른 하나를 잊지 않는다.
- **Composer**(`assistant-ui/elements/thread.aui.tsx`): `ComposerPrimitive`가 전송/Enter/
  Shift+Enter/자동 높이/실행 중 비활성을 소유한다. Send/Stop은 `AuiIf`로
  전환하고 직접 상태를 구독해 조건부 렌더하지 않는다. Input에는 반드시
  `aria-label`을 둔다(placeholder만으로 접근성 이름을 대신하지 않는다).
- **Sidebar**(`app-sidebar.tsx`): 세션 목록이 아직 영속 저장소가 아니므로
  "예시 세션 · 현재 대화만 유지됩니다" 같은 안내를 목록 위에 유지한다.
  실제 persistence 계약이 생기기 전까지 이 안내를 지우지 않는다. 실제로
  연결되지 않은 액션(설정 등)은 `disabled` + `title`로 이유를 밝힌다.
- **Inspector**(`context-inspector.tsx`): 탭 순서는 실제 연결(Skills) →
  참고용 예시(메타) → 참고용 예시(프롬프트) 순을 유지한다. 실제 API가 없는
  탭은 패널 첫 줄에 "예시 · 아직 실제 연결 값이 아닙니다" 류의 caption을
  둔다. 저장처럼 실행해도 아무 일도 일어나지 않는 버튼은 만들지 않는다 —
  계약이 생기기 전에는 읽기 전용으로 보여준다.
- **Empty/loading/error 상태**: 오류는 항상 "무엇이 실패했고 무엇을 하면
  되는지"까지 문장으로 설명한다(`ConnectionBanner` 참고). 로딩은
  스켈레톤보다 짧은 문구("불러오는 중…")나 `role="status"` pulse 블록을
  우선한다(차트 로딩 등 형태가 예측 가능한 경우만 스켈레톤 사용).
- **Button/icon**: Lucide 아이콘 `size-3~3.5`. 1차 액션(전송)만 `bg-accent`
  채움, 나머지는 텍스트/ghost. 파괴적 액션은 이 저장소에 아직 없다 — 추가할
  때는 `--block-ink` 텍스트 + 명확한 확인 문구를 쓴다.
- **focus-visible/keyboard**: 모든 대화형 요소는 `:focus-visible`의 전역
  outline(`--accent`, 2px)에 기대고 별도 outline 제거하지 않는다. 새 버튼도
  `<button type="button">` + `aria-label`(아이콘만 있을 때) 규칙을 따른다.

## 금지 사항

- 외부 폰트·CDN·telemetry 추가.
- 컴포넌트에 semantic token 없이 hex/rgb 하드코딩(다크 코드 트레이 등
  기존 예외 외 새로 늘리지 않기).
- 과도한 gradient·glassmorphism·큰 그림자·전면 카드화.
- Backend 계약(`AgentEvent`, tool payload, Result Store, `tool_call_id`
  등)에 없는 데이터를 추측해 표시하거나 새로 만들어내기.
- 결과·근거를 항상 펼쳐 놓아 최종 답변보다 시각적으로 우세하게 두기.
- `status` 이벤트를 비공개 reasoning처럼(또는 반대로 숨겨야 할 정보를
  노출하는 방식으로) 표현하기.
- 이유 없는 신규 UI 라이브러리·패키지 추가. 현재 카탈로그(shadcn 소스,
  assistant-ui Elements, Recharts, Lucide)로 해결되지 않는
  화면이 생기면 먼저 결정 기록(`docs/decisions.md`)에 근거를 남긴다.

## assistant-ui Elements 적용 기준

- 공통 채팅은 `components/assistant-ui/elements/thread.aui.tsx`를 사용한다.
  `App` 루트 provider 아래에 두고 `components` 슬롯 객체는 모듈 범위에 둔다.
- 템플릿의 radius·색·폰트·그림자를 그대로 도입하지 않고 위 semantic token에
  맞춘다. Thread의 읽기 폭은 47.5rem, composer는 sticky ViewportFooter다.
- 빈 대화는 중앙 welcome·예시 질문·composer로 구성한다. 메시지 편집창에도
  접근성 이름을 둔다. 접힌 pane은 마운트를 유지하되 `invisible`로 포커스에서 제외한다.
- 공개 진행 단계는 AgentPlan, 도구 결과는 ToolCall을 사용한다. 추정 reasoning,
  가짜 tool args나 미연결 버튼을 만들지 않는다. 실제 완료된 단계만 완료로 센다.
- 원격 이미지·첨부·음성·Cloud 기능은 현재 계약에 없다. 공식 예제의
  useChatRuntime은 현재 SSE에 적용하지 않는다. 상세 예외는 [AGENTS.md](AGENTS.md),
  전환 근거는 [기술 결정](docs/decisions.md)을 따른다.
