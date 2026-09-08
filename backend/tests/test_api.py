"""API Endpoint 검증."""

import json

from fastapi.testclient import TestClient

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
    assert "query_database" in tool_calls


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
