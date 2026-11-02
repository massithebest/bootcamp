"""OpenAI Agents SDK 실행부: 지침 조합·Tool 등록·모델 연결·트레이싱·max_turns.

가짜 게이트웨이(`tests/openai_fakes.py`)로 모델 품질이 아니라 "어떤 요청을 보냈고
Tool 결과를 어떻게 이어 붙였는가"를 검증한다.
"""

import asyncio
import json
from typing import Any

import pytest
from agents import MaxTurnsExceeded
from agents.tracing import trace
from agents.tracing.traces import NoOpTrace

from agent import openai_runtime
from agent.skills import get_skill, list_skills
from agent.system_prompt import SYSTEM_PROMPT
from agent.tool_events import TOOL_FAILURE_PAYLOAD
from agent.tool_specs import tool_specs
from core import config
from tests.openai_fakes import DEPLOYMENT, FakeGateway, text_turn, tool_messages, tool_turn


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


def test_tracing_is_disabled_on_import() -> None:
    assert isinstance(trace("probe"), NoOpTrace)


def test_system_instructions_hold_the_role_prompt_and_skill_index_only() -> None:
    instructions = openai_runtime.build_instructions()
    guide = openai_runtime.INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip()

    assert instructions.startswith(SYSTEM_PROMPT.strip())
    assert guide not in instructions
    assert "load_skill(name)" in instructions
    for skill in list_skills():
        assert f"`{skill.name}`: {skill.description}" in instructions


def test_runtime_guide_precedes_only_the_first_question_of_a_conversation() -> None:
    from agent import openai_session_store

    openai_session_store.clear()
    guide = openai_runtime.INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip()
    gateway = FakeGateway(text_turn("A1"), text_turn("A2"))

    async def turn(message: str) -> None:
        async for _ in openai_runtime.run_openai_agent(message, "guide-conv", None, "scope", model=gateway.model()):
            pass

    asyncio.run(turn("Q1"))
    asyncio.run(turn("Q2"))
    openai_session_store.clear()

    # Claude CLI 처럼 CLAUDE.md 를 대화 첫 질문 바로 앞에 둔다(system 에 두면 caveats 를 덜 지킨다).
    first = gateway.bodies[0]["messages"][1]["content"]
    assert guide in first and first.endswith("\n\nQ1") and first == openai_runtime.with_guide("Q1")
    later = [m["content"] for m in gateway.bodies[1]["messages"] if m["role"] == "user"]
    assert later == [openai_runtime.with_guide("Q1"), "Q2"]


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
    sql_output = tool_messages(gateway.bodies[1])[0]
    assert sql_output["tool_call_id"] == "call_sql"
    assert json.loads(sql_output["content"]) == {"status": "success", "result_id": "a" * 32, "row_count": 3}
    follow_up = tool_messages(gateway.bodies[2])[-1]
    assert follow_up["tool_call_id"] == "call_next"
    assert json.loads(follow_up["content"]).get("status") != "error"
    assert len(gateway.bodies) == 3


def test_load_skill_returns_the_skill_body_without_frontmatter() -> None:
    gateway = FakeGateway(tool_turn("load_skill", {"name": "sql-analysis"}), text_turn("절차를 읽었습니다."))

    _run(gateway, "DB에서 조회해 주세요.")

    content = tool_messages(gateway.bodies[1])[0]["content"]
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


def test_tool_exception_returns_the_public_failure_payload(monkeypatch, caplog) -> None:
    async def broken_execute_sql(**_kwargs) -> dict:
        raise OSError(r"C:\internal\path\db.sqlite locked")

    monkeypatch.setattr("agent.tool_specs.execute_sql", broken_execute_sql)
    gateway = FakeGateway(
        tool_turn("execute_sql", {"sql": "SELECT 1", "purpose": "확인"}),
        text_turn("조회에 실패했습니다."),
    )

    _run(gateway, "조회")

    content = tool_messages(gateway.bodies[1])[0]["content"]
    assert json.loads(content) == TOOL_FAILURE_PAYLOAD
    assert "internal" not in caplog.text and "OSError" in caplog.text


def test_gateway_client_leaves_retries_to_the_runner_policy(monkeypatch) -> None:
    monkeypatch.setattr(config, "AZURE_OPENAI_ENDPOINT", "https://gateway.test")
    monkeypatch.setattr(config, "AZURE_OPENAI_API_KEY", "test-key")

    model = openai_runtime.build_model()

    # 클라이언트 재시도는 이벤트 없이 게이트웨이의 Retry-After(60초)를 기다려 대기 한도를 넘긴다.
    assert model._client.max_retries == 0
    retry_wait = openai_runtime.RetryWait()
    retry = openai_runtime.model_settings(retry_wait).retry
    assert retry.max_retries == len(openai_runtime.RETRY_DELAYS)
    assert retry.policy == retry_wait.policy
