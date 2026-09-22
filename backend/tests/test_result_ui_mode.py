"""`RESULT_UI_MODE`가 결과 payload·Tool 집합·Agent 옵션·자동 표 보완을 함께 전환한다."""

import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from fastapi.testclient import TestClient

from agent import agent as agent_module
from agent.agent import AGENT_SDK_CWD, AGENT_SDK_PRESENT_CWD, _build_options, run_agent
from main import app
from services import result_store, visualization_store
from services.mock import mock_simulation_service, mock_sql_service
from services.result_store import LocalParquetResultStore
from services.visualization_store import LocalVisualizationStore

SCOPE = "scope-a"


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch, smt2020_assets):
    db_path = smt2020_assets.main(
        smt2020_assets.DEFAULT_SOURCE_ROOT, tmp_path / "smt2020.db"
    )
    monkeypatch.setattr("core.config.SMT2020_DB_PATH", db_path)
    monkeypatch.setattr(
        result_store, "_store", LocalParquetResultStore(tmp_path / "results")
    )
    monkeypatch.setattr(
        visualization_store, "_store", LocalVisualizationStore(tmp_path / "visualizations")
    )
    return db_path


@pytest.fixture()
def present_mode(monkeypatch):
    monkeypatch.setattr("core.config.RESULT_UI_MODE", "present")


FULL_ROW_KEYS = {"table", "results", "type", "sql", "summary_rows"}


def test_execute_sql_present_mode_returns_preview_without_rows(seeded_db, present_mode) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT route, step FROM route_step WHERE dataset='HVLM' LIMIT 300",
            purpose="Part 확인",
            access_scope=SCOPE,
        )
    )

    assert result["status"] == "ok" and result["kind"] == "database"
    assert result["purpose"] == "Part 확인"
    assert len(result["sample_rows"]) <= 5
    assert result["row_count"] > 5
    assert set(result) >= {
        "result_id", "row_count", "source_truncated", "columns", "sample_rows",
        "date_ranges", "distinct_counts", "statistics", "top_groups",
    }
    assert not FULL_ROW_KEYS & set(result)
    assert "SELECT" not in json.dumps(result)
    # 같은 결과를 Result API로 페이지 단위 조회할 수 있다.
    client = TestClient(app)
    client.cookies.set("pp_session_scope", SCOPE)
    page = client.get(f"/api/query-results/{result['result_id']}/table?page_size=3")
    assert page.status_code == 200 and len(page.json()["rows"]) == 3


def test_execute_sql_legacy_mode_keeps_inline_payload(seeded_db) -> None:
    result = asyncio.run(
        mock_sql_service.execute_sql(
            "SELECT part FROM part WHERE dataset='HVLM'", purpose="Part 확인", access_scope=SCOPE
        )
    )

    assert "table" in result or "sample_rows" in result
    assert "top_groups" not in result and "date_ranges" not in result


def test_run_simulation_present_mode_returns_preview_and_kpis(seeded_db, present_mode) -> None:
    result = asyncio.run(
        mock_simulation_service.run_simulation(
            "SMT2020_입력검증", {"dataset": "HVLM"}, access_scope=SCOPE
        )
    )

    assert result["status"] == "ok" and result["kind"] == "simulation"
    assert result["kpis"] and result["scenario"] and result["summary"]
    assert result["dataset"] == "HVLM"
    assert "results" not in result and "table" not in result and "type" not in result
    assert len(result["sample_rows"]) <= 5
    assert result["result_id"]


def test_build_options_select_tools_and_instructions_by_mode(monkeypatch) -> None:
    legacy = _build_options(None)
    monkeypatch.setattr("core.config.RESULT_UI_MODE", "present")
    present = _build_options(None)

    assert legacy.cwd == AGENT_SDK_CWD and present.cwd == AGENT_SDK_PRESENT_CWD
    assert "mcp__planning__prepare_table" in legacy.allowed_tools
    assert "mcp__planning__present" not in legacy.allowed_tools
    assert "mcp__planning__present" in present.allowed_tools
    assert "mcp__planning__prepare_table" not in present.allowed_tools
    assert "Skill" in present.allowed_tools


async def _collect(agen: AsyncIterator[object]) -> list:
    return [event async for event in agen]


def test_present_mode_does_not_add_automatic_table(monkeypatch, present_mode) -> None:
    result_id = "a" * 32

    async def fake_query(*, prompt, options) -> AsyncIterator[object]:
        yield AssistantMessage(
            content=[ToolUseBlock(id="sql-1", name="mcp__planning__execute_sql", input={"sql": "SELECT 1"})],
            model="x",
        )
        yield UserMessage(content=[ToolResultBlock(
            tool_use_id="sql-1",
            content=[{"type": "text", "text": json.dumps({"status": "ok", "result_id": result_id})}],
        )])
        yield AssistantMessage(
            content=[TextBlock(text="| a | b |\n| --- | --- |\n| 1 | 2 |")], model="x", uuid="u1"
        )
        yield ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
            num_turns=1, session_id="sess-present", uuid="r1",
        )

    async def boom(*args, **kwargs):  # 자동 보완이 호출되면 실패한다
        raise AssertionError("present 모드에서는 자동 표 보완을 하지 않는다")

    monkeypatch.setattr(agent_module, "query", fake_query)
    monkeypatch.setattr(agent_module, "prepare_table", boom)

    events = asyncio.run(_collect(run_agent("표로 보여줘", access_scope=SCOPE)))

    assert events[-1].type == "done" and events[-1].data["turn_id"]
    assert not [e for e in events if e.tool_name == "prepare_table"]


def test_present_call_flows_through_event_adapter() -> None:
    from agent.event_adapter import AgentEventAdapter

    adapter = AgentEventAdapter()
    wire_tree = {"$type": "QueryTable", "$key": "table-1", "resultId": "a" * 32}
    assistant_ui_tree = {"$type": "QueryTable", "$key": "table-1", "resultId": "a" * 32}
    call = adapter.convert(AssistantMessage(
        content=[ToolUseBlock(
            id="present-1",
            name="mcp__planning__present",
            input={"tree": json.dumps(wire_tree)},
        )], model="x",
    ))
    result = adapter.convert(UserMessage(content=[ToolResultBlock(
        tool_use_id="present-1", content=[{"type": "text", "text": "{}"}],
    )]))

    assert call[0].type == "tool_call" and call[0].tool_name == "present"
    assert call[0].data == {"args": assistant_ui_tree}
    assert [e.type for e in result] == ["tool_result", "status"]
    assert result[0].data == {} and result[0].tool_call_id == "present-1"
    assert result[1].data["status"] == "completed"
