"""실제 Agent(LLM)를 호출하는 opt-in E2E. (설계 §5, §8 Phase 1 완료 기준)

실패하면 코드가 아니라 지식(Skill 본문·KPI diagnostics·CLAUDE.md 인덱스)을
고쳐서 통과시킨다 — 무엇이 부족했는지가 곧 다음에 보강할 지식이다.
문서 검색 시나리오는 격리된 합성 문서 하나만 사용한다.

    pytest -m e2e -s tests/test_e2e.py
"""

import asyncio
import os

import pytest

from core import config
from services.knowledge.documents import DocumentStore

pytestmark = pytest.mark.e2e


def _require_api_key() -> None:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("ANTHROPIC_API_KEY / OPENROUTER_API_KEY 가 없다")


# ---- 관통 예제: KPI 정의 → SQL 조회 → 입력 정합성 검증 ----


QUERY = "SEG_B에서 제품별 초기 WIP를 조회하고 simulation 입력 관계도 검증해줘."


@pytest.fixture(scope="module")
def agent_run(tmp_path_factory, mock_database):
    """시드 DB 를 만들고 에이전트를 한 번 돌려 이벤트를 모은다."""

    _require_api_key()

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
        "KPI 정의보다 SQL 조회가 먼저다"
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


# ---- 문서 검색: 게시된 합성 문서를 찾아 출처·버전과 함께 인용 ----


def test_real_agent_searches_and_cites_published_document(tmp_path, monkeypatch):
    _require_api_key()
    if not config.CLAUDE_CLI_PATH:
        pytest.skip("CLI/provider credentials are not configured")
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(config, "KNOWLEDGE_SEARCH_BACKEND", "local")
    store = DocumentStore(config.KNOWLEDGE_DB_PATH)
    doc = store.save(dict(title="ZETA 검증 정책", content="ZETA 검증 정책의 확인 코드는 CHECK-742입니다.", category="검증", tags=["ZETA"], owner="테스트", source="합성 E2E 검증 자료"))
    doc = store.transition(doc["id"], "review", 1, version=1, actor="테스트", note="합성 fixture")
    store.transition(doc["id"], "activate", doc["revision"], version=1, actor="테스트")
    from agent.agent import run_agent
    async def collect():
        return [event async for event in run_agent("search_documents로 ZETA 검증 정책을 찾아 확인 코드와 문서 제목, 출처, 버전을 알려줘.")]
    events = asyncio.run(asyncio.wait_for(collect(), timeout=150))
    errors = [e for e in events if e.type == "error"]
    assert not errors, "Agent returned a public error"
    results = [e.data for e in events if e.type == "tool_result" and e.tool_name == "search_documents"]
    assert results and any(d.get("document_id") == doc["id"] and d.get("version") == 1 for r in results for d in r.get("documents", []))
    answer = "".join(e.content or "" for e in events)
    assert "CHECK-742" in answer and "ZETA" in answer
    assert "합성 E2E 검증 자료" in answer and "1" in answer
