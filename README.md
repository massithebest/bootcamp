# Production Planning Agent

제조 생산계획 데이터를 자연어로 조회·분석·시뮬레이션하는 폐쇄망용
Agent 애플리케이션이다. 현재 개발·검증 기준 데이터는 SMT2020 HVLM/LVHM이며,
운영 데이터 쓰기 없이 조회 전용 SQL과 입력 정합성 simulation을 제공한다.

## 주요 기능

- Claude Agent SDK 기반 대화와 공개 업무 단계·Tool 실행 SSE 스트리밍
- table·KPI·recipe·scenario YAML과 버전형 텍스트 지식 조회·관리
- 카탈로그의 조회·집계 규칙을 적용한 읽기 전용 SQL
- 최대 1,000행 Result Store, 결과 요약·구간 조회
- 검색·정렬·페이지 이동이 가능한 최대 100행 독립 표
- 실제 결과 컬럼과 grain을 검증한 bar·line 차트
- 질문 편집·재생성·중단과 3-pane Agent Workbench

```text
Frontend (Vite 7 + React 18 + assistant-ui)
  └─ POST /api/chat (SSE AgentEvent)
Backend (FastAPI + Claude Agent SDK)
  ├─ Knowledge tools ─ YAML catalog / SQLite text knowledge
  ├─ SQL / Simulation ─ mock 또는 real service
  └─ Result Store ─ Table / Visualization
```

## 저장소 구조

- `backend/`: FastAPI, Agent SDK adapter, Tool, 지식·결과 service와 테스트
- `frontend/`: Vite SPA, assistant-ui 기반 채팅·지식 관리 UI와 테스트
- `backend/plan`: Backend 현재 계약·다음 작업·완료 이력
- `frontend/plan`: Frontend 기대 API·다음 작업·완료 이력

## 빠른 실행

### Backend

Python 3.11의 표준 `venv` 환경을 기준으로 한다.

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

SMT2020 원본, 생성 DB와 `scripts/build_smt2020_db.py`는 폐쇄망 반입용 로컬
자산으로 Git에 포함되지 않는다. 해당 자산을 전달받은 환경에서만 다음 명령으로
DB를 생성한다.

```bash
python -m scripts.build_smt2020_db
```

Claude/provider 없이 UI와 이벤트 흐름을 확인하려면 Fake Runner로 실행한다.

```bash
SERVICE_MODE=mock PLANNING_AGENT_FAKE=1 uvicorn main:app --reload --port 8100
```

실제 Agent SDK 실행은 [Backend 안내](backend/README.md)와
[폐쇄망 배포 가이드](backend/docs/CLOSED_NETWORK_SETUP.md)를 따른다.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

기본 주소는 Backend `http://localhost:8100`, Frontend
`http://localhost:3100`이다. 비밀값은 `backend/.env`와
`frontend/.env.local`에만 두며 커밋하지 않는다.

## 검증

```bash
cd backend
python -m pytest -q

cd ../frontend
npm test
npm run build
npm run lint
```

브라우저 자동화 산출물인 `.playwright-mcp/`와 `artifacts/`는 Git에서 제외한다.

## 문서

- [Backend 계획과 이력](backend/plan/Todo.md)
- [Frontend 계획과 이력](frontend/plan/Todo.md)
- [Backend 실행·운영](backend/README.md)
- [Frontend 실행·검증](frontend/README.md)
- [도메인 지식 관리](backend/docs/domain-knowledge-management.md)
- [개발 Agent 작업 지침](AGENTS.md)

현재 실제 사내 DB·RAG·simulation 연결, 대화 영속 저장과 동적 후속질문은 후속
범위다. 세부 상태는 각 workspace의 `plan/Todo.md`를 기준으로 한다.
