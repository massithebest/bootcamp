# Frontend 결정 사항 기록

`frontend/`에서 스캐폴딩 이후 내려진 주요 결정과 그 배경을 시간순으로
정리한다. [closed-network.md](./closed-network.md)(폐쇄망 운영 원칙, 스캐폴딩
시점부터 계속 유효)만 별도 문서로 두고, 나머지 개별 결정은 모두 이 문서
하나에 절 단위로 모아둔다.

## 빠른 요약

| 결정 | 상태 | 절 |
| --- | --- | --- |
| 스캐폴드 §29 (사이드바/세션 목록/설정/인스펙터 "not yet") | **superseded** — 전부 구현됨 | [3-pane 워크벤치 리디자인](#3-pane-워크벤치-리디자인) |
| shadcn/ui 도입 (스캐폴딩 당시 "custom Tailwind만" 방침 대체) | **결정 완료** (2026-09-11) | [shadcn/ui 도입](#shadcnui-도입) |
| Tailwind v3 → v4 | 완료 (shadcn 도입에 따른 부수 작업) | [shadcn/ui 도입](#shadcnui-도입) |
| 외부 폰트/CDN/원격 리소스 미사용 | 유효, 계속 적용 중 | [closed-network.md](./closed-network.md) |
| 마크다운 렌더러 자체 구현 (라이브러리 미사용) | 유효 | [closed-network.md](./closed-network.md) |
| AI Elements 컴포넌트 도입 (`useChat`/`@ai-sdk/react`/`streamdown` 미사용) | **결정 완료** (2026-09-14) | [ai SDK 및 채팅 UI 라이브러리 도입 검토](#ai-sdk-및-채팅-ui-라이브러리-도입-검토) |
| 지식 카드(`kind: catalog`)·Skills 탭 API 연결 | **대기** — 백엔드 계약 확정 후 착수 | [plan/domain-knowledge-plan.md](../plan/domain-knowledge-plan.md) |

---

## 3-pane 워크벤치 리디자인

**일자:** 2026-09-08
**상태:** 결정 완료 — 스캐폴드 §29(사이드바/세션 목록/설정/인스펙터 "not yet")를 대체(supersede)함

### 구현된 것

- `app-sidebar` — 세션 목록
- `context-inspector` — Skills / Metadata / Prompt 3개 탭
- `chat-window.tsx` 안의 3-pane 셸 (사이드바 / 중앙 대화 / 인스펙터)

### 데이터 소스

- 사이드바·인스펙터·시드(seed) 대화 내용은 `src/lib/dummy.ts`에 **하드코딩된 더미 데이터**다. 실제 제조 도메인 용어를 사용하며 lorem ipsum은 쓰지 않는다.
- 실제 백엔드 연동은 `lib/chat-api.ts`를 통해 유지된다 — 사용자가 새로 보내는 메시지는 실제 백엔드를 호출한다.

### 디자인 토큰

`src/app/globals.css`의 CSS 변수 + `tailwind.config.ts`의 semantic 이름 매핑을 사용한다.

- 표면 3단계: `--canvas` (중앙, 가장 밝음) → `--surface` (사이드바/인스펙터) → `--surface-2` (hover/중첩)
- 텍스트: `--ink` / `--ink-2` / `--ink-3`
- 액센트: 파란색 1개 (`--accent`, 활성 세션·포커스·주요 액션 한정)
- 상태: 저채도 3색 (정상/주의/차단 — `--ok-*` / `--warn-*` / `--block-*`)
- 폰트: 산문은 sans, 데이터/SQL/코드/숫자는 mono로 명확히 구분

> shadcn/ui 도입(2026-09-11) 이후에도 이 토큰 체계가 그대로 기준이다. shadcn 컴포넌트는 자체 팔레트를 쓰지 않고 이 토큰에 재매핑되어 있다. 자세한 내용은 [shadcn/ui 도입](#shadcnui-도입) 참고.

### 메시지 구조

어시스턴트 메시지는 `parts: MessagePart[]` (text/tool, 도착 순서)를 사용한다. 단일 `content` 문자열이 아니다 — 그래야 도구 호출 전 내레이션과 최종 답변이 하나의 블록으로 뭉개지지 않는다. `content` 필드는 이제 사용자 메시지 전용이다.

### 마크다운 렌더링

어시스턴트 텍스트는 `src/components/chat/markdown.tsx`에서 직접 구현한 최소 마크다운 뷰어로 렌더링한다 (외부 라이브러리 미사용 — [closed-network.md](./closed-network.md) 참고). 지원 범위: 헤딩, 볼드/이탤릭/코드, 리스트, 테이블, 인용, hr, 코드 펜스.

### 알아둘 CSS 이슈

`chat-window.tsx`의 flexbox 스크롤 관련:

- 중앙 `<section>` → `min-h-0 overflow-hidden` 필요
- 스크롤 div → `min-h-0` 필요
- 입력창 wrapper → `shrink-0` 필요

이 셋 중 하나라도 빠지면, 긴 스트리밍 응답이 들어올 때 입력창이 화면 밖으로 밀려난다.

### 백엔드 계약

`AgentEvent` 타입(text/status/tool_call/tool_result/error/done)은 변경되지 않았다. `status` 이벤트의 data shape은 `{ step, label?, status }`로 가정하며, `backend/agent/event_adapter.py`와 일치한다.

당시 로컬 환경에서 8000을 무관한 `toss-portfolio-api`가 점유하고 있어 백엔드를 포트 8010으로 띄웠다 (`.env.local` → `NEXT_PUBLIC_API_BASE_URL=http://localhost:8010`). 이후 그 제약이 사라져 포트는 다시 **8000**으로 되돌렸다 — 현재 기준은 [frontend/CLAUDE.md](../CLAUDE.md)를 따른다. `backend/main.py` + `backend/core/config.py`에 CORS 미들웨어 추가됨 (`CORS_ALLOW_ORIGINS`, localhost:3000만 허용).

---

## shadcn/ui 도입

**일자:** 2026-09-11
**상태: 결정 완료** — shadcn/ui 도입. (스캐폴딩 당시의 "custom Tailwind 컴포넌트만 사용" 방침을 대체함)

### shadcn/ui 설치 방식과 폐쇄망 영향

shadcn/ui는 일반적인 npm 패키지가 아니다. `npx shadcn add <component>` CLI가 컴포넌트 소스 코드(`.tsx`)를 **`https://ui.shadcn.com` 레지스트리에서 fetch해서 프로젝트에 직접 복사**하는 방식이다. 즉:

- **CLI 자체(`shadcn` 패키지)** 는 일반 npm 패키지라 사내 레지스트리 미러링 가능
- **컴포넌트 소스**는 npm 의존성이 아니라 복사된 코드 — 한 번 인터넷 환경에서 `add`해서 커밋해두면, 이후 폐쇄망 빌드/설치 시 `ui.shadcn.com` 접근이 전혀 필요 없다

**결론: 인터넷 되는 환경에서 필요한 컴포넌트를 미리 다 추가해서 커밋해두는 전략을 취했다.** 폐쇄망에는 이미 소스로 반입되므로 CLI나 네트워크가 필요 없다.

### CLI가 자동으로 깨뜨린 것들 (init 시 발견)

`shadcn@4.21.0`의 `init`은 최신 Tailwind v4 스타일(`base-nova`)을 기본값으로 쓰는데, 이 프로젝트는 당시 Tailwind v3.4.6이었다. 그 결과:

1. **버전 불일치로 컴포넌트가 동작하지 않음** — v4 전용 문법(`@theme`, `@import "shadcn/tailwind.css"`)을 `globals.css`에 그대로 썼고, `tailwind.config.ts`는 전혀 갱신하지 않아 `bg-background` 등 shadcn 유틸리티 클래스가 아예 매핑되지 않았다.
2. **디자인 토큰 충돌** — shadcn이 `:root`에 자기 `--accent`를 새로 정의하면서, 기존 프로젝트의 `--accent: #2f5fd0`(파란 액센트, [3-pane 워크벤치 리디자인](#3-pane-워크벤치-리디자인) 참고)를 그대로 덮어썼다. CSS는 나중 선언이 이기므로 `:focus-visible` 아웃라인 등 액센트를 쓰는 모든 곳이 무채색으로 깨졌다.
3. **폐쇄망 원칙 위반** — `layout.tsx`에 `next/font/google`의 `Geist` 폰트를 자동으로 추가했다. 이 프로젝트는 외부 폰트/CDN을 쓰지 않고 시스템 폰트만 사용한다는 원칙([closed-network.md](./closed-network.md))이 있는데, `next/font/google`은 빌드 시점에 Google Fonts를 네트워크로 fetch하려 시도하므로 폐쇄망에서 반드시 빌드 실패한다. 실제로 빌드해보니 `Unknown font 'Geist'` 에러로 즉시 드러났다.

### 해결 방법

1. **Tailwind v3 → v4로 업그레이드**
   - `tailwindcss@4.3.3`, `@tailwindcss/postcss@4.3.3` 설치
   - `autoprefixer` 제거 (v4에 내장됨)
   - `postcss.config.mjs` → `@tailwindcss/postcss` 플러그인으로 교체
   - `globals.css` 상단을 `@import "tailwindcss";` + `@import "tw-animate-css";` + `@config "../../tailwind.config.ts";`로 재작성 — 기존 `tailwind.config.ts`의 커스텀 색상/폰트/radius 확장을 그대로 유지하면서 v4 엔진에 연결

2. **shadcn 토큰을 별도 네임스페이스로 분리**
   - shadcn이 쓰는 모든 CSS 변수(`--background`, `--primary`, `--accent`, `--border` 등)를 `--shadcn-*`로 프리픽스
   - `@theme inline` 블록에서 `--color-primary: var(--shadcn-primary)` 식으로 Tailwind 유틸리티에 연결
   - `--shadcn-*` 값 자체는 기존 프로젝트 토큰을 가리키도록 매핑: 예) `--shadcn-primary: var(--accent)`, `--shadcn-background: var(--canvas)`, `--shadcn-muted-foreground: var(--ink-2)`
   - 결과: shadcn 컴포넌트도 자체 팔레트가 아니라 프로젝트 고유 디자인 언어를 그대로 따른다. 이 프로젝트는 라이트 테마만 쓰므로 `.dark` 블록은 만들지 않았다.

3. **Geist 폰트 추가분 제거**
   - `layout.tsx`에서 `next/font/google` import와 `Geist(...)` 호출, `cn(...)` 적용을 되돌리고 원래의 시스템 폰트 기반 `<html lang="ko">`로 복구

4. **package.json 정리**
   - `@tailwindcss/postcss`, `shadcn`은 devDependency로 이동 (런타임 코드가 아닌 빌드/CLI 도구)
   - 런타임 dependency로 남은 것: `@base-ui/react`(헤드리스 UI 프리미티브), `class-variance-authority`, `cn`, `lucide-react`(아이콘, SVG 번들 방식이라 외부망 호출 없음), `tw-animate-css`

### 검증

`npm run build`로 정적 빌드 성공을 확인했다. 새로 추가된 모든 의존성은 순수 npm 패키지이며, 런타임에 외부 CDN·폰트·API를 호출하는 코드는 없다 (소스 내 하드코딩된 외부 URL 없음을 grep으로 확인).

### 설치된 컴포넌트 (1차)

`button`, `input`, `textarea`, `select`, `dialog`, `tabs`, `sidebar`(+ 의존 컴포넌트 `sheet`, 훅 `use-mobile`), `separator`, `scroll-area`, `tooltip`, `badge`, `dropdown-menu`, `popover`, `skeleton`.

- `tooltip`은 실제로 쓰기 시작하는 시점에 `layout.tsx`를 `TooltipProvider`로 감싸야 한다. 현재는 아무 데서도 쓰지 않으므로 아직 추가하지 않았다.

### 열린 이슈

shadcn의 `sidebar.tsx`(자체 `--sidebar-*` CSS 변수와 `SidebarProvider` 구조를 가짐)와, [3-pane 워크벤치 리디자인](#3-pane-워크벤치-리디자인)에서 이미 만든 커스텀 `app-sidebar` 컴포넌트 사이의 이름/동작 충돌 여부가 아직 검토되지 않았다. shadcn의 sidebar를 실제 3-pane 레이아웃에 배선하기 전에 확인이 필요하다.

### 향후 컴포넌트 추가 시 체크리스트

인터넷 되는 환경에서 `npx shadcn add <component>` 실행 후:

1. `globals.css`에 새 `--shadcn-*` 변수가 추가됐다면, 프로젝트 기존 토큰에 매핑되어 있는지 확인 (자체 색상값을 그대로 두지 말 것)
2. `layout.tsx`나 다른 파일에 원치 않는 자동 변경(폰트, 전역 스타일 등)이 없는지 `git diff`로 확인
3. `npm run build`로 폐쇄망 조건(오프라인 리소스 없이)에서도 빌드되는지 확인
4. 문제 없으면 커밋 — 이후 폐쇄망에는 이 소스만 반입하면 됨

---

## ai SDK 및 채팅 UI 라이브러리 도입 검토

**일자:** 2026-09-14
**상태: 결정 완료 — AI Elements 채택, 컴포넌트만 사용 (`useChat` 미사용).**

### 배경

`ai` 패키지(`ai@7.0.97`)는 설치만 되어 있고 코드베이스 어디에서도 import되지
않은 상태였다. 채팅 UI/에이전트 진행상태 표시 라이브러리 도입 필요성이
제기되어, AI Elements / assistant-ui / CopilotKit / Chatscope / react-chat-elements
5종을 이 프로젝트 기준(폐쇄망, FastAPI 커스텀 SSE, Tailwind v4 + shadcn, 도구
실행 진행상태 표시가 핵심 요구사항)으로 검토했다.

### 결론: AI Elements 채택 — 단, "컴포넌트 소스"만

`useChat`/`@ai-sdk/react`/`streamdown`은 도입하지 않는다.

**근거:**

- AI Elements 컴포넌트(`tool`, `chain-of-thought`, `task`)는 plain props로
  동작하며 React 19나 AI SDK 풀스택 도입을 강제하지 않는다. `tool`/`message`는
  `ai` 패키지의 **타입만** import(`ToolUIPart`, `UIMessage`) — 이미 설치된
  `ai@7.0.97`로 충분하다.
- assistant-ui는 런타임 프레임워크라 스레드·브랜칭·첨부 등 이 프로젝트가 안
  쓰는 기능까지 번들에 들어오고(dist 4.1MB), `radix-ui` 전체·`zustand`·`zod@4`를
  런타임 의존성으로 끌고 와 shadcn base-nova(`@base-ui/react`)와 프리미티브가
  이중화된다. `assistant-cloud` 모듈에 `https://backend.assistant-api.com`이
  하드코딩되어 있다(opt-in이라 실제 호출은 없지만 감사 대상으로 남는다).
- Chatscope / react-chat-elements는 사람-사람 메신저 UI라 도구 실행 단계
  표시라는 핵심 요구사항 자체를 지원하지 않는다.
- 상태 소유권은 그대로 유지된다. `chat-window.tsx`의 `applyEvent` 리듀서·
  `AbortController`·재시도 로직, `types/chat.ts`의 `AgentEvent` 계약,
  `lib/chat-api.ts`는 변경하지 않았다.

### 적용 범위

- `agent-progress.tsx` → `ChainOfThought` + `ChainOfThoughtStep`(status
  `active|complete|pending`, `StatusStep`과 거의 1:1; `error`는 아이콘으로
  표현). "진행 중 자동 펼침 / 완료 후 접힘 / 사용자 토글 우선" 동작은
  controlled `open`/`onOpenChange`로 보존.
- `tool-result-card.tsx` → `Tool` + `ToolHeader`(state
  `output-available|output-error`) + `ToolOutput`(ReactNode 슬롯). 기존
  `DatabaseResult`/`KnowledgeResult`/`SimulationResult`와 예정된 `ChartBlock`이
  이 슬롯에 들어간다.
- 복사된 소스는 `src/components/ai-elements/`에 두고 **우리 코드로 취급**한다
  (shadcn `ui/`와 동일한 원칙). `tool.tsx`는 색을 프로젝트 토큰
  (`--ok-ink`/`--block-ink`/`--accent`)으로, 상태 라벨을 한국어로 바꿨다.

### 폐쇄망 검증

AI Elements는 소스 복사 방식. 받은 소스가 의존하는 `streamdown`(마크다운),
`shiki`(code-block), `@radix-ui/react-use-controllable-state`(chain-of-thought
훅) **셋 다 도입하지 않았다** — `message`(streamdown)는 받지 않았고,
`tool.tsx`에서 `code-block` import를 제거했으며, radix 훅은
`src/hooks/use-controllable-state.ts` 로컬 구현으로 치환했다. 결과적으로
**신규 npm 런타임 의존성 0**, `package.json` 변경 없음. 프리미티브는
`@/components/ui/collapsible`(base-ui)을 그대로 쓴다.

### 재검토 트리거

- 자체 `markdown.tsx`를 `streamdown`(AI Elements `message`)으로 대체할지 —
  코드블록 하이라이팅·mermaid가 필요해지는 시점. closed-network.md 원칙
  4("마크다운 렌더러는 자체 구현 우선")와 충돌하므로 별도 결정 필요.
- tool 승인(human-in-the-loop) UX가 필요해지면 AI Elements `confirmation`
  또는 assistant-ui의 approval 흐름을 비교.
- CopilotKit은 세부 검증하지 않았다 — 필요해지면 별도 조사.

### 관련 문서

- [closed-network.md](./closed-network.md) — 폐쇄망 원칙
- [shadcn/ui 도입](#shadcnui-도입) — shadcn CLI 소스 복사 방식의 선례
