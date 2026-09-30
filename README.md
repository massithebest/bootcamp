# Production Planning Agent

제조 생산계획 데이터를 자연어로 조회·분석·시뮬레이션하는 폐쇄망용
Agent 애플리케이션이다. 개발용 mock 회귀에는 결정적으로 생성되는 합성
데이터(SEG_A/SEG_B 두 생산 세그먼트)를 사용하며, 폐쇄망 운영은 별도 지식과
production service만 사용한다.

## 주요 기능

- Claude Agent SDK 기반 대화와 공개 업무 단계·Tool 실행 SSE 스트리밍
- table·KPI·recipe·scenario YAML과 버전형 텍스트 지식 조회·관리
- 카탈로그의 조회·집계 규칙을 적용한 읽기 전용 SQL
- 최대 1,000행 Result Store, 결과 요약·구간 조회
- `present_*` Tool의 서버 페이지 표, bar·line·area 차트와 시뮬레이션 요약
- 질문 편집·재생성·중단과 3-pane Agent Workbench

```text
Frontend (Vite 7 + React 18 + assistant-ui)
  └─ POST /api/chat (SSE AgentEvent)
Backend (FastAPI + Claude Agent SDK)
  ├─ Knowledge tools ─ YAML catalog / SQLite text knowledge
  ├─ SQL / Simulation ─ mock 또는 production service
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
python -m pip install -r requirements.txt
```

`scripts/generate_mock_database.py`는 외부 원본 없이 합성 mock SQLite DB를
결정적으로 생성하는 Git 포함 스크립트다. 아무 환경에서나 실행할 수 있다.

```bash
python -m scripts.generate_mock_database
python -m scripts.generate_mock_documents
```

```bash
SERVICE_MODE=mock uvicorn main:app --reload --port 8100
```

`/api/chat`은 항상 실제 Claude Agent SDK 경로를 사용한다. 채팅을 확인하려면
`.env`에 `LLM_PROVIDER`와 인증값을 설정한다. 지식·시각화 API와 `pytest`는
provider 없이 동작한다. 자세한 실행 방법은 [Backend 안내](backend/README.md)와
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

Backend 테스트는 합성 mock DB 생성기를 항상 사용할 수 있어 별도 자산 없이
전체가 실행된다. 폐쇄망의 production 전용 검증 절차는
[폐쇄망 배포 가이드](backend/docs/CLOSED_NETWORK_SETUP.md)를 따른다.

브라우저 자동화 산출물인 `.playwright-mcp/`와 `artifacts/`는 Git에서 제외한다.

## 문서

- Backend: [할 일·아이디어](backend/plan/Todo.md) · [진행 중·현재 계약](backend/plan/InProgress.md) · [완료 이력](backend/plan/History.md)
- Frontend: [할 일·아이디어](frontend/plan/Todo.md) · [진행 중·현재 계약](frontend/plan/InProgress.md) · [완료 이력](frontend/plan/History.md)
- [Backend 실행·운영](backend/README.md)
- [Frontend 실행·검증](frontend/README.md)
- [Frontend UI 디자인 기준](frontend/docs/assistant-ui-design.md)
- [도메인 지식 관리](backend/docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md)
- [개발 Agent 작업 지침](AGENTS.md)

현재 실제 사내 DB·RAG·simulation 연결, 대화 영속 저장과 동적 후속질문은 후속
범위다. 세부 상태와 현재 계약은 각 workspace의 `plan/InProgress.md`를 기준으로 한다.
