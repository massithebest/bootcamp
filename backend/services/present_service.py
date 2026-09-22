"""`present` Tool의 UI 트리 vocabulary와 검증.

Claude에는 재귀 ``$ref`` Tool schema 호환성 문제를 피하도록 UI node 전체를
``tree`` JSON 문자열로 받는다. 문자열 안의 node는 assistant-ui Generative
UI의 표준 ``$type``/``$key`` 트리다. 과거 ``component``/``nodeKey`` wire node는
호환 입력으로만 정규화한다. 원본 행·차트 데이터·HTML·URL·
이벤트/action prop은 받지 않으며, ``resultId``와 chart 설정은 실제 저장
결과에 대해 재검증한다.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

from services.chart_projection import AGGREGATIONS, CHART_TYPES
from services.query_result_errors import QueryResultError
from services.query_result_service import check_accessible, read_chart
from services.service_logging import logged_service_operation


PRESENT_MAX_BYTES = 64 * 1024
PRESENT_MAX_DEPTH = 8
PRESENT_MAX_NODES = 50
DEFAULT_MAX_STRING = 2000
SQL_MAX_STRING = 20_000
RESULT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

TYPE_KEY = "$type"
KEY_KEY = "$key"
WIRE_TYPE_KEY = "component"
WIRE_KEY_KEY = "nodeKey"
WIRE_TREE_KEY = "tree"
_DATA_PROP_NAMES = {"rows", "data", "series", "values", "items", "table", "results", "records"}

def _string(max_length: int = DEFAULT_MAX_STRING) -> dict[str, Any]:
    return {"type": "string", "maxLength": max_length}


def _enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


def _number(minimum: float, maximum: float) -> dict[str, Any]:
    return {"type": "number", "minimum": minimum, "maximum": maximum}


_RESULT_ID = {
    "type": "string",
    "pattern": "^[0-9a-f]{32}$",
    "description": "execute_sql·run_simulation 결과의 result_id(32자 소문자 hex).",
}
_KPIS = {
    "type": "array",
    "maxItems": 12,
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


@dataclass(frozen=True)
class Component:
    description: str
    props: dict[str, dict[str, Any]] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    #: "any": 문자열·node 자식 허용, "result": QueryChart/QueryTable node만, "none": 자식 없음
    children: str = "none"


VOCABULARY: dict[str, Component] = {
    "Card": Component(
        "제목이 있는 관련 내용 묶음.",
        {"title": _string(120), "padding": _number(0, 8)},
        children="any",
    ),
    "SqlPreview": Component(
        "실행한 SQL 원문(기본 접힘).",
        {"sql": _string(SQL_MAX_STRING), "title": _string(120)},
        ("sql",),
    ),
    "QueryChart": Component(
        "저장 결과를 서버가 집계한 차트. 데이터는 넣지 않고 컬럼 설정만 지정한다.",
        {
            "resultId": _RESULT_ID,
            "chartType": _enum(list(CHART_TYPES)),
            "xColumn": _string(200),
            "yColumn": _string(200),
            "groupByColumn": {"anyOf": [_string(200), {"type": "null"}]},
            "aggregation": _enum(list(AGGREGATIONS)),
            "title": _string(120),
        },
        ("resultId", "chartType", "xColumn", "yColumn"),
    ),
    "QueryTable": Component(
        "저장 결과를 페이지 단위로 보여 주는 표. 데이터는 넣지 않는다.",
        {
            "resultId": _RESULT_ID,
            "columns": {"type": "array", "items": _string(200), "maxItems": 50},
            "title": _string(120),
        },
        ("resultId",),
    ),
    "SimulationSummary": Component(
        "시뮬레이션 시나리오·요약과 KPI. 자식으로 QueryChart/QueryTable만 둘 수 있다.",
        {
            "scenario": _string(200),
            "summary": _string(),
            "kpis": _KPIS,
            "resultId": _RESULT_ID,
        },
        ("scenario", "summary", "kpis"),
        children="result",
    ),
}


def _schema_hint(schema: dict[str, Any]) -> str:
    """Opaque ``tree`` 문자열에서도 모델이 prop 타입을 알 수 있게 요약한다."""

    if "enum" in schema:
        return "|".join(json.dumps(value, ensure_ascii=False) for value in schema["enum"])
    if "anyOf" in schema:
        return "|".join(_schema_hint(option) for option in schema["anyOf"])
    kind = schema.get("type", "unknown")
    if kind == "array":
        return f"{_schema_hint(schema['items'])}[]"
    if kind == "object":
        required = set(schema.get("required", []))
        fields = ",".join(
            f"{name}{'' if name in required else '?'}:{_schema_hint(child)}"
            for name, child in schema.get("properties", {}).items()
        )
        return "{" + fields + "}"
    if kind == "number":
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None or maximum is not None:
            return f"number[{minimum if minimum is not None else ''}..{maximum if maximum is not None else ''}]"
    return str(kind)


def _component_schema_hint(name: str, component: Component) -> str:
    required = set(component.required)
    props = ", ".join(
        f"{prop}{'' if prop in required else '?'}:{_schema_hint(schema)}"
        for prop, schema in component.props.items()
    ) or "props 없음"
    children = {
        "none": "children 금지",
        "any": "children: text|node|node[] 선택",
        "result": "children: QueryChart|QueryTable node[] 선택",
    }[component.children]
    return f"{name}({props}; {children})"


def present_input_schema() -> dict[str, Any]:
    """`present` Tool에 광고하는 provider-호환 JSON Schema를 만든다.

    assistant-ui의 원래 schema는 ``children``을 ``$defs``로 재귀 표현한다.
    현재 Claude Code/MCP 경계에서는 해당 입력이 ``children`` JSON 문자열로
    변형되고 root의 필수 ``component``가 누락될 수 있어, 재귀 구조는 한
    ``tree`` 문자열 안에 담는다. 파싱 후의 node는 아래 실행 경계에서
    동일한 vocabulary·크기·깊이·Result Store 규칙으로 검증한다.
    """

    contract = "; ".join(
        _component_schema_hint(name, component)
        for name, component in VOCABULARY.items()
    )
    return {
        "type": "object",
        "properties": {
            WIRE_TREE_KEY: {
                "type": "string",
                "maxLength": PRESENT_MAX_BYTES,
                "description": (
                    "UI root node 하나를 JSON으로 직렬화한 문자열. "
                    "모든 node는 $type을 포함하고 $key는 선택이며 "
                    "children으로 중첩한다. JSON 배열이 아니라 root 객체를 넣는다. "
                    "각 $type에 적힌 prop만 사용하고 ?는 선택 prop이다. "
                    f"허용 계약: {contract}."
                ),
            },
        },
        "required": [WIRE_TREE_KEY],
        "additionalProperties": False,
    }


def decode_present_input(args: Any) -> dict[str, Any]:
    """Provider Tool args의 ``tree`` JSON을 canonical assistant-ui node로 바꾼다."""

    if not isinstance(args, dict):
        raise _fail("INVALID_UI_TREE", "present 입력은 객체여야 합니다.", "$")
    if set(args) != {WIRE_TREE_KEY}:
        unknown = next((key for key in args if key != WIRE_TREE_KEY), WIRE_TREE_KEY)
        raise _fail("INVALID_UI_TREE", "tree JSON 문자열 하나만 전달해야 합니다.", f"$.{unknown}")
    raw = args.get(WIRE_TREE_KEY)
    if not isinstance(raw, str):
        raise _fail("INVALID_UI_TREE", "tree는 JSON 문자열이어야 합니다.", f"$.{WIRE_TREE_KEY}")
    if len(raw.encode("utf-8")) > PRESENT_MAX_BYTES:
        raise _fail("UI_LIMIT_EXCEEDED", "UI 트리가 너무 큽니다(최대 64 KiB).", f"$.{WIRE_TREE_KEY}")
    try:
        node = json.loads(raw)
    except (TypeError, ValueError):
        raise _fail("INVALID_UI_TREE", "tree가 올바른 JSON이 아닙니다.", f"$.{WIRE_TREE_KEY}") from None
    if not isinstance(node, dict):
        raise _fail("INVALID_UI_TREE", "tree의 root는 UI node 객체여야 합니다.", f"$.{WIRE_TREE_KEY}")
    # 이전 component/nodeKey wire node도 진행 중 session 호환을 위해 받되,
    # 신규 Tool schema·지침은 assistant-ui 표준 $type/$key만 생성한다.
    return to_assistant_ui_tree(node)


def to_assistant_ui_tree(node: Any) -> Any:
    """Tool wire tree를 assistant-ui Generative UI의 ``$type`` tree로 변환한다.

    재귀 UI node가 허용되는 ``children``만 순회한다. 예를 들어 ``kpis`` 안의 일반
    객체는 UI node가 아니므로 그 내부 필드까지 잘못 변환하지 않는다. 입력 객체는
    변경하지 않는다.
    """

    if not isinstance(node, dict):
        return node

    converted = dict(node)
    if WIRE_TYPE_KEY in converted:
        converted[TYPE_KEY] = converted.pop(WIRE_TYPE_KEY)
    if WIRE_KEY_KEY in converted:
        converted[KEY_KEY] = converted.pop(WIRE_KEY_KEY)

    if "children" in converted:
        children = converted["children"]
        if isinstance(children, list):
            converted["children"] = [
                to_assistant_ui_tree(child) if isinstance(child, dict) else child
                for child in children
            ]
        elif isinstance(children, dict):
            converted["children"] = to_assistant_ui_tree(children)

    return converted


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


def _check_value(value: Any, schema: dict[str, Any], path: str) -> None:
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                _check_value(value, option, path)
                return
            except PresentError:
                continue
        raise _fail("INVALID_PROP", "prop 값이 허용된 형식이 아닙니다.", path)
    kind = schema["type"]
    if kind == "null":
        if value is not None:
            raise _fail("INVALID_PROP", "null이어야 합니다.", path)
    elif kind == "string":
        if not isinstance(value, str):
            raise _fail("INVALID_PROP", "문자열이어야 합니다.", path)
        if len(value) > schema.get("maxLength", DEFAULT_MAX_STRING):
            raise _fail("UI_LIMIT_EXCEEDED", "문자열이 너무 깁니다.", path)
        if "enum" in schema and value not in schema["enum"]:
            raise _fail("INVALID_PROP", "허용되지 않은 값입니다.", path, allowed=schema["enum"])
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise _fail("INVALID_PROP", "형식이 올바르지 않습니다.", path)
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise _fail("INVALID_PROP", "유한한 숫자여야 합니다.", path)
        if not schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf):
            raise _fail("INVALID_PROP", "허용 범위를 벗어났습니다.", path)
    elif kind == "array":
        if not isinstance(value, list):
            raise _fail("INVALID_PROP", "배열이어야 합니다.", path)
        if len(value) > schema.get("maxItems", 100):
            raise _fail("UI_LIMIT_EXCEEDED", "배열 항목이 너무 많습니다.", path)
        for index, item in enumerate(value):
            _check_value(item, schema["items"], f"{path}[{index}]")
    elif kind == "object":
        if not isinstance(value, dict):
            raise _fail("INVALID_PROP", "객체여야 합니다.", path)
        allowed = schema.get("properties", {})
        for key in value:
            if key not in allowed:
                raise _fail("UNKNOWN_PROP", "허용되지 않은 필드입니다.", f"{path}.{key}")
        for key in schema.get("required", []):
            if key not in value:
                raise _fail("INVALID_PROP", "필수 필드가 없습니다.", f"{path}.{key}")
        for key, item in value.items():
            _check_value(item, allowed[key], f"{path}.{key}")


class _Walk:
    def __init__(self) -> None:
        self.nodes = 0
        self.charts: list[tuple[str, dict[str, Any]]] = []
        self.tables: list[tuple[str, dict[str, Any]]] = []
        self.results: list[tuple[str, str]] = []


def _walk(node: Any, path: str, depth: int, state: _Walk, *, only_query: bool = False) -> None:
    if depth > PRESENT_MAX_DEPTH:
        raise _fail("UI_LIMIT_EXCEEDED", f"트리 깊이는 {PRESENT_MAX_DEPTH} 이하여야 합니다.", path)
    state.nodes += 1
    if state.nodes > PRESENT_MAX_NODES:
        raise _fail("UI_LIMIT_EXCEEDED", f"node는 {PRESENT_MAX_NODES}개 이하여야 합니다.", path)
    if not isinstance(node, dict):
        raise _fail("INVALID_UI_TREE", "UI node는 객체여야 합니다.", path)
    type_name = node.get(TYPE_KEY)
    if not isinstance(type_name, str) or type_name not in VOCABULARY:
        raise _fail(
            "UNKNOWN_COMPONENT",
            "허용되지 않은 $type입니다.",
            f"{path}.{TYPE_KEY}",
            allowed=list(VOCABULARY),
        )
    if only_query and type_name not in {"QueryChart", "QueryTable"}:
        raise _fail(
            "INVALID_UI_TREE",
            "SimulationSummary의 자식은 QueryChart/QueryTable만 가능합니다.",
            path,
        )
    component = VOCABULARY[type_name]

    for key, value in node.items():
        here = f"{path}.{key}"
        if key == TYPE_KEY or key == "children":
            continue
        if key == KEY_KEY:
            if isinstance(value, bool) or not isinstance(value, (str, int, float)) or (
                isinstance(value, str) and len(value) > 64
            ):
                raise _fail("INVALID_PROP", "$key는 64자 이하 문자열 또는 숫자여야 합니다.", here)
            continue
        if key.startswith("$"):
            raise _fail("UNKNOWN_PROP", "예약된 $ prop은 사용할 수 없습니다.", here)
        if key in _DATA_PROP_NAMES:
            raise _fail(
                "DATA_NOT_ALLOWED",
                "원본·차트 데이터를 넣을 수 없습니다. resultId만 전달하세요.",
                here,
            )
        if key not in component.props:
            raise _fail("UNKNOWN_PROP", f"{type_name}에서 허용되지 않은 prop입니다.", here)
        _check_value(value, component.props[key], here)
    for name in component.required:
        if name not in node:
            raise _fail("INVALID_PROP", f"{type_name}에 필수 prop이 없습니다.", f"{path}.{name}")

    if type_name == "QueryChart":
        state.charts.append((path, node))
        state.results.append((path, node["resultId"]))
    elif type_name == "QueryTable":
        state.tables.append((path, node))
        state.results.append((path, node["resultId"]))
    elif type_name == "SimulationSummary" and "resultId" in node:
        state.results.append((path, node["resultId"]))

    if "children" in node:
        if component.children == "none":
            raise _fail("INVALID_UI_TREE", f"{type_name}은 자식을 가질 수 없습니다.", f"{path}.children")
        children = node["children"]
        items = children if isinstance(children, list) else [children]
        for index, child in enumerate(items):
            child_path = f"{path}.children[{index}]" if isinstance(children, list) else f"{path}.children"
            if isinstance(child, str):
                if component.children == "result":
                    raise _fail(
                        "INVALID_UI_TREE",
                        "SimulationSummary의 자식은 QueryChart/QueryTable만 가능합니다.",
                        child_path,
                    )
                if len(child) > DEFAULT_MAX_STRING:
                    raise _fail("UI_LIMIT_EXCEEDED", "문자열이 너무 깁니다.", child_path)
                state.nodes += 1
                if state.nodes > PRESENT_MAX_NODES:
                    raise _fail(
                        "UI_LIMIT_EXCEEDED", f"node는 {PRESENT_MAX_NODES}개 이하여야 합니다.", child_path
                    )
                continue
            _walk(child, child_path, depth + 1, state, only_query=component.children == "result")


@logged_service_operation
def validate_present(node: Any, *, access_scope: str | None) -> dict[str, Any]:
    """UI 트리를 검증한다. 성공하면 빈 dict, 실패하면 ``PresentError``를 던진다."""

    try:
        size = len(json.dumps(node, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        raise _fail("INVALID_UI_TREE", "JSON으로 직렬화할 수 없는 값이 있습니다.", "$") from None
    if size > PRESENT_MAX_BYTES:
        raise _fail("UI_LIMIT_EXCEEDED", "UI 트리가 너무 큽니다(최대 64 KiB).", "$")

    state = _Walk()
    _walk(node, "$", 1, state)

    try:
        checked: dict[str, Any] = {}
        for path, result_id in state.results:
            if result_id not in checked:
                try:
                    checked[result_id] = check_accessible(result_id, access_scope)
                except QueryResultError as exc:
                    raise _fail(exc.code, exc.message, f"{path}.resultId") from None
        for path, table in state.tables:
            names = table.get("columns")
            if names is None:
                continue
            available = [column.name for column in checked[table["resultId"]].columns]
            if len(set(names)) != len(names):
                raise _fail("INVALID_PROP", "columns에 같은 컬럼을 중복 지정할 수 없습니다.", f"{path}.columns")
            missing = [name for name in names if name not in available]
            if missing:
                raise _fail(
                    "COLUMN_NOT_FOUND",
                    "조회 결과에 없는 컬럼이 지정되었습니다.",
                    f"{path}.columns",
                    columns=missing,
                )
        for path, chart in state.charts:
            try:
                read_chart(
                    chart["resultId"],
                    chart_type=chart["chartType"],
                    x_column=chart["xColumn"],
                    y_column=chart["yColumn"],
                    group_by_column=chart.get("groupByColumn"),
                    aggregation=chart.get("aggregation"),
                    title=chart.get("title"),
                    access_scope=access_scope,
                )
            except QueryResultError as exc:
                raise _fail(exc.code, exc.message, path, **(exc.details or {})) from None
    except QueryResultError as exc:
        raise _fail(exc.code, exc.message, "$", **(exc.details or {})) from None
    return {}
