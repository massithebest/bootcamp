# Production Planning Agent Backend

```text
Frontend → FastAPI(/api/chat, SSE) → Agent Runner → Claude Agent SDK
        → Tools(in-process MCP) → Services(mock | real)
```

## 실행 환경

```bash
conda env create -f environment.yml     # 최초 1회 (Python 3.11)
conda activate production-planning
pip install -r requirements-dev.txt
cp .env.example .env                     # 환경변수 설정 (.env 는 커밋 금지)
```

`.env` 는 `core/config.py` 에서 자동 로드된다. (실제 환경변수가 항상 우선)

### LLM Provider 전환

| `LLM_PROVIDER` | 필요 값 | 동작 |
| --- | --- | --- |
| `anthropic` (기본) | `ANTHROPIC_API_KEY` | Anthropic API 직결 |
| `openrouter` | `OPENROUTER_API_KEY` | `ANTHROPIC_BASE_URL` 을 OpenRouter 로 주입 (`agent/agent.py` → `ClaudeAgentOptions.env`) |

`AGENT_MODEL` 로 모델 지정 (openrouter 예: `anthropic/claude-sonnet-4.5`).
비(非)Anthropic 모델은 tool calling 이 불안정할 수 있다.

### `claude` CLI 경로

Agent SDK 는 `claude` 실행 파일(Node.js 필요)이 있어야 한다. PATH 에 없으면
`CLAUDE_CLI_PATH` 로 절대경로를 지정한다. 탐색 순서:

```text
CLAUDE_CLI_PATH → PATH(shutil.which) → SDK 자체 탐색 → 없으면 CLINotFoundError
```

## 서버 실행

```bash
export ENV=dev
export SERVICE_MODE=mock          # mock | real
uvicorn main:app --reload
```

확인:

```bash
curl localhost:8000/health        # {"status":"ok"}
```

## Agent 실행 모드

| 모드 | 조건 | 설명 |
| --- | --- | --- |
| 실제 Agent SDK | 기본값 | `claude_agent_sdk.query()` 로 Claude 모델 + in-process MCP Tool 실행. `claude` CLI 와 인증(`ANTHROPIC_API_KEY` 등)이 필요하다. |
| Fake Runner | `PLANNING_AGENT_FAKE=1` | Claude 호출 없이 Mock Service 를 거쳐 전체 이벤트 계약(text/status/tool_call/tool_result/done)을 재현. 테스트·데모용. |

```bash
PLANNING_AGENT_FAKE=1 uvicorn main:app --reload
curl -N -X POST localhost:8000/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"9월에 A라인에서 1000개 생산 가능한가?","conversation_id":"c1"}'
```

## 계층 책임

| 계층 | 파일 | 책임 |
| --- | --- | --- |
| API | `api/routes_chat.py` | AgentEvent → SSE 직렬화만 |
| Agent Runner | `agent/agent.py` | SDK 실행, 이벤트 수신 |
| Event Adapter | `agent/event_adapter.py` | SDK 이벤트 → `AgentEvent` 변환 (SDK 종속 코드 집중) |
| SDK Tools | `agent/sdk_tools.py` | `tools/` 함수를 `@tool` 로 감싼 in-process MCP Server |
| Tools | `tools/*.py` | 입력 검증 + Service 호출 |
| Services | `services/{mock,real}/*` | 실제 I/O (DB / Milvus / Simulation MCP) |

- `conversation_id`(사용자 대화) 와 SDK `session_id` 는 `agent/session_store.py` 에서 매핑한다.
- `services/real/*` 는 폐쇄망 이식 대상으로 `NotImplementedError` 상태다.

## 테스트

```bash
python -m pytest -q
```
