# Production Planning Agent — Frontend

Claude Agent SDK 기반 Backend와 통신하는 질의응답형 3-pane 에이전트 워크벤치 (사이드바 / 대화 / 컨텍스트 인스펙터).

## 스택

- Next.js 14 (App Router) · React 18 · TypeScript
- Tailwind CSS **v4** + shadcn/ui 컴포넌트
- 상태관리: React 기본(`useState`/`useRef`)만 사용
- Vercel AI SDK(`ai@7.0.97`) 설치됨. 프론트는 외부 LLM provider를 직접 호출하지 않고 항상 사내 백엔드(`src/lib/chat-api.ts`)를 경유한다.

## 실행

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

Backend 주소는 `.env.local`의 `NEXT_PUBLIC_API_BASE_URL` (기본 `http://localhost:8000`).
Browser가 FastAPI를 직접 호출한다 (Next.js BFF 없음). Backend에 `localhost:3000`
Origin 허용 CORS 설정이 필요하다.

## 구조

```
src/
├── app/                          layout / page / globals.css
├── components/
│   ├── chat/                     3-pane 워크벤치
│   │   ├── app-sidebar.tsx       세션 목록 사이드바 (커스텀 구현)
│   │   ├── chat-window.tsx       전체 Chat 상태 · Streaming · AgentEvent 처리, 3-pane 셸
│   │   ├── context-inspector.tsx Skills / Metadata / Prompt 탭
│   │   ├── message-bubble.tsx    메시지 표현 (parts 배열 렌더링)
│   │   ├── message-input.tsx     입력창
│   │   ├── markdown.tsx          자체 구현 마크다운 뷰어 (외부 라이브러리 미사용)
│   │   ├── tool-result-card.tsx  Tool 결과 (tool_name 별 확장 분기)
│   │   └── tool-results/         DB/지식/시뮬레이션 결과 전용 컴포넌트
│   └── ui/                       shadcn/ui 컴포넌트
├── lib/
│   ├── chat-api.ts               POST /api/chat · SSE 파싱 · AbortController
│   └── dummy.ts                  사이드바/인스펙터/시드 대화용 더미 데이터
└── types/chat.ts                 Backend api/schemas.py AgentEvent 와 동일 Contract
```

## AgentEvent Contract

`text` `status` `tool_call` `tool_result` `error` `done` — Backend `api/schemas.py`
와 동일. `status` Event는 `data: { step, label?, status }` 형태를 가정하며 같은
`step`은 갱신된다.

어시스턴트 메시지는 단일 `content` 문자열이 아니라 `parts: MessagePart[]` (text/tool, 도착 순서)로 표현한다 — 도구 호출 전 내레이션과 최종 답변이 하나로 뭉개지지 않게 하기 위함.

## 폐쇄망 원칙

외부 Font / CDN / 외부 Script / Telemetry 없음. FastAPI Backend 주소 외 외부 Network 호출 없음. `next/font/google` 미사용 (System Font만 사용). 새 의존성 도입 시 검증 절차는 [docs/closed-network.md](docs/closed-network.md) 참고.

## 문서

아키텍처 결정과 그 배경은 [docs/decisions.md](docs/decisions.md)에서 시작한다. Claude Code로 이 디렉토리에서 작업할 때 지켜야 할 규칙은 [CLAUDE.md](CLAUDE.md) 참고.
