"""OpenAI Agents SDK 실행부: 지침 조합·Tool 등록·모델 연결·트레이싱·max_turns.

실제 `AsyncAzureOpenAI` 클라이언트를 가짜 HTTP transport 에 연결해, 게이트웨이가
돌려줄 Chat Completions 스트리밍(SSE) 응답을 턴마다 재생한다. 모델 품질이 아니라
"어떤 요청을 보냈고 Tool 결과를 어떻게 이어 붙였는가"를 검증한다.
"""

import asyncio
import json
from typing import Any

import httpx2
import pytest
from agents import MaxTurnsExceeded
from agents.tracing import trace
from agents.tracing.traces import NoOpTrace
from openai import AsyncAzureOpenAI

from agent import openai_runtime
from agent.skills import get_skill, list_skills
from agent.system_prompt import SYSTEM_PROMPT
from agent.tool_specs import tool_specs
from core import config


DEPLOYMENT = "test-deployment"


def _chunk(delta: dict | None = None, finish: str | None = None, usage: dict | None = None) -> dict:
    choices = [] if delta is None else [{"index": 0, "delta": delta, "finish_reason": finish}]
    chunk: dict[str, Any] = {
        "id": "chatcmpl-test", "object": "chat.completion.chunk", "created": 0,
        "model": DEPLOYMENT, "choices": choices,
    }
    if usage:
        chunk["usage"] = usage
    return chunk


_USAGE = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}


def text_turn(*pieces: str) -> list[dict]:
    chunks = [_chunk({"role": "assistant", "content": ""})]
    chunks += [_chunk({"content": piece}) for piece in pieces]
    return chunks + [_chunk({}, "stop"), _chunk(usage=_USAGE)]


def tool_turn(name: str, args: dict, call_id: str = "call_1") -> list[dict]:
    call = {
        "index": 0, "id": call_id, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
    }
    return [
        _chunk({"role": "assistant", "tool_calls": [call]}),
        _chunk({}, "tool_calls"),
        _chunk(usage=_USAGE),
    ]


class FakeGateway:
    """턴마다 준비한 SSE 응답을 순서대로 돌려주고 받은 요청을 기록한다."""

    def __init__(self, *turns: list[dict]) -> None:
        self.turns = list(turns)
        self.requests: list[httpx2.Request] = []
        self.bodies: list[dict] = []

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        self.bodies.append(json.loads(request.content))
        chunks = self.turns.pop(0)
        body = "".join(f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks) + "data: [DONE]\n\n"
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())

    def model(self):
        client = AsyncAzureOpenAI(
            azure_endpoint="https://gateway.test",
            api_key="test-key",
            api_version="2024-12-01-preview",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(self.handler)),
            max_retries=0,
        )
        return openai_runtime.build_model(client)


@pytest.fixture(autouse=True)
def _gateway_config(monkeypatch):
    monkeypatch.setattr(config, "AZURE_OPENAI_DEPLOYMENT", DEPLOYMENT)
    monkeypatch.setattr(config, "AZURE_OPENAI_MAX_TOKENS", None)


def _run(gateway: FakeGateway, input_items: Any, access_scope: str | None = "scope-a"):
    async def go():
        result = openai_runtime.run_streamed(input_items, access_scope=access_scope, model=gateway.model())
        async for _ in result.stream_events():
            pass
        return result

    return asyncio.run(go())


def _tool_messages(body: dict) -> list[dict]:
    return [m for m in body["messages"] if m.get("role") == "tool"]


def test_tracing_is_disabled_on_import() -> None:
    assert isinstance(trace("probe"), NoOpTrace)


def test_instructions_combine_system_prompt_runtime_guide_and_skill_index() -> None:
    instructions = openai_runtime.build_instructions()

    assert instructions.startswith(SYSTEM_PROMPT.strip())
    assert openai_runtime.INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip() in instructions
    assert "load_skill(name)" in instructions
    for skill in list_skills():
        assert f"`{skill.name}`: {skill.description}" in instructions


def test_hidden_tools_are_skill_loading_and_follow_ups() -> None:
    assert openai_runtime.HIDDEN_TOOL_NAMES == {"load_skill", "suggest_follow_ups"}


def test_text_turn_calls_the_gateway_deployment_with_runtime_settings() -> None:
    gateway = FakeGateway(text_turn("안녕", "하세요."))

    result = _run(gateway, "안녕?")

    assert result.final_output == "안녕하세요."
    request, body = gateway.requests[0], gateway.bodies[0]
    assert request.url.path == f"/openai/deployments/{DEPLOYMENT}/chat/completions"
    assert request.headers["api-key"] == "test-key"
    assert body["model"] == DEPLOYMENT and body["stream"] is True
    assert body["stream_options"] == {"include_usage": True}
    assert body["parallel_tool_calls"] is False
    assert "temperature" not in body and "max_tokens" not in body
    assert body["messages"][0]["content"] == openai_runtime.build_instructions()
    assert body["messages"][-1] == {"role": "user", "content": "안녕?"}
    assert [t["function"]["name"] for t in body["tools"]] == [
        *(spec.name for spec in tool_specs()), "load_skill"
    ]
    assert result.context_wrapper.usage.input_tokens == 100


def test_tool_results_and_follow_ups_flow_back_to_the_model(monkeypatch) -> None:
    seen: dict = {}

    async def fake_execute_sql(*, sql: str, purpose: str, access_scope: str | None) -> dict:
        seen.update(sql=sql, purpose=purpose, access_scope=access_scope)
        return {"status": "success", "result_id": "a" * 32, "row_count": 3}

    monkeypatch.setattr("agent.tool_specs.execute_sql", fake_execute_sql)
    questions = ["2026년 6월 공장별 계획수량도 보여주세요.", "FAC002의 제품별 계획수량을 보여주세요."]
    gateway = FakeGateway(
        tool_turn("execute_sql", {"sql": "SELECT 1", "purpose": "공장별 합계"}, "call_sql"),
        tool_turn("suggest_follow_ups", {"questions": questions}, "call_next"),
        text_turn("FAC002가 가장 큽니다."),
    )

    result = _run(gateway, "공장별 계획수량 합계", access_scope="scope-x")

    assert result.final_output == "FAC002가 가장 큽니다."
    assert seen == {"sql": "SELECT 1", "purpose": "공장별 합계", "access_scope": "scope-x"}
    sql_output = _tool_messages(gateway.bodies[1])[0]
    assert sql_output["tool_call_id"] == "call_sql"
    assert json.loads(sql_output["content"]) == {"status": "success", "result_id": "a" * 32, "row_count": 3}
    follow_up = _tool_messages(gateway.bodies[2])[-1]
    assert follow_up["tool_call_id"] == "call_next"
    assert json.loads(follow_up["content"]).get("status") != "error"
    assert len(gateway.bodies) == 3


def test_load_skill_returns_the_skill_body_without_frontmatter() -> None:
    gateway = FakeGateway(tool_turn("load_skill", {"name": "sql-analysis"}), text_turn("절차를 읽었습니다."))

    _run(gateway, "DB에서 조회해 주세요.")

    content = _tool_messages(gateway.bodies[1])[0]["content"]
    assert content == get_skill("sql-analysis").content
    assert not content.startswith("---")


def test_unknown_skill_and_bad_arguments_return_safe_errors() -> None:
    load_skill = openai_runtime._load_skill_tool()
    unknown = json.loads(asyncio.run(load_skill.on_invoke_tool(None, '{"name": "../CLAUDE"}')))
    assert unknown["status"] == "error" and "sql-analysis" in unknown["message"]

    spec = next(s for s in tool_specs() if s.name == "execute_sql")
    execute_sql = openai_runtime._function_tool(spec, "scope-a")
    not_json = json.loads(asyncio.run(execute_sql.on_invoke_tool(None, "SELECT")))
    missing = json.loads(asyncio.run(execute_sql.on_invoke_tool(None, "{}")))
    assert not_json == {"status": "error", "message": "Tool 인자를 JSON 객체로 읽을 수 없습니다."}
    assert missing == {"status": "error", "message": "필수 인자가 없습니다: sql"}


def test_max_turns_comes_from_config(monkeypatch) -> None:
    monkeypatch.setattr(config, "AGENT_MAX_TURNS", 1)
    gateway = FakeGateway(tool_turn("list_simulation", {}), text_turn("끝"))

    with pytest.raises(MaxTurnsExceeded):
        _run(gateway, "시뮬레이션 종류")
    assert len(gateway.bodies) == 1


def test_max_completion_tokens_cap_uses_the_reasoning_model_parameter(monkeypatch) -> None:
    monkeypatch.setattr(config, "AZURE_OPENAI_MAX_TOKENS", 2048)
    gateway = FakeGateway(text_turn("짧게"))

    _run(gateway, "요약")

    assert gateway.bodies[0]["max_completion_tokens"] == 2048
    assert "max_tokens" not in gateway.bodies[0]


@pytest.mark.parametrize("name", ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"])
def test_build_model_requires_gateway_settings(monkeypatch, name: str) -> None:
    monkeypatch.setattr(config, "AZURE_OPENAI_ENDPOINT", "https://gateway.test")
    monkeypatch.setattr(config, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(config, name, "")

    with pytest.raises(RuntimeError, match=name):
        openai_runtime.build_model()
