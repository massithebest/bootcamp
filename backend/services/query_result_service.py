"""저장된 조회 결과의 preview·table·chart를 접근 제어와 함께 읽는다.

모든 함수는 읽기 전용이며 새 파일을 저장하지 않는다. 없음·만료·다른 scope·손상은
동일한 ``RESULT_NOT_FOUND``로 통일해 다른 세션 결과의 존재 여부를 노출하지 않는다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from services.chart_projection import _json_value, project_chart
from services.query_result_errors import QueryResultError, query_error
from services.result_store import (
    ResultMeta,
    ResultStore,
    dataframe_rows,
    get_result_store,
)
from services.service_logging import logged_service_operation


logger = logging.getLogger(__name__)

PREVIEW_SAMPLE_ROWS = 5
PREVIEW_GROUP_VALUES = 10
TABLE_DEFAULT_PAGE_SIZE = 10
TABLE_MAX_PAGE_SIZE = 100
TABLE_SEARCH_MAX_LENGTH = 200


def _not_found() -> QueryResultError:
    return query_error("RESULT_NOT_FOUND", "결과를 찾을 수 없습니다(만료되었거나 접근할 수 없음).")


def open_result(
    result_id: Any, access_scope: str | None, store: ResultStore | None = None
) -> tuple[ResultMeta, pd.DataFrame]:
    """접근 가능한 결과의 메타데이터와 DataFrame을 반환한다."""

    results = store or get_result_store()
    meta = _accessible_meta(result_id, access_scope, results)
    try:
        return meta, results.load(result_id)
    except Exception as exc:
        logger.warning("결과 데이터 조회 실패: error_type=%s", type(exc).__name__)
        raise _not_found() from None


def _accessible_meta(
    result_id: Any, access_scope: str | None, results: ResultStore
) -> ResultMeta:
    """조회 API와 Tool이 공유하는 strict scope·TTL metadata 검사."""

    if not isinstance(result_id, str) or not access_scope:
        raise _not_found()
    try:
        meta = results.get_meta(result_id)
    except Exception as exc:  # 손상된 metadata도 내부 정보 없이 not found
        logger.warning("결과 메타데이터 조회 실패: error_type=%s", type(exc).__name__)
        raise _not_found() from None
    if (
        meta is None
        or not meta.access_scope
        or meta.access_scope != access_scope
        or meta.expires_at <= datetime.now(timezone.utc)
    ):
        raise _not_found()
    return meta


def check_accessible(
    result_id: Any, access_scope: str | None, store: ResultStore | None = None
) -> ResultMeta:
    """데이터를 읽지 않고 접근 가능한 결과인지만 확인한다."""

    results = store or get_result_store()
    return _accessible_meta(result_id, access_scope, results)


def _column_payload(meta: ResultMeta, names: list[str] | None = None) -> list[dict[str, Any]]:
    by_name = {column.name: column for column in meta.columns}
    selected = names if names is not None else list(by_name)
    return [
        {"name": name, "dtype": by_name[name].dtype, "role": by_name[name].role}
        for name in selected
    ]


def _series_value(value: Any) -> Any:
    return _json_value(value)


def build_preview(meta: ResultMeta, frame: pd.DataFrame) -> dict[str, Any]:
    """모델과 UI가 표현을 판단하는 bounded metadata. 전체 행은 포함하지 않는다."""

    roles = {column.name: column.role for column in meta.columns}
    sample_rows = [
        {str(name): _series_value(value) for name, value in zip(frame.columns, row)}
        for row in frame.head(PREVIEW_SAMPLE_ROWS).itertuples(index=False)
    ]
    date_ranges: dict[str, dict[str, Any]] = {}
    distinct_counts: dict[str, int] = {}
    statistics: dict[str, dict[str, Any]] = {}
    top_groups: dict[str, list[dict[str, Any]]] = {}
    for name in frame.columns:
        role = roles.get(str(name))
        series = frame[name]
        if role == "measure":
            statistics[str(name)] = {
                "min": _series_value(series.min()),
                "max": _series_value(series.max()),
                "avg": _series_value(series.mean()),
                "sum": _series_value(series.sum(min_count=1)),
                "null_count": int(series.isna().sum()),
            }
            continue
        distinct_counts[str(name)] = int(series.nunique(dropna=True))
        if role == "time":
            values = series.dropna()
            if not values.empty:
                try:
                    date_ranges[str(name)] = {
                        "min": _series_value(values.min()),
                        "max": _series_value(values.max()),
                    }
                except TypeError:
                    pass
        elif role == "category":
            counts = series.dropna().value_counts().sort_values(
                ascending=False, kind="stable"
            )
            top_groups[str(name)] = [
                {"value": _series_value(value), "count": int(count)}
                for value, count in counts.head(PREVIEW_GROUP_VALUES).items()
            ]
    return {
        "status": "ok",
        "result_id": meta.result_id,
        "row_count": meta.row_count,
        "source_truncated": meta.source_truncated,
        "columns": _column_payload(meta),
        "sample_rows": sample_rows,
        "date_ranges": date_ranges,
        "distinct_counts": distinct_counts,
        "statistics": statistics,
        "top_groups": top_groups,
    }


def tool_preview(
    meta: ResultMeta, frame: pd.DataFrame, *, kind: str, **extra: Any
) -> dict[str, Any]:
    """`present` 모드에서 execute_sql·run_simulation이 모델에 돌려주는 payload.

    전체 행·인라인 표·SQL 원문은 포함하지 않는다.
    """

    preview = build_preview(meta, frame)
    return {"status": preview.pop("status"), "kind": kind, **extra, **preview}


@logged_service_operation
def read_preview(
    result_id: str, *, access_scope: str | None, result_store: ResultStore | None = None
) -> dict[str, Any]:
    meta, frame = open_result(result_id, access_scope, result_store)
    return build_preview(meta, frame)


def _parse_positive(value: Any, field: str, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise query_error("INVALID_REQUEST", f"{field}은 정수여야 합니다.") from None
    if parsed < 1:
        raise query_error("INVALID_REQUEST", f"{field}은 1 이상이어야 합니다.")
    return parsed


@logged_service_operation
def read_table(
    result_id: str,
    *,
    page: Any = None,
    page_size: Any = None,
    columns: list[str] | None = None,
    search: Any = None,
    sort_column: Any = None,
    sort_direction: Any = None,
    access_scope: str | None,
    result_store: ResultStore | None = None,
) -> dict[str, Any]:
    """저장된 결과를 검색·정렬한 뒤 page 단위로 잘라 낸 표.

    검색·정렬·page는 항상 서버에 저장된 전체 결과 범위에서 적용한다.
    page_size는 기본 10, 최대 100이다.
    """

    number = _parse_positive(page, "page", 1)
    size = _parse_positive(page_size, "page_size", TABLE_DEFAULT_PAGE_SIZE)
    if size > TABLE_MAX_PAGE_SIZE:
        raise query_error(
            "INVALID_REQUEST", f"page_size는 {TABLE_MAX_PAGE_SIZE} 이하여야 합니다."
        )
    meta, frame = open_result(result_id, access_scope, result_store)

    available = [column.name for column in meta.columns]
    if columns:
        selected = [name.strip() if isinstance(name, str) else "" for name in columns]
        if any(not name for name in selected) or len(set(selected)) != len(selected):
            raise query_error(
                "INVALID_REQUEST", "columns에는 서로 다른 컬럼 이름이 필요합니다."
            )
        missing = [name for name in selected if name not in available]
        if missing:
            raise query_error(
                "COLUMN_NOT_FOUND",
                "조회 결과에 없는 컬럼이 지정되었습니다.",
                columns=missing,
            )
    else:
        selected = available

    if search is not None and not isinstance(search, str):
        raise query_error("INVALID_REQUEST", "search는 문자열이어야 합니다.")
    needle = search.strip() if isinstance(search, str) else ""
    if len(needle) > TABLE_SEARCH_MAX_LENGTH:
        raise query_error(
            "INVALID_REQUEST",
            f"search는 {TABLE_SEARCH_MAX_LENGTH}자 이하여야 합니다.",
        )

    has_sort_column = sort_column is not None and sort_column != ""
    has_sort_direction = sort_direction is not None and sort_direction != ""
    if has_sort_column != has_sort_direction:
        raise query_error(
            "INVALID_REQUEST", "sort_column과 sort_direction은 함께 지정해야 합니다."
        )
    if has_sort_column:
        if not isinstance(sort_column, str) or sort_column not in selected:
            raise query_error(
                "COLUMN_NOT_FOUND",
                "표에 없는 정렬 컬럼이 지정되었습니다.",
                columns=[sort_column] if isinstance(sort_column, str) else [],
            )
        if not isinstance(sort_direction, str) or sort_direction not in {"asc", "desc"}:
            raise query_error(
                "INVALID_REQUEST", "sort_direction은 asc 또는 desc여야 합니다."
            )

    table = frame.loc[:, selected]
    if needle:
        matches = pd.Series(False, index=table.index, dtype=bool)
        for name in selected:
            matches |= table[name].astype("string").str.contains(
                needle, case=False, regex=False, na=False
            )
        table = table.loc[matches]

    filtered_row_count = len(table)
    if has_sort_column:
        try:
            table = table.sort_values(
                by=sort_column,
                ascending=sort_direction == "asc",
                kind="mergesort",
                na_position="last",
            )
        except (TypeError, ValueError):
            raise query_error(
                "UNRENDERABLE_VALUES", "해당 컬럼의 값을 정렬할 수 없습니다."
            ) from None

    offset = (number - 1) * size
    rows = dataframe_rows(table.iloc[offset : offset + size])
    return {
        "status": "ok",
        "result_id": meta.result_id,
        "page": number,
        "page_size": size,
        "row_count": meta.row_count,
        "filtered_row_count": filtered_row_count,
        "source_truncated": meta.source_truncated,
        "columns": _column_payload(meta, selected),
        "rows": rows,
    }


@logged_service_operation
def read_chart(
    result_id: str,
    *,
    chart_type: Any = None,
    x_column: Any = None,
    y_column: Any = None,
    group_by_column: Any = None,
    aggregation: Any = None,
    title: Any = None,
    access_scope: str | None,
    result_store: ResultStore | None = None,
) -> dict[str, Any]:
    meta, frame = open_result(result_id, access_scope, result_store)
    chart, warnings = project_chart(
        frame,
        meta.columns,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        group_by_column=group_by_column,
        aggregation=aggregation,
        title=title,
        source_truncated=meta.source_truncated,
    )
    return {
        "status": "ok",
        "result_id": meta.result_id,
        "chart": chart,
        "warnings": warnings,
    }
