# Production Planning Agent — Frontend

Claude Agent SDK 기반 Backend와 통신하는 질의응답형 3-pane 에이전트 워크벤치 (사이드바 / 대화 / 컨텍스트 인스펙터).

## 스택

- Next.js 14 (App Router) · React 18 · TypeScript
- Tailwind CSS **v4** + shadcn/ui 컴포넌트 (2026-09-11 도입)
- **AI Elements** (2026-09-14 채택) — `src/components/ai-elements/`에 소스로 복사해 우리 코드로 관리한다(`chain-of-thought` / `tool` / `task`). 컴포넌트만 쓰고 `useChat`·`@ai-sdk/react`·`streamdown`은 도입하지 않는다.
- 아이콘은 `lucide-react` (npm 번들, 외부 CDN 아님)
- 상태관리: React 기본(`useState`/`useRef`)만 사용
- Vercel AI SDK(`ai@7.0.97`)는 AI Elements `tool.tsx`가 **타입만**(`ToolUIPart`) import한다. 런타임 코드 미사용이며, 프론트는 외부 LLM provider를 직접 호출하지 않고 항상 사내 백엔드(`src/lib/chat-api.ts`)를 경유한다.

## 실행

```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL 확인
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

Backend 주소는 `.env.local`의 `NEXT_PUBLIC_API_BASE_URL` (기본 `http://localhost:8000`).
Browser가 FastAPI를 직접 호출한다 (Next.js BFF 없음). Backend에 `localhost:3000`
Origin 허용 CORS 설정이 필요하다. 연결에 실패하면 대화 내용을 유지한 채
`connection-banner.tsx`가 요청 주소와 확인할 항목을 안내한다.

## 구조

```
src/
├── app/                          layout / page / globals.css / icon.svg
├── components/
│   ├── ai-elements/              AI Elements 복사 소스 (chain-of-thought / tool / task) — 우리 코드로 취급
│   ├── chat/                     3-pane 워크벤치
│   │   ├── agent-progress.tsx    진행 단계 블록 (ChainOfThought 기반, 진행 중 펼침 · 완료 후 접힘)
│   │   ├── app-sidebar.tsx       세션 목록 사이드바 (커스텀 구현 — shadcn sidebar 아님)
│   │   ├── chat-window.tsx       전체 Chat 상태 · Streaming · AgentEvent 처리, 3-pane 셸
│   │   ├── connection-banner.tsx 백엔드 연결 실패 안내 · 재시도
│   │   ├── context-inspector.tsx Skills(실 API) / Metadata / Prompt 탭
│   │   ├── empty-state.tsx       대화 시작 전 예시 질문
│   │   ├── markdown.tsx          자체 구현 마크다운 뷰어 (외부 라이브러리 미사용)
│   │   ├── message-bubble.tsx    메시지 표현 (parts 배열 렌더링)
│   │   ├── message-input.tsx     입력창
│   │   ├── primitives.tsx        공용 UI 조각 (StatusDot 등, 직접 작성)
│   │   ├── tool-result-card.tsx  AI Elements `Tool` 래퍼 안에서 tool_name 별 분기
│   │   └── tool-results/         database / knowledge / catalog / simulation 전용 렌더러
│   └── ui/                       shadcn/ui 컴포넌트 (자동 생성)
├── hooks/                        use-controllable-state / use-mobile
├── lib/
│   ├── chat-api.ts               POST /api/chat · SSE 파싱 · AbortController — 백엔드 통신 유일 창구
│   ├── knowledge-api.ts          GET /api/knowledge/* 읽기 전용 조회
│   ├── dummy.ts                  사이드바/인스펙터/시드 대화용 더미 데이터
│   └── utils.ts                  shadcn 표준 `cn()` 헬퍼
└── types/
    ├── chat.ts                   Backend `api/schemas.py` AgentEvent 와 동일 Contract
    └── workspace.ts              프론트 전용 UI 타입 (Session / Skill / SessionMetadata …)
```

## 데이터 소스

실제 백엔드에 붙은 것과 아직 더미인 것이 섞여 있다.

| 영역 | 소스 |
| --- | --- |
| 대화 · 진행 상태 · 도구 결과 | 실 API (`POST /api/chat`, SSE) |
| 인스펙터 Skills 탭 | 실 API (`GET /api/knowledge/skills`) |
| 세션 목록 · 사용자 · Metadata · Prompt · 시드 대화 · 예시 질문 | `lib/dummy.ts` 하드코딩 |

## AgentEvent Contract

`text` `status` `tool_call` `tool_result` `error` `done` — Backend `api/schemas.py`
와 동일하다. 바꿀 때는 `backend/agent/event_adapter.py`와 함께 맞춰야 한다.

- `status` Event는 `data: { step, label?, status }` 형태를 가정하며 같은 `step`은 갱신된다.
- `tool_result`는 `data.kind`로 렌더러가 갈린다 — `database`(표) / `knowledge`(RAG 인용) / `catalog`(카탈로그·KPI, **기본 접힘**) / `simulation`. `execute_sql` 결과의 컬럼·행은 `data.table.{columns,rows}` 아래에 온다.
- 어시스턴트 메시지는 단일 `content` 문자열이 아니라 `parts: MessagePart[]` (text/tool, 도착 순서)로 표현한다 — 도구 호출 전 내레이션과 최종 답변이 하나로 뭉개지지 않게 하기 위함.

## 폐쇄망 원칙

외부 Font / CDN / 외부 Script / Telemetry 없음. FastAPI Backend 주소 외 외부 Network 호출 없음. `next/font/google` 미사용 (System Font만 사용). shadcn·AI Elements처럼 CLI가 레지스트리에서 소스를 받아오는 도구는 인터넷 환경에서 미리 받아 커밋해 둔다. 새 의존성 도입 시 검증 절차는 [docs/closed-network.md](docs/closed-network.md) 참고.

## 문서

- [docs/decisions.md](docs/decisions.md) — 아키텍처 결정과 그 배경 (워크벤치 리디자인 · shadcn 도입/Tailwind v4 · AI Elements 채택)
- [docs/closed-network.md](docs/closed-network.md) — 폐쇄망 원칙과 의존성 검증 체크리스트
- [plan/](plan/) — 실행 계획 문서
- [CLAUDE.md](CLAUDE.md) — Claude Code로 이 디렉토리에서 작업할 때의 규칙
