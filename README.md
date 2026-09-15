# P&T FP Agent

제조 생산계획 데이터를 자연어로 조회·분석·시뮬레이션하는 폐쇄망용 Agent 도구다.

```text
Frontend(Vite + React)
  → POST /api/chat (SSE)
  → Backend(FastAPI + Claude Agent SDK)
  → Knowledge / SQL / Simulation / Result Store / Visualization
```

## 실행

Backend:

```bash
cd backend
conda env create -f environment.yml
conda activate production-planning
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.build_smt2020_db
PLANNING_AGENT_FAKE=1 uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

비밀값은 `backend/.env`와 `frontend/.env.local`에만 두며 커밋하지 않는다.

## 문서

- [프로젝트 현황](plan/Todo.md)
- [전체 요구사항과 기능별 계획](plan/)
- [Backend 실행·운영](backend/README.md)
- [Frontend 실행·운영](frontend/README.md)
- [Agent 작업 지침](AGENTS.md)
