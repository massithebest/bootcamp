"""관통 예제 E2E. (설계 §5, §8 Phase 1 완료 기준)

에이전트를 실제로 호출한다. 실패하면 코드가 아니라 지식(Skill 본문·KPI
diagnostics·CLAUDE.md 인덱스)을 고쳐서 통과시킨다 — 무엇이 부족했는지가
곧 다음에 보강할 지식이다.

    pytest -m e2e -s tests/test_e2e_scenario.py
"""

import os

import pytest

from core.config import KNOWLEDGE_DIR
from services.knowledge_service import KnowledgeStore

pytestmark = pytest.mark.e2e


QUERY = "FGS 입고 실적이 부진한 원인을 찾아줘. 기간은 2026년 9월."


def _require_api_key() -> None:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("ANTHROPIC_API_KEY / OPENROUTER_API_KEY 가 없다")


@pytest.fixture(scope="module")
def agent_run(tmp_path_factory):
    """시드 DB 를 만들고 에이전트를 한 번 돌려 이벤트를 모은다."""

    _require_api_key()

    import asyncio

    from scripts.seed_sample_db import main as seed_main
    from core import config

    db_path = seed_main(tmp_path_factory.mktemp("e2e") / "sample.sqlite")
    original = config.SAMPLE_DB_PATH
    config.SAMPLE_DB_PATH = db_path

    monkeypatched_fake = os.environ.pop("PLANNING_AGENT_FAKE", None)

    async def collect():
        from agent.agent import run_agent

        return [event async for event in run_agent(QUERY, conversation_id="e2e")]

    try:
        events = asyncio.run(collect())
    finally:
        config.SAMPLE_DB_PATH = original
        if monkeypatched_fake is not None:
            os.environ["PLANNING_AGENT_FAKE"] = monkeypatched_fake

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


def test_query_is_decomposed(agent_run) -> None:
    """부진 판정 후 라인·품목 분해까지 갔는지."""

    assert agent_run["tool_calls"].count("execute_sql") >= 2


def test_answer_names_the_seeded_cause(agent_run) -> None:
    """답변이 심어둔 원인을 지목했는가 — Phase 1 완료 기준."""

    scenario = KnowledgeStore.load(KNOWLEDGE_DIR).scenarios[
        "fgs_line_b_material_shortage"
    ]
    answer = agent_run["answer"]

    # 표현 흔들림(결품/부족)까지 실패로 보면 지식이 아니라 문구를 맞추게 된다.
    assert scenario.expected_diagnosis in answer or "자재 부족" in answer, (
        f"답변이 심어둔 원인({scenario.expected_diagnosis})을 지목하지 않았다"
    )
    assert scenario.line_cd in answer and scenario.product_id in answer, (
        "부진이 집중된 라인·품목을 특정하지 못했다"
    )


def test_rejected_hypothesis_is_reported(agent_run) -> None:
    """기각 근거(확정 MP 변경 없음)도 답변에 남는지 — Skill 규칙."""

    assert "MP" in agent_run["answer"]


def test_no_error_events(agent_run) -> None:
    assert agent_run["errors"] == []
