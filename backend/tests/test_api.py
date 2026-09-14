"""API Endpoint 검증."""

import json

from fastapi.testclient import TestClient

from api.schemas import AgentEvent
from main import app


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
    assert tool_calls == ["get_kpi", "execute_sql", "run_simulation"]

    # 프론트가 catalog / database 두 kind 를 모두 받아본다.
    kinds = [
        e["data"].get("kind")
        for e in events
        if e["type"] == "tool_result" and isinstance(e.get("data"), dict)
    ]
    assert kinds[:2] == ["catalog", "database"]


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

    async def fake_run_agent(*, message, conversation_id, fork_from_turn_id):
        captured["fork_from_turn_id"] = fork_from_turn_id
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
    assert len(tables) == 6
    assert set(tables[0]) == {"table", "description", "grain", "tags", "verified"}


def test_knowledge_kpis_endpoint() -> None:
    response = client.get("/api/knowledge/kpis")

    assert response.status_code == 200
    kpis = response.json()
    assert [kpi["kpi_id"] for kpi in kpis] == ["fgs_inbound"]
    assert set(kpis[0]) == {"kpi_id", "name", "aliases", "verified"}
