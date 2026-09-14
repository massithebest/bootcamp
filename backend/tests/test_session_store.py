"""session_store: conversation_id <-> session_id, turn_id -> TurnAnchor."""

import pytest

from agent import session_store


@pytest.fixture(autouse=True)
def _clear_store():
    session_store.clear()
    yield
    session_store.clear()


def test_session_id_roundtrip() -> None:
    assert session_store.get_session_id("conv-1") is None

    session_store.bind_session_id("conv-1", "sess-a")
    assert session_store.get_session_id("conv-1") == "sess-a"

    # 같은 conversation_id 에 다시 bind 하면 최신 값으로 덮어쓴다.
    session_store.bind_session_id("conv-1", "sess-b")
    assert session_store.get_session_id("conv-1") == "sess-b"


def test_bind_session_id_ignores_none() -> None:
    session_store.bind_session_id(None, "sess-a")
    session_store.bind_session_id("conv-1", None)
    assert session_store.get_session_id("conv-1") is None


def test_turn_anchor_roundtrip() -> None:
    assert session_store.get_turn_anchor("turn-1") is None

    session_store.record_turn_anchor("turn-1", "sess-a", "entry-uuid-1")
    anchor = session_store.get_turn_anchor("turn-1")

    assert anchor is not None
    assert anchor.session_id == "sess-a"
    assert anchor.last_entry_uuid == "entry-uuid-1"


def test_turn_anchor_allows_none_entry_uuid() -> None:
    # ResultMessage 까지 uuid 가 하나도 안 잡히는 극단적인 경우(가짜/미완성
    # 스트림) 를 방어적으로 허용한다 — resume_session_at=None 이면 fork_session
    # 옵션이 꺼지므로 안전하게 평범한 resume 으로 동작한다 (agent.py 참고).
    session_store.record_turn_anchor("turn-1", "sess-a", None)
    anchor = session_store.get_turn_anchor("turn-1")

    assert anchor is not None
    assert anchor.last_entry_uuid is None


def test_clear_resets_both_maps() -> None:
    session_store.bind_session_id("conv-1", "sess-a")
    session_store.record_turn_anchor("turn-1", "sess-a", "entry-1")

    session_store.clear()

    assert session_store.get_session_id("conv-1") is None
    assert session_store.get_turn_anchor("turn-1") is None
