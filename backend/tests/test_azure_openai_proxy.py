"""LLM_PROVIDER=azure_openai: Anthropic ↔ Azure OpenAI 변환과 /anthropic 프록시 경로."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app
from services.llm import azure_openai_proxy as proxy

TOKEN = "test-proxy-token"
KEY = "atl-secret-key-should-not-leak"


@pytest.fixture()
def azure(monkeypatch):
    monkeypatch.setattr("core.config.LLM_PROVIDER", "azure_openai")
    monkeypatch.setattr("core.config.LOCAL_PROXY_TOKEN", TOKEN)
    monkeypatch.setattr("core.config.AZURE_OPENAI_ENDPOINT", "https://gateway.test")
    monkeypatch.setattr("core.config.AZURE_OPENAI_API_KEY", KEY)
    monkeypatch.setattr("core.config.AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setattr("core.config.AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    monkeypatch.setattr("core.config.AZURE_OPENAI_MAX_TOKENS", None)


def _gateway(monkeypatch, handler):
    """게이트웨이 HTTP 를 가짜 transport 로 바꾸고, 받은 요청을 기록한다."""

    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    real = httpx.AsyncClient
    monkeypatch.setattr(proxy.httpx, "AsyncClient",
                        lambda **kwargs: real(transport=httpx.MockTransport(record), **kwargs))
    return seen


# ---- 요청 변환 ------------------------------------------------------------


def test_request_conversion_covers_system_tools_and_tool_round_trip(azure) -> None:
    body = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 32000,
        "system": [{"type": "text", "text": "역할 지침", "cache_control": {"type": "ephemeral"}}],
        "thinking": {"type": "enabled", "budget_tokens": 1000},
        "tools": [{"name": "mcp__planning__execute_sql", "description": "SQL", "input_schema": {"type": "object"}},
                  {"type": "web_search_20250305", "name": "web_search"}],
        "tool_choice": {"type": "any"},
        "messages": [
            {"role": "user", "content": "6월 계획은?"},
            {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "비공개"},
                {"type": "text", "text": "조회합니다."},
                {"type": "tool_use", "id": "toolu_1", "name": "mcp__planning__execute_sql", "input": {"sql": "SELECT 1"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_1", "content": [{"type": "text", "text": "139953"}]},
                {"type": "text", "text": "표로도 보여줘"},
            ]},
        ],
    }
    request = proxy.to_openai_request(body)

    assert [m["role"] for m in request["messages"]] == ["system", "user", "assistant", "tool", "user"]
    assert request["messages"][0]["content"] == "역할 지침"
    assistant = request["messages"][2]
    assert assistant["content"] == "조회합니다."
    assert assistant["tool_calls"][0]["function"] == {"name": "mcp__planning__execute_sql", "arguments": '{"sql": "SELECT 1"}'}
    assert request["messages"][3] == {"role": "tool", "tool_call_id": "toolu_1", "content": "139953"}
    assert [t["function"]["name"] for t in request["tools"]] == ["mcp__planning__execute_sql"]
    assert request["tool_choice"] == "required"
    assert request["max_completion_tokens"] == 32000
    assert "thinking" not in json.dumps(request)
    assert proxy.resolve_deployment(body["model"]) == "gpt-4.1"
    assert proxy.resolve_deployment("gpt-5-mini") == "gpt-5-mini"


def test_tool_error_is_marked_and_max_tokens_is_capped(azure, monkeypatch) -> None:
    monkeypatch.setattr("core.config.AZURE_OPENAI_MAX_TOKENS", 16384)
    request = proxy.to_openai_request({"max_tokens": 32000, "messages": [{"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": "boom"}]}]})

    assert request["messages"] == [{"role": "tool", "tool_call_id": "t", "content": "[tool error] boom"}]
    assert request["max_completion_tokens"] == 16384


# ---- 응답 변환 ------------------------------------------------------------


def test_response_conversion_maps_tool_calls_stop_reason_and_usage() -> None:
    message = proxy.to_anthropic_message({
        "id": "chatcmpl-1",
        "choices": [{"finish_reason": "tool_calls", "message": {"content": "확인합니다", "tool_calls": [
            {"id": "call_1", "function": {"name": "describe_table", "arguments": '{"table": "FP_TARGET"}'}}]}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }, "gpt-4.1")

    assert message["content"] == [
        {"type": "text", "text": "확인합니다"},
        {"type": "tool_use", "id": "call_1", "name": "describe_table", "input": {"table": "FP_TARGET"}},
    ]
    assert message["stop_reason"] == "tool_use"
    assert message["usage"] == {"input_tokens": 10, "output_tokens": 5}


def _events(raw: list[str]) -> list[dict]:
    return [json.loads(chunk.split("data: ", 1)[1]) for chunk in raw]


def test_stream_translator_emits_text_then_tool_blocks() -> None:
    translator = proxy.StreamTranslator("gpt-4.1")
    raw = []
    for chunk in [
        {"choices": [{"delta": {"content": "조회"}}]},
        {"choices": [{"delta": {"content": "합니다"}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "execute_sql", "arguments": ""}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"sql":'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ' "SELECT 1"}'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 3}},
    ]:
        raw += translator.feed(chunk)
    raw += translator.finish()
    events = _events(raw)

    assert [e["type"] for e in events] == [
        "message_start", "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "message_delta", "message_stop",
    ]
    assert events[5]["content_block"] == {"type": "tool_use", "id": "call_1", "name": "execute_sql", "input": {}}
    assert "".join(e["delta"]["partial_json"] for e in events[6:8]) == '{"sql": "SELECT 1"}'
    assert events[9]["delta"]["stop_reason"] == "tool_use"
    assert events[9]["usage"]["output_tokens"] == 3


# ---- /anthropic 경로 ------------------------------------------------------


def test_proxy_requires_the_process_token(azure) -> None:
    client = TestClient(app)
    body = {"model": "gpt-4.1", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}

    assert client.post("/anthropic/v1/messages", json=body).status_code == 401
    assert client.post("/anthropic/v1/messages", json=body, headers={"x-api-key": "wrong"}).status_code == 401
    assert client.get("/anthropic/v1/models", headers={"x-api-key": TOKEN}).status_code == 404


def test_non_stream_message_round_trip(azure, monkeypatch) -> None:
    seen = _gateway(monkeypatch, lambda request: httpx.Response(200, json={
        "id": "c1", "choices": [{"finish_reason": "stop", "message": {"content": "안녕하세요"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2}}))
    client = TestClient(app)

    response = client.post("/anthropic/v1/messages", headers={"authorization": f"Bearer {TOKEN}"},
                           json={"model": "claude-haiku-4-5", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]})

    assert response.status_code == 200
    assert response.json()["content"] == [{"type": "text", "text": "안녕하세요"}]
    assert str(seen[0].url) == "https://gateway.test/openai/deployments/gpt-4.1/chat/completions?api-version=2024-12-01-preview"
    assert seen[0].headers["api-key"] == KEY


def test_stream_message_round_trip(azure, monkeypatch) -> None:
    lines = [
        'data: {"choices":[{"delta":{"content":"안녕"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        'data: {"choices":[],"usage":{"prompt_tokens":4,"completion_tokens":1}}',
        "data: [DONE]",
    ]
    seen = _gateway(monkeypatch, lambda request: httpx.Response(
        200, content="\n\n".join(lines).encode(), headers={"content-type": "text/event-stream"}))
    client = TestClient(app)

    response = client.post("/anthropic/v1/messages", headers={"x-api-key": TOKEN},
                           json={"model": "gpt-5-mini", "max_tokens": 10, "stream": True,
                                 "messages": [{"role": "user", "content": "hi"}]})

    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events][0] == "message_start" and events[-1]["type"] == "message_stop"
    assert any(e.get("delta", {}).get("text") == "안녕" for e in events)
    payload = json.loads(seen[0].content)
    assert payload["stream"] is True and payload["stream_options"] == {"include_usage": True}
    assert "/deployments/gpt-5-mini/" in str(seen[0].url)


def test_gateway_error_is_returned_without_leaking_the_key(azure, monkeypatch) -> None:
    _gateway(monkeypatch, lambda request: httpx.Response(400, json={"error": {"message": "unsupported parameter"}}))
    client = TestClient(app)

    response = client.post("/anthropic/v1/messages", headers={"x-api-key": TOKEN},
                           json={"model": "gpt-4.1", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]})

    assert response.status_code == 400
    assert response.json()["type"] == "error"
    assert "unsupported parameter" in response.json()["error"]["message"]
    assert KEY not in response.text


def test_count_tokens_returns_an_estimate(azure) -> None:
    client = TestClient(app)
    response = client.post("/anthropic/v1/messages/count_tokens", headers={"x-api-key": TOKEN},
                           json={"model": "gpt-4.1", "messages": [{"role": "user", "content": "안녕하세요" * 10}]})

    assert response.status_code == 200 and response.json()["input_tokens"] > 0


def test_cli_env_points_at_the_backend_proxy_with_process_token(azure) -> None:
    from core.config import agent_provider_env

    env = agent_provider_env()
    assert env["ANTHROPIC_BASE_URL"].endswith("/anthropic")
    assert env["ANTHROPIC_AUTH_TOKEN"] == TOKEN
    assert env["ANTHROPIC_API_KEY"] == ""
