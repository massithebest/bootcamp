@AGENTS.md

# Frontend 디자인 가이드

2026-09-16 `frontend-design` Skill 기반 UI/UX 개선(3-pane 워크벤치)에서 확정한
규칙과 최종 token 기준. 2026-09-16 assistant-ui Elements 전환으로 공통 UI
구현 경로를 갱신했으며 아래 token과 정보 위계는 유지한다. 구현 근거와 검증 결과는
[Frontend 계획과 완료 이력](plan/Todo.md)을 따른다.

## 제품 UX 원칙

- **Chat Workspace가 Primary다.** 중앙 대화 컬럼이 항상 가장 넓고 시각
  우선순위가 가장 높다. Sidebar/Inspector는 그 다음이다.
- **실행 과정은 Secondary다.** Tool 실행·진행 상태는 실행 중에는 펼쳐서
  보여주고, 완료되면 접어 최종 답변보다 낮은 위계로 내려간다. 완료 후 접힌
  카드도 헤더 한 줄로 결과 종류·상태·행 수/핵심 수치를 알 수 있어야 한다
  (raw JSON·payload를 기본 화면의 중심 정보로 남기지 않는다).
- **Context Inspector는 Progressive Disclosure다.** 도구 → 스킬 → 지식 탭을
  제공하고 도구 탭을 기본으로 연다. 각 탭의 상세는 필요할 때만 펼친다.
- **정확성과 밀도를 장식보다 우선한다.** 카드·그림자·그라디언트로 꾸미지
  않는다. 구분은 1px 룰과 배경 톤 한 단계 차이로 만든다.
- **실제로 연결되지 않은 기능을 동작하는 것처럼 표현하지 않는다.** 버튼을
  누르면 정말 무언가 바뀌어야 한다. 저장·설정처럼 아직 백엔드 계약이 없는
  기능은 읽기 전용으로 보여주거나 명시적으로 비활성화하고 이유를 밝힌다
  (`app-sidebar.tsx`의 설정 버튼 참고). 지식 변경은 서버(`GET /api/me`의 `knowledge_management`와 권한)가 허용한 경우에만 제공한다.
- **모델 추론(reasoning)과 업무 단계를 구분한다.** `status` 이벤트는 모델의
  reasoning이 아니라 사용자용 업무 진행 단계(질문 분석→데이터 확인→
  SQL 조회→시뮬레이션→결과 분석→답변)이며 실행 과정 안의 `AgentPlan`으로만 표현한다.
  모델 thinking(chain-of-thought)은 어떤 경우에도 공개하지 않는다(추정 추론·`status`를
  추론처럼 위장하는 표시 금지).

## Layout 기준

- 3-pane 구조: `Sidebar(15.5rem) | Chat(1fr) | Inspector(기본 20rem, 1280px 이상 23rem)`.
  Inspector는 세션 동안 `16~35rem` 범위에서 좌측 경계를 드래그하거나
  `←/→`, `Home/End`로 조절할 수 있다. 실제 상한은 Chat 최소 `32.5rem`과
  현재 viewport를 우선해 더 작아질 수 있다. Chat이 항상 남은 공간을 모두
  갖는다. 폭을 바꿀 때는 좁은 화면 임계값과 헤더 정렬, 중앙 읽기 폭을 함께 검증한다.
- 대화 읽기 폭은 Thread의 `--thread-max-width: 47.5rem`을 기준으로 한다.
  메시지, 진행 블록, Composer를 같은 중앙 축에 정렬한다.
- Sidebar/Inspector는 폭 0으로 접힌다(언마운트하지 않음). 접힌 pane을 다시
  여는 버튼은 헤더 좌/우 끝에 두고, 아이콘 방향으로 "펼쳐질 방향"을 알려준다.
- 좁은 화면 자동 접힘 임계값: Inspector `< 1180px`, Sidebar `< 860px`.
  **임계값을 아래로 통과하는 순간에만** 접는다(리사이즈마다 재적용하지
  않는다) — 그래야 사용자가 임계값 아래에서 직접 펼친 pane을 창 드래그 중
  발생하는 연속 resize 이벤트가 다시 강제로 닫지 않는다
  (`chat-window.tsx`의 `prevWidthRef` 패턴 참고).
- **모바일 환경은 지원하지 않으며 검증하지 않는다.** 이 앱은 데스크톱 브라우저에서만
  구동한다. 휴대폰·태블릿 폭(예: ~400px) 확인, 터치 조작, 모바일 device emulation,
  모바일 가상 키보드는 검증 항목이 아니다. 창 폭 임계값(860/1180px) 동작은
  데스크톱 창을 줄였을 때의 제품 동작이므로 유지한다.
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

- 일반 패널과 결과 surface는 `rounded`를 기본으로 한다. 홈페이지형 Composer는
  입력 affordance를 위해 `rounded-2xl`을 쓰는 명시적 예외다. 공식 Elements의
  radius를 그대로 복사해 새 예외를 늘리지 않는다.
- Panel 헤더: `px-4 py-2.5` (Sidebar/Inspector 헤더는 `px-2~3 py-2~3`로 더
  좁음). Composer: `px-4 py-3`. 메시지 컬럼 세로 간격: `gap-6 py-6`.
- 카드로 감싸는 대신 좌측 룰(`border-l`)과 배경 톤 한 단계 차이로 구분한다.
  카드(둥근 테두리 박스)는 차트, 대용량 결과 요약(`ResultSummaryCard`)처럼
  화면 안에서 독립된 시각 단위로 다뤄야 하는 콘텐츠에만 쓴다. Tool 결과·
  진행 블록·지식 카드는 좌측 룰만 쓴다.
- 그림자는 Composer와 ScrollToBottom 버튼의 `shadow-sm`처럼 입력·부유 제어를
  구분하는 최소 예외만 유지한다. 그라디언트·glassmorphism은 쓰지 않는다.
- Compact 컨트롤(아이콘 버튼, 탭, 태그) 높이는 `text-2xs` 기준 `py-1~1.5`.

## Component별 규칙

- **User message**: 오른쪽 정렬, `border border-line-strong bg-surface`
  말풍선. 카드 그림자 없음.
- **Assistant message**: 왼쪽 정렬, 말풍선 없이 컬럼 전체 폭 사용. 일반 Tool
  실행 그룹을 먼저 두고, standalone 표·차트와 각 도입·해석은 이벤트 문맥
  순서대로 배치한 뒤 액션바를 둔다.
- **실행 과정**(`thread-messages.tsx`): 독립적인 공개 `status`는 `AgentPlan`,
  Tool 호출은 `MessagePrimitive.GroupedParts`와 `ToolGroup`으로 한 블록에
  표시한다. Tool 실행 단계는 그룹의 `part.status`로 판별하고, 회전 아이콘은
  메시지 전체가 실행 중인 동안 유지한다. 헤더는 `요청 분석 중` → `툴 N개
  실행 중` → `응답 작성 중` → `응답 작성 완료` 단계를 구분한다. 메시지가
  실행 중인 동안 블록을 펼치고 최종 상태가 되면 자동으로 접는다. 완료 후
  사용자가 다시 펼치면 공개 단계와 Tool 목록이 보인다. 초기·진행 상태 문구는
  `text-ui`와 `text-ink-2` 이상의 가독성을 유지한다. 일반 Tool 직전에 공개된
  `text`는 해당 Tool이 실행 중일 때만 현재 Tool 행 바로 위에 일반 텍스트로
  유지한다. ToolGroup 상단의 별도 강조 블록으로 올리지 않고, Tool 결과가
  도착하면 즉시 제거한다. 일반 모션 환경에서 실행 중 헤더의 좌측 아이콘은 계속 회전하고,
  reduced-motion에서도 실행 중 아이콘 회전은 유지한다(진행 신호이며 상태 텍스트를 함께 둔다). 한글 라벨과 아이콘의 광학적 중심을 맞춘다.
- **Tool 결과**(`tool-result-card.tsx`): 개별 Tool 상세는 종류와 관계없이
  기본 접힘이며 ToolGroup 안에서 두 번째 disclosure 단계가 된다. 접힌 헤더는
  `tool_name · 요약`(예: `execute_sql · 10행`) 형식을 유지한다. 결과가 도착하기
  전에 실행이 끝난 Tool은 완료로 추정하지 않고 `미완료`로 표시한다.
  그룹 헤더에도 오류·미완료 개수를 반영한다. 자동 접힘으로 숨겨질 내부 포커스는
  보이는 trigger로 복원하며 외부 입력 포커스는 유지한다.
  브라우저에서 실제로 측정한 시간만 `응답 시간`으로 표시하고 서버 처리 시간으로
  표현하지 않는다.
- **조합형 결과**(`components/chat/generative/`): `present`가 만든 트리는 `SqlPreview`(기본 접힘·복사),
  `QueryChart`(서버 집계 chart, 항상 보이는 범례·`sr-only` 요약·표 대안·reduced-motion 시 animation 없음),
  `QueryTable`(TanStack Table 수동 모드, 서버 검색·열 정렬·page, 기본 10행,
  loading 중에도 직전 표 유지), `SimulationSummary`로 그린다. `QueryTable`은 저장된 최대
  1,000건 전체에 서버에서 검색·정렬을 적용하고 현재 page만 받는다.
  package의 unstyled `data-aui` hook은 `globals.css`에서 semantic token에 매핑한다.
  새 결과 API 오류는 "결과를 찾을 수 없습니다(만료되었거나 접근할 수 없음)" 한 상태로 알리고 재시도는
  network·형식 오류에만 둔다.
- **Standalone 표**(`interactive-data-table.tsx`, legacy `prepare_table`): Backend가 검증해 보낸
  최대 100행 안에서 검색·열 정렬·페이지 크기 10/25/50/100과 이전/다음 이동을
  제공한다. 원본 건수와 실제 포함 건수를 함께 표시하고 잘린 결과를 알린다.
  표 본문은 최대 `32rem` 높이에서 내부 스크롤한다.
- **Markdown**: `AssistantText`의 `leading-[1.6]`, 표/코드/SQL은 항상 mono +
  `tabular-nums` + 가로/세로 스크롤 캡(`max-h-96`). 답변의 숨김 h2 아래에서
  Markdown 제목을 h3~h6으로 정규화하되 시각적 크기는 기존 type scale로 유지한다.
  긴 본문·링크·inline code는 줄바꿈하고 표·코드 블록의 내부 스크롤은 보존한다.
  표 중복 제거는 standalone payload와 컬럼·행이 확인된 경우에만 적용한다.
- **메시지 액션**: Copy/Edit/Reload primitives를 유지하며 hover 없이도 키보드로
  접근하도록 액션 DOM을 유지한다. 편집·재생성은 이전 내용을 지우지 않고 새 분기로
  남기므로 확인창을 띄우지 않고, 대안이 둘 이상일 때만 `BranchPickerPrimitive`
  (`이전/다음 질문·답변`, `n / m`)를 보인다. 분기는 이번 브라우저 세션 동안만 유지된다.
  새 채팅·대화 전환에도 확인창을 띄우지 않는다. 지식 편집의 미저장 변경 보호는
  별도로 유지한다. DB 세션 관리는 후속 범위다.
- **좁은 화면 패널**: 기존 860/1180px 접힘 임계값을 유지한다. 임계값 아래 재개방은
  Chat 폭을 줄이지 않는 비모달 overlay이며 Escape/닫기 시 여는 조작으로 복귀한다.
  Tab으로 패널을 벗어나면 닫되 이동한 포커스를 빼앗지 않는다.
- **Data table**(`primitives.tsx` `DataTable`, `assistant-ui/elements/markdown-text.tsx` `Table`):
  동일한 스크롤 래퍼(`thin-scroll max-h-96 overflow-x-auto overflow-y-auto`)
  를 공유한다. 둘 중 하나만 고치고 다른 하나를 잊지 않는다.
- **Composer**(`assistant-ui/elements/thread.aui.tsx`): `ComposerPrimitive`가 전송/Enter/
  Shift+Enter/자동 높이/실행 중 비활성을 소유한다. Send/Stop은 `AuiIf`로
  전환하고 직접 상태를 구독해 조건부 렌더하지 않는다. Input에는 반드시
  `aria-label`을 둔다(placeholder만으로 접근성 이름을 대신하지 않는다).
- **Sidebar**(`app-sidebar.tsx`): 대화 목록은 assistant-ui `ThreadListPrimitive`이고
  이번 브라우저 세션 동안만 유지되므로 상단 전역 메뉴는 `새 채팅` → `지식 관리`, 그 아래는 최근 대화 목록으로
  구성한다. 지식 관리에서 채팅으로 돌아갈 때 중앙 헤더에 별도 복귀 버튼이나
  `채팅` 메뉴를 두지 않고, 현재로 표시된 최근 대화 항목을 사용한다. 같은 항목을
  누르면 Composer·스트리밍·스크롤을 보존해 복귀한다. `새 채팅`은 새 thread로 전환하고
  (이미 빈 새 대화라면 초안을 지운다) 첫 질문 전에는 `새 대화` 항목이 현재로 표시된다.
  대화가 있는 thread의 Composer 초안은 그 thread에 남는다. 다른 thread가 응답 중이어도
  전환할 수 있으며 목록에 `응답 중…`으로 표시한다. 제목은 첫 질문을 줄인 값이다.
  "현재 브라우저 세션 동안만 유지됩니다" 같은 안내를 목록 위에 유지한다.
  실제 persistence 계약이 생기기 전까지 이 안내를 지우지 않는다. 실제로
  연결되지 않은 액션(설정 등)은 `disabled` + `title`로 이유를 밝힌다.
- **Inspector**(`context-inspector.tsx`): 도구 → 스킬 → 지식 순의 읽기 전용 조회다.
  지식은 제목·유형·검토 상태와 짧은 설명을 간결한 목록으로 함께 보여준다.
  우측 패널에는 출처와 중앙 관리 화면 이동 링크를 표시하지 않는다.
  텍스트 등록·검토·활성화는 좌측 지식 관리 메뉴에서 수행한다. 구조화 YAML과
  도구·Skills에는 활성화 토글을 두지 않는다. 메타·프롬프트 예시 탭은 제거했다.
  도구 상세에는 설명과 결과 형태만 표시하고 입력 JSON Schema는 노출하지 않는다.
  Skills는 이름·요약을 항상 표시하고 disclosure를 열었을 때 상세 Markdown을
  제목·목록·코드로 렌더링한다. 버튼은 `aria-expanded`/`aria-controls`를 제공한다.
  1280px 이상에서는 긴 절차의 줄바꿈을 줄이기 위해 23rem 폭을 쓴다.
- **지식 관리 상세**(`knowledge/structured-detail.tsx`): 구조화 YAML의 배열·객체를
  raw JSON으로 기본 출력하지 않는다. 최상위는 필드명과 값의 2열 구조, 태그·grain은
  줄바꿈 chip, 설명 목록은 불릿, 컬럼은 이름·형식·설명 행, SQL은 제한 높이의 mono
  블록으로 표시한다. 최상위 빈 값은 `없음`으로 알리고 반복 행의 선택적 빈 필드는
  생략한다. `query_rules`, `aggregation_rules`, `visualization_hints`는 각각 조회 규칙·
  집계 규칙·시각화 안내로 표시하고, table/recipe의 `sample_queries`는 질문·SQL만
  렌더링한다. 좁은 폭에서는 1열로 재배치하며 전체 페이지 가로 스크롤을 만들지 않는다.
- **구조화 지식 편집**(`knowledge/editor/`): 상세(`StructuredDetail`)는 읽기 전용으로 두고 "수정 요청"·"구조화 지식 추가"로만 편집기를 연다.
  편집기는 `입력 폼 | 원문 YAML | 변경 검토` 탭(`role="tablist"`, 방향키·Home/End)으로 구성한다. 폼은 서버 가이드 명세의 `widget`으로 재귀 렌더링하고
  카드 대신 좌측 룰(`border-l`)과 그룹 제목의 하단 룰로 구분한다. 필수는 "필수" 텍스트, 오류는 필드 아래 문장과 `aria-invalid`로 알리며
  색만으로 전달하지 않는다. 식별자(key) 필드와 `status`·`updated`는 읽기 전용이다. 검증 요약은 polite live region, 승인·반려는 근거 필수 Dialog다.
  diff는 mono `text-data`, 추가·삭제를 `+`/`−`와 sr-only 텍스트로 함께 표시하고 변경 없는 구간은 접는다.
  상태 배지(초안·검토 대기·승인됨·반려됨·철회됨)는 점 + 텍스트다. 임시 사용자 선택기는 인증 연동 전임을 밝히는 문구를 유지한다.
- **Empty/loading/error 상태**: 오류는 항상 "무엇이 실패했고 무엇을 하면
  되는지"까지 문장으로 설명한다(`MessageError`·`ErrorState` 참고). 로딩은
  스켈레톤보다 짧은 문구("불러오는 중…")나 `role="status"` pulse 블록을
  우선한다(차트 로딩 등 형태가 예측 가능한 경우만 스켈레톤 사용).
- **Button/icon**: Lucide 아이콘 `size-3~3.5`. 1차 액션(전송)만 `bg-accent`
  채움, 나머지는 텍스트/ghost. 파괴적 액션은 이 저장소에 아직 없다 — 추가할
  때는 `--block-ink` 텍스트 + 명확한 확인 문구를 쓴다.
- **focus-visible/keyboard**: 모든 대화형 요소는 `:focus-visible`의 전역
  outline(`--accent`, 2px)을 기본으로 한다. Composer textarea만 form의
  `focus-within` 테두리와 중복되지 않도록 내부 outline을 제거한다. 새 버튼은
  `<button type="button">` + `aria-label`(아이콘만 있을 때) 규칙을 따른다.

## 금지 사항

- 외부 폰트·CDN·telemetry 추가.
- 컴포넌트에 semantic token 없이 hex/rgb 하드코딩(다크 코드 트레이 등
  기존 예외 외 새로 늘리지 않기).
- 과도한 gradient·glassmorphism·큰 그림자·전면 카드화.
- Backend 계약(`AgentEvent`, tool payload, Result Store, `tool_call_id`
  등)에 없는 데이터를 추측해 표시하거나 새로 만들어내기.
- 결과·근거를 항상 펼쳐 놓아 최종 답변보다 시각적으로 우세하게 두기.
- `status` 이벤트를 모델 reasoning처럼 표현하거나 모델 thinking을 꾸며 표시하기.
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
- 공개 진행 단계는 AgentPlan, 도구 결과는 ToolCall을 사용한다. 가짜 tool args나
  미연결 버튼을 만들지 않는다. 실제 완료된 단계만 완료로 센다.
- 원격 이미지·첨부·음성·Cloud 기능은 현재 계약에 없다. 공식 예제의
  useChatRuntime은 현재 SSE에 적용하지 않는다. 상세 예외는 [AGENTS.md](AGENTS.md),
  전환 근거는 [기술 결정](docs/decisions.md)을 따른다.
