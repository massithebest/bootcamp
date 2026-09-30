"""API Endpoint 검증."""

import json

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from fastapi.testclient import TestClient

import agent.agent as agent_module
from agent import session_store
from api.schemas import AgentEvent
from main import app


client = TestClient(app)


def _parse_sse(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: "):])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


@pytest.fixture(autouse=True)
def clear_agent_sessions():
    session_store.clear()
    yield
    session_store.clear()


def _install_sdk_stream(
    monkeypatch, messages: list[object], session_id: str, *, failed: bool = False
) -> None:
    async def fake_query(**_):
        for message in messages:
            yield message
        yield ResultMessage(
            subtype="error" if failed else "success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=failed,
            num_turns=1,
            session_id=session_id,
        )

    monkeypatch.setattr(agent_module, "query", fake_query)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_streams_sdk_agent_events(monkeypatch) -> None:
    """실제 run_agent와 adapter가 SDK 이벤트를 SSE 계약으로 변환한다."""

    _install_sdk_stream(
        monkeypatch,
        [
            AssistantMessage(
                content=[
                    TextBlock(text="조회 결과를 확인합니다."),
                    ToolUseBlock(
                        id="sql-1",
                        name="mcp__planning__execute_sql",
                        input={"sql": "SELECT 1 AS qty", "purpose": "계약 검증"},
                    ),
                ],
                model="fixture",
            ),
            UserMessage(
                content=[
                    ToolResultBlock(
                        tool_use_id="sql-1",
                        content=json.dumps(
                            {
                                "status": "ok",
                                "kind": "database",
                                "row_count": 1,
                                "table": {"columns": ["qty"], "rows": [[1]]},
                            }
                        ),
                    )
                ]
            ),
            AssistantMessage(
                content=[TextBlock(text="조회 결과는 1건입니다.")],
                model="fixture",
            ),
        ],
        session_id="api-stream-session",
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "조회 결과를 알려줘",
            "conversation_id": "api-stream-conversation",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    types = [e["type"] for e in events]

    assert types[-1] == "done"
    assert {"text", "status", "tool_call", "tool_result"} <= set(types)

    tool_call = next(e for e in events if e["type"] == "tool_call")
    tool_result = next(e for e in events if e["type"] == "tool_result")
    assert tool_call["tool_name"] == tool_result["tool_name"] == "execute_sql"
    assert tool_call["tool_call_id"] == tool_result["tool_call_id"] == "sql-1"
    assert tool_call["data"]["args"]["purpose"] == "계약 검증"
    assert tool_result["data"]["kind"] == "database"
    assert tool_result["data"]["row_count"] == 1
    answer = "".join(
        event.get("content") or "" for event in events if event["type"] == "text"
    )
    assert answer == "조회 결과를 확인합니다.조회 결과는 1건입니다."


# ---- workbench 종료 상태: case 이름은 frontend/tests/workbench.test.mjs와 대응한다 ----


def _tool_call(call_id):
    return AssistantMessage(content=[ToolUseBlock(
        id=call_id, name="mcp__planning__execute_sql", input={"sql": "SELECT 1"},
    )], model="fixture")


def _tool_result(call_id, data):
    return UserMessage(content=[ToolResultBlock(tool_use_id=call_id, content=json.dumps(data))])


ZERO = {"status": "ok", "kind": "database", "row_count": 0, "table": {"columns": ["qty"], "rows": []}}
ERROR = {"status": "error", "message": "조회 조건을 확인하세요."}


@pytest.mark.parametrize("case", ["tool-error-done", "missing-result", "empty-done", "zero-rows", "error-done", "parallel-reversed", "recovered-tool-error"])
def test_workbench_terminal_states_on_sse_wire(monkeypatch, case):
    messages = []
    if case not in ("empty-done", "error-done"):
        messages.append(_tool_call("sql-1"))
    if case == "tool-error-done":
        messages.extend([_tool_result("sql-1", ERROR), AssistantMessage(content=[TextBlock(text="조건 확인이 필요합니다.")], model="fixture")])
    elif case == "zero-rows":
        messages.append(_tool_result("sql-1", ZERO))
    elif case == "parallel-reversed":
        messages.extend([_tool_call("sql-2"), _tool_result("sql-2", ZERO), _tool_result("sql-1", ERROR)])
    elif case == "recovered-tool-error":
        messages.extend([_tool_result("sql-1", ERROR), _tool_call("sql-2"), _tool_result("sql-2", ZERO),
            AssistantMessage(content=[TextBlock(text="조건을 수정해 조회했습니다. 결과는 0건입니다.")], model="fixture")])
    _install_sdk_stream(monkeypatch, messages, session_id="ux-fixture", failed=case == "error-done")
    response = client.post("/api/chat", json={"message": "조회 결과를 알려줘"})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[-1]["type"] == "done"
    assert sum(e["type"] == "done" for e in events) == 1
    results = [e for e in events if e["type"] == "tool_result"]
    calls = {e["tool_call_id"]: e for e in events if e["type"] == "tool_call"}
    for event in results:
        assert event["tool_call_id"] in calls
        assert event["tool_name"] == calls[event["tool_call_id"]]["tool_name"]
        result_index = events.index(event)
        assert events.index(calls[event["tool_call_id"]]) < result_index
        status = events[result_index + 1]
        assert status["type"] == "status"
        assert status["tool_call_id"] == event["tool_call_id"]
        assert status["data"]["status"] == ("error" if event["data"]["status"] == "error" else "completed")
    if case in ("empty-done", "missing-result"):
        assert results == []  # Never synthesize a successful tool result.
        assert len(calls) == (case == "missing-result")
    if case == "empty-done":
        assert [e["type"] for e in events] == ["done"]
    if case == "error-done":
        assert [e["type"] for e in events] == ["error", "done"]
        assert events[-1]["data"] is None
    elif case == "tool-error-done":
        assert results[0]["data"] == ERROR
        assert events[-2]["type"] == "text"
        assert events[-1]["data"]["turn_id"]
    elif case == "zero-rows":
        assert results[0]["data"] == ZERO
    elif case == "parallel-reversed":
        assert [e["tool_call_id"] for e in results] == ["sql-2", "sql-1"]
    elif case == "recovered-tool-error":
        assert [e["data"]["status"] for e in results] == ["error", "ok"]
        assert events[-2]["type"] == "text"
    assert all("access_scope" not in e.get("data", {}).get("args", {}) for e in calls.values())


def test_chat_endpoint_reports_error_gracefully(monkeypatch, caplog) -> None:
    """run_agent 내부 오류가 상세 노출 없이 error/done 으로 전달된다."""

    async def boom(*args, **kwargs):
        raise RuntimeError("internal detail should not leak")
        yield  # pragma: no cover

    monkeypatch.setattr("api.routes_chat.run_agent", boom)

    response = client.post("/api/chat", json={"message": "hi"})
    events = _parse_sse(response.text)

    assert response.status_code == 200
    assert events[-1]["type"] == "done"
    assert any(e["type"] == "error" for e in events)
    assert all("internal detail" not in (e.get("content") or "") for e in events)
    assert events[-2:] == [
        {"type": "error", "content": "Agent 실행 중 오류가 발생했습니다."},
        {"type": "done"},
    ]
    assert "error_type=RuntimeError" in caplog.text
    assert "internal detail" not in caplog.text


def test_chat_endpoint_passes_fork_from_turn_id_through(monkeypatch) -> None:
    """`fork_from_turn_id` 가 요청 바디에서 run_agent 까지 그대로 전달된다."""

    captured: dict[str, object] = {}

    async def fake_run_agent(*, message, conversation_id, fork_from_turn_id, access_scope):
        captured["fork_from_turn_id"] = fork_from_turn_id
        captured["access_scope"] = access_scope
        yield AgentEvent(type="done", data={"turn_id": "new-turn"})

    monkeypatch.setattr("api.routes_chat.run_agent", fake_run_agent)

    response = client.post(
        "/api/chat",
        json={
            "message": "다시 답해줘",
            "conversation_id": "conv-1",
            "fork_from_turn_id": "turn-1",
        },
    )

    assert response.status_code == 200
    assert captured["fork_from_turn_id"] == "turn-1"
    assert isinstance(captured["access_scope"], str)


def test_chat_endpoint_issues_and_reuses_http_only_scope_cookie(monkeypatch) -> None:
    captured: list[str] = []

    async def fake_run_agent(**kwargs):
        captured.append(kwargs["access_scope"])
        yield AgentEvent(type="done", data={"turn_id": "new-turn"})

    monkeypatch.setattr("api.routes_chat.run_agent", fake_run_agent)
    scoped_client = TestClient(app, base_url="https://testserver")
    first = scoped_client.post("/api/chat", json={"message": "첫 요청"})
    second = scoped_client.post("/api/chat", json={"message": "다음 요청"})

    assert "HttpOnly" in first.headers["set-cookie"]
    assert "SameSite=lax" in first.headers["set-cookie"]
    assert "set-cookie" not in second.headers
    assert captured[0] == captured[1]


def test_chat_request_fork_from_turn_id_defaults_to_none() -> None:
    from api.schemas import ChatRequest

    request = ChatRequest(message="hi")
    assert request.fork_from_turn_id is None


def test_knowledge_skills_endpoint() -> None:
    response = client.get("/api/knowledge/skills")

    assert response.status_code == 200
    skills = response.json()
    assert {skill["name"] for skill in skills} == {"sql-analysis", "simulation"}
    assert all(set(skill) == {"name", "description", "status"} for skill in skills)
    assert all(skill["description"] for skill in skills)


@pytest.mark.usefixtures("bundled_knowledge")
def test_knowledge_catalog_endpoint() -> None:
    response = client.get("/api/knowledge/catalog")

    assert response.status_code == 200
    tables = response.json()
    assert len(tables) == 12
    assert {table["table"] for table in tables} == {
        "part",
        "route_step",
        "tool",
        "orders",
        "wip",
        "setup",
        "setup_group",
        "down_calendar",
        "pm_calendar",
        "calendar_attach",
        "transport",
        "FP_TARGET",
    }
    assert set(tables[0]) == {"table", "description", "grain", "tags", "verified"}


@pytest.mark.usefixtures("bundled_knowledge")
def test_knowledge_kpis_endpoint() -> None:
    response = client.get("/api/knowledge/kpis")

    assert response.status_code == 200
    kpis = response.json()
    assert [kpi["kpi_id"] for kpi in kpis] == ["initial_wip"]
    assert set(kpis[0]) == {"kpi_id", "name", "aliases", "verified"}


def test_client_disconnect_cancels_agent_iterator(monkeypatch):
    import asyncio
    from fastapi import Request
    from api.routes_chat import chat
    from api.schemas import ChatRequest

    async def scenario():
        sent = asyncio.Event()
        closed = asyncio.Event()

        async def fake_agent(**kwargs):
            try:
                yield AgentEvent(type="text", content="부분 응답")
                await asyncio.Event().wait()
            finally:
                closed.set()

        monkeypatch.setattr("api.routes_chat.run_agent", fake_agent)
        scope = {"type": "http", "method": "POST", "path": "/api/chat",
                 "headers": [], "asgi": {"spec_version": "2.0"}}
        response = await chat(ChatRequest(message="q"), Request(scope))

        async def receive():
            await sent.wait()
            return {"type": "http.disconnect"}

        async def send(event):
            if event["type"] == "http.response.body":
                sent.set()

        await asyncio.wait_for(response(scope, receive, send), timeout=2)
        assert closed.is_set()

    asyncio.run(scenario())
