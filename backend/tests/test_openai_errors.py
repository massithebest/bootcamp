"""OpenAI 실행부의 오류·타임아웃·연결 종료: 공개 문구로 `error` → `done`, 실행 취소, 기록 없음."""

import asyncio
import logging

import pytest

from agent import openai_session_store as session_store
from agent.openai_runtime import run_openai_agent
from agent.public_messages import (
    INCOMPLETE_RESPONSE_MESSAGE,
    LLM_API_FAILURE_MESSAGE,
    LLM_RESPONSE_TIMEOUT_MESSAGE,
    MAX_TURNS_MESSAGE,
)
from core import config
from tests.openai_fakes import DEPLOYMENT, GATEWAY_ERROR_DETAIL, FakeGateway, text_turn, tool_turn


SQL_ARGS = {"sql": "SELECT 1", "purpose": "확인"}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setattr(config, "AZURE_OPENAI_DEPLOYMENT", DEPLOYMENT)
    monkeypatch.setattr(config, "AZURE_OPENAI_MAX_TOKENS", None)
    session_store.clear()
    yield
    session_store.clear()


class SlowTool:
    """오래 걸리는 Tool. 실행부가 취소하면 `cancelled`가 참이 된다."""

    def __init__(self) -> None:
        self.started = False
        self.cancelled = False

    async def __call__(self, **_kwargs) -> dict:
        self.started = True
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return {"status": "ok"}


def _collect(gateway: FakeGateway) -> list:
    async def go():
        events = [e async for e in run_openai_agent("질문", "conv", None, "scope", model=gateway.model())]
        await asyncio.sleep(0.05)  # 취소된 SDK 작업이 정리될 시간을 준다.
        return events

    return asyncio.run(go())


def _assert_failed_with(events: list, message: str) -> None:
    assert [(e.type, e.content) for e in events[-2:]] == [("error", message), ("done", None)]
    assert events[-1].data is None  # 실패한 턴은 분기 anchor(turn_id)를 주지 않는다.
    assert session_store._snapshot_by_turn == {} and session_store.latest_history("conv") == []


def test_timeout_cancels_the_running_tool_and_ends_with_error_then_done(monkeypatch) -> None:
    slow = SlowTool()
    monkeypatch.setattr("agent.tool_specs.execute_sql", slow)
    monkeypatch.setattr(config, "LLM_RESPONSE_TIMEOUT_SECONDS", 0.3)
    gateway = FakeGateway(tool_turn("execute_sql", SQL_ARGS, text="조회합니다."), text_turn("끝"))

    events = _collect(gateway)

    assert [e.type for e in events[:3]] == ["text", "tool_call", "status"]
    _assert_failed_with(events, LLM_RESPONSE_TIMEOUT_MESSAGE)
    assert slow.started and slow.cancelled
    assert len(gateway.bodies) == 1


def test_max_turns_ends_with_a_public_message(monkeypatch) -> None:
    monkeypatch.setattr(config, "AGENT_MAX_TURNS", 1)
    gateway = FakeGateway(tool_turn("list_simulation", {}), text_turn("끝"))

    _assert_failed_with(_collect(gateway), MAX_TURNS_MESSAGE)


def test_gateway_error_is_reported_without_upstream_details(caplog) -> None:
    caplog.set_level(logging.ERROR, logger="agent.openai_runtime")
    gateway = FakeGateway(500)

    events = _collect(gateway)

    _assert_failed_with(events, LLM_API_FAILURE_MESSAGE)
    assert "InternalServerError" in caplog.text and "status=500" in caplog.text
    assert GATEWAY_ERROR_DETAIL not in caplog.text
    assert all(GATEWAY_ERROR_DETAIL not in (e.content or "") for e in events)


def test_model_calling_an_unknown_tool_ends_as_incomplete() -> None:
    gateway = FakeGateway(tool_turn("drop_table", {"table": "FP_TARGET"}), text_turn("끝"))

    _assert_failed_with(_collect(gateway), INCOMPLETE_RESPONSE_MESSAGE)


def test_client_disconnect_cancels_the_run_without_recording(monkeypatch) -> None:
    slow = SlowTool()
    monkeypatch.setattr("agent.tool_specs.execute_sql", slow)
    gateway = FakeGateway(tool_turn("execute_sql", SQL_ARGS, text="조회합니다."), text_turn("끝"))

    async def go():
        stream = run_openai_agent("질문", "conv", None, "scope", model=gateway.model())
        seen = [await anext(stream) for _ in range(3)]  # text, tool_call, status(running)
        await asyncio.sleep(0.05)
        await stream.aclose()
        await asyncio.sleep(0.05)
        return seen

    seen = asyncio.run(go())

    assert [e.type for e in seen] == ["text", "tool_call", "status"]
    assert slow.started and slow.cancelled
    assert session_store._snapshot_by_turn == {}


def test_unhandled_errors_propagate_to_the_route(monkeypatch) -> None:
    monkeypatch.setattr(config, "AZURE_OPENAI_ENDPOINT", "")

    async def go():
        return [e async for e in run_openai_agent("질문", "conv")]

    with pytest.raises(RuntimeError, match="AZURE_OPENAI_ENDPOINT"):
        asyncio.run(go())
