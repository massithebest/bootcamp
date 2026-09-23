"""종류별 편집 가이드. pydantic 모델에서 필드 구조를 뽑고 라벨·도움말·예시를 덧붙인다.

폼 화면은 이 명세만으로 입력 위젯을 그린다. 구조(필수·타입·enum)는 모델이 기준이고
문구만 이 파일이 소유한다. 예시는 입력 형식을 보여 주는 placeholder 이며
특정 데이터에 종속된 답변이나 값을 담지 않는다.
"""

from __future__ import annotations

import types
from datetime import date
from functools import lru_cache
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from services.knowledge.catalog import KIND_SPECS

# (라벨, 도움말, 예시, 그룹). 그룹은 최상위 필드에만 쓴다.
_META = {
    "active": ("사용 여부", "끄면 Agent 검색·Tool·SQL 허용 목록에서 제외됩니다.", None, "관리 정보"),
    "status": ("검토 상태", "승인하면 verified 로 바뀝니다. 직접 바꿀 수 없습니다.", None, "관리 정보"),
    "owner": ("담당자", "이 지식을 관리하는 사람이나 팀. 비우면 작성자로 채워집니다.", "생산관리팀", "관리 정보"),
    "updated": ("수정일", "승인 시 자동으로 기록됩니다.", None, "관리 정보"),
    "source": ("근거·출처", "확인한 원본 자료나 검토 근거. 비밀값·사내 URL은 적지 않습니다.", "설비 마스터 정의서 v2", "관리 정보"),
}

_RULES = "규칙·가이드"
_RULE_FIELDS = {
    "query_rules": ("조회 규칙", "기본 날짜·필터·정렬·조인 전제. 조회 전에 지켜야 할 조건만 적습니다.", "기간 조건은 기준 시각 컬럼으로 건다", _RULES),
    "aggregation_rules": ("집계 규칙", "grain, 집계 함수, 중복 제거, 재집계 방법. 표현 권고는 적지 않습니다.", "건수는 키 기준 COUNT(DISTINCT)로 센다", _RULES),
    "visualization_hints": ("시각화 안내", "어떤 차트가 적합한지에 대한 표현 권고만 적습니다.", "항목별 비교에는 bar 차트가 적합하다", _RULES),
}
_SAMPLE = {
    "sample_queries": ("SQL 예시", "질문과 실행 가능한 SQL만 저장합니다. 현재 데이터 값(답변)은 적지 않습니다.", None, _RULES),
    "sample_queries.question": ("질문", "사용자가 물을 법한 자연어 질문", "라인별 건수는?", None),
    "sample_queries.sql": ("SQL", "읽기 전용 SELECT 만 허용됩니다.", "SELECT ... FROM ...", None),
}

GUIDES: dict[str, dict[str, tuple[str, str, str | None, str | None]]] = {
    "table": {
        "table": ("테이블명", "SQL 에서 쓰는 실제 테이블 이름. 저장 후에는 바꿀 수 없습니다.", "lot_status", "기본 정보"),
        "description": ("설명", "이 테이블이 무엇을 담는지 한두 문장으로 적습니다.", "Lot별 현재 진행 상태", "기본 정보"),
        "grain": ("행 단위(grain)", "한 행을 유일하게 정하는 컬럼들.", "lot_id", "기본 정보"),
        "time_column": ("기준 시각 컬럼", "기간 조건에 쓰는 기본 시각 컬럼. 없으면 비웁니다.", "event_time", "기본 정보"),
        "tags": ("태그", "검색에 쓰는 키워드.", "재공", "기본 정보"),
        "columns": ("컬럼", "테이블의 모든 컬럼을 적습니다.", None, "구조"),
        "columns.name": ("컬럼명", "", "lot_id", None),
        "columns.type": ("타입", "SQL 타입", "varchar", None),
        "columns.desc": ("설명", "", "Lot 식별자", None),
        "columns.ref": ("참조", "다른 테이블 컬럼을 가리키면 TABLE.column 형태로 적습니다.", "part.part_id", None),
        "columns.codes": ("코드 값", "코드 값과 의미의 대응표.", None, None),
        "joins": ("조인", "다른 테이블과의 관계.", None, "구조"),
        "joins.to": ("대상 테이블", "", "part", None),
        "joins.on": ("조인 컬럼", "여러 개면 모두 조인 조건에 포함됩니다.", "part_id", None),
        "joins.kind": ("관계", "many-to-one, one-to-many 등", "many-to-one", None),
        "joins.note": ("비고", "", None, None),
        "caveats": ("주의사항", "데이터를 해석할 때 놓치기 쉬운 점.", "빈 값은 NULL 로 저장된다", "구조"),
        **_RULE_FIELDS,
        **_SAMPLE,
    },
    "kpi": {
        "kpi_id": ("KPI ID", "영문 식별자. 저장 후에는 바꿀 수 없습니다.", "on_time_rate", "기본 정보"),
        "name": ("이름", "", "납기 준수율", "기본 정보"),
        "aliases": ("별칭", "사용자가 부르는 다른 이름.", None, "기본 정보"),
        "definition": ("정의", "업무적으로 무엇을 뜻하는지.", None, "기본 정보"),
        "formula": ("산식", "", "준수 건수 / 전체 건수", "기본 정보"),
        "sources": ("원천 테이블", "산식이 읽는 카탈로그 테이블. 비활성 테이블이 있으면 KPI 도 숨겨집니다.", "lot_status", "구조"),
        "grain": ("집계 단위", "", "line", "구조"),
        "baseline": ("비교 기준", "무엇과 비교해 부진을 판단하는지.", None, "구조"),
        "shortfall_rule": ("부진 판단 규칙", "", None, "구조"),
        "sql_template": ("SQL 템플릿", "sources 에 적은 테이블만 사용합니다.", None, "구조"),
        "aggregation_rules": _RULE_FIELDS["aggregation_rules"],
        "recipe_refs": ("연결 recipe", "재사용할 recipe ID.", None, "관계"),
        "diagnostics": ("원인 진단", "부진 원인 가설과 확인 방법.", None, "관계"),
        "diagnostics.hypothesis": ("가설", "", None, None),
        "diagnostics.how": ("확인 방법", "sql 또는 simulation", None, None),
        "diagnostics.ref": ("대상", "sql 이면 테이블명 또는 recipes/<id>, simulation 이면 simulation type", None, None),
    },
    "recipe": {
        "recipe_id": ("Recipe ID", "영문 식별자. 저장 후에는 바꿀 수 없습니다.", "wip_by_part", "기본 정보"),
        "name": ("이름", "", None, "기본 정보"),
        "description": ("설명", "", None, "기본 정보"),
        "when_to_use": ("사용 시점", "이 recipe 를 써야 하는 질문 유형.", None, "기본 정보"),
        "cte_name": ("CTE 이름", "WITH 절에서 쓸 별칭.", "wip_by_part", "구조"),
        "cte_sql": ("CTE 본문", "WITH ... AS ( 와 ) 는 적지 않고 본문만 씁니다.", "SELECT ... FROM ...", "구조"),
        "sources": ("원천 테이블", "cte_sql 이 읽는 카탈로그 테이블.", None, "구조"),
        "output_grain": ("출력 grain", "output_columns 에 있는 컬럼이어야 합니다.", None, "구조"),
        "output_columns": ("출력 컬럼", "CTE 결과 컬럼의 의미.", None, "구조"),
        "output_columns.name": ("컬럼명", "", None, None),
        "output_columns.role": ("역할", "category / measure / time", None, None),
        "output_columns.unit": ("단위", "", "건", None),
        "output_columns.desc": ("설명", "", None, None),
        **_RULE_FIELDS,
        **_SAMPLE,
    },
    "simulation": {
        "type": ("Simulation type", "호출에 쓰는 식별자. 저장 후에는 바꿀 수 없습니다.", None, "기본 정보"),
        "name": ("이름", "", None, "기본 정보"),
        "aliases": ("별칭", "", None, "기본 정보"),
        "when_to_use": ("사용 시점", "어떤 상황에서 호출하는지.", None, "기본 정보"),
        "params": ("입력 파라미터", "이름별로 필수 여부와 설명을 적습니다.", None, "구조"),
        "params.required": ("필수", "", None, None),
        "params.description": ("설명", "", None, None),
        "params.example": ("예시 값", "", None, None),
        "output_schema": ("출력 스키마", "JSON 으로 적습니다.", None, "구조"),
        "aggregation_rules": _RULE_FIELDS["aggregation_rules"],
        "visualization_hints": _RULE_FIELDS["visualization_hints"],
        "follows": ("후속 simulation", "이 결과 다음에 이어서 쓰는 simulation type.", None, "관계"),
    },
    "glossary": {
        "term": ("용어", "저장 후에는 바꿀 수 없습니다.", None, "기본 정보"),
        "definition": ("정의", "", None, "기본 정보"),
        "aliases": ("별칭", "", None, "기본 정보"),
        "related_kpis": ("관련 KPI", "KPI ID 목록.", None, "관계"),
        "related_tables": ("관련 테이블", "", None, "관계"),
    },
    "scenario": {
        "scenario_id": ("Scenario ID", "저장 후에는 바꿀 수 없습니다.", None, "기본 정보"),
        "name": ("이름", "", None, "기본 정보"),
        "description": ("설명", "", None, "기본 정보"),
        "dataset": ("데이터셋", "", None, "기본 정보"),
        "question": ("검증 질문", "", None, "기본 정보"),
        "steps": ("단계", "recipe 또는 simulation 을 차례로 적습니다.", None, "구조"),
        "steps.action": ("종류", "recipe 또는 simulation", None, None),
        "steps.ref": ("대상 ID", "", None, None),
        "steps.params": ("파라미터", "", None, None),
        "steps.expectation": ("기대 결과", "", None, None),
        "expected": ("기대값", "고정 검증 데이터에서 바뀌면 안 되는 최소 값.", None, "구조"),
        "expected.table_counts": ("테이블별 건수", "", None, None),
        "expected.unmatched_rows": ("관계별 미매칭 건수", "", None, None),
    },
}

_TEXT_FIELDS = {"description", "definition", "formula", "baseline", "shortfall_rule", "expectation", "question", "when_to_use"}
_SQL_FIELDS = {"sql", "cte_sql", "sql_template"}
#: 문장 하나가 한 줄을 넘기 쉬운 목록 필드. 화면은 여러 줄 입력으로 그린다.
_TEXT_LIST_FIELDS = {"caveats", "when_to_use", "query_rules", "aggregation_rules", "visualization_hints"}
_READONLY = {"status", "updated"}


def _unwrap(annotation: Any) -> tuple[Any, bool]:
    """`X | None` 을 벗겨 (X, nullable)을 돌려준다."""

    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0], True
    return annotation, False


def _scalar_widget(annotation: Any) -> dict[str, Any] | None:
    if annotation is str:
        return {"widget": "string"}
    if annotation is bool:
        return {"widget": "boolean"}
    if annotation is int:
        return {"widget": "number"}
    if annotation is date:
        return {"widget": "date"}
    if get_origin(annotation) is Literal:
        return {"widget": "enum", "options": list(get_args(annotation))}
    return None


def _widget(annotation: Any, prefix: str, kind: str) -> dict[str, Any]:
    annotation, _ = _unwrap(annotation)
    scalar = _scalar_widget(annotation)
    if scalar:
        return scalar
    origin = get_origin(annotation)
    args = get_args(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {"widget": "object", "fields": _model_fields(annotation, prefix, kind)}
    if origin is list:
        item, _ = _unwrap(args[0])
        if item is str:
            return {"widget": "string_list"}
        if isinstance(item, type) and issubclass(item, BaseModel):
            return {"widget": "record_list", "fields": _model_fields(item, prefix, kind)}
    if origin in (Union, types.UnionType):  # str | list[str]
        return {"widget": "string_list"}
    if origin is dict:
        value, _ = _unwrap(args[1])
        if isinstance(value, type) and issubclass(value, BaseModel):
            return {"widget": "map", "value": {"widget": "object", "fields": _model_fields(value, prefix, kind)}}
        scalar = _scalar_widget(value)
        if scalar:
            return {"widget": "map", "value": scalar}
    return {"widget": "json"}


def _model_fields(model: type[BaseModel], prefix: str, kind: str) -> list[dict[str, Any]]:
    fields = []
    for name, info in model.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        label, helper, example, group = GUIDES.get(kind, {}).get(path) or _META.get(name) or (name, "", None, None)
        spec = _widget(info.annotation, path, kind)
        if spec["widget"] == "string_list":
            spec["item_widget"] = "text" if name in _TEXT_LIST_FIELDS and not prefix else "string"
        if spec["widget"] == "string":
            if name in _SQL_FIELDS:
                spec["widget"] = "sql"
            elif name in _TEXT_FIELDS and not prefix:
                spec["widget"] = "text"
        field: dict[str, Any] = {
            "name": name,
            "path": path,
            "label": label,
            "help": helper,
            "required": info.is_required(),
            "readonly": name in _READONLY,
            **spec,
        }
        if example:
            field["example"] = example
        if group and not prefix:
            field["group"] = group
        fields.append(field)
    return fields


@lru_cache(maxsize=None)
def field_specs(kind: str) -> tuple[dict[str, Any], ...]:
    fields = _model_fields(KIND_SPECS[kind].model, "", kind)
    # 키 필드가 앞에 오고 관리 메타는 끝에 온다. pydantic 은 부모(메타) 필드를 먼저 낸다.
    meta = [field for field in fields if field["name"] in _META]
    return tuple([field for field in fields if field["name"] not in _META] + meta)


def _blank(field: dict[str, Any]) -> Any:
    widget = field["widget"]
    if widget == "boolean":
        return field["name"] == "active"
    if widget == "enum":
        return field["options"][0]
    if widget == "record_list":
        return [{item["name"]: _blank(item) for item in field["fields"] if item["required"]}] if field["required"] else []
    if widget in ("string_list",):
        return []
    if widget in ("map", "json"):
        return {}
    if widget == "object":
        return {item["name"]: _blank(item) for item in field["fields"]}
    if widget == "number":
        return 0
    return ""


def blank_template(kind: str) -> dict[str, Any]:
    """필수 필드만 빈 값으로 채운 시작 골격. 데이터 값은 담지 않는다."""

    data = {field["name"]: _blank(field) for field in field_specs(kind) if field["required"]}
    data["active"] = True
    return data


def guide(kind: str) -> dict[str, Any]:
    spec = KIND_SPECS[kind]
    return {
        "kind": kind,
        "key_field": spec.key_field,
        "fields": list(field_specs(kind)),
        "template": blank_template(kind),
        "immutable": [spec.key_field],
    }


def shape_errors(kind: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """모델이 조용히 무시하는 오류를 필드 경로와 함께 돌려준다.

    알 수 없는 필드(오타 포함), 비어 있는 필수 문자열, 비어 있는 필수 목록이 대상이다.
    """

    errors: list[dict[str, Any]] = []

    def add(path: str, message: str) -> None:
        errors.append({"path": path, "line": None, "message": message})

    def walk(fields: list[dict[str, Any]], value: Any, path: str) -> None:
        if not isinstance(value, dict):
            return
        by_name = {field["name"]: field for field in fields}
        for raw_key in value:
            # YAML 1.1 은 따옴표 없는 `on:` 을 True 로 읽는다. Join 모델이 되돌리므로 허용한다.
            name = "on" if raw_key is True else raw_key
            if name not in by_name:
                add(f"{path}.{name}" if path else str(name), "알 수 없는 필드입니다.")
        for field in fields:
            current = value.get(field["name"], value.get(True) if field["name"] == "on" else None)
            where = f"{path}.{field['name']}" if path else field["name"]
            widget = field["widget"]
            if field["required"] and not field["readonly"]:
                blank = (
                    (widget in ("string", "text", "sql") and not str(current or "").strip())
                    or (widget in ("string_list", "record_list") and not current)
                )
                if blank:
                    add(where, f"{field['label']}은(는) 필수입니다.")
                    continue
            if widget == "record_list" and isinstance(current, list):
                for index, item in enumerate(current):
                    walk(field["fields"], item, f"{where}[{index}]")
            elif widget == "object":
                walk(field["fields"], current, where)
            elif widget == "map" and isinstance(current, dict) and field["value"]["widget"] == "object":
                for map_key, item in current.items():
                    walk(field["value"]["fields"], item, f"{where}.{map_key}")

    walk(list(field_specs(kind)), data, "")
    return errors
