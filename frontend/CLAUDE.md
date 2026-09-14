# frontend/ 작업 지침

Production Planning Agent의 Vite + React SPA 프론트엔드 (2026-09-14 Next.js 14 App Router에서 이관 — [docs/decisions.md#nextjs--vite-이관](docs/decisions.md#nextjs--vite-이관)). 이 파일이 다루는 범위는 `frontend/` 디렉토리로 한정된다. 백엔드 런타임 에이전트 지침은 `backend/agent/agent_sdk/CLAUDE.md`이며 이 파일과 무관하다.

## 스택

- Vite 7 · React 18 · TypeScript. **App Router가 아니다** — `src/app/`이라는 디렉토리명은 Next 시절 잔재이며 (아래 "구조" 참고), 라우터 없는 단일 페이지 SPA다.
- Tailwind CSS **v4** (`@tailwindcss/vite` 플러그인 경유, v3에서 마이그레이션됨, 2026-09-11 — [docs/decisions.md#shadcnui-도입](docs/decisions.md#shadcnui-도입))
- shadcn/ui 컴포넌트 (2026-09-11 도입, 그 이전엔 custom Tailwind만 사용하는 게 원칙이었음 — [docs/decisions.md#shadcnui-도입](docs/decisions.md#shadcnui-도입))
- 상태관리: React 기본(`useState`/`useRef`)만 사용, 외부 상태관리 라이브러리 없음
- **AI Elements** (2026-09-14 채택) — `src/components/ai-elements/`에 shadcn CLI로 복사된 소스(`chain-of-thought`, `tool`, `task`). **컴포넌트만 쓰고 `useChat`/`@ai-sdk/react`/`streamdown`은 도입하지 않는다.** 복사된 소스는 우리 코드로 취급해 토큰·한국어 라벨로 다듬었고, `code-block`(shiki)·radix 훅 의존은 제거했다(로컬 `hooks/use-controllable-state.ts`). 배경과 assistant-ui 비교는 [docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토](docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토).
- **Vercel AI SDK(`ai`)는 도입하지 않는다.** AI Elements `tool.tsx`가 예전엔 `ToolUIPart`/`DynamicToolUIPart` 타입만 import했지만, Vite 이관(2026-09-14) 때 실제로 쓰는 표면(`type`/`state`)만 로컬 타입으로 옮기고 `ai` 의존성 자체를 제거했다 (`ai` + `@ai-sdk/*` 트리 ~12.6MB, `@ai-sdk/gateway`에 외부 URL 하드코딩 — 폐쇄망 반입 대상에서 뺐다). **외부 LLM provider(OpenAI/Anthropic 등)를 프론트에서 직접 호출하지 않는다** — 반드시 사내 백엔드(`lib/chat-api.ts`)를 경유한다.
- **assistant-ui**(`@assistant-ui/react` + `@assistant-ui/react-markdown`, 2026-09-14 도입)는 **상태·UI 플럼빙 계층으로만** 쓴다. `useExternalStoreRuntime`으로 메시지 상태 소유권은 계속 우리(`hooks/use-agent-chat.ts`)가 갖는다. **`@ai-sdk/react`/`useChat`/AI SDK 데이터 스트림 프로토콜은 도입하지 않는다** — 백엔드가 그 포맷을 쓰지 않는다. 범용 채팅 UI 기능(스크롤 앵커링·컴포저·액션바·마크다운)은 assistant-ui 프리미티브에 위임하고, 도메인 렌더링(`tool-results/*`, `AgentEvent` 처리)은 계속 자체 구현한다. 새 assistant-ui API를 쓰기 전에 `node_modules/@assistant-ui/*/dist/**/*.d.ts`를 직접 읽을 것 — 문서·기억에 의존하지 말 것(실제로 독스트링과 다르게 동작하는 API가 있었다, `resume_session_at` 사례는 [docs/decisions.md#assistant-ui-도입](docs/decisions.md#assistant-ui-도입) Q5 참고). 배경·설계 결정 전체는 [docs/decisions.md#assistant-ui-도입](docs/decisions.md#assistant-ui-도입).

## 최우선 원칙: 폐쇄망(closed-network)

이 앱은 최종적으로 인터넷이 차단된 환경에 배포된다. 새 의존성/라이브러리를 추가하기 전에 반드시 **[docs/closed-network.md](docs/closed-network.md)의 체크리스트**를 따른다. 요약:

- 외부 폰트 금지 — 시스템 폰트만 사용
- 외부 CDN/스크립트 금지 — 전부 npm 의존성으로 번들
- 새 패키지의 런타임 코드에 하드코딩된 외부 URL이 없는지 확인 (`grep -rEo 'https?://...' node_modules/<pkg>/dist`)
- 의심되면 오프라인 조건으로 `npm run build`를 재현해서 검증
- shadcn/ui처럼 CLI가 자체 레지스트리에서 소스를 받아오는 도구는, 인터넷 환경에서 미리 `add`해서 커밋해두고 폐쇄망에는 CLI 실행 자체가 필요 없게 한다

과거 실제로 이 원칙 위반이 자동으로 발생한 적 있음 (shadcn init이 `next/font/google` Geist를 자동 추가 → 빌드 실패로 발견 후 제거). 새 CLI 도구를 처음 실행할 때는 diff를 반드시 확인할 것.

## 디자인 토큰 / 스타일 규칙

- 색상은 `src/app/globals.css`의 CSS 변수로 정의하고 `tailwind.config.ts`에서 semantic 이름으로 매핑한다. **컴포넌트에 색을 하드코딩하지 않는다.**
- 표면 3단계(`--canvas` > `--surface` > `--surface-2`), 텍스트 3단계(`--ink`/`--ink-2`/`--ink-3`), 액센트는 파란색 1개(`--accent`, 활성 세션/포커스/주요 액션 한정), 상태는 저채도 3색(`--ok-*`/`--warn-*`/`--block-*`)만 쓴다. 새 색을 함부로 추가하지 않는다.
- 산문은 sans, 데이터/SQL/코드/숫자는 mono로 명확히 구분한다.
- **shadcn 컴포넌트는 자체 팔레트를 쓰지 않는다.** 모든 shadcn CSS 변수는 `--shadcn-*`로 네임스페이스가 분리되어 있고 위 프로젝트 토큰에 재매핑되어 있다 (`globals.css`의 `@theme inline` 블록 참고). 새 shadcn 컴포넌트를 추가했을 때 새 `--shadcn-*` 변수가 생기면, 반드시 기존 토큰에 매핑할 것 — shadcn 기본값(oklch 팔레트)을 그대로 두지 않는다.
- 라이트 테마만 지원한다. `.dark` 관련 코드를 추가하지 않는다.

자세한 배경은 [docs/decisions.md](docs/decisions.md) 참고.

## 구조

```
index.html                        Vite 엔트리 HTML — title/description/favicon
src/
├── main.tsx                      ReactDOM 엔트리 (globals.css import, <React.StrictMode>)
├── App.tsx                       루트 컴포넌트 (<ChatWindow /> 렌더링, 구 page.tsx)
├── vite-env.d.ts                 ImportMetaEnv 타입 선언
├── app/                          globals.css / icon.svg (Next 시절 경로를 파일 이동 없이 유지 —
│                                  globals.css의 @config 상대경로, components.json의 css 경로 보존 목적)
├── components/
│   ├── ai-elements/              AI Elements 복사 소스 (chain-of-thought / tool / task) — 우리 코드로 취급, 토큰 규칙 적용
│   ├── chat/                     3-pane 워크벤치 (사이드바 / 대화 / 인스펙터)
│   │   ├── agent-progress.tsx    진행 단계 블록 (ChainOfThought 기반, 펼침 상태는 여기서 소유)
│   │   ├── app-sidebar.tsx       세션 목록 사이드바 (커스텀 구현 — shadcn sidebar 아님, 아래 참고)
│   │   ├── chat-window.tsx       3-pane 셸 조립 · 패널 토글 · 세션 선택 (상태는 hooks/use-agent-chat.ts 로 이전)
│   │   ├── context-inspector.tsx Skills(실 API) / Metadata / Prompt 탭
│   │   ├── empty-state.tsx       대화 시작 전 예시 질문 (ThreadPrimitive.Suggestion)
│   │   ├── markdown-text.tsx     `@assistant-ui/react-markdown` 기반 마크다운 렌더러 (remark-gfm)
│   │   ├── thread-messages.tsx   ThreadPrimitive.Messages 에 등록하는 User/AssistantMessage · UserEditComposer · ActionBar(복사/재생성/편집)
│   │   ├── message-input.tsx     입력창 (ComposerPrimitive — 전송/Enter/자동높이/취소 라이브러리 위임)
│   │   ├── tool-result-card.tsx  Tool 결과 — AI Elements `Tool` 래퍼 안에서 tool_name 별 분기
│   │   └── tool-results/         DB/지식(RAG)/카탈로그/시뮬레이션 결과 전용 컴포넌트
│   └── ui/                       shadcn/ui 컴포넌트 (자동 생성, 직접 로직 추가 지양)
├── hooks/
│   ├── use-agent-chat.ts         대화 상태 · SSE Streaming · AgentEvent 처리 · assistant-ui 런타임(useExternalStoreRuntime) 생성 · 편집/재생성 포크
│   ├── use-controllable-state.ts AI Elements chain-of-thought 훅 의존 로컬 구현
│   └── use-mobile.ts             shadcn sidebar 반응형 훅 (미사용 sidebar.tsx 부속)
├── lib/
│   ├── chat-api.ts                POST /api/chat · SSE 파싱 · AbortController — 백엔드 통신 유일 창구
│   ├── chat-runtime.ts            `ChatMessage` -> assistant-ui `ThreadMessageLike` 변환 (convertMessage)
│   ├── knowledge-api.ts           GET /api/knowledge/* (Skills 목록 등) 읽기 전용 조회
│   ├── dummy.ts                   사이드바/인스펙터/시드 대화용 하드코딩 더미 데이터 (실제 제조 용어, lorem 금지)
│   └── utils.ts                   shadcn 표준 `cn()` 헬퍼
└── types/chat.ts                 Backend `api/schemas.py` AgentEvent 와 동일 Contract
```

`@/*` alias는 `vite.config.ts`의 `resolve.alias`와 `tsconfig.json`의 `paths` 양쪽에 유지한다 — 하나만 바꾸면 빌드는 되는데 에디터 타입 탐색이 깨지거나 그 반대가 된다.

## 중요한 구현 디테일

- **메시지 구조**: 어시스턴트 메시지는 `parts: MessagePart[]` (text/tool, 도착 순서)를 쓴다. 단일 `content` 문자열이 아니다 — 도구 호출 전 내레이션과 최종 답변이 하나로 뭉개지지 않게 하기 위함. `content`는 사용자 메시지 전용.
- **tool_result `kind`**: `database`(표) / `knowledge`(RAG 인용) / `catalog`(카탈로그·KPI, **기본 접힘**) / `simulation`. `catalog` 는 분석 한 번에 4~6회 오므로 헤더 한 줄로만 보여준다. `execute_sql` 결과는 컬럼·행이 `data.table.{columns,rows}` 아래에 온다.
- **AgentEvent 계약**: `text` / `status` / `tool_call` / `tool_result` / `error` / `done`. `status` 이벤트의 data는 `{ step, label?, status }` 형태를 가정하며 같은 `step`은 갱신된다. `done` 이벤트의 data는 `{ turn_id }`를 싣는다 — 편집/재생성이 이 값을 `ChatRequestBody.fork_from_turn_id`로 되돌려 보내 백엔드 세션을 그 지점에서 포크한다(`hooks/use-agent-chat.ts`의 `anchorTurnIdBefore`). 이 계약을 바꾸려면 `backend/agent/event_adapter.py`·`backend/agent/agent.py`와 함께 맞춰야 한다.
- **flexbox 스크롤**: `ThreadPrimitive.Viewport`가 스크롤을 담당한다 — 여전히 중앙 `<section>`은 `min-h-0 overflow-hidden`, `ThreadPrimitive.Root`/`Viewport`는 `min-h-0`, 입력창 wrapper는 `shrink-0`이 필요하다(assistant-ui 도입 이후에도 이 flexbox 규칙 자체는 안 바뀜). 하나라도 빠지면 긴 스트리밍 응답이 입력창을 화면 밖으로 밀어낸다.
- **shadcn `sidebar.tsx`는 아직 미사용**: `components/ui/sidebar.tsx`(+ `sheet.tsx`, `use-mobile.ts`)가 설치는 되어 있지만, 실제 3-pane 레이아웃은 커스텀 `app-sidebar.tsx`를 쓴다. 두 사이드바 구현을 통합/교체하기 전에 `--sidebar-*` 변수와 `SidebarProvider` 구조가 기존 커스텀 구현과 충돌하지 않는지 확인할 것 ([docs/decisions.md#열린-이슈](docs/decisions.md#열린-이슈)).

## 백엔드 연동

- 백엔드는 포트 **8000**에서 실행한다. `.env.local`의 `VITE_API_BASE_URL=http://localhost:8000`.
- Browser가 FastAPI를 직접 호출한다 (BFF 없음). 백엔드에 `localhost:3000` Origin CORS 허용 필요 (`backend/main.py` + `backend/core/config.py`의 `CORS_ALLOW_ORIGINS`). `vite.config.ts`가 dev/preview 포트를 3000으로 고정(`strictPort: true`)해 이 CORS 설정과 어긋나면 조용히 넘어가지 않고 서버가 즉시 실패하게 한다 — 다른 프로세스가 3000을 점유 중이면 그 프로세스를 먼저 정리할 것.
- 현재 백엔드 LLM provider는 개발 단계라 OpenRouter를 임시로 쓴다. 프론트 코드는 이 사실에 의존하지 않는다 — provider 교체는 백엔드 책임이고, 프론트는 항상 `lib/chat-api.ts`를 통해서만 통신한다.

## 명령어

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # tsc -b && vite build
npm run lint     # eslint .
npm run preview  # 빌드 산출물(dist/)을 :3000에서 서빙 (start와 동일)
```

## 문서

결정 사항의 전체 배경과 근거는 [docs/decisions.md](docs/decisions.md) 하나에
절 단위로 모여 있다 (워크벤치 리디자인, shadcn 도입·Tailwind v4 마이그레이션,
ai SDK/채팅 UI 라이브러리 검토):

- [docs/decisions.md](docs/decisions.md) — 결정 사항 기록 (전체)
- [docs/closed-network.md](docs/closed-network.md) — 폐쇄망 원칙과 의존성 검증 체크리스트
- [plan/](plan/) — 실행 계획 문서 모음 ([plan/CLAUDE.md](plan/CLAUDE.md) 참고)
  - [plan/domain-knowledge-plan.md](plan/domain-knowledge-plan.md) — 도메인 지식 연동 계획. 백엔드 Phase 1([backend/plan/domain-knowledge-plan.md](../backend/plan/domain-knowledge-plan.md)) 완료 후 착수

새로운 아키텍처/의존성 결정을 내리면 이 `docs/` 아래 문서를 갱신하고, 이 CLAUDE.md에서 필요한 부분만 요약해서 반영한다.
