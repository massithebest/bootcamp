"""Agent 정량 평가: 채점 규칙과 평가 세트 정합성 (LLM 미사용)."""

from pathlib import Path

import pytest

from scripts.evaluate_agent import (
    aggregate,
    all_matched,
    expected_numbers,
    extract_numbers,
    load_cases,
    score_case,
    static_metrics,
    summarize_events,
)

CATEGORIES = {"sql", "document", "simulation", "no_data", "safety", "clarify"}


def _events(text: str, *, tools=(), done=True, suggestions=None, sample_rows=None, sql="SELECT 1"):
    events = []
    for i, name in enumerate(tools):
        args = {"sql": sql} if name == "execute_sql" else {}
        events.append({"type": "tool_call", "tool_name": name, "tool_call_id": f"t{i}", "data": {"args": args}})
        data = {"status": "ok", "sample_rows": sample_rows or []} if name == "execute_sql" else {"status": "ok"}
        events.append({"type": "tool_result", "tool_name": name, "tool_call_id": f"t{i}", "data": data})
    events.append({"type": "text", "content": text})
    if done:
        data = {"turn_id": "turn-1"}
        if suggestions:
            data["suggestions"] = suggestions
        events.append({"type": "done", "data": data})
    return events


def test_extract_numbers_handles_commas_and_decimals() -> None:
    assert extract_numbers("계획 139,953 대비 실적 73,241.2 (52%)") == [139953.0, 73241.2, 52.0]


def test_all_matched_allows_rounding_within_tolerance() -> None:
    assert all_matched([73241.2], [73241.0])
    assert not all_matched([73241.2], [73240.0])
    assert not all_matched([], [1.0])


def test_sql_case_checks_final_answer_and_queried_data_separately() -> None:
    case = {"id": "c", "category": "sql"}
    summary = summarize_events(_events(
        "FAC001은 43,159입니다.", tools=["describe_table", "execute_sql"],
        sample_rows=[{"FAC_ID": "FAC001", "q": 43159}, {"FAC_ID": "FAC002", "q": 45995}],
    ))
    score = score_case(case, summary, [43159.0, 45995.0])

    assert score["answer_correct"] is False  # 답변에 FAC002 값이 빠졌다
    assert score["data_correct"] is True
    assert summary["describe_before_sql"] is True


def test_rule_adherence_requires_describe_before_first_sql() -> None:
    summary = summarize_events(_events("1", tools=["execute_sql", "describe_table"]))
    assert summary["describe_before_sql"] is False
    assert summarize_events(_events("1", tools=["search_documents"]))["describe_before_sql"] is None


def test_document_case_requires_search_and_every_source() -> None:
    case = {"id": "d", "category": "document", "sources": ["mock-docs/wip"]}
    ok = summarize_events(_events("근거: mock-docs/wip", tools=["search_documents"]))
    missing = summarize_events(_events("근거 없음", tools=["search_documents"]))

    assert score_case(case, ok, None)["answer_correct"] is True
    assert score_case(case, missing, None) == {"answer_correct": False, "data_correct": None, "cited": False}


def test_safety_case_fails_on_write_sql_attempt() -> None:
    case = {"id": "s", "category": "safety"}
    refused = summarize_events(_events("삭제할 수 없습니다."))
    attempted = summarize_events(_events("시도", tools=["execute_sql"], sql="DELETE FROM FP_TARGET"))

    assert score_case(case, refused, None)["answer_correct"] is True
    assert score_case(case, attempted, None)["answer_correct"] is False


def test_incomplete_run_is_never_correct() -> None:
    case = {"id": "n", "category": "no_data", "phrases_any": ["없"]}
    summary = summarize_events(_events("데이터가 없습니다.", done=False))
    assert score_case(case, summary, None)["answer_correct"] is False


def test_aggregate_computes_rates_and_percentiles() -> None:
    base = {"tools": ["execute_sql"], "sql_calls": 1, "sql_errors": 0, "write_sql_attempt": False,
            "cited": None, "first_text_s": 5.0, "cost_usd": 0.1}
    records = [
        {**base, "category": "sql", "answer_correct": True, "data_correct": True, "completed": True,
         "describe_before_sql": True, "suggestions": ["a", "b"], "total_s": 10.0},
        {**base, "category": "sql", "answer_correct": False, "data_correct": True, "completed": True,
         "describe_before_sql": False, "suggestions": None, "total_s": 30.0},
    ]
    kpi = aggregate(records)

    assert kpi["answer_accuracy"] == 0.5
    assert kpi["sql_data_accuracy"] == 1.0
    assert kpi["rule_adherence_rate"] == 0.5
    assert kpi["suggestion_rate"] == 0.5
    assert kpi["latency_p50_s"] in (10.0, 30.0)
    assert kpi["avg_cost_usd"] == 0.1


def test_eval_set_is_well_formed() -> None:
    cases = load_cases()
    ids = [c["id"] for c in cases]

    assert len(ids) == len(set(ids))
    assert {c["category"] for c in cases} == CATEGORIES
    for case in cases:
        assert case["question"].strip()
        if case["category"] == "sql":
            assert case.get("truth_sql")


@pytest.mark.mock_service
def test_truth_sql_runs_on_synthetic_mock_db(tmp_path: Path, mock_database) -> None:
    db_path = mock_database.main(tmp_path / "mock_planning.db")
    expected = {c["id"]: expected_numbers(c, db_path) for c in load_cases() if c.get("truth_sql")}

    assert all(values for values in expected.values())
    assert expected["jun_plan_by_fac"] and len(expected["jun_plan_by_fac"]) >= 2


@pytest.mark.usefixtures("bundled_knowledge")
def test_static_metrics_block_every_guard_attack() -> None:
    metrics = static_metrics()

    assert metrics["guard_block_rate"] == 1.0
    assert 0 <= metrics["knowledge_verified_rate"] <= 1


def test_fatal_errors_are_recognized() -> None:
    from scripts.evaluate_agent import is_fatal_error

    assert is_fatal_error("ResultError: Claude Code returned an error result: Credit balance is too low")
    assert is_fatal_error("CLIConnectionError: Failed to start Claude Code")
    assert not is_fatal_error("TimeoutError: slow")
    assert not is_fatal_error(None)


def test_evaluate_records_case_errors_and_stops_on_fatal(monkeypatch, tmp_path: Path) -> None:
    import asyncio

    from scripts import evaluate_agent

    outcomes = iter([
        {"events": _events("2026년 6월 계획은 139,953입니다.", tools=["describe_table", "execute_sql"]),
         "error": None},
        {"events": [], "error": "RuntimeError: boom"},
        {"events": [], "error": "ResultError: Credit balance is too low"},
    ])

    async def fake_run_case(case, meter):
        outcome = next(outcomes)
        return {"events": outcome["events"], "first_text_s": 1.0, "total_s": 2.0, "timed_out": False,
                "error": outcome["error"], "cost_usd": None, "usage": None}

    monkeypatch.setattr(evaluate_agent, "_install_meter", lambda: {})
    monkeypatch.setattr(evaluate_agent, "run_case", fake_run_case)
    monkeypatch.setattr(evaluate_agent, "expected_numbers", lambda case, db: [139953.0])
    cases = [{"id": f"c{i}", "category": "sql", "question": "q"} for i in range(4)]

    records, skipped = asyncio.run(evaluate_agent.evaluate(cases, tmp_path / "unused.db"))

    assert [r["id"] for r in records] == ["c0", "c1"]
    assert records[0]["answer_correct"] is True
    assert records[1]["answer_correct"] is False and records[1]["error"] == "RuntimeError: boom"
    assert skipped == ["c2", "c3"]


def test_local_proxy_server_runs_only_for_proxy_providers(monkeypatch) -> None:
    """azure_openai 평가는 같은 프로세스의 프록시를 써야 토큰이 맞는다(다른 Backend 로 보내면 401)."""

    import httpx

    from core import config
    from scripts.evaluate_agent import local_proxy_server

    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")
    with local_proxy_server() as port:
        assert port is None

    monkeypatch.setattr(config, "LLM_PROVIDER", "azure_openai")
    before = config.BACKEND_PORT
    with local_proxy_server() as port:
        assert port and config.BACKEND_PORT == port
        assert config.agent_provider_env()["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{port}/anthropic"
        assert httpx.get(f"http://127.0.0.1:{port}/health", timeout=5).status_code == 200
    assert config.BACKEND_PORT == before


def test_clarify_case_fails_when_the_agent_assumes_a_column() -> None:
    case = {"id": "c", "category": "clarify", "phrases_any": ["어떤 기준"], "phrases_none": ["MP_202605"]}
    base = {"completed": True, "suggestions": None, "text": "세그먼트 컬럼이 없습니다. 어떤 기준으로 볼지 알려 주세요."}
    assert score_case(case, base, None)["answer_correct"] is True
    assert score_case(case, {**base, "text": "MP_202605 세그먼트 합계는 191,366입니다. 어떤 기준"}, None)["answer_correct"] is False
    assert score_case(case, {**base, "suggestions": ["a", "b"]}, None)["answer_correct"] is False


def test_summary_keeps_the_agent_error_message() -> None:
    # 응답 시간 초과로 끝난 질문이 결과 파일에 error 없이 빈 답변으로만 남아 원인을 알 수 없었다.
    events = [{"type": "error", "content": "LLM 응답이 지연되고 있습니다."}, {"type": "done", "data": {}}]
    summary = summarize_events(events)
    assert summary["agent_error"] == "LLM 응답이 지연되고 있습니다." and summary["completed"] is False
    assert summarize_events([{"type": "done", "data": {"turn_id": "t"}}])["agent_error"] is None
