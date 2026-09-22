"""`present_*` Tool들: 인자 schema, result 교차 검증, 접근 제어, SDK 등록."""

import asyncio

import pytest

from agent.sdk_tools import planning_tools, tool_catalog, tool_names
from services import result_store
from services.present_service import (
    PresentError,
    present_chart_input_schema,
    present_simulation_input_schema,
    present_sql_preview_input_schema,
    present_table_input_schema,
    validate_present_chart,
    validate_present_simulation,
    validate_present_sql_preview,
    validate_present_table,
)
from services.result_store import LocalParquetResultStore
from tools.present_tool import present_chart, present_simulation, present_sql_preview, present_table

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


def _error(fn, args, *, scope=SCOPE) -> PresentError:
    with pytest.raises(PresentError) as caught:
        fn(args, access_scope=scope)
    return caught.value


# ---- 성공 ----


def test_valid_chart_returns_empty_object(result) -> None:
    args = {
        "result_id": result.result_id,
        "chart_type": "line",
        "x_column": "work_month",
        "y_column": "qty",
        "group_by_column": "line",
        "title": "추이",
    }

    assert validate_present_chart(args, access_scope=SCOPE) == {}
    assert asyncio.run(present_chart(args, access_scope=SCOPE)) == {}


def test_valid_table_returns_empty_object(result) -> None:
    args = {"result_id": result.result_id, "columns": ["work_month", "qty"]}

    assert validate_present_table(args, access_scope=SCOPE) == {}
    assert asyncio.run(present_table(args, access_scope=SCOPE)) == {}


def test_valid_sql_preview_returns_empty_object() -> None:
    args = {"sql": "SELECT 1", "title": "쿼리"}

    assert validate_present_sql_preview(args, access_scope=SCOPE) == {}
    assert asyncio.run(present_sql_preview(args, access_scope=SCOPE)) == {}


def test_valid_simulation_returns_empty_object(result) -> None:
    args = {
        "scenario": "HVLM 입력검증",
        "summary": "요약",
        "kpis": [{"label": "불량률", "value": 1.2, "unit": "%"}],
        "result_id": result.result_id,
    }

    assert validate_present_simulation(args, access_scope=SCOPE) == {}
    assert asyncio.run(present_simulation(args, access_scope=SCOPE)) == {}


def test_simulation_without_result_id_is_valid() -> None:
    args = {"scenario": "s", "summary": "su", "kpis": []}

    assert validate_present_simulation(args, access_scope=SCOPE) == {}


# ---- result_id 접근 제어 ----


def test_chart_unknown_result_id_is_not_found() -> None:
    args = {
        "result_id": "0" * 32,
        "chart_type": "bar",
        "x_column": "work_month",
        "y_column": "qty",
    }

    error = _error(validate_present_chart, args)

    assert error.code == "RESULT_NOT_FOUND" and error.details["path"] == "$.result_id"


def test_table_wrong_scope_is_not_found(result) -> None:
    args = {"result_id": result.result_id}

    error = _error(validate_present_table, args, scope="other-scope")

    assert error.code == "RESULT_NOT_FOUND"


def test_simulation_unknown_result_id_is_not_found() -> None:
    args = {"scenario": "s", "summary": "su", "kpis": [], "result_id": "0" * 32}

    error = _error(validate_present_simulation, args)

    assert error.code == "RESULT_NOT_FOUND" and error.details["path"] == "$.result_id"


# ---- 실제 저장 결과에 대한 교차 검증 ----


def test_chart_unknown_column_reports_invalid_column_role_or_not_found(result) -> None:
    args = {
        "result_id": result.result_id,
        "chart_type": "bar",
        "x_column": "not_a_column",
        "y_column": "qty",
    }

    error = _error(validate_present_chart, args)

    assert error.code == "COLUMN_NOT_FOUND"


def test_chart_aggregation_required_when_grain_duplicates(result) -> None:
    args = {
        "result_id": result.result_id,
        "chart_type": "bar",
        "x_column": "work_month",
        "y_column": "qty",
    }

    error = _error(validate_present_chart, args)

    assert error.code == "AGGREGATION_REQUIRED"


def test_chart_non_numeric_y_column_reports_invalid_column_role(result) -> None:
    args = {
        "result_id": result.result_id,
        "chart_type": "bar",
        "x_column": "work_month",
        "y_column": "line",
        "group_by_column": None,
    }

    error = _error(validate_present_chart, args)

    assert error.code == "INVALID_COLUMN_ROLE"


def test_table_duplicate_columns_are_rejected(result) -> None:
    args = {"result_id": result.result_id, "columns": ["qty", "qty"]}

    error = _error(validate_present_table, args)

    assert error.code == "INVALID_PROP" and error.details["path"] == "$.columns"


def test_table_missing_column_is_reported(result) -> None:
    args = {"result_id": result.result_id, "columns": ["not_a_column"]}

    error = _error(validate_present_table, args)

    assert error.code == "COLUMN_NOT_FOUND"
    assert error.details["columns"] == ["not_a_column"]


def test_tool_returns_safe_error_payload(result) -> None:
    args = {
        "result_id": result.result_id,
        "chart_type": "bar",
        "x_column": "work_month",
        "y_column": "qty",
    }

    payload = asyncio.run(present_chart(args, access_scope=SCOPE))

    assert payload["status"] == "error" and payload["code"] == "AGGREGATION_REQUIRED"


# ---- Tool schema 형태 ----


def test_input_schemas_are_flat_scalar_objects() -> None:
    for schema in (
        present_sql_preview_input_schema(),
        present_chart_input_schema(),
        present_table_input_schema(),
        present_simulation_input_schema(),
    ):
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        for prop_schema in schema["properties"].values():
            # 재귀($ref)나 문자열-속-JSON 없이 scalar/array-of-scalar/object(kpi)만 쓴다.
            kind = prop_schema.get("type") or {
                option.get("type") for option in prop_schema.get("anyOf", [])
            }
            assert kind, prop_schema


def test_present_chart_schema_requires_core_fields() -> None:
    schema = present_chart_input_schema()

    assert set(schema["required"]) == {"result_id", "chart_type", "x_column", "y_column"}
    assert schema["properties"]["chart_type"]["enum"] == ["bar", "line", "area"]


def test_present_simulation_schema_requires_scenario_summary_kpis() -> None:
    schema = present_simulation_input_schema()

    assert set(schema["required"]) == {"scenario", "summary", "kpis"}
    assert "result_id" not in schema["required"]


# ---- 등록 ----


def test_present_tools_are_always_registered() -> None:
    names = {t.name for t in planning_tools()}

    assert {"present_sql_preview", "present_chart", "present_table", "present_simulation"} <= names
    assert not {"prepare_table", "prepare_visualization"} & names


def test_tool_names_prefixes_present_tools() -> None:
    names = tool_names()

    for short in ("present_sql_preview", "present_chart", "present_table", "present_simulation"):
        assert f"mcp__planning__{short}" in names


def test_tool_catalog_advertises_present_schema() -> None:
    catalog = asyncio.run(tool_catalog())
    by_name = {item["name"]: item for item in catalog}

    for short in ("present_sql_preview", "present_chart", "present_table", "present_simulation"):
        assert short in by_name
        assert by_name[short]["input_schema"]["type"] == "object"
        assert by_name[short]["status"] == "available"
