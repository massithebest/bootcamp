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
| 마크다운 렌더러 자체 구현 (라이브러리 미사용) | **superseded** (2026-09-14) — `@assistant-ui/react-markdown` 로 교체 | [assistant-ui 도입](#assistant-ui-도입) |
| AI Elements 컴포넌트 도입 (`useChat`/`@ai-sdk/react`/`streamdown` 미사용) | 유효 — `tool`/`chain-of-thought`/`task` 는 계속 재사용 중 | [ai SDK 및 채팅 UI 라이브러리 도입 검토](#ai-sdk-및-채팅-ui-라이브러리-도입-검토) |
| assistant-ui(`@assistant-ui/react`/`react-markdown`) 도입 — 2026-09-14 기각 결정을 뒤집음 | **결정 완료** (2026-09-14) | [assistant-ui 도입](#assistant-ui-도입) |
| 지식 카드(`kind: catalog`)·Skills 탭 API 연결 | **대기** — 백엔드 계약 확정 후 착수 | [plan/domain-knowledge-plan.md](../plan/domain-knowledge-plan.md) |
| Next.js 14 App Router → Vite 7 + React 18 이관, `ai` 의존성 제거 | **결정 완료** (2026-09-14) | [Next.js → Vite 이관](#nextjs--vite-이관) |

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

- ~~자체 `markdown.tsx`를 `streamdown`(AI Elements `message`)으로 대체할지~~ —
  **발동함 (2026-09-14).** 단 `streamdown`이 아니라 `@assistant-ui/react-markdown`
  으로 교체했다 — assistant-ui 도입 자체가 이 트리거보다 먼저 결정됐기
  때문. 근거는 [assistant-ui 도입](#assistant-ui-도입) 참고.
- tool 승인(human-in-the-loop) UX가 필요해지면 AI Elements `confirmation`
  또는 assistant-ui의 approval 흐름을 비교.
- CopilotKit은 세부 검증하지 않았다 — 필요해지면 별도 조사.

### 관련 문서

- [closed-network.md](./closed-network.md) — 폐쇄망 원칙
- [shadcn/ui 도입](#shadcnui-도입) — shadcn CLI 소스 복사 방식의 선례

---

## Next.js → Vite 이관

**일자:** 2026-09-14
**상태:** 결정 완료

### 배경

`frontend/`는 Next.js 14 App Router로 스캐폴딩됐지만 실제로는 단일 라우트
SPA였다 — `src/app/page.tsx`가 `<ChatWindow />` 하나를 렌더링하는 게
전부이고, 브라우저가 FastAPI를 직접 호출해 BFF도 없었다 (Next를 쓰는
이유였던 App Router 데이터 페칭·Server Action·라우팅이 애초에 전부
미사용). 실제로 쓰인 Next 기능은 번들링·dev 서버·JSX 트랜스폼뿐이었고,
그 대가로 `"use client"` 29개, App Router 파일 규약, `next-env.d.ts`
앰비언트 타입, `eslint-config-next` 같은 프레임워크 결합이 남아 있었다.

이관 전 전수조사 결과 `next/*` import는 전체 소스에서 `src/app/layout.tsx`의
`import type { Metadata } from "next"` 단 1건, 그것도 타입 전용이었다.
`next/image`·`next/link`·`next/navigation`·`next/font`·`next/dynamic`·
`next/script`·`next/headers`, Server Action, async 서버 컴포넌트,
route handler, `middleware.ts`는 전부 0건이었다.

### 결정

- **Vite 7.3.6** (`@vitejs/plugin-react@5.2.0`, `@tailwindcss/vite@4.3.3`).
  Rollup+esbuild 기반 — 폐쇄망 반입 대상 네이티브 바이너리가 esbuild 하나만
  늘어난다 (기존에도 `@next/swc-linux-x64-gnu`를 반입했던 것과 같은 급).
  Vite 8(rolldown 기반)은 `@rolldown/binding-*`·`lightningcss-*` 계열이
  추가로 필요해 반입 표면이 넓어져 제외
- **`ai@7.0.97` 제거.** `src/components/ai-elements/tool.tsx`가
  `ToolUIPart`/`DynamicToolUIPart` 타입만 쓰고 있었는데, 실제로 소비하는
  표면은 `type`(`` `tool-${string}` `` / `"dynamic-tool"`)과 7개짜리
  `state` 유니온뿐이었다. `ai` + `@ai-sdk/*` 트리가 ~12.6MB이고
  `@ai-sdk/gateway`에 `https://ai-gateway.vercel.sh`가 하드코딩돼 있어
  (기존엔 "쓰지 않는 코드 경로라 문제 없음"으로 정리했던 항목, 위
  "AI Elements" 절 참고) 타입 10여 줄로 옮기고 의존성 자체를 뺐다.
  `ToolPart`/`ToolState`/`ToolHeaderProps` 공개 타입의 이름과 형태는
  그대로 유지했다
- **dev 서버 포트 3000 고정 + 직접 호출 유지.** 백엔드
  `CORS_ALLOW_ORIGINS` 기본값이 `localhost:3000`이라, `vite.config.ts`에
  `server.port`/`preview.port`를 3000으로 고정하고 `strictPort: true`를
  줘서 다른 포트로 조용히 밀리지 않게 했다. dev proxy는 도입하지
  않았다 — 브라우저가 FastAPI를 직접 호출하는 운영 경로를 dev에서도
  그대로 검증하기 위함
- **`src/app/globals.css`·`src/app/icon.svg`는 이동하지 않았다.**
  `globals.css`의 `@config "../../tailwind.config.ts"` 상대경로와
  `components.json`의 `tailwind.css` 경로가 무수정으로 유지된다.
  `src/main.tsx`에서 `import "./app/globals.css"`로 원위치를 참조하고,
  `index.html`은 `icon.svg`를 `href="/src/app/icon.svg"`로 가리킨다.
  트레이드오프로 `src/app/` 디렉토리에 CSS·아이콘 2개만 남는다
- **`base: "./"` (상대 경로).** FastAPI가 아직 프론트를 서빙하지 않아
  (`backend/main.py`에 `StaticFiles` 마운트 없음) 마운트 지점이 미정.
  클라이언트 라우터가 없으므로 상대 경로면 `/`든 서브패스든 동작한다

### 이관하며 바뀐 것

- `src/app/layout.tsx`(App Router 레이아웃) → `index.html`(charset·
  viewport·favicon·title·description) + `src/main.tsx`
  (`<React.StrictMode>`로 `next.config.mjs`의 `reactStrictMode: true`
  대체) + `src/App.tsx`(구 `page.tsx`와 동일 내용)
- `process.env.NEXT_PUBLIC_API_BASE_URL` → `import.meta.env.VITE_API_BASE_URL`
  (`src/lib/chat-api.ts` 2줄만; `knowledge-api.ts`·`connection-banner.tsx`는
  `API_BASE_URL` 재수출을 그대로 재사용해 무수정)
- `"use client"` 29개 파일 전부 제거 (RSC 경계가 의미 없는 순수 SPA이므로)
- `tsconfig.json`: `jsx: "preserve"` → `"react-jsx"`, Next 전용
  `plugins`/`include` 항목 제거. `tsconfig.node.json`은 추가하지 않고
  단일 tsconfig로 `tsc -b`가 `vite.config.ts`까지 그대로 타입체크하게 함
- `.eslintrc.json`(`next/core-web-vitals` 한 줄) → `eslint.config.js`
  (flat config, `eslint@9` + `typescript-eslint@8` +
  `eslint-plugin-react-hooks@7`의 `rules-of-hooks`/`exhaustive-deps`만).
  **커버리지 축소**: `eslint-plugin-react`(`jsx-key` 등),
  `eslint-plugin-jsx-a11y`, `eslint-plugin-import`를 더는 쓰지 않는다.
  `@next/next/*`는 프레임워크 제거로 당연히 빠짐
- **typescript 5.5.3 → 5.9.3.** 예정에 없던 변경 — `@vitejs/plugin-react`의
  타입 선언이 `export { x as "module.exports" }`(임의 문자열 export
  이름)를 쓰는데 TS 5.5.3이 이 구문 자체를 파싱하지 못해 `tsc -b`가
  즉시 실패했다. 5.6+ 부터 지원. `typescript-eslint@8`의 `<6.1.0`
  제약 안에서 최신인 5.9.3을 선택
- `@types/node` 20.14.10 → `^20.19.0` (Vite 7의 peer 요구사항)
- `components.json`: `"rsc": true` → `false` (이후 `shadcn add`가
  `"use client"`를 다시 붙이지 않도록)
- `package.json`에 `"type": "module"` 추가 (`eslint.config.js`가 ESM)

### 폐쇄망 검증

`npm run build` 후 `grep -rE "https?://" dist/`로 확인. 매치된 것은 전부
양성이었다: `w3.org/*` 5건(SVG/XML 네임스페이스 식별자, fetch 아님),
`http://localhost:8000`(`API_BASE_URL` 폴백, 의도된 값),
`base-ui.com/production-error`·`reactjs.org/docs/error-decoder.html`
(React/`@base-ui/react`가 프로덕션 에러 메시지에 박아두는 표준 관행 —
텍스트로만 조립되고 fetch되지 않음, Next 아래서도 원래 있던 것). 화이트리스트
필터로 위 항목을 제외하면 잔여 매치 0건. `vite`/`@vitejs/plugin-react`/
`@tailwindcss/vite` 모두 postinstall/preinstall 스크립트 없음 확인.

`ai` 제거는 폐쇄망 관점에서 순이익이다 — closed-network.md "실제 발견
사례"에 있던 `@ai-sdk/gateway` 하드코딩 URL이 "안 쓰는 코드 경로라
괜찮음"에서 "트리 자체가 빠짐"으로 바뀌었다.

### 재검토 트리거

- FastAPI가 `StaticFiles`로 프론트를 서빙하게 되면 `vite.config.ts`의
  `base: "./"`와 마운트 서브패스가 맞는지 재확인
- `eslint-plugin-react`/`jsx-a11y`/`import` 커버리지 축소가 실제
  문제(접근성 회귀, 미사용 import 누락 등)로 이어지면 flat config에
  다시 추가

### 관련 문서

- [closed-network.md](./closed-network.md) — 폐쇄망 원칙, 네이티브 바이너리
  구성 변경(`@next/swc-*` → `@esbuild/*` + `@rollup/rollup-*`)

---

## assistant-ui 도입

**일자:** 2026-09-14
**상태: 결정 완료 — 상태/UI 플럼빙 계층으로 도입, `useChat`/AI SDK 데이터
스트림 프로토콜은 도입하지 않음. 2026-09-14 [ai SDK 및 채팅 UI 라이브러리
도입 검토](#ai-sdk-및-채팅-ui-라이브러리-도입-검토)의 assistant-ui 기각
결정을 뒤집었다.**

### 배경

`chat-window.tsx`가 채팅의 모든 기본기(자동 스크롤 앵커링, 취소,
재생성·편집, 메시지 루프)를 직접 구현해 유지보수하고 있었다. 그중 범용
채팅 UI 기능은 유지보수 가치가 없는데도 품질이 떨어지고 있었다 —
`el.scrollTop = el.scrollHeight`가 메시지가 바뀔 때마다 무조건 하단으로
끌어내려 스트리밍 중 위로 스크롤해 읽는 게 불가능했고, 취소는 헤더 버튼
하나뿐이었으며 재생성·편집·복사는 아예 없었다. 자체 `markdown.tsx`는
중첩 리스트 들여쓰기를 버리고 평탄화했고 링크를 원문 텍스트로 흘렸다.

목표는 이런 범용 기능을 assistant-ui 표준 구현으로 넘기고, 도메인
지식이 들어간 코드(생산계획 도구 결과 렌더링, `AgentEvent` 계약, 폐쇄망
제약)는 계속 우리가 소유하는 것이었다. `useExternalStoreRuntime`으로
메시지 상태 소유권을 프론트에 남긴다 — assistant-ui는 상태와 UI
플럼빙 계층일 뿐이다.

2026-09-14 기각 결정의 근거(번들 크기, `radix-ui` 전체 + `zustand` +
`zod@4` 유입, `@base-ui/react`와 프리미티브 이중화, `assistant-cloud`의
하드코딩 URL)를 재검증 대상으로 삼아 다시 조사했고, 아래 "폐쇄망 검증"
절에서 보듯 대부분 해소됐다는 것을 확인한 뒤 결정을 뒤집었다.

### 0단계: 기능 인벤토리

판정 기준: **기능이 동등하거나 나아질 때만 교체.**

| 현재 파일/기능 | assistant-ui 대응 | 얻는 것 | 잃는 것 | 판정 |
| --- | --- | --- | --- | --- |
| `markdown.tsx` (자체 파서) | `MarkdownTextPrimitive` + `remark-gfm` | 정식 CommonMark+GFM. 중첩 리스트·링크(기존엔 버그)·취소선·자동링크 | `· item` 비표준 불릿(`preprocess` 훅으로 정규화해 메꿈) | **교체** |
| `message-bubble.tsx` | `MessagePrimitive.Root` + `.Parts` | 파트 디스패치를 라이브러리가 담당, ActionBar·편집의 전제 | 없음 | **교체** |
| `message-input.tsx` | `ComposerPrimitive.{Root,Input,Send,Cancel}` | 자동 높이, Enter/Shift+Enter, 실행 중 비활성, 취소 버튼 | 없음 | **교체** |
| `empty-state.tsx` 질문 버튼 | `ThreadPrimitive.Suggestion` | `onPick`/`handleSend` prop 드릴링 제거, 런타임 직접 전송 | 없음 | **교체** |
| 수동 스크롤(`scrollRef`+`useEffect`) | `ThreadPrimitive.Viewport` | 하단 앵커링, 위로 스크롤 시 고정 해제, 이번 전환의 핵심 목적 | 없음(`min-h-0`/`overflow-hidden` 규칙 재적용 필요) | **교체** |
| 복사/재생성/편집(없음) | `ActionBarPrimitive`, `ComposerPrimitive`(편집 모드) | 신규 확보 | 없음(현재 부재) | **교체** |
| `tool-result-card.tsx` 분기 | `MessagePrimitive.Parts`의 `tools.Override` | 툴 파트 공식 슬롯으로 편입 | 없음 — `tool_name`/`data.kind` 2단 분기는 그대로 둠 | **부분 교체** |
| `app-sidebar.tsx` 세션 목록 | `ThreadListPrimitive` | 없음 — 백엔드 세션 API가 아직 없다 | 시간 그룹핑·도구 흔적 글리프(`TraceMarks`)는 대응물 없음 | **유지(연기)** |
| `agent-progress.tsx` | 없음(표준 content part에 대응물 없음) | — | — | **유지** — 공급 경로만 변경 |
| `primitives.tsx`(StatusDot 등) | 없음(headless) | — | — | **유지** |
| `connection-banner.tsx` / `tool-results/*` / `context-inspector.tsx` | 없음(도메인) | — | — | **유지**, 무수정 |

**교체하지 않기로 한 것과 이유:** `app-sidebar.tsx`(백엔드 세션 API
부재로 지금 붙이면 얻을 게 없음), `primitives.tsx`의 `Tag`/`ToneText`/
`Chevron`/`RuleLabel`(4단계 정리 때 git log로 확인 — 이번 마이그레이션
이전부터, Initial commit부터 미사용이던 pre-existing dead code라 범위
밖으로 판단), `isEmpty` 삼항 분기(`ThreadPrimitive.Empty`가 deprecated고
`s.thread.isEmpty`와 동일 소스라 교체 실익 없음).

### 설계 질문 답변

#### Q1. `status` 이벤트를 어디에 둘 것인가 → `metadata.custom` + `Parts` 앞 렌더

제시됐던 세 안(Thread 바깥 블록 / 커스텀 part 타입 / 선행 part)을 모두
기각했다. (a)는 메시지별 진행 이력을 잃는다. (b)/(c)는 애초에 "content
part 유니온이 닫혀 있다"는 잘못된 전제 위에 있었다 — 실제로는
`DataMessagePart`(`{type:"data", name, data}`)가 있어 가능했지만, 그래도
채택하지 않았다: 진행 블록은 답변 본문이 아니라 메시지 머리말이라
`Parts` 앞에 별도로 얹는 (d)가 맞다. `ThreadMessageLike.metadata.custom`
(실재 필드, `.d.ts` 확인)에 `{statuses, streaming, error}`를 실어 보내고
`AssistantMessage` 컴포넌트가 `useAuiState`로 읽어 `<AgentProgress/>`를
`<MessagePrimitive.Parts/>` 위에 렌더한다.

assistant-ui 0.15의 `MessagePrimitive.Parts`에는 reasoning+tool-call
파트를 하나의 접이식으로 묶는 `ChainOfThought` 그룹핑 변형이 있었지만
채택하지 않았다 — `ChainOfThoughtComponents`는 `tools?: never`라 tool
렌더링 전체를 가져가버려 도구 결과 카드 4종이 본문 흐름에서 사라진다.

**재검증 (2026-09-15):** 설치 버전이 그대로 `0.15.19`라 바뀔 이유는
없었지만, `ai-elements`(`tool.tsx`/`chain-of-thought.tsx`)와
assistant-ui가 겹치는 것 아니냐는 재질문을 받고 `node_modules`의
`.d.ts`를 다시 직접 읽어 확인했다. 결론 불변 — `tools?: never` 제약이
`MessageParts.d.ts:139`에 그대로 있다. 다만 그 사이 문서에 없던 사실을
하나 더 확인했다: `ChainOfThoughtComponents.ChainOfThought` 필드 자체도
`@deprecated`로 표시되어 있고(`MessageParts.d.ts:132-137`), JSDoc이
`<MessagePrimitive.GroupedParts>`를 `groupBy`가 `["group-thought", ...]`
를 반환하도록 써서 대체하라고 안내한다. 즉 assistant-ui 쪽 그룹핑
API 자체가 세대교체 중 — 이 프로젝트가 그 변형을 채택하지 않은 것과는
별개로, 향후 `GroupedParts` API가 안정화되면 AI Elements
`ChainOfThought` 유지 여부를 다시 재볼 트리거로 아래 "재검토 트리거"에
추가한다.

#### Q2. `MessagePart[]` → `ThreadMessageLike.content` 매핑

`parts` 배열을 인덱스 대 인덱스로 그대로 옮긴다 — 도착 순서 보존은 이
배열 구조 자체가 보장한다. `tool` 파트는
`{type:"tool-call", toolCallId, toolName, result: <ToolResult 통째로>,
isError}`로 매핑해 `ToolResultCard`의 props를 한 글자도 바꾸지 않는다.
`tool_call`만 오고 `tool_result`가 아직 안 온 중간 상태는 파트를 만들지
않는다 — `AgentEvent`에 `tool_call_id`가 없고 Claude가 한
`AssistantMessage`에 `ToolUseBlock`을 병렬로 여러 개 담을 수 있어(
`event_adapter.py` 확인) 이름 기반 짝짓기가 결과를 잘못 붙일 수 있다.
진행 중 표시는 진행 블록이 담당한다.

#### Q3. 툴 렌더러 등록 → `MessagePrimitive.Parts`의 `tools.Override`

원래 계획은 `makeAssistantToolUI`로 8개 도구 이름을 등록하는 것이었으나,
설치된 `.d.ts`를 읽어보니 **`makeAssistantToolUI`가 0.15.19에서
deprecated**였다 — JSDoc이 명시적으로 `MessagePrimitive.Parts`의 tool
override를 쓰라고 안내한다. 대신 `tools: { Override: ToolPart }` 하나로
모든 tool-call 파트를 받고, `ToolPart`가 `props.result`(우리가 실어보낸
`ToolResult`)를 그대로 `ToolResultCard`에 넘긴다. 이게 오히려
`tool-result-card.tsx`가 이미 내부에서 하던 `tool_name` 1차 분기 +
`data.kind` 2차 분기 구조와 정확히 맞아, 계획했던 8줄의 이름별 등록
코드가 아예 사라졌다.

#### Q4. 취소 → 기존 `handleStop`을 `onCancel`로 그대로 연결

`useExternalStoreRuntime`의 `onCancel`에 기존 AbortController 기반
`handleStop`을 감싼 `handleCancel`을 연결한다. `chat-api.ts`는 이미
`signal`을 받고 `AbortError`를 삼키므로 무수정. `ComposerPrimitive.Cancel`
이 `isRunning` 동안 중단 버튼을 렌더한다 — 헤더에 있던 기존 중단
버튼은 중복이라 4단계에서 제거했다(3단계에서 하기로 계획해놓고 빠뜨렸던
항목).

#### Q5. 편집/재생성 → 백엔드 세션 fork로 구현. 실제 Claude CLI로 검증 완료

대화 이력이 프론트에 없다 — `agent.py`가 `conversation_id → session_id`로
Claude Agent SDK 세션을 서버에서 resume하고, 프론트는 `{message,
conversation_id}`만 보낸다. 같은 `conversation_id`로 다시 보내면
**append**되어 모델이 같은 질문을 두 번 보게 된다.

**백엔드:**
- `session_store.py`에 `TurnAnchor{session_id, last_entry_uuid}`를
  `turn_id`(요청마다 서버가 발급하는 uuid4) 키로 저장하는 `dict` 추가.
- `event_adapter.py`가 `last_entry_uuid`를 추적 — **AssistantMessage/
  UserMessage 만** 대상이고 ResultMessage는 제외한다(아래 "실제 CLI로
  검증하며 드러난 사실" 참고).
- `agent.py` `run_agent(..., fork_from_turn_id)` — `None`이면 평범한
  다음 턴(기존 동작 무변경), 빈 문자열(`""`)이면 대화를 처음부터 다시
  시작(`resume=None`), 알려진 `turn_id`면 그 anchor의 `session_id`를
  `resume`하고 `fork_session=True` + `resume_session_at=<last_entry_uuid>`
  로 그 지점에서 새 session_id를 받는다. 알 수 없는 `turn_id`면 `error`
  이벤트 하나를 내보내고 새 대화로 폴백한다.
- `done` 이벤트에 `data.turn_id`를 실어 프론트로 돌려보낸다
  (`api/schemas.py`는 바꾸지 않음 — `data: dict[str, Any]`는 원래도
  자유 형식이었다. `backend/CLAUDE.md`가 "AgentEvent 계약을 바꾸면
  프론트와 함께 맞춘다"고 이미 명시하고 있어 이 확장은 그 규칙을 따른
  것이다).

**계획했던 `resume_drops_turn`(CLI의 추가 검증 플래그)은 쓰지 않기로
했다** — 그 검증은 "동시에 여러 메시지가 큐잉되는" 레이스를 방지하기
위한 것인데, 우리 컴포저는 스트리밍 중 전송 자체가 비활성화되고
`queue` 어댑터도 설정하지 않아 그런 레이스가 구조적으로 없다. 생략하면
포기하는 게시지가 실패한 turn의 사용자 프롬프트 uuid를
`get_session_messages()`로 되찾아와야 하는 복잡도뿐이라, 뺐다.

**실제 Claude CLI로 검증하며 드러난 사실 (문서만으로는 몰랐던 것):**
`resume_session_at`의 SDK 독스트링은 "AssistantMessage.uuid 등 아무
transcript entry나(whatever its type)" 된다고 적혀 있었지만, 실제로는
**`ResultMessage.uuid`를 넘기면 CLI가 `No message found with
message.uuid of: ...`로 거부한다** — `ResultMessage`는 uuid 필드는
있어도 실제 Transcript(JSONL)에는 적히지 않는 프로토콜 프레임이기
때문이다(`get_session_messages()`로 저장된 transcript를 직접 읽어
대조해 확인). `AssistantMessage`/`UserMessage`의 uuid만 유효하다. 처음
구현·머지된 테스트는 이 사실을 놓치고 있었고, 실제 CLI로 재현한 뒤에야
`event_adapter.py`의 추적 대상에서 `ResultMessage`를 뺐다 — 목 기반
유닛 테스트만으로는 잡을 수 없었던 문제라, 이 기능은 실제 CLI로 4개
시나리오(신규 턴/이어가는 턴/알려진 turn_id 포크/알 수 없는 turn_id
폴백/빈 문자열 재시작)를 모두 라이브로 실행해 확인했다
(`backend/tests/test_agent.py`에 목 기반 회귀 테스트로도 고정).

**프론트:**
- `types/chat.ts` — `ChatMessage.turnId?: string`(assistant 메시지의
  `done.data.turn_id`), `ChatRequestBody.fork_from_turn_id?: string`.
  두 필드 다 `AgentEvent` 자체 타입은 건드리지 않는다.
- `chat-api.ts` — `SendChatMessageOptions.forkFromTurnId`를 요청 바디에
  실어 보내는 한 줄만 추가(SSE 파싱·AbortController 로직 무수정).
- `hooks/use-agent-chat.ts` — `onReload(parentId)`는 해당 user 메시지
  텍스트를 재사용하고, `onEdit(message)`는 `message.sourceId`(편집된 user
  메시지)부터 잘라내고 새 텍스트로 다시 실행한다. 둘 다 그 user 메시지
  바로 앞 assistant 메시지의 `turnId`를 포크 지점으로 쓴다 —
  `anchorTurnIdBefore()`. 그 assistant 메시지가 없거나 `turnId`가 없으면
  (더미 시드 대화처럼 실제 백엔드 턴을 거친 적이 없는 메시지) 빈
  문자열을 보내 대화를 처음부터 새로 시작한다 — 시드 데이터는 백엔드에
  보낸 적이 없어 포크할 실제 지점이 없기 때문에 내린 판단이다.
- `thread-messages.tsx` — `ActionBarPrimitive.Reload`(어시스턴트 메시지),
  `ActionBarPrimitive.Edit` + `UserEditComposer`(사용자 메시지, `Edit`
  클릭 시 `ThreadPrimitive.Messages`의 `UserEditComposer` 슬롯으로
  교체 렌더 — `ComposerPrimitive`는 편집 컨텍스트에서도 그대로
  동작한다, 별도 EditComposer 프리미티브가 없다).
- 편집/재생성 실패(연결 끊김) 시 재시도가 포크 지점을 잃지 않도록
  `retryContextRef`에 `{text, forkFromTurnId, prefix}`를 따로 기억해뒀다가
  "다시 시도" 클릭 시 그대로 재실행한다. 평범한 턴의 실패-재시도는 이
  컨텍스트가 없다(기존 동작 그대로).

**BranchPickerPrimitive는 붙이지 않았다** — 우리 `setMessages`는 배열을
통째로 교체하는 방식이라 브랜치(메시지 트리)를 유지하지 않는다.
재생성/편집은 이전 응답을 완전히 대체하지, 나란히 두고 고르게 하지
않는다. 여러 버전을 보관하고 넘나들려면 `messageRepository`/브랜치
추적이 별도로 필요하다 — 지금은 YAGNI로 범위 밖에 둔다.

### 실행 단계 요약

1. **런타임 어댑터** — `lib/chat-runtime.ts`(`convertMessage`) +
   `useExternalStoreRuntime`. 렌더링은 그대로 `message-bubble.tsx`.
2. **Thread 프리미티브 + 마크다운** — `ThreadPrimitive.Root/Viewport/
   Messages`, `markdown-text.tsx`, `thread-messages.tsx` 신규.
3. **컴포저·액션바·빈 상태** — `ComposerPrimitive`, `ThreadPrimitive.
   Suggestion`, `ActionBarPrimitive`(복사), `ThreadPrimitive.
   ScrollToBottom`.
4. **정리** — `markdown.tsx`/`message-bubble.tsx` 삭제(참조 0건 확인
   후). `chat-window.tsx`(457줄)의 상태·이벤트 처리 로직을 `hooks/
   use-agent-chat.ts`(340줄)로 분리, 셸은 레이아웃만 남김(196줄). 죽은
   `scrollRef`/헤더 중복 중단 버튼 제거.
5. **편집/재생성** — 백엔드 세션 fork(`TurnAnchor`) + 프론트
   `onEdit`/`onReload`. 실제 Claude CLI로 라이브 검증.

각 단계 Playwright로 실제 SSE 스트림(1~4단계는 `PLANNING_AGENT_FAKE=1`,
5단계는 실제 Claude CLI) 위에서 확인 — text/tool 파트 도착 순서, status
갱신·접힘, tool_result 4종 렌더러, 자동 스크롤 앵커링(위로 스크롤 시
해제, 하단 이동 버튼), 취소, 복사, 재생성·편집(실제로 다른 응답을
받아오는지까지) 전부 실제 동작 확인. 콘솔 에러/경고 0건 유지.

### 폐쇄망 검증

`npm i -E @assistant-ui/react@0.15.19 @assistant-ui/react-markdown@0.14.15
remark-gfm@4.0.1` — caret 없이 고정. `npx assistant-ui init/create`는
실행하지 않았다(Next.js 스캐폴딩 + 레지스트리 fetch를 하므로).

- 신규 패키지 **179개**(410→589), `node_modules` +39M(271M→310M). 구성:
  `@radix-ui/*` 60, micromark* 28, mdast-util-* 15, unist-util-* 6,
  remark* 5, `@assistant-ui/*` 5, 나머지 hast/rehype 등.
- **postinstall/preinstall 스크립트 0건**(179개 전부 확인).
- `npm run build` 후 `dist/`의 외부 URL: 신규 유입 **0건**. w3.org
  네임스페이스, `reactjs.org/docs/error-decoder.html`/`base-ui.com/
  production-error`(기존 발견 사례와 동일 패턴 — 에러 메시지 텍스트,
  fetch 안 됨)에 더해 `github.com/remarkjs/react-markdown/blob/main/
  changelog.md`·`github.com/syntax-tree/hast-util-to-jsx-runtime` 2건이
  새로 보이지만 둘 다 같은 패턴(`TypeError` 메시지에 박힌 문서 링크
  텍스트, 런타임에 호출되지 않음) — 코드 내 사용 지점을 직접 확인.
- **`assistant-cloud`의 `https://backend.assistant-api.com` 하드코딩 —
  2026-09-14 기각 사유 중 가장 컸던 항목 — 트리셰이킹으로 dist에서
  완전히 제거됨을 확인**(우리는 `AssistantCloud`를 생성하지 않는다).
- `zod`/`nanoid`는 이미 설치돼 있던 패키지라 신규 유입이 아니다 — 2026-
  09-14 기각 사유였던 "zod@4·zustand·nanoid 중복 유입"도 사실상 해소.
- 남은 우려: `radix-ui` 메타 패키지가 `@radix-ui/*` 60개를 끌고 온다 —
  번들에선 셰이킹되지만(위 dist 스캔 결과) 사내 미러링 대상 패키지 수는
  실제로 늘어난다. `@base-ui/react`와의 프리미티브 이중화는 여전히
  남아 있는 트레이드오프다(shadcn 컴포넌트는 `@base-ui/react`, assistant-ui
  내부는 `radix-ui` — 서로 겹치지 않고 각자 쓰는 것이라 충돌은 없다).
- `nanoid@6.0.1`이 `engines.node: "^22 || ^24 || >=26"`을 요구해
  `npm install` 시 `EBADENGINE` 경고가 난다(현재 개발 환경 v25.5.0이라
  실제로는 문제 없이 동작). 폐쇄망 Node 버전을 고정할 때 참고할 것.

### 재검토 트리거

- `radix-ui` 메타 패키지를 서브패스 import(`radix-ui/primitives/...`
  같은 개별 패키지)로 좁혀 사내 미러링 대상을 줄일 수 있는지 —
  assistant-ui가 내부적으로 어떤 서브셋만 쓰는지 확인되면.
- `ThreadListPrimitive`(세션 목록) — 백엔드 세션 API가 생기면
  `app-sidebar.tsx` 교체를 재검토.
- 여러 재생성 결과를 나란히 두고 고르는 UX가 필요해지면
  `BranchPickerPrimitive` + `messageRepository` 도입을 별도 결정.
- `AgentEvent`에 `tool_call_id`가 추가되면(계약 변경) `tool_call`만 온
  중간 상태에서도 진행 중 툴 카드를 표시하도록 Q2 매핑을 다시 검토.
- assistant-ui를 마이너 이상 업그레이드하면 `ChainOfThoughtComponents`
  자체가 deprecated(→ `MessagePrimitive.GroupedParts` 권장, Q1 재검증
  2026-09-15 참고)인 점을 감안해 `agent-progress.tsx`의 AI Elements
  `ChainOfThought` 유지 여부를 다시 검토. `tools?: never` 제약이
  `GroupedParts`에서도 유지되는지가 관건.

### 관련 문서

- [closed-network.md](./closed-network.md) — 폐쇄망 원칙과 검증 체크리스트
- [ai SDK 및 채팅 UI 라이브러리 도입 검토](#ai-sdk-및-채팅-ui-라이브러리-도입-검토)
  — 이번에 뒤집은 기각 결정의 원문
