"""실행부 중립 Tool 명세와 Claude 등록 계층의 연결 검증."""

import asyncio
import json

from mcp_types import CallToolRequestParams, PaginatedRequestParams

from agent.sdk_tools import TOOL_NAMES, build_planning_mcp_server
from agent.tool_specs import SUGGESTION_TOOL_NAME, tool_catalog, tool_specs


def test_tool_specs_have_unique_names_and_object_schemas() -> None:
    specs = tool_specs()
    names = [spec.name for spec in specs]

    assert len(names) == len(set(names))
    assert TOOL_NAMES == [f"mcp__planning__{name}" for name in names]
    for spec in specs:
        assert spec.description and spec.output
        assert spec.input_schema["type"] == "object"
        assert isinstance(spec.input_schema["properties"], dict)
        # access_scope 는 handler 인자로만 받고 모델 입력 schema 에 노출하지 않는다.
        assert "access_scope" not in spec.input_schema["properties"]


def test_only_the_suggestion_tool_is_hidden_from_tool_events() -> None:
    hidden = {spec.name for spec in tool_specs() if not spec.visible}

    assert hidden == {SUGGESTION_TOOL_NAME}


def test_claude_wire_and_catalog_use_the_shared_specs() -> None:
    specs = {spec.name: spec for spec in tool_specs()}
    server = build_planning_mcp_server("scope-a")["instance"]
    wire = asyncio.run(server._request_handlers["tools/list"].handler(None, PaginatedRequestParams()))

    assert {t.name: (t.description, t.input_schema) for t in wire.tools} == {
        name: (spec.description, spec.input_schema) for name, spec in specs.items()
    }
    catalog = asyncio.run(tool_catalog())
    assert {row["name"]: row["output"] for row in catalog} == {
        name: spec.output for name, spec in specs.items()
    }


def test_claude_tools_bind_access_scope_to_shared_handlers(monkeypatch) -> None:
    seen: dict = {}

    async def fake_execute_sql(*, sql: str, purpose: str, access_scope: str | None) -> dict:
        seen.update(sql=sql, purpose=purpose, access_scope=access_scope)
        return {"status": "success", "row_count": 1}

    monkeypatch.setattr("agent.tool_specs.execute_sql", fake_execute_sql)
    server = build_planning_mcp_server("scope-x")["instance"]
    call = server._request_handlers["tools/call"].handler

    result = asyncio.run(call(
        None,
        CallToolRequestParams(name="execute_sql", arguments={"sql": "SELECT 1", "purpose": "확인"}),
    ))

    assert result.is_error is not True
    assert seen == {"sql": "SELECT 1", "purpose": "확인", "access_scope": "scope-x"}
    assert json.loads(result.content[0].text) == {"status": "success", "row_count": 1}
