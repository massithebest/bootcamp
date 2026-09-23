"""관통 예제 E2E. (설계 §5, §8 Phase 1 완료 기준)

에이전트를 실제로 호출한다. 실패하면 코드가 아니라 지식(Skill 본문·KPI
diagnostics·CLAUDE.md 인덱스)을 고쳐서 통과시킨다 — 무엇이 부족했는지가
곧 다음에 보강할 지식이다.

    pytest -m e2e -s tests/test_e2e_scenario.py
"""

import os

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.mock_service]


QUERY = "SEG_B에서 제품별 초기 WIP를 조회하고 simulation 입력 관계도 검증해줘."


def _require_api_key() -> None:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("ANTHROPIC_API_KEY / OPENROUTER_API_KEY 가 없다")


@pytest.fixture(scope="module")
def agent_run(tmp_path_factory, mock_database):
    """시드 DB 를 만들고 에이전트를 한 번 돌려 이벤트를 모은다."""

    _require_api_key()

    import asyncio

    from core import config

    db_path = mock_database.main(tmp_path_factory.mktemp("e2e") / "mock_planning.db")
    original = config.MOCK_DB_PATH
    config.MOCK_DB_PATH = db_path

    async def collect():
        from agent.agent import run_agent

        return [event async for event in run_agent(QUERY, conversation_id="e2e")]

    try:
        events = asyncio.run(collect())
    finally:
        config.MOCK_DB_PATH = original

    tool_calls = [e.tool_name for e in events if e.type == "tool_call"]
    answer = "".join(e.content or "" for e in events if e.type == "text")
    errors = [e for e in events if e.type == "error"]

    print("\n--- tool 호출 순서:", tool_calls)
    print("--- 최종 답변:\n", answer)
    if errors:
        print("--- error 이벤트:", [e.content for e in errors])

    return {"tool_calls": tool_calls, "answer": answer, "errors": errors}


def test_kpi_definition_is_read_before_querying(agent_run) -> None:
    tool_calls = agent_run["tool_calls"]

    assert "get_kpi" in tool_calls, "KPI 정의를 읽지 않았다"
    assert "execute_sql" in tool_calls, "데이터를 조회하지 않았다"
    assert tool_calls.index("get_kpi") < tool_calls.index("execute_sql"), (
        "KPI 정의보다 SQL 조회가 먼저다 — kpi-shortfall-analysis Skill 절차를 따르지 않았다"
    )


def test_input_validation_is_run(agent_run) -> None:
    assert "run_simulation" in agent_run["tool_calls"]


def test_answer_names_dataset_and_wip(agent_run) -> None:
    answer = agent_run["answer"]
    assert "SEG_B" in answer
    assert "WIP" in answer or "재공" in answer


def test_answer_does_not_claim_real_des(agent_run) -> None:
    assert "입력" in agent_run["answer"] or "정합" in agent_run["answer"]


def test_no_error_events(agent_run) -> None:
    assert agent_run["errors"] == []
