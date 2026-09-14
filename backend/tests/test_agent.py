"""agent.run_agent: 편집/재생성 포크 분기 검증.

`query()` 는 실제 `claude` CLI 서브프로세스를 띄우므로 monkeypatch 로
대체한다 — 여기서 검증하는 건 "어떤 옵션으로 SDK 를 호출했는가" 와
"턴이 끝난 뒤 무엇을 기록했는가" 지, 실제 모델 응답이 아니다.
"""

from collections.abc import AsyncIterator

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

import agent.agent as agent_module
from agent import session_store
from agent.agent import _build_options, _resolve_resume, run_agent
from api.schemas import AgentEvent


@pytest.fixture(autouse=True)
def _clear_store():
    session_store.clear()
    yield
    session_store.clear()


# ---- _resolve_resume (순수 함수) ----------------------------------------


def test_resolve_resume_plain_next_turn_uses_bound_session() -> None:
    session_store.bind_session_id("conv-1", "sess-current")

    resume, resume_at, warning = _resolve_resume("conv-1", None)

    assert resume == "sess-current"
    assert resume_at is None
    assert warning is None


def test_resolve_resume_empty_string_starts_over() -> None:
    session_store.bind_session_id("conv-1", "sess-current")

    resume, resume_at, warning = _resolve_resume("conv-1", "")

    assert resume is None
    assert resume_at is None
    assert warning is None


def test_resolve_resume_known_turn_id_forks_from_anchor() -> None:
    session_store.record_turn_anchor("turn-1", "sess-a", "entry-uuid-1")

    resume, resume_at, warning = _resolve_resume("conv-1", "turn-1")

    assert resume == "sess-a"
    assert resume_at == "entry-uuid-1"
    assert warning is None


def test_resolve_resume_unknown_turn_id_warns_and_starts_over() -> None:
    resume, resume_at, warning = _resolve_resume("conv-1", "no-such-turn")

    assert resume is None
    assert resume_at is None
    assert warning is not None
    assert warning.type == "error"


# ---- _build_options (순수 함수) ------------------------------------------


def test_build_options_plain_resume_does_not_fork() -> None:
    options = _build_options("sess-current", None)

    assert options.resume == "sess-current"
    assert options.fork_session is False
    assert options.resume_session_at is None


def test_build_options_fork_point_enables_fork_session() -> None:
    options = _build_options("sess-a", "entry-uuid-1")

    assert options.resume == "sess-a"
    assert options.fork_session is True
    assert options.resume_session_at == "entry-uuid-1"


# ---- run_agent (query() 를 대체) ------------------------------------------


def _fake_query_factory(
    session_id: str,
    assistant_uuid: str = "assistant-uuid",
    result_uuid: str = "result-uuid",
):
    """실제 CLI 를 흉내낸다: AssistantMessage 다음 ResultMessage 순서로 낸다.

    `ResultMessage.uuid` 는 편집/재생성 포크 지점 후보에서 제외돼야 한다
    (event_adapter.last_entry_uuid 참고) — 그래서 두 uuid 를 다르게 줘서
    최종적으로 `assistant_uuid` 만 남는지 검증할 수 있게 한다.
    """

    captured: dict[str, object] = {}

    async def fake_query(*, prompt, options) -> AsyncIterator[object]:
        captured["prompt"] = prompt
        captured["options"] = options
        yield AssistantMessage(
            content=[TextBlock(text="응답")], model="x", uuid=assistant_uuid
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id=session_id,
            uuid=result_uuid,
        )

    return fake_query, captured


async def _collect(agen: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    return [event async for event in agen]


def test_run_agent_plain_turn_records_new_anchor_and_yields_turn_id(
    monkeypatch,
) -> None:
    fake_query, captured = _fake_query_factory(session_id="sess-1")
    monkeypatch.setattr(agent_module, "query", fake_query)

    import asyncio

    events = asyncio.run(_collect(run_agent("안녕", conversation_id="conv-1")))

    assert captured["options"].resume is None
    assert captured["options"].fork_session is False

    assert session_store.get_session_id("conv-1") == "sess-1"

    done = events[-1]
    assert done.type == "done"
    turn_id = done.data["turn_id"]
    assert turn_id

    anchor = session_store.get_turn_anchor(turn_id)
    assert anchor is not None
    assert anchor.session_id == "sess-1"
    # AssistantMessage 의 uuid 만 남아야 한다 — ResultMessage 의 uuid 는
    # Transcript 에 없어 포크 지점으로 쓸 수 없다 (실제 CLI 로 확인).
    assert anchor.last_entry_uuid == "assistant-uuid"


def test_run_agent_second_turn_resumes_bound_session_without_forking(
    monkeypatch,
) -> None:
    session_store.bind_session_id("conv-1", "sess-1")
    fake_query, captured = _fake_query_factory(session_id="sess-1")
    monkeypatch.setattr(agent_module, "query", fake_query)

    import asyncio

    asyncio.run(_collect(run_agent("이어서", conversation_id="conv-1")))

    assert captured["options"].resume == "sess-1"
    assert captured["options"].fork_session is False
    assert captured["options"].resume_session_at is None


def test_run_agent_fork_from_turn_id_forks_and_rebinds_new_session(
    monkeypatch,
) -> None:
    # 턴 1 이 이미 끝나서 conv-1 은 sess-1 을 가리키고, turn-1 의 포크 지점을
    # 기록해뒀다고 가정한다.
    session_store.bind_session_id("conv-1", "sess-1")
    session_store.record_turn_anchor("turn-1", "sess-1", "entry-uuid-1")

    # 편집/재생성 — sess-1 의 entry-uuid-1 지점에서 포크해 sess-1-fork 를 새로 받는다.
    fake_query, captured = _fake_query_factory(session_id="sess-1-fork")
    monkeypatch.setattr(agent_module, "query", fake_query)

    import asyncio

    events = asyncio.run(
        _collect(
            run_agent(
                "다시 답해줘", conversation_id="conv-1", fork_from_turn_id="turn-1"
            )
        )
    )

    assert captured["options"].resume == "sess-1"
    assert captured["options"].fork_session is True
    assert captured["options"].resume_session_at == "entry-uuid-1"

    # 대화의 현재 세션이 새로 포크된 세션으로 갱신됐다 — 다음 평범한 턴은
    # sess-1 이 아니라 sess-1-fork 를 이어서 쓴다.
    assert session_store.get_session_id("conv-1") == "sess-1-fork"

    assert [e.type for e in events] == ["text", "done"]
    assert events[-1].data["turn_id"] != "turn-1"


def test_run_agent_unknown_fork_turn_id_warns_then_starts_fresh(
    monkeypatch,
) -> None:
    fake_query, captured = _fake_query_factory(session_id="sess-new")
    monkeypatch.setattr(agent_module, "query", fake_query)

    import asyncio

    events = asyncio.run(
        _collect(
            run_agent(
                "다시", conversation_id="conv-1", fork_from_turn_id="no-such-turn"
            )
        )
    )

    assert captured["options"].resume is None
    assert captured["options"].fork_session is False

    assert [e.type for e in events] == ["error", "text", "done"]


def test_run_agent_empty_fork_turn_id_starts_conversation_over(
    monkeypatch,
) -> None:
    session_store.bind_session_id("conv-1", "sess-old")
    fake_query, captured = _fake_query_factory(session_id="sess-restarted")
    monkeypatch.setattr(agent_module, "query", fake_query)

    import asyncio

    asyncio.run(
        _collect(run_agent("처음부터", conversation_id="conv-1", fork_from_turn_id=""))
    )

    assert captured["options"].resume is None
    assert captured["options"].fork_session is False
    assert session_store.get_session_id("conv-1") == "sess-restarted"
