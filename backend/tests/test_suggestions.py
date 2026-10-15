"""후속질문: 검증 규칙, Tool trace 비노출, 성공한 done 에만 전달."""

import asyncio
from collections.abc import AsyncIterator

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

import agent.agent as agent_module
from agent import session_store
from agent.agent import run_agent
from agent.event_adapter import AgentEventAdapter
from agent.sdk_tools import tool_catalog
from api.schemas import AgentEvent
from tools.suggestion_tool import normalize_suggestions, suggest_follow_ups

TOOL = "mcp__planning__suggest_follow_ups"
QUESTIONS = ["GB1 영업배치별 달성률도 보여주세요.", "5월과 비교하면 어떤가요?"]


@pytest.fixture(autouse=True)
def _clear_store():
    session_store.clear()
    yield
    session_store.clear()


def test_normalize_trims_and_dedupes() -> None:
    assert normalize_suggestions(["  A라인 실적은?  ", "A라인 실적은?", "B라인 실적은?"]) == [
        "A라인 실적은?",
        "B라인 실적은?",
    ]


@pytest.mark.parametrize(
    "value",
    [
        None,
        "질문",
        ["하나뿐인 질문인가요?"],
        ["같은 질문?", " 같은 질문? "],
        ["첫째 질문?", "둘째 질문?", "셋째 질문?", "넷째 질문?", "다섯째 질문?"],
        ["정상 질문?", ""],
        ["정상 질문?", "가" * 121],
        ["정상 질문?", 3],
        ["정상 질문?", "Show me more?"],
    ],
)
def test_normalize_rejects_invalid_shapes(value) -> None:
    assert normalize_suggestions(value) is None


def test_tool_reports_error_without_raising() -> None:
    assert asyncio.run(suggest_follow_ups(QUESTIONS)) == {"status": "ok", "count": 2}
    assert asyncio.run(suggest_follow_ups(["하나"]))["code"] == "INVALID_SUGGESTIONS"


def test_adapter_hides_suggestion_tool_and_keeps_last_valid_call() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        AssistantMessage(
            content=[
                ToolUseBlock(id="s1", name=TOOL, input={"questions": QUESTIONS}),
                ToolUseBlock(id="s2", name=TOOL, input={"questions": ["잘못된 하나"]}),
            ],
            model="x",
        )
    )
    events += adapter.convert(
        UserMessage(content=[ToolResultBlock(tool_use_id="s1", content='{"status": "ok"}')])
    )

    assert events == []
    assert adapter.suggestions == QUESTIONS


def test_catalog_describes_suggestion_tool() -> None:
    catalog = {item["name"]: item for item in asyncio.run(tool_catalog())}
    schema = catalog["suggest_follow_ups"]["input_schema"]
    assert schema["properties"]["questions"]["maxItems"] == 4


def _fake_query(questions: object, *, is_error: bool = False):
    async def fake_query(*, prompt, options) -> AsyncIterator[object]:
        yield AssistantMessage(
            content=[ToolUseBlock(id="s1", name=TOOL, input={"questions": questions})],
            model="x",
            uuid="a-1",
        )
        yield AssistantMessage(content=[TextBlock(text="응답")], model="x", uuid="a-2")
        yield ResultMessage(
            subtype="error" if is_error else "success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=is_error,
            num_turns=1,
            session_id="sess-1",
        )

    return fake_query


async def _collect(agen: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    return [event async for event in agen]


def test_successful_done_carries_suggestions(monkeypatch) -> None:
    monkeypatch.setattr(agent_module, "query", _fake_query(QUESTIONS))
    events = asyncio.run(_collect(run_agent("질문", conversation_id="conv-1")))

    assert [e.type for e in events] == ["text", "done"]
    assert events[-1].data["suggestions"] == QUESTIONS
    assert events[-1].data["turn_id"]


def test_invalid_suggestions_are_omitted_without_failing(monkeypatch) -> None:
    monkeypatch.setattr(agent_module, "query", _fake_query(["하나뿐"]))
    events = asyncio.run(_collect(run_agent("질문", conversation_id="conv-1")))

    assert [e.type for e in events] == ["text", "done"]
    assert "suggestions" not in events[-1].data


def test_failed_turn_does_not_carry_suggestions(monkeypatch) -> None:
    monkeypatch.setattr(agent_module, "query", _fake_query(QUESTIONS, is_error=True))
    events = asyncio.run(_collect(run_agent("질문", conversation_id="conv-1")))

    assert [e.type for e in events][-2:] == ["error", "done"]
    assert events[-1].data is None
