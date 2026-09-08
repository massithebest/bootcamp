"""AgentEventAdapter: SDK 이벤트 -> AgentEvent 변환 검증."""

import json

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from agent.event_adapter import AgentEventAdapter


def test_text_block_becomes_text_event() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        AssistantMessage(content=[TextBlock(text="생산 실적 확인 결과 ")], model="x")
    )

    assert [e.type for e in events] == ["text"]
    assert events[0].content == "생산 실적 확인 결과 "


def test_thinking_block_is_not_exposed() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        AssistantMessage(
            content=[ThinkingBlock(thinking="내부 추론", signature="s")],
            model="x",
        )
    )

    assert events == []


def test_tool_use_emits_tool_call_and_status_with_short_name() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        AssistantMessage(
            content=[
                ToolUseBlock(
                    id="t1",
                    name="mcp__planning__query_database",
                    input={"question": "9월 A라인"},
                )
            ],
            model="x",
        )
    )

    assert [e.type for e in events] == ["tool_call", "status"]
    assert events[0].tool_name == "query_database"
    assert events[1].data["status"] == "running"


def test_builtin_tool_is_filtered_out() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        AssistantMessage(
            content=[ToolUseBlock(id="s1", name="Skill", input={})],
            model="x",
        )
    )
    assert events == []

    result_events = adapter.convert(
        UserMessage(
            content=[ToolResultBlock(tool_use_id="s1", content="done")]
        )
    )
    assert result_events == []


def test_tool_result_name_resolved_from_prior_tool_use() -> None:
    adapter = AgentEventAdapter()
    adapter.convert(
        AssistantMessage(
            content=[
                ToolUseBlock(
                    id="t1",
                    name="mcp__planning__query_database",
                    input={},
                )
            ],
            model="x",
        )
    )

    payload = {"status": "ok", "rows": [{"line": "A"}]}
    events = adapter.convert(
        UserMessage(
            content=[
                ToolResultBlock(
                    tool_use_id="t1",
                    content=[
                        {"type": "text", "text": json.dumps(payload)}
                    ],
                )
            ]
        )
    )

    assert [e.type for e in events] == ["tool_result", "status"]
    assert events[0].tool_name == "query_database"
    assert events[0].data == payload
    assert events[1].data["status"] == "completed"


def test_result_message_error_becomes_error_event_and_tracks_session() -> None:
    adapter = AgentEventAdapter()
    events = adapter.convert(
        ResultMessage(
            subtype="error",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="sess-123",
        )
    )

    assert [e.type for e in events] == ["error"]
    assert adapter.session_id == "sess-123"
