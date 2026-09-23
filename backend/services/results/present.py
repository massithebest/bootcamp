"""`present_*` Tool들의 인자 schema와 결과 교차 검증.

각 Tool은 UI vocabulary 컴포넌트 하나(SqlPreview/QueryChart/QueryTable/
SimulationSummary)에 대응하는 평평한(scalar) 인자만 받는다. 型·enum·필수 여부는
Claude Agent SDK가 이 모듈이 만든 JSON Schema로 호출 전에 강제 검증하므로, 여기서는
``result_id``의 접근 권한과 실제 저장 결과(컬럼·grain)에 대한 교차 검증만 한다.
원본 행·차트 데이터·HTML·URL·이벤트/action prop은 애초에 어떤 Tool schema에도 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.results.chart import AGGREGATIONS, CHART_TYPES
from services.results.errors import QueryResultError
from services.results.query import check_accessible, read_chart
from services.service_logging import logged_service_operation


SQL_MAX_STRING = 20_000
TITLE_MAX_STRING = 120
DEFAULT_MAX_STRING = 2000
KPI_MAX_ITEMS = 12
COLUMNS_MAX_ITEMS = 50


def _string(max_length: int = DEFAULT_MAX_STRING) -> dict[str, Any]:
    return {"type": "string", "maxLength": max_length}


def _enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


_RESULT_ID = {
    "type": "string",
    "pattern": "^[0-9a-f]{32}$",
    "description": "execute_sql·run_simulation 결과의 result_id(32자 소문자 hex).",
}
_KPIS = {
    "type": "array",
    "maxItems": KPI_MAX_ITEMS,
    "items": {
        "type": "object",
        "properties": {
            "label": _string(80),
            "value": {"anyOf": [_string(80), {"type": "number"}]},
            "unit": _string(20),
        },
        "required": ["label", "value"],
        "additionalProperties": False,
    },
}


def present_sql_preview_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"sql": _string(SQL_MAX_STRING), "title": _string(TITLE_MAX_STRING)},
        "required": ["sql"],
        "additionalProperties": False,
    }


def present_chart_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "result_id": _RESULT_ID,
            "chart_type": _enum(list(CHART_TYPES)),
            "x_column": _string(200),
            "y_column": _string(200),
            "group_by_column": {"anyOf": [_string(200), {"type": "null"}]},
            "aggregation": _enum(list(AGGREGATIONS)),
            "title": _string(TITLE_MAX_STRING),
        },
        "required": ["result_id", "chart_type", "x_column", "y_column"],
        "additionalProperties": False,
    }


def present_table_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "result_id": _RESULT_ID,
            "columns": {"type": "array", "items": _string(200), "maxItems": COLUMNS_MAX_ITEMS},
            "title": _string(TITLE_MAX_STRING),
        },
        "required": ["result_id"],
        "additionalProperties": False,
    }


def present_simulation_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "scenario": _string(200),
            "summary": _string(),
            "kpis": _KPIS,
            "result_id": _RESULT_ID,
        },
        "required": ["scenario", "summary", "kpis"],
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class PresentError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def as_tool_result(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


def _fail(code: str, message: str, path: str, **details: Any) -> PresentError:
    return PresentError(code, message, {"path": path, **details})


@logged_service_operation
def validate_present_sql_preview(
    args: dict[str, Any], *, access_scope: str | None
) -> dict[str, Any]:
    """``SqlPreview``는 원문을 그대로 보여줄 뿐 결과 조회가 필요 없다."""

    return {}


@logged_service_operation
def validate_present_chart(args: dict[str, Any], *, access_scope: str | None) -> dict[str, Any]:
    result_id = args["result_id"]
    try:
        check_accessible(result_id, access_scope)
    except QueryResultError as exc:
        raise _fail(exc.code, exc.message, "$.result_id") from None
    try:
        read_chart(
            result_id,
            chart_type=args["chart_type"],
            x_column=args["x_column"],
            y_column=args["y_column"],
            group_by_column=args.get("group_by_column"),
            aggregation=args.get("aggregation"),
            title=args.get("title"),
            access_scope=access_scope,
        )
    except QueryResultError as exc:
        raise _fail(exc.code, exc.message, "$", **(exc.details or {})) from None
    return {}


@logged_service_operation
def validate_present_table(args: dict[str, Any], *, access_scope: str | None) -> dict[str, Any]:
    result_id = args["result_id"]
    try:
        meta = check_accessible(result_id, access_scope)
    except QueryResultError as exc:
        raise _fail(exc.code, exc.message, "$.result_id") from None
    names = args.get("columns")
    if names is not None:
        if len(set(names)) != len(names):
            raise _fail(
                "INVALID_PROP", "columns에 같은 컬럼을 중복 지정할 수 없습니다.", "$.columns"
            )
        available = [column.name for column in meta.columns]
        missing = [name for name in names if name not in available]
        if missing:
            raise _fail(
                "COLUMN_NOT_FOUND",
                "조회 결과에 없는 컬럼이 지정되었습니다.",
                "$.columns",
                columns=missing,
            )
    return {}


@logged_service_operation
def validate_present_simulation(
    args: dict[str, Any], *, access_scope: str | None
) -> dict[str, Any]:
    result_id = args.get("result_id")
    if result_id:
        try:
            check_accessible(result_id, access_scope)
        except QueryResultError as exc:
            raise _fail(exc.code, exc.message, "$.result_id") from None
    return {}
