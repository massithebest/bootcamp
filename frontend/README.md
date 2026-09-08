# Production Planning Agent — Frontend

Claude Agent SDK 기반 Backend 와 통신하는 질의응답형 Chat Frontend 스캐폴딩.

## 스택

- Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS 3
- 상태관리: React 기본 (`useState` / `useRef`) 만 사용
- Vercel AI SDK(`ai`, `@ai-sdk/react`): **미설치** → Browser 기본 API 로 SSE 처리
  (설치되면 `src/lib/chat-api.ts` 의 Transport 만 교체하면 됨. Component / 타입 불변)

## 실행

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

Backend 주소는 `.env.local` 의 `NEXT_PUBLIC_API_BASE_URL` (기본 `http://localhost:8000`).
Browser 가 FastAPI 를 직접 호출한다 (Next.js BFF 없음). Backend 에 `localhost:3000`
Origin 허용 CORS 설정이 필요하다.

## 구조

```
src/
├── app/                     layout / page / globals.css
├── components/chat/
│   ├── chat-window.tsx      전체 Chat 상태 · Streaming · AgentEvent 처리
│   ├── message-bubble.tsx   Message 표현 (Status → Text → Tool Result)
│   ├── message-input.tsx    textarea 입력 · Enter 전송 · 중복 전송 방지
│   ├── status-card.tsx      Agent 진행 상태 (pending/running/completed/error)
│   └── tool-result-card.tsx Tool 결과 (현재 JSON/Text, tool_name 별 확장 분기)
├── lib/chat-api.ts          POST /api/chat · SSE 파싱 · AbortController
└── types/chat.ts            Backend api/schemas.py AgentEvent 와 동일 Contract
```

## AgentEvent Contract

`text` `status` `tool_call` `tool_result` `error` `done` — Backend `api/schemas.py`
와 동일. `status` Event 는 `data: { step, label?, status }` 형태를 가정하며 같은
`step` 은 갱신된다 (`content` 만 있는 형태도 허용).

## 폐쇄망 원칙

외부 Font / CDN / 외부 Script / Telemetry 없음. FastAPI Backend 주소 외
외부 Network 호출 없음. `next/font/google` 미사용 (System Font).

## 아직 구현하지 않은 것

로그인 · Sidebar · 대화 목록 · Conversation DB 저장 · Markdown Renderer · Chart ·
Simulation/Scenario 전용 UI · Dark Mode · Mobile 최적화.
tool_name 별 전용 결과 Component(DatabaseResult 등)는 `tool-result-card.tsx` 에
분기 자리만 마련되어 있다.
