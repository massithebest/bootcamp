# frontend/ 작업 지침

Production Planning Agent의 Next.js 프론트엔드. 이 파일이 다루는 범위는 `frontend/` 디렉토리로 한정된다. 백엔드 런타임 에이전트 지침은 `backend/agent/agent_sdk/CLAUDE.md`이며 이 파일과 무관하다.

## 스택

- Next.js 14 (App Router) · React 18 · TypeScript
- Tailwind CSS **v4** (v3에서 마이그레이션됨, 2026-09-11 — [docs/decisions.md#shadcnui-도입](docs/decisions.md#shadcnui-도입))
- shadcn/ui 컴포넌트 (2026-09-11 도입, 그 이전엔 custom Tailwind만 사용하는 게 원칙이었음 — [docs/decisions.md#shadcnui-도입](docs/decisions.md#shadcnui-도입))
- 상태관리: React 기본(`useState`/`useRef`)만 사용, 외부 상태관리 라이브러리 없음
- **AI Elements** (2026-09-14 채택) — `src/components/ai-elements/`에 shadcn CLI로 복사된 소스(`chain-of-thought`, `tool`, `task`). **컴포넌트만 쓰고 `useChat`/`@ai-sdk/react`/`streamdown`은 도입하지 않는다.** 복사된 소스는 우리 코드로 취급해 토큰·한국어 라벨로 다듬었고, `code-block`(shiki)·radix 훅 의존은 제거했다(로컬 `hooks/use-controllable-state.ts`). 배경과 assistant-ui 비교는 [docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토](docs/decisions.md#ai-sdk-및-채팅-ui-라이브러리-도입-검토).
- Vercel AI SDK(`ai@7.0.97`)는 AI Elements `tool.tsx`가 **타입만** import한다(`ToolUIPart`). 런타임 코드 미사용. **외부 LLM provider(OpenAI/Anthropic/`@ai-sdk/gateway` 등)를 프론트에서 직접 호출하지 않는다** — 반드시 사내 백엔드(`lib/chat-api.ts`)를 경유한다.

## 최우선 원칙: 폐쇄망(closed-network)

이 앱은 최종적으로 인터넷이 차단된 환경에 배포된다. 새 의존성/라이브러리를 추가하기 전에 반드시 **[docs/closed-network.md](docs/closed-network.md)의 체크리스트**를 따른다. 요약:

- 외부 폰트 금지 (`next/font/google` 등) — 시스템 폰트만 사용
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
src/
├── app/                          layout / page / globals.css
├── components/
│   ├── ai-elements/              AI Elements 복사 소스 (chain-of-thought / tool / task) — 우리 코드로 취급, 토큰 규칙 적용
│   ├── chat/                     3-pane 워크벤치 (사이드바 / 대화 / 인스펙터)
│   │   ├── agent-progress.tsx    진행 단계 블록 (ChainOfThought 기반, 펼침 상태는 여기서 소유)
│   │   ├── app-sidebar.tsx       세션 목록 사이드바 (커스텀 구현 — shadcn sidebar 아님, 아래 참고)
│   │   ├── chat-window.tsx       전체 Chat 상태 · Streaming · AgentEvent 처리, 3-pane 셸
│   │   ├── context-inspector.tsx Skills / Metadata / Prompt 탭
│   │   ├── message-bubble.tsx    메시지 표현 (parts 배열 렌더링)
│   │   ├── message-input.tsx     입력창
│   │   ├── markdown.tsx          자체 구현 마크다운 뷰어 (외부 라이브러리 미사용)
│   │   ├── tool-result-card.tsx  Tool 결과 — AI Elements `Tool` 래퍼 안에서 tool_name 별 분기
│   │   └── tool-results/         DB/지식/시뮬레이션 결과 전용 컴포넌트
│   └── ui/                       shadcn/ui 컴포넌트 (자동 생성, 직접 로직 추가 지양)
├── lib/
│   ├── chat-api.ts                POST /api/chat · SSE 파싱 · AbortController — 백엔드 통신 유일 창구
│   ├── dummy.ts                   사이드바/인스펙터/시드 대화용 하드코딩 더미 데이터 (실제 제조 용어, lorem 금지)
│   └── utils.ts                   shadcn 표준 `cn()` 헬퍼
└── types/chat.ts                 Backend `api/schemas.py` AgentEvent 와 동일 Contract
```

## 중요한 구현 디테일

- **메시지 구조**: 어시스턴트 메시지는 `parts: MessagePart[]` (text/tool, 도착 순서)를 쓴다. 단일 `content` 문자열이 아니다 — 도구 호출 전 내레이션과 최종 답변이 하나로 뭉개지지 않게 하기 위함. `content`는 사용자 메시지 전용.
- **AgentEvent 계약**: `text` / `status` / `tool_call` / `tool_result` / `error` / `done`. `status` 이벤트의 data는 `{ step, label?, status }` 형태를 가정하며 같은 `step`은 갱신된다. 이 계약을 바꾸려면 `backend/agent/event_adapter.py`와 함께 맞춰야 한다.
- **flexbox 스크롤**: `chat-window.tsx`에서 중앙 `<section>`은 `min-h-0 overflow-hidden`, 스크롤 div는 `min-h-0`, 입력창 wrapper는 `shrink-0`이 반드시 필요하다. 하나라도 빠지면 긴 스트리밍 응답이 입력창을 화면 밖으로 밀어낸다.
- **shadcn `sidebar.tsx`는 아직 미사용**: `components/ui/sidebar.tsx`(+ `sheet.tsx`, `use-mobile.ts`)가 설치는 되어 있지만, 실제 3-pane 레이아웃은 커스텀 `app-sidebar.tsx`를 쓴다. 두 사이드바 구현을 통합/교체하기 전에 `--sidebar-*` 변수와 `SidebarProvider` 구조가 기존 커스텀 구현과 충돌하지 않는지 확인할 것 ([docs/decisions.md#열린-이슈](docs/decisions.md#열린-이슈)).

## 백엔드 연동

- 백엔드는 포트 **8000**에서 실행한다. `.env.local`의 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.
- Browser가 FastAPI를 직접 호출한다 (Next.js BFF 없음). 백엔드에 `localhost:3000` Origin CORS 허용 필요 (`backend/main.py` + `backend/core/config.py`의 `CORS_ALLOW_ORIGINS`).
- 현재 백엔드 LLM provider는 개발 단계라 OpenRouter를 임시로 쓴다. 프론트 코드는 이 사실에 의존하지 않는다 — provider 교체는 백엔드 책임이고, 프론트는 항상 `lib/chat-api.ts`를 통해서만 통신한다.

## 명령어

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
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
