"""저장 없는 chart projection.

Result Store의 DataFrame과 표시 설정만 받아 Recharts 소비 형태의 chart payload를 만든다.
집계·컬럼 검증·series/point 축약은 모두 이 모듈이 결정적으로 수행한다.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any

import pandas as pd

from services.results.errors import QueryResultError, query_error
from services.results.store import ResultColumn


CHART_TYPES = ("bar", "line", "area")
AGGREGATIONS = ("sum", "avg", "count", "min", "max")
MAX_POINTS = 500
MAX_SERIES = 8
TITLE_MAX_LENGTH = 120
_BUCKET_LEVELS = ("week", "month", "quarter", "year")
_BUCKET_LABEL = {"week": "주", "month": "월", "quarter": "분기", "year": "연"}
#: long 형식 결과에서 지표 이름을 담는 범주 컬럼으로 보는 이름(metric, measure_name, 지표명 등).
_METRIC_COLUMN = re.compile(r"(?i)(?:^|_)(?:metric|measure|indicator|kpi)s?(?:_|$)|지표")


def _json_value(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    item = getattr(value, "item", None)
    value = item() if callable(item) else value
    if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _identity(value: Any) -> tuple[str, str]:
    normalized = _json_value(value)
    return type(normalized).__name__, repr(normalized)


_YEAR_MONTH_COMPACT = re.compile(r"^(\d{4})(\d{2})$")
_YEAR_MONTH_DASH = re.compile(r"^(\d{4})-(\d{1,2})$")


def _time_key(value: Any) -> pd.Timestamp:
    if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
        raise ValueError("시간축에 NULL이 있습니다")
    if isinstance(value, bool) or isinstance(value, (int, float)):
        raise ValueError("숫자 시간축은 지원하지 않습니다")
    if isinstance(value, str):
        compact = _YEAR_MONTH_COMPACT.fullmatch(value.strip())
        if compact:
            return pd.Timestamp(year=int(compact.group(1)), month=int(compact.group(2)), day=1)
        dashed = _YEAR_MONTH_DASH.fullmatch(value.strip())
        if dashed:
            return pd.Timestamp(year=int(dashed.group(1)), month=int(dashed.group(2)), day=1)
    parsed = pd.to_datetime(value, errors="raise")
    if pd.isna(parsed):
        raise ValueError("시간축 값을 해석할 수 없습니다")
    return pd.Timestamp(parsed)


def _label_column(frame: pd.DataFrame, group_by: str) -> str | None:
    candidates: list[str] = []
    if group_by.endswith("_cd"):
        candidates.append(f"{group_by[:-3]}_nm")
    if group_by.endswith("_code"):
        candidates.append(f"{group_by[:-5]}_name")
    for candidate in candidates:
        if candidate not in frame.columns:
            continue
        pairs = frame[[group_by, candidate]].drop_duplicates()
        non_null = pairs.dropna(subset=[group_by, candidate])
        if non_null.groupby(group_by, dropna=False)[candidate].nunique().max() <= 1:
            return candidate
    return None


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise query_error("INVALID_REQUEST", f"{field}에는 컬럼 이름이 필요합니다.")
    return value.strip()


def normalize_title(title: Any) -> str | None:
    if title is None:
        return None
    if not isinstance(title, str):
        raise query_error("INVALID_REQUEST", "title은 문자열이어야 합니다.")
    title = title.strip()
    if not title:
        return None
    if len(title) > TITLE_MAX_LENGTH:
        raise query_error(
            "INVALID_REQUEST", f"title은 {TITLE_MAX_LENGTH}자 이하여야 합니다."
        )
    return title


def _bucket_keys(stamps: pd.Series, level: str) -> pd.Series:
    if level == "week":
        return (stamps - pd.to_timedelta(stamps.dt.weekday, unit="D")).dt.normalize()
    freq = {"month": "M", "quarter": "Q", "year": "Y"}[level]
    return stamps.dt.to_period(freq).dt.start_time


def _bucket_label(stamp: pd.Timestamp, level: str) -> str:
    if level == "week":
        return stamp.strftime("%Y-%m-%d")
    if level == "month":
        return stamp.strftime("%Y-%m")
    if level == "quarter":
        return f"{stamp.year}-Q{(stamp.month - 1) // 3 + 1}"
    return f"{stamp.year}"


def _finite(value: Any) -> Any:
    normalized = _json_value(value)
    if isinstance(normalized, float) and not math.isfinite(normalized):
        raise query_error(
            "UNRENDERABLE_VALUES", "차트에 표시할 수 없는 값(NaN·무한대)이 있습니다."
        )
    return normalized


def project_chart(
    frame: pd.DataFrame,
    columns: list[ResultColumn],
    *,
    chart_type: Any,
    x_column: Any,
    y_column: Any,
    group_by_column: Any = None,
    aggregation: Any = None,
    title: Any = None,
    source_truncated: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """검증·집계·축약한 ``(chart, warnings)``를 반환한다."""

    if chart_type not in CHART_TYPES:
        raise query_error(
            "INVALID_REQUEST", "chart_type은 bar, line, area 중 하나여야 합니다."
        )
    if aggregation is not None and aggregation not in AGGREGATIONS:
        raise query_error(
            "INVALID_REQUEST",
            "aggregation은 sum, avg, count, min, max 중 하나여야 합니다.",
        )
    x = _name(x_column, "x_column")
    y = _name(y_column, "y_column")
    group = None if group_by_column in (None, "") else _name(group_by_column, "group_by_column")
    chart_title = normalize_title(title)

    mapped = [x, y, *([group] if group else [])]
    if len(set(mapped)) != len(mapped):
        raise query_error(
            "INVALID_REQUEST", "x, y, group_by에는 서로 다른 컬럼을 지정해 주세요."
        )
    roles = {column.name: column.role for column in columns}
    missing = [name for name in mapped if name not in frame.columns]
    if missing:
        raise query_error(
            "COLUMN_NOT_FOUND", "조회 결과에 없는 컬럼이 지정되었습니다.", columns=missing
        )
    if frame.empty:
        raise query_error("EMPTY_RESULT", "빈 조회 결과는 차트로 표시할 수 없습니다.")

    if roles.get(x) not in {"category", "time"}:
        raise query_error(
            "INVALID_COLUMN_ROLE",
            "x_column에는 범주 또는 시간 컬럼만 사용할 수 있습니다.",
            column=x,
        )
    if group and roles.get(group) != "category":
        raise query_error(
            "INVALID_COLUMN_ROLE",
            "group_by_column에는 범주 컬럼만 사용할 수 있습니다.",
            column=group,
        )
    # long 형식 결과의 지표 이름 컬럼(metric 등)이 x·group_by 가 아니면 서로 다른 지표
    # (예: Lot 수와 수량)가 한 막대에 합산된다. 의미 없는 차트를 만들지 않고 되돌려 보낸다.
    for column in columns:
        name = column.name
        if (
            name not in mapped
            and column.role == "category"
            and _METRIC_COLUMN.search(name)
            and name in frame.columns
            and frame[name].nunique(dropna=True) > 1
        ):
            raise query_error(
                "INVALID_REQUEST",
                f"'{name}' 컬럼에 서로 다른 지표가 섞여 있어 하나의 값으로 합칠 수 없습니다. "
                "같은 단위의 지표면 group_by_column(또는 x_column)으로 지정하고, 단위가 다르면 "
                "SQL에서 지표 하나만 남겨 지표별로 따로 그려 주세요.",
                column=name,
                values=[str(value) for value in frame[name].dropna().unique()[:5]],
            )

    numeric_y = pd.api.types.is_numeric_dtype(frame[y].dtype) and not pd.api.types.is_bool_dtype(
        frame[y].dtype
    )
    if aggregation != "count" and not numeric_y:
        raise query_error(
            "INVALID_COLUMN_ROLE",
            "y_column에는 숫자 컬럼만 사용할 수 있습니다(count 집계는 제외).",
            column=y,
        )

    work = frame[mapped].copy()
    if work[x].isna().any() or (group and work[group].isna().any()):
        raise query_error(
            "UNRENDERABLE_VALUES", "x·group_by 컬럼에는 NULL이 없어야 합니다."
        )
    if numeric_y:
        values = work[y].dropna()
        if values.empty:
            raise query_error(
                "UNRENDERABLE_VALUES",
                "y_column에는 표시 가능한 숫자 값이 하나 이상 필요합니다.",
                column=y,
            )
        if not all(math.isfinite(float(value)) for value in values.tolist()):
            raise query_error(
                "UNRENDERABLE_VALUES",
                "차트에 표시할 수 없는 값(NaN·무한대)이 있습니다.",
                column=y,
            )

    warnings: list[dict[str, str]] = []
    if source_truncated:
        warnings.append(
            {"code": "SOURCE_TRUNCATED", "message": "조회 결과가 저장 한도에서 잘렸습니다."}
        )

    # ---- x축 정렬 키와 시간 bucket ----
    time_axis = chart_type in {"line", "area"}
    stamps: dict[tuple[str, str], pd.Timestamp] = {}
    x_key = x
    if time_axis or roles.get(x) == "time":
        try:
            converted = {_identity(v): _time_key(v) for v in work[x].tolist()}
        except (TypeError, ValueError, OverflowError) as exc:
            if time_axis:
                raise query_error(
                    "INVALID_COLUMN_ROLE",
                    "line·area 차트의 x 값은 날짜 또는 연월로 해석할 수 있어야 합니다.",
                    column=x,
                ) from exc
            converted = {}
        if converted:
            stamps = converted
    if time_axis and len(stamps) > MAX_POINTS:
        if aggregation is None:
            raise query_error(
                "AGGREGATION_REQUIRED",
                "시계열 포인트가 500개를 넘어 재집계할 집계 방식(aggregation)이 필요합니다.",
                limit=MAX_POINTS,
                actual=len(stamps),
            )
        series_stamps = work[x].map(lambda value: stamps[_identity(value)])
        stamped = pd.Series(pd.to_datetime(series_stamps), index=work.index)
        for level in _BUCKET_LEVELS:
            bucket = _bucket_keys(stamped, level)
            if bucket.nunique() <= MAX_POINTS or level == _BUCKET_LEVELS[-1]:
                break
        original = len(stamps)
        labels = bucket.map(lambda stamp: _bucket_label(stamp, level))
        stamps = {
            _identity(label): stamp
            for label, stamp in zip(labels.tolist(), bucket.tolist())
        }
        work[x] = labels
        warnings.append(
            {
                "code": "TIME_BUCKETED",
                "message": f"{original}개 시점을 {_BUCKET_LABEL[level]} 단위로 재집계했습니다.",
            }
        )

    # ---- 집계 ----
    keys = [x] + ([group] if group else [])
    if aggregation is None:
        if work.duplicated(subset=keys, keep=False).any():
            raise query_error(
                "AGGREGATION_REQUIRED",
                "차트 grain이 중복됩니다. aggregation을 지정하거나 x·group_by 단위로 다시 집계해 주세요.",
                columns=keys,
            )
        aggregated = work[keys + [y]]
    else:
        grouped = work.groupby(keys, sort=False)[y]
        method = {"avg": "mean"}.get(aggregation, aggregation)
        if method == "sum":
            series = grouped.sum(min_count=1)
        else:
            series = getattr(grouped, method)()
        aggregated = series.reset_index()
    aggregated = aggregated.reset_index(drop=True)

    # ---- series ----
    group_values: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for value in aggregated[group].tolist() if group else [None]:
        key = _identity(value)
        if key not in seen:
            seen.add(key)
            group_values.append(_json_value(value))

    def _totals(select: Any) -> float:
        subset = aggregated if group is None else aggregated[
            aggregated[group].map(lambda v: _json_value(v) == select)
        ]
        return float(subset[y].abs().sum(skipna=True))

    if len(group_values) > MAX_SERIES:
        ranked = sorted(group_values, key=lambda item: (-_totals(item), str(item)))
        kept = ranked[:MAX_SERIES]
        warnings.append(
            {
                "code": "SERIES_LIMITED",
                "message": f"그룹 {len(group_values)}개 중 값이 큰 상위 {MAX_SERIES}개만 표시합니다.",
            }
        )
        group_values = kept
        aggregated = aggregated[
            aggregated[group].map(lambda v: _json_value(v) in kept)
        ]

    label_column = _label_column(frame, group) if group else None
    series_defs: list[dict[str, str]] = []
    series_key: dict[tuple[str, str], str] = {}
    for index, value in enumerate(group_values):
        key = f"series_{index}"
        series_key[_identity(value)] = key
        label = y
        if group:
            label = str(value)
            if label_column is not None:
                matched = frame[frame[group].map(_json_value) == value][label_column]
                name = next(
                    (v for v in (_json_value(item) for item in matched.tolist()) if v is not None),
                    None,
                )
                if name is not None:
                    label = str(name)
        series_defs.append({"key": key, "label": label})

    # ---- categories ----
    order: dict[tuple[str, str], int] = {}
    category_values: dict[tuple[str, str], Any] = {}
    for value in aggregated[x].tolist():
        key = _identity(value)
        if key not in order:
            order[key] = len(order)
            category_values[key] = _json_value(value)
    ordered = list(order)
    if stamps:
        ordered.sort(key=lambda key: (stamps.get(key, pd.Timestamp.max), order[key]))
    if len(ordered) > MAX_POINTS:  # bar 범주: 절대 집계값 상위 N개
        totals: dict[tuple[str, str], float] = {}
        for value, amount in zip(aggregated[x].tolist(), aggregated[y].tolist()):
            key = _identity(value)
            totals[key] = totals.get(key, 0.0) + (
                0.0 if amount is None or pd.isna(amount) else abs(float(amount))
            )
        top = sorted(ordered, key=lambda key: (-totals[key], order[key]))[:MAX_POINTS]
        keep = set(top)
        warnings.append(
            {
                "code": "CATEGORIES_LIMITED",
                "message": f"범주 {len(ordered)}개 중 값이 큰 상위 {MAX_POINTS}개만 표시합니다.",
            }
        )
        ordered = [key for key in ordered if key in keep]

    rows = {
        key: {x: category_values[key], **{d["key"]: None for d in series_defs}}
        for key in ordered
    }
    for _, record in aggregated.iterrows():
        key = _identity(record[x])
        if key not in rows:
            continue
        group_value = _json_value(record[group]) if group else None
        rows[key][series_key[_identity(group_value)]] = _finite(record[y])

    chart = {
        "type": chart_type,
        "x": x,
        "series": series_defs,
        "categories": [category_values[key] for key in ordered],
        "data": list(rows.values()),
        "title": chart_title,
        "x_label": x,
        "y_label": y,
        "unit": None,
    }
    return chart, warnings


__all__ = ["AGGREGATIONS", "CHART_TYPES", "MAX_POINTS", "MAX_SERIES", "QueryResultError", "project_chart"]
