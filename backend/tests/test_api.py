"""API Endpoint 검증."""

import json

from fastapi.testclient import TestClient

from api.schemas import AgentEvent
from main import app
from services import result_store, visualization_store
from services.result_store import LocalParquetResultStore
from services.visualization_models import VisualizationRequest
from services.visualization_service import prepare_visualization
from services.visualization_store import LocalVisualizationStore


client = TestClient(app)


def _parse_sse(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: "):])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_streams_agent_events(monkeypatch) -> None:
    """Fake Runner 기준으로 전체 이벤트 계약을 검증한다."""

    monkeypatch.setenv("PLANNING_AGENT_FAKE", "1")

    response = client.post(
        "/api/chat",
        json={
            "message": "9월에 A라인에서 1000개 생산 가능한가?",
            "conversation_id": "conv-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    types = [e["type"] for e in events]

    assert types[-1] == "done"
    assert {"text", "status", "tool_call", "tool_result"} <= set(types)

    tool_calls = [e["tool_name"] for e in events if e["type"] == "tool_call"]
    assert tool_calls == [
        "get_kpi",
        "execute_sql",
        "run_simulation",
        "prepare_table",
        "prepare_visualization",
    ]
    tool_call_ids = [e["tool_call_id"] for e in events if e["type"] == "tool_call"]
    assert len(tool_call_ids) == len(set(tool_call_ids)) == 5
    assert all(e["data"].get("args") is not None for e in events if e["type"] == "tool_call")
    assert {
        e["tool_call_id"] for e in events if e["type"] == "tool_result"
    } == set(tool_call_ids)

    table_call_index = next(
        index
        for index, event in enumerate(events)
        if event["type"] == "tool_call" and event.get("tool_name") == "prepare_table"
    )
    chart_call_index = next(
        index
        for index, event in enumerate(events)
        if event["type"] == "tool_call"
        and event.get("tool_name") == "prepare_visualization"
    )
    text_indexes = [
        index for index, event in enumerate(events) if event["type"] == "text"
    ]
    assert any(index < table_call_index for index in text_indexes)
    assert any(table_call_index < index < chart_call_index for index in text_indexes)
    assert any(chart_call_index < index for index in text_indexes)

    # 프론트가 catalog / database 두 kind 를 모두 받아본다.
    kinds = [
        e["data"].get("kind")
        for e in events
        if e["type"] == "tool_result" and isinstance(e.get("data"), dict)
    ]
    assert kinds[:2] == ["catalog", "database"]

    prepared = next(
        event["data"]
        for event in events
        if event.get("tool_name") == "prepare_visualization"
        and event["type"] == "tool_result"
    )
    assert prepared["status"] == "ok"
    visualization_id = prepared["visualization_id"]
    answer = "".join(event.get("content") or "" for event in events if event["type"] == "text")
    assert visualization_id not in answer
    assert "```chart" not in answer
    assert client.get(f"/api/visualizations/{visualization_id}").status_code == 200

    prepared_table = next(
        event["data"]
        for event in events
        if event.get("tool_name") == "prepare_table"
        and event["type"] == "tool_result"
    )
    assert prepared_table["status"] == "ok"
    assert prepared_table["displayed_count"] <= 100
    assert prepared_table["columns"] == ["part", "lot_count", "piece_count"]


def test_chat_endpoint_done_event_carries_turn_id(monkeypatch) -> None:
    """편집/재생성이 다음 요청의 `fork_from_turn_id` 로 돌려보낼 값."""

    monkeypatch.setenv("PLANNING_AGENT_FAKE", "1")

    response = client.post(
        "/api/chat",
        json={"message": "hi", "conversation_id": "conv-1"},
    )

    events = _parse_sse(response.text)
    done = events[-1]

    assert done["type"] == "done"
    assert isinstance(done["data"]["turn_id"], str)
    assert done["data"]["turn_id"]


def test_chat_endpoint_reports_error_gracefully(monkeypatch) -> None:
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
    scoped_client = TestClient(app)
    first = scoped_client.post("/api/chat", json={"message": "첫 요청"})
    second = scoped_client.post("/api/chat", json={"message": "다음 요청"})

    assert "HttpOnly" in first.headers["set-cookie"]
    assert "SameSite=lax" in first.headers["set-cookie"]
    assert "set-cookie" not in second.headers
    assert captured[0] == captured[1]


def test_visualization_api_scope_lifecycle_and_payload(tmp_path, monkeypatch) -> None:
    results = LocalParquetResultStore(tmp_path / "results")
    visualizations = LocalVisualizationStore(tmp_path / "visualizations")
    monkeypatch.setattr(result_store, "_store", results)
    monkeypatch.setattr(visualization_store, "_store", visualizations)
    source = results.save(
        ["work_month", "actual"],
        [["2026-08", 10], ["2026-09", 20]],
        source="execute_sql",
        conversation_id=None,
        access_scope="scope-a",
    )
    saved = prepare_visualization(
        VisualizationRequest(source.result_id, "line", "work_month", ("actual",)),
        access_scope="scope-a",
        result_store=results,
        visualization_store=visualizations,
    )

    scoped_client = TestClient(app)
    scoped_client.cookies.set("pp_session_scope", "scope-a")
    response = scoped_client.get(f"/api/visualizations/{saved.visualization_id}")

    assert response.status_code == 200
    assert response.json()["chart"]["categories"] == ["2026-08", "2026-09"]
    assert response.headers["cache-control"].startswith("private, max-age=")
    assert response.headers["vary"] == "Cookie"

    other_client = TestClient(app)
    other_client.cookies.set("pp_session_scope", "scope-b")
    hidden = other_client.get(f"/api/visualizations/{saved.visualization_id}")
    missing = other_client.get(f"/api/visualizations/{'f' * 32}")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()

    results.delete(source.result_id)
    gone = scoped_client.get(f"/api/visualizations/{saved.visualization_id}")
    assert gone.status_code == 410
    assert gone.json()["detail"]["code"] == "RESULT_UNAVAILABLE"


def test_chat_request_fork_from_turn_id_defaults_to_none() -> None:
    from api.schemas import ChatRequest

    request = ChatRequest(message="hi")
    assert request.fork_from_turn_id is None


def test_knowledge_skills_endpoint() -> None:
    response = client.get("/api/knowledge/skills")

    assert response.status_code == 200
    skills = response.json()
    assert {skill["name"] for skill in skills} == {
        "kpi-shortfall-analysis",
        "sql-analysis",
        "simulation",
    }
    assert all(set(skill) == {"name", "description", "status"} for skill in skills)
    assert all(skill["description"] for skill in skills)


def test_knowledge_catalog_endpoint() -> None:
    response = client.get("/api/knowledge/catalog")

    assert response.status_code == 200
    tables = response.json()
    assert len(tables) == 11
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
    }
    assert set(tables[0]) == {"table", "description", "grain", "tags", "verified"}


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
