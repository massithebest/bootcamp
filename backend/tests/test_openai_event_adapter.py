"""OpenAIEventAdapter: OpenAI Agents SDK 스트림 -> AgentEvent 변환과 실행부 선택.

같은 시나리오를 Claude 어댑터와 OpenAI 실행부에 넣어 같은 `AgentEvent` 목록이 나오는지
비교한다. OpenAI 쪽은 가짜 게이트웨이로 실제 SDK 스트림 이벤트를 만든다.
"""

import asyncio
import json

import pytest
from agents import Agent, MessageOutputItem, RawResponsesStreamEvent, RunItemStreamEvent, ToolCallItem, ToolCallOutputItem
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

import agent.agent as agent_module
from agent.event_adapter import AgentEventAdapter
from agent.openai_event_adapter import VISIBLE_TOOL_NAMES, OpenAIEventAdapter
from agent.openai_runtime import run_openai_agent
from agent.tool_events import TOOL_FAILURE_PAYLOAD
from core import config
from tests.openai_fakes import DEPLOYMENT, FakeGateway, text_turn, tool_turn


SQL_ARGS = {"sql": "SELECT 1", "purpose": "공장별 합계"}
SQL_PAYLOAD = {"status": "ok", "kind": "database", "result_id": "a" * 32, "row_count": 3}
QUESTIONS = ["2026년 6월 공장별 계획수량도 보여주세요.", "FAC002의 제품별 계획수량을 보여주세요."]
_AGENT = Agent(name="test")


@pytest.fixture(autouse=True)
def _gateway_config(monkeypatch):
    monkeypatch.setattr(config, "AZURE_OPENAI_DEPLOYMENT", DEPLOYMENT)
    monkeypatch.setattr(config, "AZURE_OPENAI_MAX_TOKENS", None)


def _collect(stream) -> list:
    async def go():
        return [event async for event in stream]

    return asyncio.run(go())


def _claude_events() -> tuple[list, list[str] | None]:
    adapter = AgentEventAdapter()
    raw = [
        StreamEvent(uuid="u0", session_id="s", event={"type": "message_start", "message": {"id": "m1"}}),
        StreamEvent(uuid="u1", session_id="s", event={
            "type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "조회하겠습니다."},
        }),
        AssistantMessage(content=[ToolUseBlock(id="call_skill", name="Skill", input={"skill": "sql-analysis"})], model="x"),
        UserMessage(content=[ToolResultBlock(tool_use_id="call_skill", content="절차")]),
        AssistantMessage(
            content=[
                TextBlock(text="조회하겠습니다."),
                ToolUseBlock(id="call_sql", name="mcp__planning__execute_sql", input=SQL_ARGS),
            ],
            model="x",
            message_id="m1",
        ),
        UserMessage(content=[ToolResultBlock(
            tool_use_id="call_sql",
            content=[{"type": "text", "text": json.dumps(SQL_PAYLOAD, ensure_ascii=False)}],
        )]),
        AssistantMessage(content=[ToolUseBlock(
            id="call_next", name="mcp__planning__suggest_follow_ups", input={"questions": QUESTIONS},
        )], model="x"),
        UserMessage(content=[ToolResultBlock(tool_use_id="call_next", content='{"status": "ok"}')]),
        AssistantMessage(content=[TextBlock(text="FAC002가 가장 큽니다.")], model="x"),
        ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=4, session_id="s"),
    ]
    events = [event for item in raw for event in adapter.convert(item)]
    return events, adapter.suggestions


def test_both_adapters_emit_the_same_events_for_the_same_scenario(monkeypatch) -> None:
    async def fake_execute_sql(**_kwargs) -> dict:
        return SQL_PAYLOAD

    monkeypatch.setattr("agent.tool_specs.execute_sql", fake_execute_sql)
    gateway = FakeGateway(
        tool_turn("load_skill", {"name": "sql-analysis"}, "call_skill"),
        tool_turn("execute_sql", SQL_ARGS, "call_sql", text="조회하겠습니다."),
        tool_turn("suggest_follow_ups", {"questions": QUESTIONS}, "call_next"),
        text_turn("FAC002가 가장 큽니다."),
    )

    openai_events = _collect(run_openai_agent("공장별 합계", access_scope="scope", model=gateway.model()))
    claude_events, claude_suggestions = _claude_events()

    *body, done = openai_events
    assert [e.model_dump() for e in body] == [e.model_dump() for e in claude_events]
    assert [e.type for e in body] == ["text", "tool_call", "status", "tool_result", "status", "text"]
    assert body[1].data == {"args": SQL_ARGS} and body[3].data == SQL_PAYLOAD
    assert done.type == "done" and done.data["suggestions"] == claude_suggestions == QUESTIONS
    assert isinstance(done.data["turn_id"], str) and done.data["turn_id"]


def _tool_call(name: str, call_id: str, arguments: str) -> RunItemStreamEvent:
    raw = ResponseFunctionToolCall(arguments=arguments, call_id=call_id, name=name, type="function_call")
    return RunItemStreamEvent(name="tool_called", item=ToolCallItem(agent=_AGENT, raw_item=raw))


def _tool_output(call_id: str, output: str) -> RunItemStreamEvent:
    raw = {"call_id": call_id, "output": output, "type": "function_call_output"}
    return RunItemStreamEvent(name="tool_output", item=ToolCallOutputItem(agent=_AGENT, raw_item=raw, output=output))


def _message(text: str) -> RunItemStreamEvent:
    raw = ResponseOutputMessage(
        id="msg", role="assistant", status="completed", type="message",
        content=[ResponseOutputText(text=text, annotations=[], type="output_text")],
    )
    return RunItemStreamEvent(name="message_output_created", item=MessageOutputItem(agent=_AGENT, raw_item=raw))


class _RawEvent:
    def __init__(self, type_: str, delta: str) -> None:
        self.type, self.delta = type_, delta


def test_message_text_is_sent_only_when_it_was_not_streamed() -> None:
    adapter = OpenAIEventAdapter()

    streamed = adapter.convert(RawResponsesStreamEvent(data=_RawEvent("response.output_text.delta", "안녕")))
    duplicate = adapter.convert(_message("안녕"))
    unstreamed = adapter.convert(_message("두 번째"))

    assert [e.content for e in streamed] == ["안녕"]
    assert duplicate == []
    assert [(e.type, e.content) for e in unstreamed] == [("text", "두 번째")]


def test_reasoning_deltas_and_hidden_tools_are_not_emitted() -> None:
    adapter = OpenAIEventAdapter()

    events = [
        *adapter.convert(RawResponsesStreamEvent(data=_RawEvent("response.reasoning_text.delta", "내부 추론"))),
        *adapter.convert(_tool_call("load_skill", "c1", '{"name": "simulation"}')),
        *adapter.convert(_tool_output("c1", "# 절차")),
        *adapter.convert(_tool_call("suggest_follow_ups", "c2", json.dumps({"questions": ["하나"]}))),
        *adapter.convert(_tool_output("unknown", "{}")),
    ]

    assert events == []
    assert adapter.suggestions is None  # 2~4개 규칙에 맞지 않아 버린다.
    assert VISIBLE_TOOL_NAMES.isdisjoint({"load_skill", "suggest_follow_ups"})


def test_tool_failures_and_bad_arguments_keep_the_public_contract() -> None:
    adapter = OpenAIEventAdapter()

    call = adapter.convert(_tool_call("describe_table", "c1", "not json"))
    result = adapter.convert(_tool_output("c1", json.dumps(TOOL_FAILURE_PAYLOAD, ensure_ascii=False)))

    assert call[0].data == {"args": {}}
    assert result[0].data == TOOL_FAILURE_PAYLOAD
    assert result[1].data == {"step": "c1", "status": "error", "label": "describe_table 실패"}


def test_run_agent_dispatches_to_the_openai_runtime(monkeypatch) -> None:
    calls: list = []

    async def fake_run_openai_agent(*args):
        calls.append(args)
        yield agent_module.AgentEvent(type="done", data={"turn_id": "t"})

    def fail_query(**_kwargs):
        raise AssertionError("Claude 실행부를 호출하면 안 된다")

    monkeypatch.setattr(config, "AGENT_RUNTIME", "openai")
    monkeypatch.setattr("agent.openai_runtime.run_openai_agent", fake_run_openai_agent)
    monkeypatch.setattr(agent_module, "query", fail_query)

    events = _collect(agent_module.run_agent("질문", "conv", None, "scope"))

    assert calls == [("질문", "conv", None, "scope")]
    assert [e.type for e in events] == ["done"]
