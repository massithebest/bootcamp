# P&T FP agent

제조 생산계획을 자연어로 질의·시뮬레이션하는 사내 에이전트 도구.

```
production-planning-agent/
├── backend/    FastAPI + Claude Agent SDK. /api/chat 에서 AgentEvent 를 SSE 로 스트리밍
└── frontend/   Next.js(App Router) 워크스페이스 UI. 커스텀 Tailwind, 폐쇄망 대응
```

## 실행

**Backend** (`backend/README.md` 참고)
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # 값 채우기
uvicorn main:app --reload --port 8010
```

**Frontend** (`frontend/README.md` 참고)
```bash
cd frontend
npm install
cp .env.example .env.local  # NEXT_PUBLIC_API_BASE_URL 을 backend 주소로
npm run dev                 # http://localhost:3000
```

## 아키텍처

```
Frontend → POST /api/chat → FastAPI → Claude Agent SDK
                              ↓
                          AgentEvent (text / status / tool_call / tool_result / error / done)
                              ↓ SSE
                          Frontend (진행 상태 · 답변 · 도구 결과 렌더)
```

비밀값은 `backend/.env`, `frontend/.env.local` 에만 두며 커밋하지 않는다.
