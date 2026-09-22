# assistant-ui Design System 기반 Frontend 리팩토링 계획

## Context

`frontend/CLAUDE.md`는 2026-09-16 `frontend-design` Skill 기반 3-pane 워크벤치
리디자인과 이후 assistant-ui Elements 전환에서 확정된, 이미 상당히 성숙한
의미 기반(semantic token) 디자인 규칙을 갖고 있다. 카드/그림자 남용 금지,
좌측 룰 기반 구획, hex 하드코딩 금지, `text-2xs/data/ui/ui-lg` 타이포 스케일,
단일 액센트 색 등 assistant-ui의 "printed document" 철학과 상당 부분 이미
일치한다.

이번 작업은 "지저분한 프로젝트를 assistant-ui 기준으로 전면 교체"가 아니라,
**두 탐색 에이전트가 실제로 찾아낸 구체적 불일치**(아이콘 크기 12종 난립,
`tool-group.aui.tsx`의 `text-sm`/`rounded-lg` 이탈, `context-inspector.tsx`의
`space-y-1~5` 혼용, `thread.aui.tsx`의 단발성 `rounded-md`)를 assistant-ui
공식 문서(`design.md`, `/elements`) 기준으로 바로잡고, 사용자가 명시적으로
결정한 두 가지 지점(**radius 6단계 체계 도입**, **accent(blue)를 live 상태
전용으로 축소**)을 반영해 `frontend/CLAUDE.md`의 해당 규칙을 갱신하는 것이다.
또한 assistant-ui의 공식 design 문서를 폐쇄망에서도 읽을 수 있도록
`frontend/docs`에 원문을 미러링하고 `frontend/AGENTS.md`에서 그 위치를
가리키게 한다.

**범위 밖(건드리지 않음):** Backend API 계약, SSE 처리, Runtime 구조, Tool
호출 로직, Agent 상태 관리, 비즈니스 로직. 다크 모드는 추가하지 않는다(라이트
전용 유지, 기존 결정). 외부 폰트/CDN은 도입하지 않는다(폐쇄망 원칙 유지).
최근(2026-09-22) 이미 정리된 미사용 Elements(`reasoning*`, `tool-fallback.aui`,
`thread-list*`, `attachment.aui`, `image`, `file`)는 되살리지 않는다 — 제품이
쓰지 않는 기능(모델 reasoning 노출, 첨부/이미지/음성)이므로 CLAUDE.md의 기존
금지 규칙과 일치한다.

## 사전 조사 요약 (실행 시 재탐색 불필요)

- 토큰 소스: `frontend/src/app/globals.css`(CSS 변수·shadcn 브릿지),
  `frontend/tailwind.config.ts`(fontSize/borderRadius/color 매핑),
  `frontend/components.json`(`style: base-nova`, `iconLibrary: lucide`).
- 아이콘: lucide-react만 사용. 실제 `size-*` 사용 분포(92건) —
  `size-3.5`(23) ≈ `size-4`(23) ≈ `size-3`(15) 이 주력이고, `size-7`(8)/
  `size-8`(6)이 아이콘 버튼 컨테이너, 그 외 `size-6`(4)/`size-9`(1)/`size-10`(2)/
  `size-5`(1)는 이탈값. `size-1.5`/`size-2`/`size-2.5`(총 9건)는 상태 점 등
  비-아이콘 장식 요소로 별도 취급 필요.
- Radius: 현재 `--shadcn-radius: 0.3125rem`(5px) 하나에서 `sm(1px)/md(3px)/
  lg(5px)/xl(9px)`를 파생. 앱 코드는 bare `rounded`(59건, 5px)가 지배적이고
  `rounded-2xl`(1건, Composer, 명시적 예외)·`rounded-full`(14건, capsule류)이
  뒤를 잇는다. `rounded-md/lg/xl`은 대부분 `components/ui/*`(shadcn vendor)에
  집중.
- Shadow: 앱 코드에서는 `thread.aui.tsx`의 Composer·ScrollToBottom
  `shadow-sm` 2곳뿐 — 이미 규칙과 일치.
- Typography: 앱 코드는 `text-2xs/ui/ui-lg/data` 스케일을 지배적으로 사용
  (총 266건). 예외는 `tool-group.aui.tsx`의 `text-sm` 2곳뿐.
- Spacing: `chat/`·`assistant-ui/elements/`는 `gap-*` 관용구, `knowledge/`는
  `space-y-*` 관용구로 이미 폴더별 일관성이 있음. 유일한 파일 내부 불일치는
  `context-inspector.tsx`(한 파일에서 `space-y-1/2/3/4/5` 5종 혼용).
- Accent 사용처: `--accent`는 포커스 링(`:focus-visible`, 전역), 스트리밍
  커서(`AssistantText`), 실행 중 로더 아이콘(`ToolGroupTrigger`의
  `LoaderIcon`), 활성 대화 항목(`app-sidebar.tsx` `bg-accent-weak`), 전송
  버튼 채움색, 사이드바 로고 배지에 쓰인다. 앞 네 가지는 각각
  focus/streaming/running/selected로 이미 assistant-ui 기준과 일치하고,
  뒤 두 가지(전송 버튼, 로고 배지)만 live 상태가 아닌 decoration에 해당해
  변경 대상이다.
- assistant-ui `design.md` 핵심 토큰(공식 문서 원문 기준): radius
  `document/sm=6px`, `control/md=8px`, `surface/lg=10px`, `xl(floating
  card: dialog/toast)=12px`, `thread=16px`, `capsule=9999px`. Mono는
  "타이핑/설치하는 것"(SQL/코드/CLI/모델명/툴명/시스템 메타)에만. Section
  경계는 `border-t`만 인정, 나머지 구분선은 삭제 후보. Floating surface는
  반드시 shadow와 함께 rounded. Blue는 streaming/running/connected/selected
  신호 전용, decoration 금지.

## 사용자 결정 사항

1. **Radius 6단계 체계 도입.** CLAUDE.md의 "공식 Elements의 radius를 그대로
   복사해 새 예외를 늘리지 않는다" 규칙을 이 체계로 교체한다.
2. **Accent(blue)를 live 상태(streaming/running/connected/selected) 전용으로
   축소.** 전송 버튼 등 순수 CTA 강조는 무채색(ink 계열)으로 옮긴다. 포커스
   링은 "selected/현재 대상"의 연장으로 간주해 accent 유지(접근성 유지,
   design.md에 포커스에 대한 명시적 금지 없음 — 이 해석을 CLAUDE.md에 명시).

## Phase 2 — Design Token 정리

### Radius (`frontend/src/app/globals.css`, `frontend/tailwind.config.ts`)

`:root`에 의미 기반 원시 토큰 추가:

```css
--radius-document: 0.375rem; /* 6px: 패널·경고·툴 카드·배지(사각) */
--radius-control: 0.5rem;    /* 8px: 버튼·입력·탭·select trigger */
--radius-surface: 0.625rem;  /* 10px: popover·dropdown·tooltip */
--radius-floating: 0.75rem;  /* 12px: dialog·toast·sheet·card */
/* thread(16px)는 기존 rounded-2xl 그대로 사용 — 이미 정확히 일치 */
/* capsule(9999px)는 기존 rounded-full 그대로 사용 */
```

`@theme inline`의 `--radius-sm/md/lg/xl`를 위 값으로 재정의(`--radius-sm:
var(--radius-document)`, `--radius-md: var(--radius-control)`, `--radius-lg:
var(--radius-surface)`, `--radius-xl: var(--radius-floating)`). `tailwind.config.ts`의
`borderRadius.DEFAULT`를 `--radius-document`(6px)로 변경 — 앱 코드의 bare
`rounded`(59건)가 자동으로 새 document 값을 받는다(5→6px, 시각 변화 미미).

`components/ui/*`를 역할별로 재분류(대표 파일 기준, 전수 스윕):
- control(8px, `rounded-md`): `button.tsx`, `input.tsx`, `textarea.tsx`,
  `select.tsx`의 trigger, `tabs.tsx`의 trigger.
- surface(10px, `rounded-lg`): `popover.tsx`, `dropdown-menu.tsx`,
  `tooltip.tsx`, `select.tsx`의 content.
- floating card(12px, `rounded-xl`): `dialog.tsx`, `card.tsx`, `sheet.tsx`,
  `sidebar.tsx`.

앱 코드에서 위 분류에 어긋나는 것만 교정:
- `components/assistant-ui/elements/tool-group.aui.tsx`의 `outline`/`muted`
  variant(`rounded-lg`, 정적 패널) → `rounded`(document)로 변경. surface
  값을 받아 popover와 같은 radius가 되는 것을 막는다.
- `components/assistant-ui/elements/follow-up-suggestions.aui.tsx`의 제안
  칩(`rounded-lg`, 클릭 가능한 버튼) → `rounded-md`(control)로 변경.
- `components/chat/empty-state.tsx`의 예시 질문 버튼이 같은 성격이면 동일
  적용.
- `thread.aui.tsx`의 비활성 모델/추론강도 pill 2곳(`rounded-md`)은 **버튼**이므로
  이미 control 값과 일치 — 수정 불필요(기존에 "이탈"로 보였던 것이 신규
  체계에서는 올바른 분류가 됨. 최종 보고서에 명시).

### Accent 범위 축소 (`globals.css`, `tailwind.config.ts`)

`--accent` 주석을 "활성 세션·포커스·주요 액션"에서 "streaming·running·
connected·selected(및 그 연장인 focus) 전용, decoration 아님"으로 갱신.
전송 버튼 등 무채색 CTA용 토큰 추가:

```css
--ink-strong: #0d141d; /* 전송 등 1차 액션 채움 hover */
```

(fill은 기존 `--ink`, hover는 `--ink-strong` 재사용 — 새 색상 계열 최소화)

변경 대상(grep `bg-accent`/`text-accent`/`border-accent` 전수 확인 후 아래
기준으로 분류):
- **accent 유지**: `:focus-visible` outline, `AssistantText`의 스트리밍
  커서, `ToolGroupTrigger`의 실행 중 `LoaderIcon`, `app-sidebar.tsx`의
  활성 대화 항목(`bg-accent-weak`) — 각각 focus/streaming/running/selected.
- **ink로 변경**: `thread.aui.tsx`의 전송 버튼 채움(`bg-accent` →
  `bg-ink hover:bg-ink-strong text-canvas`), `app-sidebar.tsx`의 로고 배지.
- shadcn 브릿지: `--shadcn-primary`(현재 `var(--accent)`)를 `var(--ink)`로
  재매핑해 shadcn `Button`의 기본 `primary` variant가 더 이상 blue가
  아니게 한다. `--shadcn-ring`은 accent 유지(포커스 예외).

## Phase 3 — Core Chat UI

- `tool-group.aui.tsx`: `text-sm` 2곳(트리거 라벨, content wrapper) →
  프로젝트 스케일(`text-ui` 또는 `text-2xs`, 실제 렌더 크기가 자식 요소의
  명시적 클래스로 이미 결정되는지 확인 후 결정)로 교체. radius는 위 Phase 2
  적용.
- `thread.aui.tsx`: 전송 버튼 색 변경 반영, Composer(`rounded-2xl`,
  `shadow-sm`)와 ScrollToBottom(`shadow-sm`)은 유지(이미 규칙과 일치 —
  assistant-ui의 "floating UI만 shadow" 원칙과도 일치).
- `follow-up-suggestions.aui.tsx`: radius 변경 반영.
- 아이콘 크기 스윕: `size-6`/`size-9`/`size-10`/`size-5` 이탈값을 문맥에
  맞춰 아래 4단계로 재분류(전수 그렙 후 파일별 적용, 패턴은 한 번만 기술):
  - `size-3.5`: 버튼/트리거 안의 보조 아이콘(기본값)
  - `size-4`: 독립적으로 배치되는 일반 아이콘
  - `size-7`: 아이콘 전용 소형 버튼 컨테이너(`TooltipIconButton` 기준)
  - `size-8`: 1차 액션 아이콘 버튼(전송 등)
  - `size-3`, `size-1.5`~`size-2.5`: 상태 점(`StatusDot`)·체크마크 등
    비-아이콘 마커는 이 규칙 대상에서 제외하고 그대로 둔다(CLAUDE.md에
    명시적으로 예외 기술).

## Phase 4 — Application UI

- `context-inspector.tsx`: 3개 탭 패널의 `space-y-1/2/3/4/5` 혼용을
  정리 — 항목 내부 간격(라벨-값 등)은 `space-y-1`, 항목 간 간격은
  `space-y-3`처럼 역할 2단계로 축소하고 세 탭에 동일 적용.
- `app-sidebar.tsx`: 로고 배지·활성 항목 색 변경 반영(위 Phase 2).
- `components/ui/*` radius 재분류 적용(대표 파일: `button.tsx`,
  `popover.tsx`, `dialog.tsx` — 나머지는 동일 패턴).
- SQL/Simulation 결과(`tool-result-card.tsx`, `tool-results/*`,
  `generative/*`)는 기존 bare `rounded`(document) 그대로 유지 — 이미
  카드가 아닌 좌측 룰 기반 구획이라 assistant-ui 원칙과 일치, 변경 불필요.
  `generative/query-table.tsx`의 카드형 section(`rounded border ... bg-surface`)만
  document 값 자동 반영 확인.

## Phase 5 — Cleanup & 문서

### `frontend/docs/assistant-ui-design.md` (신규)

`https://www.assistant-ui.com/design.md`를 원문 그대로 가져와 저장한다(요약
아님 — WebFetch는 요약 모델을 거치므로, 실행 시 `curl -sL` 또는 raw fetch로
바이트 그대로 받아 검증). 파일 최상단에 짧은 헤더만 추가:

```markdown
<!--
출처: https://www.assistant-ui.com/design.md (mirrored 2026-09-22)
이 프로젝트가 의도적으로 다르게 유지하는 부분은 frontend/CLAUDE.md
"assistant-ui 대비 의도적 차이" 절 참고. 이 파일 자체는 원문 그대로 유지한다.
-->
```

### `frontend/CLAUDE.md` 갱신

- Spacing과 shape 절: 기존 "공식 Elements의 radius를 그대로 복사해 새
  예외를 늘리지 않는다" 문장을 6단계 radius 표(document/control/surface/
  floating card/thread/capsule)로 교체.
- Color 기준 절: `--accent` 설명을 "streaming·running·connected·selected
  (및 focus) 전용"으로 갱신, 표의 "강조(활성 세션·포커스·주요 액션 한정)"
  문구 수정.
- Button/icon 절: "1차 액션(전송)만 `bg-accent` 채움"을 "1차 액션은 `bg-ink`
  채움, `bg-accent`는 streaming/running/connected/selected 신호 전용"으로
  교체. 아이콘 크기 규칙을 `size-3~3.5`에서 4단계 표(3.5/4/7/8, 상태 점
  예외 명시)로 교체.
- 새 절 "assistant-ui 대비 의도적 차이" 추가: 라이트 전용(다크 미지원),
  시스템 폰트만 사용(별도 display 서체 없음, 산문=`--font-sans`/데이터=
  `--font-mono` 2계열만 운용), reasoning UI 미사용(모델 chain-of-thought
  비공개 원칙), 첨부/이미지/음성/Cloud Elements 미사용 — 각각 폐쇄망 제약
  또는 기존 제품 결정이 이유임을 한 줄씩 남긴다.
- 문서 맨 위 또는 관련 절에 `frontend/docs/assistant-ui-design.md`를
  "공식 디자인 원문(폐쇄망 미러본)"으로 링크.

### `frontend/AGENTS.md` 갱신

"assistant-ui 적용 범위" 절에 현재 `https://www.assistant-ui.com/llms-full.txt`
링크 옆에, 디자인 규칙은 폐쇄망에서 `frontend/docs/assistant-ui-design.md`를
1차 참고 문서로 삼는다는 문장을 추가한다(API/동작 문서 링크는 유지, 디자인은
로컬 미러 우선).

### 최종 스윕

- 위 변경 후 `rounded-md/lg/xl` 잔여 사용을 재그렙해 새 3단계(control/
  surface/floating) 분류에서 벗어난 곳이 없는지 확인.
- `size-*` 재그렙으로 이탈값(6/9/10) 잔존 여부 확인.
- `frontend/plan/Todo.md`에 이번 작업의 핵심 결정(2가지 사용자 결정 +
  변경/유지 목록)과 검증 결과를 요약 통합하고, 이 상세 계획 파일
  (`frontend/plan/260922-assistant-ui-design-system-plan.md`)은 제거한다.

## 검증

```bash
cd frontend
npm test
npm run build   # type check 포함
npm run lint
```

수동 확인(데스크톱 브라우저, 1280px 이상만 — 모바일 검증 안 함):
- 빈 대화 welcome 화면, 스트리밍 중 assistant 메시지(커서 accent 유지 확인),
  ToolGroup 접힘/펼침(라벨 크기·radius), 전송 버튼(신규 ink 색·대비),
  Composer(`rounded-2xl` 그대로).
- Sidebar: 로고 배지(신규 색), 활성 대화 항목(accent-weak 유지).
- Context Inspector 3탭: 간격 일관성.
- Popover/Dropdown/Dialog(설정 버튼 tooltip 등): 새 surface/floating radius.
- SQL 결과·Simulation 결과 카드: radius·shadow 변화 없음(document 유지) 확인.
- 접근성: `:focus-visible` accent 링이 모든 대화형 요소에서 여전히 보이는지
  키보드 탭으로 확인(전송 버튼 색이 바뀌어도 포커스 링 자체는 유지).

## 최종 보고 형식

작업 완료 후 다음을 정리해 사용자에게 보고한다:
- 변경 파일 목록과 각각의 핵심 변경(토큰/컴포넌트별).
- radius/accent 재분류 표(무엇이 어디로 이동했는지).
- "이탈로 보였지만 신규 체계에서 올바른 것으로 판명된" 항목(`thread.aui.tsx`의
  `rounded-md` 버튼 2곳) — 큰 변화 없음도 명시.
- assistant-ui 대비 의도적으로 유지한 차이(라이트 전용, 시스템 폰트, reasoning
  UI 미사용 등)와 그 이유.
