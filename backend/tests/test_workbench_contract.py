"""F01/F02/F12: real adapter + agent + SSE, with a deterministic SDK substitute.

Case names are also used by the frontend workbench regression fixtures.
No new API, payload fields, provider calls, or runtime behavior are introduced.
"""
import json

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage
from fastapi.testclient import TestClient

import agent.agent as agent_module
from agent import session_store
from main import app


def tool_call(call_id):
    return AssistantMessage(content=[ToolUseBlock(
        id=call_id, name="mcp__planning__execute_sql", input={"sql": "SELECT 1"},
    )], model="fixture")


def tool_result(call_id, data):
    return UserMessage(content=[ToolResultBlock(tool_use_id=call_id, content=json.dumps(data))])


ZERO = {"status": "ok", "kind": "database", "row_count": 0, "table": {"columns": ["qty"], "rows": []}}
ERROR = {"status": "error", "message": "조회 조건을 확인하세요."}


@pytest.fixture
def sdk_fixture(monkeypatch):
    session_store.clear()

    def install(messages, failed=False):
        async def fake_query(**_):
            for message in messages:
                yield message
            yield ResultMessage(subtype="error" if failed else "success", duration_ms=1,
                duration_api_ms=1, is_error=failed, num_turns=1, session_id="ux-fixture")
        monkeypatch.setattr(agent_module, "query", fake_query)
    yield install
    session_store.clear()


def collect_sse():
    response = TestClient(app).post("/api/chat", json={"message": "조회 결과를 알려줘"})
    assert response.status_code == 200
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.mark.parametrize("case", ["tool-error-done", "missing-result", "empty-done", "zero-rows", "error-done", "parallel-reversed", "recovered-tool-error"])
def test_workbench_terminal_states_on_sse_wire(sdk_fixture, case):
    messages = []
    if case not in ("empty-done", "error-done"):
        messages.append(tool_call("sql-1"))
    if case == "tool-error-done":
        messages.extend([tool_result("sql-1", ERROR), AssistantMessage(content=[TextBlock(text="조건 확인이 필요합니다.")], model="fixture")])
    elif case == "zero-rows":
        messages.append(tool_result("sql-1", ZERO))
    elif case == "parallel-reversed":
        messages.extend([tool_call("sql-2"), tool_result("sql-2", ZERO), tool_result("sql-1", ERROR)])
    elif case == "recovered-tool-error":
        messages.extend([tool_result("sql-1", ERROR), tool_call("sql-2"), tool_result("sql-2", ZERO),
            AssistantMessage(content=[TextBlock(text="조건을 수정해 조회했습니다. 결과는 0건입니다.")], model="fixture")])
    sdk_fixture(messages, failed=case == "error-done")
    events = collect_sse()
    assert events[-1]["type"] == "done"
    assert sum(e["type"] == "done" for e in events) == 1
    results = [e for e in events if e["type"] == "tool_result"]
    calls = {e["tool_call_id"]: e for e in events if e["type"] == "tool_call"}
    for event in results:
        assert event["tool_call_id"] in calls
        assert event["tool_name"] == calls[event["tool_call_id"]]["tool_name"]
        result_index = events.index(event)
        assert events.index(calls[event["tool_call_id"]]) < result_index
        status = events[result_index + 1]
        assert status["type"] == "status"
        assert status["tool_call_id"] == event["tool_call_id"]
        assert status["data"]["status"] == ("error" if event["data"]["status"] == "error" else "completed")
    if case in ("empty-done", "missing-result"):
        assert results == []  # Never synthesize a successful tool result.
        assert len(calls) == (case == "missing-result")
    if case == "empty-done":
        assert [e["type"] for e in events] == ["done"]
    if case == "error-done":
        assert [e["type"] for e in events] == ["error", "done"]
        assert events[-1]["data"] is None
    elif case == "tool-error-done":
        assert results[0]["data"] == ERROR
        assert events[-2]["type"] == "text"
        assert events[-1]["data"]["turn_id"]
    elif case == "zero-rows":
        assert results[0]["data"] == ZERO
    elif case == "parallel-reversed":
        assert [e["tool_call_id"] for e in results] == ["sql-2", "sql-1"]
    elif case == "recovered-tool-error":
        assert [e["data"]["status"] for e in results] == ["error", "ok"]
        assert events[-2]["type"] == "text"
    assert all("access_scope" not in e.get("data", {}).get("args", {}) for e in calls.values())


@pytest.mark.parametrize("has_result", [False, True])
def test_unrelated_markdown_table_is_not_declared_duplicate_by_fallback(sdk_fixture, monkeypatch, has_result):
    result_id = "a" * 32
    metric = "| 지표 | 비율 |\n| --- | --- |\n| 불량률 | 2% |"
    messages = [tool_call("sql-1"), tool_result("sql-1", {**ZERO, **({"result_id": result_id} if has_result else {})}),
        AssistantMessage(content=[TextBlock(text=metric)], model="fixture")]
    sdk_fixture(messages)
    prepared = []

    async def prepare(result_id, *, access_scope):
        prepared.append((result_id, access_scope))
        return {"status": "ok", "result_id": result_id, "title": "WIP", "columns": ["제품", "WIP"],
            "rows": [["A", 20]], "row_count": 1, "displayed_count": 1, "source_truncated": False}

    monkeypatch.setattr(agent_module, "prepare_table", prepare)
    events = collect_sse()
    assert next(e["content"] for e in events if e["type"] == "text") == metric
    tables = [e for e in events if e["type"] == "tool_result" and e["tool_name"] == "prepare_table"]
    assert len(tables) == int(has_result)
    if has_result:
        assert prepared[0][0] == result_id and prepared[0][1]
        assert tables[0]["data"]["columns"] == ["제품", "WIP"]
        call = next(e for e in events if e["type"] == "tool_call" and e["tool_name"] == "prepare_table")
        assert call["tool_call_id"] == tables[0]["tool_call_id"]
        assert "access_scope" not in call["data"]["args"]
    else:
        assert not prepared
