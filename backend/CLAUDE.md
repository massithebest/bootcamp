# backend/ 작업 지침

Production Planning Agent의 FastAPI 백엔드. 이 파일이 다루는 범위는 `backend/`
디렉토리로 한정된다. Claude Agent 런타임(SDK)에 로드되는 에이전트 행동 지침은
`backend/agent/agent_sdk/CLAUDE.md`이며 이 파일과는 목적이 다르다 — 이 파일은
"이 백엔드 코드베이스를 개발할 때" 지침이고, 그쪽은 "에이전트가 실행 중 어떻게
행동할지"에 대한 지침이다.

## 아키텍처

```text
Frontend → FastAPI(/api/chat, SSE) → Agent Runner → Claude Agent SDK
        → Tools(in-process MCP) → Services(mock | real)
```

| 계층 | 파일 | 책임 |
| --- | --- | --- |
| API | `api/routes_chat.py` | AgentEvent → SSE 직렬화만 |
| Agent Runner | `agent/agent.py` | SDK 실행, 이벤트 수신 |
| Event Adapter | `agent/event_adapter.py` | SDK 이벤트 → `AgentEvent` 변환 (SDK 종속 코드 집중) |
| SDK Tools | `agent/sdk_tools.py` | `tools/` 함수를 `@tool`로 감싼 in-process MCP Server |
| Tools | `tools/*.py` | 입력 검증 + Service 호출 |
| Knowledge | `knowledge/*.yaml` + `services/knowledge_service.py` | 카탈로그·KPI·시뮬레이션 정의 (YAML이 source of truth) |
| Services | `services/{mock,real}/*` | 실제 I/O (DB / Milvus / Simulation MCP) |

- `conversation_id`(사용자 대화)와 SDK `session_id`는 `agent/session_store.py`에서 매핑한다.
- **편집/재생성 포크** (2026-09-14, 프론트 assistant-ui 도입에 맞춰 추가): 매 턴마다 `turn_id`(uuid4)를 발급해 `AgentEvent(type="done").data.turn_id`로 프론트에 돌려주고, `session_store.py`가 `turn_id -> TurnAnchor{session_id, last_entry_uuid}`를 기록한다. 프론트가 이후 요청에 `ChatRequest.fork_from_turn_id`로 그 `turn_id`를 보내면 `agent.py`가 `resume=<anchor.session_id>, fork_session=True, resume_session_at=<anchor.last_entry_uuid>`로 그 지점부터 새 세션을 포크한다(`agent.py:_resolve_resume`). `last_entry_uuid`는 **AssistantMessage/UserMessage 의 uuid만** 대상이다 — `ResultMessage.uuid`는 필드는 있어도 실제 Transcript(JSONL)에 없는 프로토콜 프레임이라 `resume_session_at`에 넘기면 CLI가 `No message found with message.uuid of: ...`로 거부한다(실제 Claude CLI로 재현해 확인, `event_adapter.py` 참고). `fork_from_turn_id`가 빈 문자열이면 대화를 처음부터 새로 시작하고, 알 수 없는 값이면 `error` Event 하나를 내보내고 새 대화로 폴백한다.
- 시뮬레이션 종류·파라미터 스키마는 `knowledge/simulations/*.yaml`에 정의하고
  `services/simulation_registry.py`가 로드해 mock/real 공용으로 제공한다.
  새 시뮬레이션 종류를 추가할 때는 YAML 파일 하나만 추가하면 된다.
- 도메인 지식(테이블 카탈로그·KPI·시뮬레이션·용어집·시나리오)은 `knowledge/`
  아래 YAML이 source of truth다. `services/knowledge_service.py`가 pydantic으로
  검증해 로드하고, 에이전트는 `tools/knowledge_tool.py`를 통해서만 접근한다
  (설계: [docs/domain-knowledge.md](../docs/domain-knowledge.md)).
- 합성 시드 SQLite(`data/sample.sqlite`, git 미추적)는 카탈로그 YAML에서
  `python -m scripts.seed_sample_db`로 생성한다. `execute_sql`과 mock 시뮬레이션이
  같은 DB를 본다. mock 개발 중 테스트가 실패하면 시드부터 확인한다.

## Mock ↔ Real 서비스 전환

`services/__init__.py`가 `SERVICE_MODE` 환경변수(`mock` | `real`)에 따라
`services/mock/*` 또는 `services/real/*`를 자동 스위칭한다. `services/real/*`는
현재 폐쇄망 이식 대상으로 `NotImplementedError` 상태다 (실제 pntfp 로직 이식
절차는 [docs/CLOSED_NETWORK_SETUP.md](docs/CLOSED_NETWORK_SETUP.md) Part 2 참고).

**mock/real 함수 시그니처와 반환 dict 키 구조는 항상 동일하게 유지한다.**
이 계약이 깨지면 `tools/*.py`, `agent/agent.py` 등 호출부를 전부 고쳐야 한다.
mock 구현은 삭제하지 않는다 — `SERVICE_MODE=mock`으로 데모/테스트할 때 계속
쓴다.

## Agent 실행 모드

| 모드 | 조건 | 설명 |
| --- | --- | --- |
| 실제 Agent SDK | 기본값 | `claude_agent_sdk.query()`로 Claude 모델 + in-process MCP Tool 실행. `claude` CLI와 인증(`ANTHROPIC_API_KEY` 등)이 필요하다. |
| Fake Runner | `PLANNING_AGENT_FAKE=1` | Claude 호출 없이 `agent/fake_runner.py`가 Mock Service를 거쳐 전체 이벤트 계약(text/status/tool_call/tool_result/done)을 재현. 테스트·데모용, CI에서 우선 사용. |

새 Tool을 추가하거나 이벤트 흐름을 바꿀 때는 먼저 Fake Runner로 계약을
검증한 뒤 실제 Agent SDK 경로로 넘어간다.

## LLM Provider

`LLM_PROVIDER` 환경변수(`anthropic` | `openrouter`)로 전환한다
(`core/config.py`의 `agent_provider_env()`). 새 키를 만들지 말고 기존
`.env` 키 체계를 따른다. **현재 OpenRouter는 개발 단계 임시 조치**이며,
폐쇄망 반입 시 사내 LLM 엔드포인트로 교체될 예정이다 — 이 사실에 의존하는
코드를 작성하지 않는다 (provider 세부사항은 `core/config.py`에만 있어야
하고, 다른 계층은 이를 몰라야 한다).

## 설정 규칙

- 환경변수는 `core/config.py`에 모아서 읽는다. `services/`나 `tools/`
  코드에서 직접 `os.getenv(...)`를 호출하지 않는다.
- 새 환경변수를 추가하면 `.env.example`에도 키 이름과 주석을 함께 추가한다
  (값은 비워둔다 — 예시 파일이므로 실제 값을 넣지 않는다).
- API 키, DB 비밀번호, 사내 내부 URL 등 민감정보는 절대 코드, 커밋 메시지,
  `.env.example`, `docs/`에 직접 적지 않는다. `.env`(git 미추적)에만 넣는다.

## 폐쇄망(closed-network) 관련 문서

이 프로젝트는 최종적으로 폐쇄망에 배포된다. 관련 작업 시 아래 문서를 따른다:

- [docs/CLOSED_NETWORK_SETUP.md](docs/CLOSED_NETWORK_SETUP.md) — Part 1: 폐쇄망
  PC에서 이 코드베이스를 처음부터 구축(의존성 오프라인 설치, Claude CLI 반입,
  `.env` 구성, 기동 검증)하는 절차. Part 2: 기존 pntfp 프로젝트의 실제
  SQL/RAG/Simulation 서비스 로직을 `services/real/*`로 이식하는 절차
  (함수 시그니처 계약, `config.dev.yaml` → `.env` 매핑)

새 의존성(`requirements.txt`)을 추가하기 전에, 폐쇄망에서 사내 반입 가능한
패키지명/버전인지 먼저 확인한다. `claude-agent-sdk`는 Node.js와 `claude` CLI
바이너리가 별도로 필요하다는 점을 특히 주의한다.

## 테스트

```bash
cd backend
python -m pytest -q
```

- `tests/test_services.py`, `tests/test_tools.py` — mock 서비스/tool 단위 테스트
- `tests/test_knowledge.py`, `tests/test_knowledge_integrity.py` — 지식 로더와
  YAML 간 참조 정합성 (KPI 원천 테이블, diagnostics 참조 등)
- `tests/test_sql_guard.py` — `execute_sql` 조회 전용 가드레일
- `tests/test_scenarios.py` — 시드 DB가 시나리오대로 이상치를 만들었는지
- `tests/test_prompt_consistency.py` — SYSTEM_PROMPT/CLAUDE.md/Skills와 `TOOL_NAMES` 드리프트 방지
- `pytest -m e2e` — 실제 에이전트를 호출하는 시나리오 테스트 (API 키 필요, 기본 실행에서 제외)
- `tests/test_event_adapter.py` — SDK 이벤트 → `AgentEvent` 변환 테스트 (last_entry_uuid 추적 포함)
- `tests/test_api.py` — `/api/chat` 엔드포인트 통합 테스트 (Fake Runner 사용)
- `tests/test_session_store.py` — conversation_id/session_id 매핑, turn_id/TurnAnchor
- `tests/test_agent.py` — 편집/재생성 포크 분기(`_resolve_resume`/`_build_options`/`run_agent`). `query()`를 monkeypatch 로 대체 — 실제 CLI 검증은 별도로 수동 수행함(2026-09-14, `resume_session_at`에 ResultMessage.uuid를 넘기면 거부되는 걸 이렇게 발견했다)
- 새 Tool/Service를 추가하면 mock 구현 기준으로 테스트를 먼저 작성한다.

## 명령어

```bash
conda env create -f environment.yml     # 최초 1회 (Python 3.11)
conda activate production-planning
pip install -r requirements-dev.txt
cp .env.example .env

uvicorn main:app --reload --port 8000   # 프론트 기본 연동 포트
curl localhost:8000/health              # {"status":"ok"}
python -m pytest -q
```

## 프론트엔드 연동

- 백엔드는 포트 **8000**에서 실행한다. 프론트 `.env.local`의
  `VITE_API_BASE_URL`이 이 포트를 가리킨다.
- Browser가 FastAPI를 직접 호출한다 (BFF 없음) — `localhost:3000`
  Origin CORS 허용이 필요하다 (`main.py` + `core/config.py`의
  `CORS_ALLOW_ORIGINS`). 프론트 `vite.config.ts`가 dev/preview 포트를
  3000으로 고정(`strictPort: true`)해 이 CORS 설정과 맞춘다.
- `AgentEvent` 계약(`text`/`status`/`tool_call`/`tool_result`/`error`/`done`,
  `api/schemas.py`)을 바꾸면 프론트 `frontend/src/types/chat.ts`와
  반드시 함께 맞춘다. `status` 이벤트의 data는 `{ step, label?, status }`
  형태를 가정하며 같은 `step`은 갱신된다. `done` 이벤트의 data는
  `{ turn_id }`를 싣는다 — 편집/재생성 포크 지점(위 "편집/재생성 포크"
  참고). `ChatRequest.fork_from_turn_id`도 이 계약의 일부다.

## 문서

- [docs/CLOSED_NETWORK_SETUP.md](docs/CLOSED_NETWORK_SETUP.md) — 폐쇄망 구축 절차 + pntfp 실제 서비스 이식 가이드
- [plan/](plan/) — 실행 계획 문서 모음 ([plan/CLAUDE.md](plan/CLAUDE.md) 참고)
  - [plan/domain-knowledge-plan.md](plan/domain-knowledge-plan.md) — 도메인 지식(카탈로그·KPI·Skill·합성 시드 DB) Phase 1 실행 계획. 설계는 최상위 [docs/domain-knowledge.md](../docs/domain-knowledge.md)
- [backend-scaffold-instructions.md](backend-scaffold-instructions.md) — 최초 스캐폴딩 지시서 (역사적 참고용)
- [README.md](README.md) — 실행/테스트 명령어 요약

새로운 아키텍처/의존성 결정을 내리면 이 `docs/` 아래 문서를 갱신하고, 이
CLAUDE.md에서 필요한 부분만 요약해서 반영한다.
