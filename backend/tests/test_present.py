"""`present` Tool: vocabulary schema, 재귀 검증, 접근 제어, SDK 등록."""

import asyncio
import copy
import json
import re

import pytest

from agent.sdk_tools import planning_tools, tool_catalog, tool_names
from services import result_store
from services.present_service import (
    PRESENT_MAX_BYTES,
    PRESENT_MAX_DEPTH,
    PRESENT_MAX_NODES,
    VOCABULARY,
    PresentError,
    decode_present_input,
    present_input_schema,
    to_assistant_ui_tree,
    validate_present,
)
from services.result_store import LocalParquetResultStore
from tools.present_tool import present

SCOPE = "scope-a"


@pytest.fixture()
def result(tmp_path, monkeypatch):
    store = LocalParquetResultStore(tmp_path / "results")
    monkeypatch.setattr(result_store, "_store", store)
    return store.save(
        ["work_month", "line", "qty"],
        [["2026-01", "A", 10], ["2026-02", "A", 20], ["2026-01", "B", 5], ["2026-02", "B", 7]],
        source="execute_sql",
        conversation_id=None,
        access_scope=SCOPE,
    )


def _tree(result_id):
    return {
        "$type": "Card",
        "title": "월별 생산량",
        "children": [
            {"$type": "SqlPreview", "sql": "SELECT 1"},
            {
                "$type": "QueryChart",
                "resultId": result_id,
                "chartType": "line",
                "xColumn": "work_month",
                "yColumn": "qty",
                "groupByColumn": "line",
                "title": "추이",
            },
            {"$type": "QueryTable", "resultId": result_id, "columns": ["work_month", "qty"]},
        ],
    }


def _error(node, *, scope=SCOPE) -> PresentError:
    with pytest.raises(PresentError) as caught:
        validate_present(node, access_scope=scope)
    return caught.value


def test_valid_tree_returns_empty_object(result) -> None:
    assert validate_present(_tree(result.result_id), access_scope=SCOPE) == {}
    assert asyncio.run(present(_tree(result.result_id), access_scope=SCOPE)) == {}


def test_simulation_summary_accepts_result_children_and_optional_fields(result) -> None:
    node = {
        "$type": "SimulationSummary",
        "scenario": "HVLM",
        "summary": "요약",
        "kpis": [{"label": "Part", "value": 3, "unit": "개"}, {"label": "상태", "value": "정상"}],
        "resultId": result.result_id,
        "children": [
            {"$type": "QueryTable", "resultId": result.result_id},
            {
                "$type": "QueryChart",
                "resultId": result.result_id,
                "chartType": "bar",
                "xColumn": "work_month",
                "yColumn": "qty",
                "aggregation": "sum",
            },
        ],
    }

    assert validate_present(node, access_scope=SCOPE) == {}


@pytest.mark.parametrize(
    "mutate,code",
    [
        (lambda n: n.update({"$type": "Chart"}), "UNKNOWN_COMPONENT"),
        (lambda n: n.update({"$type": None}), "UNKNOWN_COMPONENT"),
        (lambda n: n.update({"onClick": "x"}), "UNKNOWN_PROP"),
        (lambda n: n.update({"$action": {}}), "UNKNOWN_PROP"),
        (lambda n: n.update({"rows": [[1]]}), "DATA_NOT_ALLOWED"),
        (lambda n: n.update({"data": []}), "DATA_NOT_ALLOWED"),
        (lambda n: n.update({"title": 3}), "INVALID_PROP"),
        (lambda n: n.update({"title": "x" * 121}), "UI_LIMIT_EXCEEDED"),
        (lambda n: n.update({"padding": 99}), "INVALID_PROP"),
        (lambda n: n.update({"children": [123]}), "INVALID_UI_TREE"),
    ],
)
def test_structure_violations_report_safe_code_and_path(result, mutate, code) -> None:
    node = _tree(result.result_id)
    mutate(node)

    error = _error(node)

    assert error.code == code
    assert error.details["path"].startswith("$")


def test_root_must_be_object_and_leaf_components_reject_children() -> None:
    assert _error([]).code == "INVALID_UI_TREE"
    assert _error({"$type": "SqlPreview", "sql": "SELECT 1", "children": ["b"]}).code == "INVALID_UI_TREE"
    assert _error({"$type": "SqlPreview"}).code == "INVALID_PROP"


def test_simulation_summary_rejects_non_result_children(result) -> None:
    node = {
        "$type": "SimulationSummary",
        "scenario": "s",
        "summary": "s",
        "kpis": [],
        "children": [{"$type": "SqlPreview", "sql": "SELECT 1"}],
    }

    assert _error(node).code == "INVALID_UI_TREE"
    node["children"] = ["문자열"]
    assert _error(node).code == "INVALID_UI_TREE"


def test_limits_on_size_depth_and_node_count() -> None:
    deep: dict = {"$type": "SqlPreview", "sql": "SELECT 1"}
    for _ in range(PRESENT_MAX_DEPTH):
        deep = {"$type": "Card", "children": deep}
    wide = {
        "$type": "Card",
        "children": [{"$type": "SqlPreview", "sql": "SELECT 1"} for _ in range(PRESENT_MAX_NODES)],
    }
    huge = {"$type": "SqlPreview", "sql": "x" * 20_000, "$key": "k"}
    big = {"$type": "Card", "children": [copy.deepcopy(huge) for _ in range(4)]}

    assert _error(deep).code == "UI_LIMIT_EXCEEDED"
    assert _error(wide).code == "UI_LIMIT_EXCEEDED"
    assert len(json.dumps(big)) > PRESENT_MAX_BYTES
    assert _error(big).code == "UI_LIMIT_EXCEEDED"


def test_result_id_format_and_access_are_checked(result) -> None:
    node = _tree(result.result_id)
    other = copy.deepcopy(node)
    other["children"][1]["resultId"] = "f" * 32
    malformed = copy.deepcopy(node)
    malformed["children"][2]["resultId"] = "ABC"

    foreign = _error(node, scope="scope-b")
    missing = _error(other)

    assert foreign.code == missing.code == "RESULT_NOT_FOUND"
    assert foreign.message == missing.message
    assert _error(malformed).code == "INVALID_PROP"
    assert _error(node, scope=None).code == "RESULT_NOT_FOUND"


def test_chart_and_table_settings_are_validated_against_stored_result(result) -> None:
    bad_column = _tree(result.result_id)
    bad_column["children"][1]["xColumn"] = "nope"
    bad_role = _tree(result.result_id)
    bad_role["children"][1]["yColumn"] = "line"
    del bad_role["children"][1]["groupByColumn"]
    grain = _tree(result.result_id)
    del grain["children"][1]["groupByColumn"]
    table = _tree(result.result_id)
    table["children"][2]["columns"] = ["missing"]

    assert _error(bad_column).code == "COLUMN_NOT_FOUND"
    assert _error(bad_role).code == "INVALID_COLUMN_ROLE"
    assert _error(grain).code == "AGGREGATION_REQUIRED"
    assert _error(bad_column).details["path"] == "$.children[1]"
    error = _error(table)
    assert error.code == "COLUMN_NOT_FOUND" and error.details["path"] == "$.children[2].columns"


def test_tool_returns_safe_error_payload(result) -> None:
    bad = _tree(result.result_id)
    bad["children"][1]["yColumn"] = "line"
    del bad["children"][1]["groupByColumn"]

    payload = asyncio.run(present(bad, access_scope=SCOPE))

    assert payload["status"] == "error" and payload["code"] == "INVALID_COLUMN_ROLE"
    assert str(result.path.parent) not in json.dumps(payload)


def test_advertised_schema_uses_one_non_recursive_json_string() -> None:
    schema = present_input_schema()

    assert schema["required"] == ["tree"]
    assert set(schema["properties"]) == {"tree"}
    assert schema["properties"]["tree"]["type"] == "string"
    assert schema["properties"]["tree"]["maxLength"] == PRESENT_MAX_BYTES
    assert schema["additionalProperties"] is False
    assert "$defs" not in schema and "$ref" not in json.dumps(schema)
    description = schema["properties"]["tree"]["description"]
    assert set(VOCABULARY) == {
        "Card",
        "SqlPreview",
        "QueryChart",
        "QueryTable",
        "SimulationSummary",
    }
    assert all(name in description for name in VOCABULARY)
    assert "Card(title?:string" in description
    assert "SqlPreview(sql:string" in description
    assert "QueryTable(resultId:string" in description
    assert all(
        f"{name}(" not in description
        for name in ("Col", "Row", "Header", "Text", "Fact", "Badge", "Alert", "ListView")
    )


def test_advertised_schema_property_names_are_claude_code_compatible() -> None:
    pattern = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")

    def check(value) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                assert all(pattern.fullmatch(name) for name in properties)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(present_input_schema())


def test_tool_wire_tree_converts_to_assistant_ui_without_touching_regular_objects() -> None:
    wire = {
        "component": "SimulationSummary",
        "nodeKey": "summary-1",
        "scenario": "HVLM",
        "summary": "요약",
        "kpis": [{"label": "component", "value": "QueryTable"}],
        "children": [
            {"component": "QueryChart", "nodeKey": 1, "resultId": "a" * 32},
            "설명",
        ],
    }

    converted = to_assistant_ui_tree(wire)

    assert converted["$type"] == "SimulationSummary"
    assert converted["$key"] == "summary-1"
    assert converted["children"][0]["$type"] == "QueryChart"
    assert converted["children"][0]["$key"] == 1
    assert converted["kpis"] == wire["kpis"]
    assert wire["component"] == "SimulationSummary" and "$type" not in wire


def test_tool_input_decodes_json_string_to_assistant_ui_tree() -> None:
    tree = {
        "$type": "Card",
        "$key": "root",
        "children": [{"$type": "SqlPreview", "sql": "SELECT 1"}],
    }

    converted = decode_present_input({"tree": json.dumps(tree, ensure_ascii=False)})

    assert converted == {
        "$type": "Card",
        "$key": "root",
        "children": [{"$type": "SqlPreview", "sql": "SELECT 1"}],
    }


def test_tool_input_keeps_legacy_wire_alias_as_compatibility_only() -> None:
    wire = {"component": "SqlPreview", "nodeKey": "old", "sql": "SELECT 1"}

    assert decode_present_input({"tree": json.dumps(wire, ensure_ascii=False)}) == {
        "$type": "SqlPreview",
        "$key": "old",
        "sql": "SELECT 1",
    }


@pytest.mark.parametrize(
    "args,path",
    [
        ({}, "$.tree"),
        ({"tree": []}, "$.tree"),
        ({"tree": "not json"}, "$.tree"),
        ({"tree": "[]"}, "$.tree"),
        ({"tree": "{}", "component": "Card"}, "$.component"),
    ],
)
def test_tool_input_rejects_malformed_or_ambiguous_wire_values(args, path) -> None:
    with pytest.raises(PresentError) as caught:
        decode_present_input(args)

    assert caught.value.code == "INVALID_UI_TREE"
    assert caught.value.details["path"] == path


def test_present_registration_depends_on_mode() -> None:
    legacy = tool_names("legacy")
    present_mode = tool_names("present")

    assert "mcp__planning__present" not in legacy
    assert {"mcp__planning__prepare_table", "mcp__planning__prepare_visualization"} <= set(legacy)
    assert "mcp__planning__present" in present_mode
    assert not {"mcp__planning__prepare_table", "mcp__planning__prepare_visualization"} & set(present_mode)
    assert len(planning_tools(mode="present")) == 13


def test_tool_catalog_advertises_present_schema_in_present_mode() -> None:
    rows = asyncio.run(tool_catalog("present"))
    by_name = {row["name"]: row for row in rows}

    assert "present" in by_name and "prepare_table" not in by_name
    assert set(by_name["present"]["input_schema"]["properties"]) == {"tree"}
    assert "$defs" not in by_name["present"]["input_schema"]
    assert by_name["present"]["output"]


def test_registered_present_tool_accepts_json_wire_tree_and_validates_canonical_tree(result) -> None:
    present_tool = next(item for item in planning_tools(SCOPE, "present") if item.name == "present")

    response = asyncio.run(present_tool.handler({
        "tree": json.dumps({
            "$type": "QueryTable",
            "$key": "result-table",
            "resultId": result.result_id,
        }),
    }))

    assert json.loads(response["content"][0]["text"]) == {}


def test_registered_present_tool_returns_safe_parse_error() -> None:
    present_tool = next(item for item in planning_tools(SCOPE, "present") if item.name == "present")

    response = asyncio.run(present_tool.handler({"tree": "["}))
    payload = json.loads(response["content"][0]["text"])

    assert payload["status"] == "error" and payload["code"] == "INVALID_UI_TREE"
    assert payload["details"]["path"] == "$.tree"
