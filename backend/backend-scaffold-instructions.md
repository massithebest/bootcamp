# Production Planning Agent Backend 스캐폴딩 구축

## 목표

Claude Agent SDK 기반 생산계획 Agent Backend의 기본 구조와 스켈레톤 코드를 구축한다.

현재 단계에서는 실제 업무 로직을 구현하지 않는다.

다음 항목만 정확하게 구성한다.

- 폴더 구조
- Module 책임
- 함수 Signature
- Type
- Docstring
- Mock Service
- Agent Event 계약
- FastAPI SSE Endpoint
- Agent SDK 확장 위치

실제 SQL / RAG / Simulation / MCP 연동 로직은 모두 TODO 또는 Mock 상태로 유지한다.

---

# 1. 전체 구조

전체 Backend는 다음 흐름을 기준으로 한다.

```text
Frontend
   ↓
FastAPI
   ↓
Agent Runner
   ↓
Claude Agent SDK
   ↓
Tools
   ↓
Services
   ↓
Mock / Real
```

Frontend와 Claude Agent SDK를 직접 결합하지 않는다.

Agent SDK에서 발생하는 이벤트는 Backend에서 공통 `AgentEvent` 형태로 변환한다.

```text
Claude Agent SDK Event
       ↓
Agent Event Adapter
       ↓
AgentEvent
       ↓
FastAPI SSE
       ↓
Frontend
```

Frontend는 Claude Agent SDK 내부 Message Type을 알 필요가 없어야 한다.

---

# 2. 폴더 구조

다음 구조를 생성한다.

```text
backend/
├── main.py
├── requirements.txt
│
├── api/
│   ├── __init__.py
│   ├── routes_chat.py
│   └── schemas.py
│
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── event_adapter.py
│   ├── system_prompt.py
│   │
│   └── agent_sdk/
│       ├── CLAUDE.md
│       └── .claude/
│           └── skills/
│               ├── production-planning/
│               ├── sql-analysis/
│               └── simulation/
│
├── tools/
│   ├── __init__.py
│   ├── sql_tool.py
│   ├── rag_tool.py
│   ├── line_capacity_tool.py
│   ├── material_constraint_tool.py
│   └── line_comparison_tool.py
│
├── services/
│   ├── __init__.py
│   │
│   ├── real/
│   │   ├── __init__.py
│   │   ├── sql_service.py
│   │   ├── rag_service.py
│   │   └── simulation_service.py
│   │
│   └── mock/
│       ├── __init__.py
│       ├── mock_sql_service.py
│       ├── mock_rag_service.py
│       └── mock_simulation_service.py
│
├── core/
│   ├── __init__.py
│   └── config.py
│
└── tests/
    ├── test_tools.py
    ├── test_services.py
    └── test_api.py
```

불필요한 Factory, Repository Pattern, Dependency Injection Framework, Abstract Base Class 등은 현재 단계에서 추가하지 않는다.

---

# 3. main.py

```python
"""Production Planning Agent FastAPI application entry point."""

from fastapi import FastAPI

from api.routes_chat import router as chat_router


app = FastAPI(
    title="Production Planning Agent API",
)

app.include_router(
    chat_router,
    prefix="/api",
)


@app.get("/health")
async def health_check() -> dict:
    """Return backend health status."""
    return {"status": "ok"}


# TODO:
# Claude Agent SDK에서 애플리케이션 단위 초기화가 필요한 경우
# FastAPI lifespan을 사용하여 추가한다.
```

Deprecated startup event 방식보다 필요 시 FastAPI lifespan을 사용하는 방향으로 확장한다.

현재는 초기화 로직을 구현하지 않는다.

---

# 4. requirements.txt

현재 사내 환경에서 사용 가능한 패키지만 선언한다.

```text
fastapi
uvicorn
pydantic

# TODO:
# 폐쇄망에서 사용 가능한 Claude Agent SDK 패키지명을 확인한 후 추가
```

새로운 Dependency를 임의로 추가하지 않는다.

---

# 5. api/schemas.py

Frontend와 Backend 사이의 공통 API 계약을 정의한다.

```python
"""Frontend / Backend API contracts."""

from typing import Any, Literal

from pydantic import BaseModel


AgentEventType = Literal[
    "text",
    "status",
    "tool_call",
    "tool_result",
    "error",
    "done",
]


class ChatRequest(BaseModel):
    """Chat request from frontend."""

    message: str
    conversation_id: str | None = None


class AgentEvent(BaseModel):
    """Common agent event exposed to the frontend.

    Frontend rendering behavior is determined by `type`.

    Claude Agent SDK internal message/event types must not be exposed
    directly through this schema.
    """

    type: AgentEventType
    content: str | None = None
    tool_name: str | None = None
    data: dict[str, Any] | None = None
```

`ChatResponseChunk`보다 역할이 명확한 `AgentEvent`라는 이름을 사용한다.

---

# 6. Agent Event 규칙

Frontend에 전달할 Event는 다음 종류만 사용한다.

```text
text
status
tool_call
tool_result
error
done
```

## text

사용자에게 보여줄 Assistant 답변 스트리밍.

예:

```json
{
  "type": "text",
  "content": "생산 실적을 확인한 결과 "
}
```

## status

업무 진행 상태.

예:

```json
{
  "type": "status",
  "data": {
    "step": "simulation",
    "status": "running",
    "label": "생산계획 Simulation 수행"
  }
}
```

status 값은 기본적으로 다음을 사용한다.

```text
pending
running
completed
error
```

## tool_call

Agent가 업무 Tool을 호출했음을 나타낸다.

예:

```json
{
  "type": "tool_call",
  "tool_name": "query_database"
}
```

## tool_result

Tool 실행 결과 중 Frontend에서 표현할 수 있는 업무 결과.

예:

```json
{
  "type": "tool_result",
  "tool_name": "query_database",
  "data": {}
}
```

## error

사용자에게 전달 가능한 오류.

```json
{
  "type": "error",
  "content": "요청 처리 중 오류가 발생했습니다."
}
```

## done

현재 Agent 응답 Stream 종료.

```json
{
  "type": "done"
}
```

Agent 내부 Chain-of-Thought, Scratchpad, 내부 Reasoning은 Frontend에 전달하지 않는다.

Frontend에는 업무적으로 의미 있는 실행 상태와 결과만 전달한다.

---

# 7. api/routes_chat.py

```python
"""Chat API endpoint with SSE streaming."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.agent import run_agent
from api.schemas import ChatRequest


router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Run the production planning agent and stream AgentEvents via SSE."""

    async def event_generator():
        try:
            async for event in run_agent(
                message=request.message,
                conversation_id=request.conversation_id,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        except Exception:
            # TODO:
            # 실제 환경에서는 내부 오류를 logging 한다.
            # 상세 Exception 내용은 Frontend에 그대로 노출하지 않는다.
            yield (
                'data: {"type":"error",'
                '"content":"Agent 실행 중 오류가 발생했습니다."}\n\n'
            )

            yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

API Layer는 다음 책임만 가진다.

```text
AgentEvent
 ↓
SSE 직렬화
 ↓
HTTP Response
```

Agent SDK Event 해석이나 업무 판단 로직은 API Layer에 넣지 않는다.

---

# 8. agent/system_prompt.py

```python
"""Base system prompt for the production planning agent."""


SYSTEM_PROMPT = """
당신은 생산계획 분석 업무를 지원하는 AI Agent이다.

주요 역할:
- 생산계획 관련 사용자 질의를 이해한다.
- 필요한 경우 적절한 Tool을 선택하여 실행한다.
- 여러 Tool이 필요한 경우 순차 또는 복합적으로 활용한다.
- Tool 결과를 기반으로 사용자에게 이해하기 쉬운 결과를 제공한다.

사용 가능한 주요 Tool:
- query_database
- search_knowledge
- simulate_line_capacity
- simulate_material_constraint
- simulate_line_comparison

상세한 생산계획 업무 절차와 Tool 사용 방법은
CLAUDE.md 및 Skills의 지침을 따른다.

TODO:
- 실제 생산계획 Agent 역할 정의 보완
- 응답 원칙 정의
- 업무상 금지사항 정의
"""
```

System Prompt에 모든 업무 절차를 몰아넣지 않는다.

역할을 다음과 같이 분리한다.

```text
SYSTEM_PROMPT
 ├─ Agent 기본 역할
 ├─ 기본 응답 원칙
 └─ 핵심 제약

CLAUDE.md
 ├─ 프로젝트 전반 업무 규칙
 ├─ 생산계획 Agent 행동 원칙
 └─ 공통 Tool 사용 규칙

Skills
 ├─ 생산계획 업무 수행 방법
 ├─ SQL 조회 절차
 ├─ Simulation 수행 절차
 └─ 결과 분석 / 비교 방법
```

---

# 9. agent/agent.py

Agent SDK 초기화 및 실행만 담당한다.

```python
"""Claude Agent SDK initialization and execution."""

from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from agent.system_prompt import SYSTEM_PROMPT

from tools.sql_tool import query_database
from tools.rag_tool import search_knowledge
from tools.line_capacity_tool import simulate_line_capacity
from tools.material_constraint_tool import simulate_material_constraint
from tools.line_comparison_tool import simulate_line_comparison


# TODO:
# 폐쇄망에서 실제 Claude Agent SDK import 후 초기화
#
# Agent SDK 설정 예시:
#
# ClaudeAgentOptions(
#     cwd="./agent/agent_sdk",
#     setting_sources=["project"],
# )
#
# 실제 SDK API Signature를 확인한 후 구현할 것.


async def run_agent(
    message: str,
    conversation_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the production planning agent.

    Args:
        message:
            User input message.

        conversation_id:
            Frontend conversation identifier.
            It is intentionally separated from an Agent SDK internal
            session identifier.

    Yields:
        AgentEvent:
            Frontend-independent common agent events.

    Notes:
        - Claude Agent SDK original events must be converted into AgentEvent.
        - SSE serialization must not be handled in this layer.
        - Internal chain-of-thought must never be exposed.
    """

    # TODO:
    # 1. Agent SDK session 실행
    # 2. SDK event 수신
    # 3. event_adapter를 통해 AgentEvent로 변환
    # 4. AgentEvent yield

    raise NotImplementedError
```

`conversation_id`와 향후 Agent SDK 내부 `session_id`는 별도 개념으로 유지한다.

```text
conversation_id
    ↓
사용자 관점의 대화

agent_session_id
    ↓
Claude Agent SDK 실행 Session
```

향후 필요하면 별도의 Mapping 계층을 추가한다.

---

# 10. agent/event_adapter.py

Claude Agent SDK 내부 Event를 Frontend용 `AgentEvent`로 변환하는 역할만 담당한다.

```python
"""Convert Claude Agent SDK events into common AgentEvent objects."""

from api.schemas import AgentEvent


def convert_agent_event(raw_event: object) -> list[AgentEvent]:
    """Convert one Claude Agent SDK event into frontend-safe AgentEvents.

    Args:
        raw_event:
            Raw event emitted from Claude Agent SDK.

    Returns:
        List of common AgentEvent objects.

    Notes:
        - Do not expose internal reasoning or chain-of-thought.
        - Only user-visible text, business execution status,
          tool calls and business results should be returned.
    """

    # TODO:
    # 실제 Claude Agent SDK Event Type 확인 후 구현

    raise NotImplementedError
```

Agent SDK 종속 코드는 가능한 한 이 Adapter에 집중시킨다.

---

# 11. Tool 구현 원칙

Tool은 Agent가 사용할 수 있는 업무 Capability를 표현한다.

```text
Agent
 ↓
Tool
 ↓
Service
 ↓
External System
```

Tool 내부에서 DB Client, Milvus Client, HTTP Client 등을 직접 생성하지 않는다.

실제 I/O 작업은 Service Layer가 담당한다.

Tool과 Service는 처음부터 `async` 기준으로 통일한다.

---

# 12. tools/sql_tool.py

```python
"""SQL tool for structured production planning data."""

from services import sql_service


async def query_database(question: str) -> dict:
    """Query structured production planning data.

    Use this tool for:
    - production results
    - inventory
    - product information
    - equipment / line information
    - other structured business data
    """

    return await sql_service.generate_and_query(question)
```

---

# 13. tools/rag_tool.py

```python
"""RAG tool for production planning knowledge search."""

from services import rag_service


async def search_knowledge(query: str) -> dict:
    """Search production planning knowledge.

    Use this tool for:
    - process manuals
    - business terminology
    - production planning policies
    - non-structured domain knowledge
    """

    return await rag_service.search(query)
```

---

# 14. tools/line_capacity_tool.py

```python
"""Simulation tool for line capacity."""

from services import simulation_service


async def simulate_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Simulate whether a production target can be achieved.

    Example:
        "9월에 A라인에서 1000개 생산 가능한가?"
    """

    return await simulation_service.run_line_capacity(
        line=line,
        period=period,
        target_qty=target_qty,
    )
```

---

# 15. tools/material_constraint_tool.py

Pydantic 모델은 Tool 입력 Validation에 사용한다.

Service Layer에는 가능한 한 일반 Python 자료구조를 전달한다.

```python
"""Simulation tool for material constraints."""

from pydantic import BaseModel

from services import simulation_service


class MaterialConstraint(BaseModel):
    """Material availability constraint."""

    material_id: str
    available_qty: int


async def simulate_material_constraint(
    line: str,
    period: str,
    materials: list[MaterialConstraint],
) -> dict:
    """Simulate maximum production quantity with material constraints.

    Example:
        "자재 X 500개, Y 300개가 있을 때 A라인 최대 생산량은?"
    """

    material_payload = [
        material.model_dump()
        for material in materials
    ]

    return await simulation_service.run_material_constraint(
        line=line,
        period=period,
        materials=material_payload,
    )
```

Service Layer에서 Pydantic 객체에 직접 의존하지 않도록 한다.

---

# 16. tools/line_comparison_tool.py

```python
"""Simulation tool for multiple line comparison."""

from services import simulation_service


async def simulate_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str = "efficiency",
) -> dict:
    """Compare multiple production lines over a date range.

    Example:
        "10월 동안 A, B, C라인 중 효율이 가장 좋은 라인은?"
    """

    return await simulation_service.run_line_comparison(
        lines=lines,
        period_start=period_start,
        period_end=period_end,
        metric=metric,
    )
```

`simulation_tool_1.py` 같은 숫자 기반 파일명은 사용하지 않는다.

업무 의미가 드러나는 이름을 사용한다.

---

# 17. core/config.py

환경과 Service 선택을 분리한다.

```python
"""Application configuration."""

import os


ENV = os.getenv("ENV", "dev")

SERVICE_MODE = os.getenv(
    "SERVICE_MODE",
    "mock",
)
```

예:

```text
ENV=dev
SERVICE_MODE=mock

ENV=dev
SERVICE_MODE=real

ENV=prod
SERVICE_MODE=real
```

`ENV=dev`라고 해서 반드시 Mock Service를 사용하도록 강제하지 않는다.

---

# 18. services/__init__.py

```python
"""Select mock or real service implementations."""

from core.config import SERVICE_MODE


if SERVICE_MODE == "real":
    from services.real import rag_service
    from services.real import simulation_service
    from services.real import sql_service

else:
    from services.mock import mock_rag_service as rag_service
    from services.mock import mock_simulation_service as simulation_service
    from services.mock import mock_sql_service as sql_service
```

현재 단계에서는 별도의 Service Factory나 Dependency Injection 구조를 만들지 않는다.

---

# 19. Real SQL Service

`services/real/sql_service.py`

```python
"""Real SQL generation and database query service."""


async def generate_and_query(question: str) -> dict:
    """Generate SQL and query production planning database."""

    # TODO:
    # 폐쇄망의 실제 SQL Agent / DB Query 로직을 이식

    raise NotImplementedError(
        "Real SQL service must be implemented in the closed network."
    )
```

---

# 20. Real RAG Service

`services/real/rag_service.py`

```python
"""Real production planning knowledge search service."""


async def search(query: str) -> dict:
    """Search production planning knowledge from Milvus."""

    # TODO:
    # 폐쇄망의 기존 Milvus / Hybrid Search 로직 이식

    raise NotImplementedError(
        "Real RAG service must be implemented in the closed network."
    )
```

---

# 21. Real Simulation Service

`services/real/simulation_service.py`

```python
"""Real production planning simulation service."""


async def run_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Run line capacity simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )


async def run_material_constraint(
    line: str,
    period: str,
    materials: list[dict],
) -> dict:
    """Run material constraint simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )


async def run_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str,
) -> dict:
    """Run line comparison simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )
```

---

# 22. Mock SQL Service

`services/mock/mock_sql_service.py`

```python
"""Mock SQL service."""


async def generate_and_query(question: str) -> dict:
    """Return mock SQL query result."""

    return {
        "status": "ok",
        "question": question,
        "generated_sql": (
            "SELECT * FROM production_result LIMIT 10;"
        ),
        "rows": [
            {
                "line": "A",
                "date": "2026-09-01",
                "qty": 320,
            }
        ],
    }
```

---

# 23. Mock RAG Service

`services/mock/mock_rag_service.py`

```python
"""Mock RAG service."""


async def search(query: str) -> dict:
    """Return mock knowledge search result."""

    return {
        "status": "ok",
        "query": query,
        "documents": [
            {
                "title": "공정 매뉴얼 v1",
                "content": "더미 문서 내용",
                "score": 0.82,
            }
        ],
    }
```

---

# 24. Mock Simulation Service

`services/mock/mock_simulation_service.py`

```python
"""Mock production planning simulation services."""


async def run_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Return mock line capacity result."""

    return {
        "status": "ok",
        "line": line,
        "period": period,
        "target_qty": target_qty,
        "achievable_qty": 950,
        "achievement_rate": 0.95,
        "bottleneck": "설비 가동률",
    }


async def run_material_constraint(
    line: str,
    period: str,
    materials: list[dict],
) -> dict:
    """Return mock material constraint result."""

    return {
        "status": "ok",
        "line": line,
        "period": period,
        "max_producible_qty": 780,
        "limiting_material": (
            materials[0]["material_id"]
            if materials
            else None
        ),
        "material_usage": [
            {
                "material_id": material["material_id"],
                "required": 200,
                "available": material["available_qty"],
            }
            for material in materials
        ],
    }


async def run_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str,
) -> dict:
    """Return mock line comparison result."""

    return {
        "status": "ok",
        "period_start": period_start,
        "period_end": period_end,
        "metric": metric,
        "ranking": [
            {
                "line": line,
                "score": 0.9 - index * 0.05,
                "rank": index + 1,
            }
            for index, line in enumerate(lines)
        ],
    }
```

---

# 25. CLAUDE.md / Skills

현재는 파일과 폴더만 생성한다.

실제 업무 내용은 TODO 상태로 남긴다.

```text
agent/agent_sdk/
├── CLAUDE.md
└── .claude/
    └── skills/
        ├── production-planning/
        ├── sql-analysis/
        └── simulation/
```

`CLAUDE.md`에는 향후 다음 내용을 관리한다.

```text
- 생산계획 Agent 공통 행동 원칙
- Tool 사용 기본 규칙
- 결과 검증 원칙
- 복합 업무 처리 기본 원칙
```

Skills는 향후 다음처럼 구성할 수 있도록 한다.

```text
production-planning
→ 생산계획 업무 수행법

sql-analysis
→ SQL 조회 및 결과 분석 방법

simulation
→ Simulation 수행 / 재실행 / 비교 방법
```

현재 작업에서는 상세 Skill 내용까지 작성하지 않는다.

---

# 26. Tests

## tests/test_services.py

Mock Service의 입력/출력 계약을 검증한다.

최소한 다음 Service를 호출한다.

```text
SQL
RAG
Line Capacity Simulation
Material Constraint Simulation
Line Comparison Simulation
```

---

## tests/test_tools.py

각 Tool을 Mock Mode에서 호출하고 다음을 확인한다.

```text
- 정상 호출
- Async 함수 실행
- 입력 Schema
- 반환값이 dict인지 확인
```

---

## tests/test_api.py

최소한 다음 Endpoint를 검증할 수 있는 구조를 만든다.

```text
GET /health
POST /api/chat
```

현재 Agent SDK가 구현되지 않은 경우 `/api/chat` 테스트는 TODO 또는 Mock Runner 기반으로 남겨도 된다.

---

# 27. 구현 원칙

다음 원칙을 반드시 따른다.

## 하지 않을 것

```text
실제 SQL 생성 로직
실제 Milvus 연결
실제 Simulation API 연결
실제 MCP 연결
실제 Agent SDK 세부 구현
인증
Memory DB
Chat History DB
복잡한 Exception Framework
Repository Pattern
Dependency Injection Framework
불필요한 Abstract Class
```

현재 작업은 Skeleton 구축이 목적이다.

---

# 28. Async 원칙

I/O가 발생할 가능성이 있는 계층은 처음부터 Async Signature를 사용한다.

```text
Agent
 ↓
async Tool
 ↓
async Service
 ↓
DB / Milvus / API / MCP
```

Real / Mock Service의 Signature를 동일하게 유지한다.

---

# 29. Agent Layer 책임

Agent Layer:

```text
사용자 요청
 ↓
Claude Agent SDK 실행
 ↓
Tool 실행
 ↓
SDK Event 수신
 ↓
AgentEvent 변환
```

SSE 문자열 생성은 하지 않는다.

---

# 30. API Layer 책임

API Layer:

```text
AgentEvent
 ↓
JSON Serialization
 ↓
SSE
```

Agent 업무 판단이나 Tool 선택 로직을 넣지 않는다.

---

# 31. Tool Layer 책임

Tool Layer:

```text
Agent가 사용하는 업무 기능 정의
+
입력 Validation
+
Service 호출
```

실제 외부 시스템 연결을 구현하지 않는다.

---

# 32. Service Layer 책임

Service Layer:

```text
DB
Milvus
Simulation API
MCP
기존 사내 API
```

등 실제 외부/내부 시스템 통신을 담당한다.

Mock과 Real의 함수 Signature는 동일하게 유지한다.

---

# 33. 실행 환경

기본 개발 환경:

```text
ENV=dev
SERVICE_MODE=mock
```

실행:

```bash
uvicorn main:app --reload
```

확인:

```text
GET /health

→

{
  "status": "ok"
}
```

---

# 34. 구현 후 검증

가능한 경우 다음을 확인한다.

```bash
python -m pytest
```

그리고 전체 코드에서 다음을 확인한다.

```text
- Mock / Real Service Signature 일치
- Tool / Service Async 일치
- circular import 없음
- Agent SDK 내부 Type이 api/schemas.py로 노출되지 않음
- 실제 외부 시스템 호출 코드가 구현되지 않음
- TODO 위치가 명확하게 남아 있음
```

---

# 35. 이번 작업 완료 기준

```text
[ ] 전체 폴더 구조 생성
[ ] FastAPI 실행 가능
[ ] /health 정상 동작
[ ] AgentEvent Schema 생성
[ ] text/status/tool_call/tool_result/error/done 지원
[ ] conversation_id가 Agent Runner까지 전달됨
[ ] run_agent가 AsyncIterator[AgentEvent] Signature를 가짐
[ ] Agent Event Adapter 구조 존재
[ ] Tool이 모두 async
[ ] Mock / Real Service가 모두 async
[ ] SERVICE_MODE mock/real 전환 가능
[ ] Simulation Tool 파일명이 업무 의미 기반으로 구성됨
[ ] Pydantic 모델이 Service Layer로 직접 전달되지 않음
[ ] CLAUDE.md / Skills 확장 위치 생성
[ ] Mock Service 정상 동작
[ ] 최소 Test 구조 생성
[ ] 실제 업무 로직은 TODO 상태로 유지
```

# 핵심 설계

최종적으로 다음 구조가 명확하게 드러나도록 구현한다.

```text
                       Frontend
                           │
                           │ POST /api/chat
                           │ SSE
                           ▼
                     ┌───────────┐
                     │  FastAPI  │
                     └─────┬─────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Agent Runner│
                    └──────┬──────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Claude Agent SDK  │
                 │ CLAUDE.md / Skill│
                 └─────────┬─────────┘
                           │
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
                SQL       RAG    Simulation
                Tool      Tool       Tools
                 │         │         │
                 └─────────┼─────────┘
                           ▼
                     Service Layer
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
               Mock                 Real
                                     │
                           ┌─────────┼─────────┐
                           ▼         ▼         ▼
                           DB      Milvus      MCP
```

가장 중요한 원칙은 다음과 같다.

```text
Frontend
   ↓
AgentEvent
   ↓
Backend Agent Layer
   ↓
Claude Agent SDK
   ↓
Tool
   ↓
Service
```

Frontend가 Claude Agent SDK 내부 구현에 직접 의존하지 않도록 한다.

향후 Agent SDK 변경, Tool 추가, Simulation API 확대, SQL Agent 고도화가 발생하더라도 Frontend와 API 계약의 변경을 최소화할 수 있는 구조로 만든다.