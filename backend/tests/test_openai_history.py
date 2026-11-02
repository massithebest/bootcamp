"""OpenAI 실행부의 대화 기록과 편집/재생성 분기.

가짜 게이트웨이가 받은 요청의 messages 로 "어떤 기록에 이어 실행했는가"를 확인한다.
"""

import asyncio

import pytest
from agents import MaxTurnsExceeded

from agent import openai_session_store as session_store
from agent.agent import _resolve_resume
from agent.openai_runtime import run_openai_agent
from core import config
from tests.openai_fakes import DEPLOYMENT, FakeGateway, text_turn, tool_turn


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setattr(config, "AZURE_OPENAI_DEPLOYMENT", DEPLOYMENT)
    monkeypatch.setattr(config, "AZURE_OPENAI_MAX_TOKENS", None)
    session_store.clear()
    yield
    session_store.clear()


def _turn(gateway: FakeGateway, message: str, conversation_id: str | None = "conv", fork: str | None = None):
    async def go():
        return [
            event
            async for event in run_openai_agent(
                message, conversation_id, fork, "scope", model=gateway.model()
            )
        ]

    events = asyncio.run(go())
    return events, events[-1].data["turn_id"] if events[-1].data else None


def _dialogue(body: dict) -> list[tuple[str, str]]:
    """system 지침을 뺀 (role, content) 목록. Tool 호출 메시지는 content 대신 Tool 이름."""

    rows = []
    for message in body["messages"][1:]:
        if message.get("tool_calls"):
            rows.append(("call", message["tool_calls"][0]["function"]["name"]))
        else:
            rows.append((message["role"], message.get("content")))
    return rows


def test_next_turn_continues_the_conversation_including_tool_results(monkeypatch) -> None:
    async def fake_execute_sql(**_kwargs) -> dict:
        return {"status": "ok", "result_id": "b" * 32, "row_count": 2}

    monkeypatch.setattr("agent.tool_specs.execute_sql", fake_execute_sql)
    gateway = FakeGateway(
        tool_turn("execute_sql", {"sql": "SELECT 1", "purpose": "합계"}, "call_sql"),
        text_turn("A1"),
        text_turn("A2"),
    )

    _turn(gateway, "Q1")
    _turn(gateway, "Q2")

    dialogue = _dialogue(gateway.bodies[2])
    assert dialogue[0] == ("user", "Q1") and dialogue[1] == ("call", "execute_sql")
    assert dialogue[2][0] == "tool" and "b" * 32 in dialogue[2][1]
    assert dialogue[3:] == [("assistant", "A1"), ("user", "Q2")]


def test_fork_from_an_earlier_turn_branches_without_changing_the_original() -> None:
    gateway = FakeGateway(text_turn("A1"), text_turn("A2"), text_turn("A2'"), text_turn("A3'"))

    _, first = _turn(gateway, "Q1")
    _, second = _turn(gateway, "Q2")
    _turn(gateway, "Q2 수정", fork=first)
    _turn(gateway, "Q3")

    assert _dialogue(gateway.bodies[2]) == [("user", "Q1"), ("assistant", "A1"), ("user", "Q2 수정")]
    # 분기한 턴이 대화의 최신 갈래가 되고, 원래 갈래의 분기 지점은 그대로 남는다.
    assert _dialogue(gateway.bodies[3]) == [
        ("user", "Q1"), ("assistant", "A1"), ("user", "Q2 수정"), ("assistant", "A2'"), ("user", "Q3"),
    ]
    original = session_store.turn_history(second)
    assert [item.get("role") for item in original] == ["user", "assistant", "user", "assistant"]
    assert original[2]["content"] == "Q2"


def test_regenerate_and_restart_use_the_fork_point_or_an_empty_history() -> None:
    gateway = FakeGateway(text_turn("A1"), text_turn("A1 다시"), text_turn("처음"))

    _, first = _turn(gateway, "Q1")
    _turn(gateway, "Q1", fork="")
    _turn(gateway, "새 질문", fork="")

    assert _dialogue(gateway.bodies[1]) == [("user", "Q1")]
    assert _dialogue(gateway.bodies[2]) == [("user", "새 질문")]


def test_unknown_turn_warns_like_the_claude_runtime_and_starts_over() -> None:
    gateway = FakeGateway(text_turn("A1"), text_turn("새로"))
    _turn(gateway, "Q1")

    events, _ = _turn(gateway, "Q2", fork="missing-turn")
    _, _, claude_warning = _resolve_resume("conv", "missing-turn")

    assert events[0].type == "error" and events[0].content == claude_warning.content
    assert events[-1].type == "done"
    assert _dialogue(gateway.bodies[1]) == [("user", "Q2")]


def test_old_fork_points_are_dropped_beyond_the_per_conversation_cap(monkeypatch) -> None:
    monkeypatch.setattr(session_store, "MAX_TURNS_PER_CONVERSATION", 2)
    gateway = FakeGateway(text_turn("A1"), text_turn("A2"), text_turn("A3"), text_turn("새로"))

    _, first = _turn(gateway, "Q1")
    _, second = _turn(gateway, "Q2")
    _turn(gateway, "Q3")

    assert session_store.turn_history(first) is None
    assert session_store.turn_history(second) is not None
    events, _ = _turn(gateway, "Q2 수정", fork=first)
    assert events[0].content == session_store.FORK_FALLBACK_MESSAGE


def test_failed_turn_is_not_recorded(monkeypatch) -> None:
    gateway = FakeGateway(text_turn("A1"), tool_turn("list_simulation", {}), text_turn("A2"))
    _, first = _turn(gateway, "Q1")

    monkeypatch.setattr(config, "AGENT_MAX_TURNS", 1)
    with pytest.raises(MaxTurnsExceeded):
        _turn(gateway, "Q2")
    monkeypatch.setattr(config, "AGENT_MAX_TURNS", 25)
    _turn(gateway, "Q3")

    assert _dialogue(gateway.bodies[2]) == [("user", "Q1"), ("assistant", "A1"), ("user", "Q3")]
    assert len(session_store._snapshot_by_turn) == 2


def test_turns_without_a_conversation_id_do_not_share_history() -> None:
    gateway = FakeGateway(text_turn("A1"), text_turn("A2"))

    _, first = _turn(gateway, "Q1", conversation_id=None)
    _turn(gateway, "Q2", conversation_id=None)

    assert _dialogue(gateway.bodies[1]) == [("user", "Q2")]
    assert session_store.turn_history(first) is not None
