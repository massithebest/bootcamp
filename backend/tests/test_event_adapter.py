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


def test_last_entry_uuid_tracks_most_recent_assistant_or_user_message() -> None:
    """편집/재생성의 포크 지점(resume_session_at) — 마지막으로 본 entry 의 uuid.

    AssistantMessage/UserMessage 만 대상이다. ResultMessage 는 uuid 필드가
    있어도 실제 Transcript(JSONL)에는 적히지 않는 프로토콜 프레임이라
    `resume_session_at` 후보에서 제외한다 — 포함시키면 실제 Claude CLI 가
    "No message found with message.uuid of: ..." 로 거부한다(직접 재현 확인).
    """

    adapter = AgentEventAdapter()
    assert adapter.last_entry_uuid is None

    adapter.convert(
        AssistantMessage(content=[TextBlock(text="진행 중")], model="x", uuid="a-1")
    )
    assert adapter.last_entry_uuid == "a-1"

    adapter.convert(
        UserMessage(
            content=[ToolResultBlock(tool_use_id="t1", content="ok")],
            uuid="u-1",
        )
    )
    assert adapter.last_entry_uuid == "u-1"

    # ResultMessage 는 last_entry_uuid 를 갱신하지 않는다 — 마지막 값은
    # 여전히 방금 본 UserMessage("u-1") 여야 한다.
    adapter.convert(
        ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="sess-123",
            uuid="r-1",
        )
    )
    assert adapter.last_entry_uuid == "u-1"


def test_last_entry_uuid_stays_none_when_sdk_events_omit_it() -> None:
    """uuid 를 안 채운(테스트 더블 등) 이벤트는 조용히 무시한다."""

    adapter = AgentEventAdapter()
    adapter.convert(AssistantMessage(content=[TextBlock(text="x")], model="x"))

    assert adapter.last_entry_uuid is None


def _tool_result_events(payload, *, sdk_error=False):
    adapter = AgentEventAdapter()
    adapter.convert(AssistantMessage(content=[ToolUseBlock(
        id="t1", name="mcp__planning__execute_sql", input={}
    )], model="x"))
    return adapter.convert(UserMessage(content=[ToolResultBlock(
        tool_use_id="t1", content=json.dumps(payload), is_error=sdk_error
    )]))


def test_business_error_marks_progress_as_error():
    payload = {"status": "error", "message": "조회할 수 없습니다."}
    events = _tool_result_events(payload)
    assert events[0].data == payload
    assert events[1].data["status"] == "error"
    assert "실패" in events[1].data["label"]


def test_sdk_tool_error_does_not_expose_internal_content():
    events = _tool_result_events({"text": "private-path-placeholder"}, sdk_error=True)
    assert events[0].data["status"] == "error"
    assert "private-path-placeholder" not in events[0].model_dump_json()
    assert events[1].data["status"] == "error"
