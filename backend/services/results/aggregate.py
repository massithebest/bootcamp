"""저장된 결과를 그룹별로 다시 집계해 새 결과로 저장한다.

SQL로 다시 조회할 수 없는 결과(시뮬레이션 등)의 그룹별 합계·건수를 모델이 행을 읽어
직접 더하지 않도록 서버가 계산한다. 원본 결과는 바꾸지 않고, 같은 access scope의
새 ``result_id``를 만들어 ``present_table``·``present_chart``에 그대로 넘길 수 있게 한다.
기준 값이 비어 있는 행(예: swap이 없는 제품의 방향)은 그룹으로 만들지 않고 제외한 행 수만 알린다.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.results.errors import QueryResultError
from services.results.query import open_result, tool_preview
from services.results.store import ResultStore, get_result_store
from services.service_logging import logged_service_operation


AGGREGATIONS = ("sum", "count", "avg", "min", "max")
GROUP_BY_MAX_ITEMS = 3
#: 같은 기준으로 함께 집계할 추가 값 컬럼 수. 사이트별 계획·목표수량처럼 두 값을 한 표로 비교하려고
#: 모델이 결과 행을 SQL 리터럴로 옮겨 적어 합산했다(2026-11-04).
EXTRA_VALUE_MAX_ITEMS = 3
LABEL_MAX_LENGTH = 40
_PANDAS_AGGREGATION = {"sum": "sum", "count": "count", "avg": "mean", "min": "min", "max": "max"}
#: SQL 결과는 GROUP BY로 다시 조회하는 편이 정확하고 Tool 호출도 적다.
SQL_RESULT_SOURCE = "execute_sql"
_DEFAULT_LABEL = {"sum": "합계", "count": "건수", "avg": "평균", "min": "최소", "max": "최대"}


class AggregateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def aggregate_input_schema() -> dict[str, Any]:
    label = {"type": "string", "maxLength": LABEL_MAX_LENGTH}
    return {
        "type": "object",
        "properties": {
            "result_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "group_by": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "minItems": 1,
                "maxItems": GROUP_BY_MAX_ITEMS,
            },
            "value_column": {"type": "string", "maxLength": 200},
            "extra_value_columns": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "maxItems": EXTRA_VALUE_MAX_ITEMS,
            },
            "aggregation": {"type": "string", "enum": list(AGGREGATIONS)},
            "labels": {"type": "object", "additionalProperties": label},
        },
        "required": ["result_id", "group_by", "value_column", "aggregation"],
        "additionalProperties": False,
    }


def _output_names(
    group_by: list[str], value_columns: list[str], aggregation: str, labels: dict[str, str]
) -> tuple[list[str], list[str]]:
    groups = [str(labels.get(name) or name) for name in group_by]
    values = [str(labels.get(name) or f"{name} {_DEFAULT_LABEL[aggregation]}") for name in value_columns]
    names = [*groups, *values]
    if len(set(names)) != len(names):
        raise AggregateError("집계 결과의 컬럼 이름(labels)이 서로 겹칩니다.")
    return groups, values


def _aggregate(
    frame: pd.DataFrame, group_by: list[str], value_columns: list[str], aggregation: str
) -> tuple[pd.DataFrame, int]:
    missing = [name for name in [*group_by, *value_columns] if name not in frame.columns]
    if missing:
        raise AggregateError(f"결과에 없는 컬럼입니다: {', '.join(missing)}")
    if set(value_columns) & set(group_by):
        raise AggregateError("value_column은 group_by에 넣을 수 없습니다.")
    if len(set(value_columns)) != len(value_columns):
        raise AggregateError("값 컬럼(value_column·extra_value_columns)이 서로 겹칩니다.")
    work = frame[group_by].copy()
    keys = [f"__value{index}" for index in range(len(value_columns))]
    for key, name in zip(keys, value_columns):
        values = frame[name]
        if aggregation != "count":
            values = pd.to_numeric(values, errors="coerce")
            if values.notna().sum() == 0:
                raise AggregateError(f"{name}에 집계할 숫자 값이 없습니다.")
        work[key] = values
    blank = work[group_by].isna().any(axis=1)
    work = work[~blank]
    if work.empty:
        raise AggregateError("group_by 기준 값이 있는 행이 없습니다.")
    grouped = (
        work.groupby(group_by, sort=True)[keys]
        .agg(_PANDAS_AGGREGATION[aggregation])
        .reset_index()
    )
    if aggregation != "count":
        grouped[keys] = grouped[keys].round(6)
    return grouped, int(blank.sum())


@logged_service_operation
def aggregate_result(
    result_id: str,
    *,
    group_by: list[str],
    value_column: str,
    aggregation: str,
    extra_value_columns: list[str] | None = None,
    labels: dict[str, str] | None = None,
    access_scope: str | None,
    result_store: ResultStore | None = None,
) -> dict[str, Any]:
    if aggregation not in AGGREGATIONS:
        raise AggregateError(f"aggregation은 {', '.join(AGGREGATIONS)} 중 하나여야 합니다.")
    if not group_by or len(group_by) > GROUP_BY_MAX_ITEMS or len(set(group_by)) != len(group_by):
        raise AggregateError(f"group_by에는 서로 다른 컬럼을 1~{GROUP_BY_MAX_ITEMS}개 넣습니다.")
    if len(extra_value_columns or []) > EXTRA_VALUE_MAX_ITEMS:
        raise AggregateError(f"extra_value_columns에는 최대 {EXTRA_VALUE_MAX_ITEMS}개를 넣습니다.")
    value_columns = [value_column, *(extra_value_columns or [])]
    store = result_store or get_result_store()
    try:
        meta, frame = open_result(result_id, access_scope, store)
    except QueryResultError as exc:
        raise AggregateError(exc.message) from None
    if meta.source == SQL_RESULT_SOURCE:
        raise AggregateError(
            "SQL 조회 결과는 다시 집계하지 않습니다. 필요한 기준으로 GROUP BY 한 SQL을 다시 실행하세요."
        )

    grouped, excluded = _aggregate(frame, group_by, value_columns, aggregation)
    groups, values = _output_names(group_by, value_columns, aggregation, labels or {})
    grouped.columns = [*groups, *values]
    rows = [[None if pd.isna(cell) else cell for cell in row] for row in grouped.itertuples(index=False)]
    saved = store.save(
        [*groups, *values],
        rows,
        source=f"aggregate_result:{meta.source}",
        conversation_id=meta.conversation_id,
        source_truncated=meta.source_truncated,
        access_scope=meta.access_scope,
    )
    return tool_preview(
        saved,
        store.load(saved.result_id),
        kind="database",
        source_result_id=result_id,
        source_row_count=meta.row_count,
        excluded_blank_group_rows=excluded,
    )
