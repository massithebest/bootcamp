"""저장 결과를 검증해 bar/line 명세를 등록하고 렌더링 payload를 구성한다."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from services.result_store import ResultMeta, ResultStore, get_result_store
from services.service_logging import logged_service_operation
from services.visualization_models import (
    NormalizedSeries,
    NormalizedVisualizationSpec,
    VisualizationMeta,
    VisualizationRequest,
    VisualizationWarning,
)
from services.visualization_store import VisualizationStore, get_visualization_store


MAX_POINTS = 500
MAX_SERIES = 8
SOURCE_TRUNCATED_WARNING = VisualizationWarning(
    code="SOURCE_TRUNCATED",
    message="조회 결과가 저장 한도에서 잘렸습니다.",
)

ERROR_CODES = {
    "RESULT_NOT_FOUND",
    "RESULT_EXPIRED",
    "RESULT_FORBIDDEN",
    "RESULT_UNAVAILABLE",
    "COLUMN_NOT_FOUND",
    "INVALID_COLUMN_ROLE",
    "DUPLICATE_MAPPING",
    "DUPLICATE_GRAIN",
    "EMPTY_RESULT",
    "UNRENDERABLE_VALUES",
    "DISPLAY_LIMIT_EXCEEDED",
    "UNSUPPORTED_KIND",
}


@dataclass(frozen=True)
class VisualizationError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"알 수 없는 visualization 오류 코드: {self.code}")
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


def _error(code: str, message: str, **details: Any) -> VisualizationError:
    return VisualizationError(code, message, details or None)


def _get_result_meta(store: ResultStore, result_id: str) -> ResultMeta:
    try:
        meta = store.get_meta(result_id)
    except Exception as exc:
        raise _error(
            "RESULT_UNAVAILABLE", "저장된 조회 결과를 읽을 수 없습니다."
        ) from exc
    if meta is None:
        raise _error("RESULT_NOT_FOUND", "result_id를 찾을 수 없습니다.")
    if meta.expires_at <= datetime.now(timezone.utc):
        raise _error("RESULT_EXPIRED", "조회 결과가 만료되었습니다. 새로 조회해 주세요.")
    return meta


def _check_scope(meta_scope: str | None, access_scope: str | None) -> str:
    if not access_scope or not meta_scope or meta_scope != access_scope:
        raise _error("RESULT_FORBIDDEN", "이 조회 결과에 접근할 수 없습니다.")
    return access_scope


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


def _validate_request(request: VisualizationRequest) -> None:
    if request.kind not in {"bar", "line"}:
        raise _error(
            "UNSUPPORTED_KIND",
            "지원하지 않는 차트 종류입니다. bar 또는 line을 사용해 주세요.",
            kind=request.kind,
        )
    if not isinstance(request.result_id, str) or not request.result_id:
        raise _error("RESULT_NOT_FOUND", "result_id를 찾을 수 없습니다.")
    if not isinstance(request.x, str) or not request.x.strip():
        raise _error("INVALID_COLUMN_ROLE", "x에는 컬럼 이름이 필요합니다.")
    if not request.y or any(not isinstance(name, str) or not name.strip() for name in request.y):
        raise _error("INVALID_COLUMN_ROLE", "y에는 하나 이상의 수치 컬럼이 필요합니다.")
    if request.group_by is not None and (
        not isinstance(request.group_by, str) or not request.group_by.strip()
    ):
        raise _error("INVALID_COLUMN_ROLE", "group_by에는 컬럼 이름이 필요합니다.")

    mappings = [request.x, *request.y]
    if request.group_by is not None:
        mappings.append(request.group_by)
    duplicates = sorted({name for name in mappings if mappings.count(name) > 1})
    if duplicates:
        raise _error(
            "DUPLICATE_MAPPING",
            "x, y, group_by에는 서로 다른 컬럼을 지정해 주세요.",
            columns=duplicates,
        )


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


def _group_values(frame: pd.DataFrame, group_by: str | None) -> list[Any]:
    if group_by is None:
        return [None]
    values: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for value in frame[group_by].tolist():
        if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
            raise _error(
                "UNRENDERABLE_VALUES", "group_by 컬럼에는 NULL이 없어야 합니다."
            )
        key = _identity(value)
        if key not in seen:
            seen.add(key)
            values.append(_json_value(value))
    return values


def _group_labels(
    frame: pd.DataFrame, group_by: str | None, group_values: list[Any]
) -> dict[tuple[str, str], str]:
    if group_by is None:
        return {_identity(None): ""}
    label_column = _label_column(frame, group_by)
    labels: dict[tuple[str, str], str] = {}
    for group_value in group_values:
        label = str(group_value)
        if label_column is not None:
            matched = frame[frame[group_by].map(_json_value) == group_value][label_column]
            names = [_json_value(value) for value in matched.tolist()]
            name = next((value for value in names if value is not None), None)
            if name is not None:
                label = str(name)
        labels[_identity(group_value)] = label
    return labels


def _validate_numeric_series(
    frame: pd.DataFrame, y_names: tuple[str, ...], group_by: str | None
) -> None:
    for y_name in y_names:
        if frame[y_name].dropna().empty:
            raise _error(
                "UNRENDERABLE_VALUES",
                "각 계열에는 표시 가능한 유한 숫자 값이 하나 이상 필요합니다.",
                column=y_name,
            )
        if not pd.api.types.is_numeric_dtype(frame[y_name].dtype) or pd.api.types.is_bool_dtype(
            frame[y_name].dtype
        ):
            raise _error(
                "INVALID_COLUMN_ROLE",
                "y에는 실제 숫자 dtype 컬럼만 사용할 수 있습니다.",
                column=y_name,
            )

    groups = [(None, frame)] if group_by is None else list(frame.groupby(group_by, sort=False))
    for group_value, group in groups:
        for y_name in y_names:
            values = group[y_name].dropna().tolist()
            if not values or any(not math.isfinite(float(value)) for value in values):
                details: dict[str, Any] = {"column": y_name}
                if group_by is not None:
                    details["group"] = _json_value(group_value)
                raise _error(
                    "UNRENDERABLE_VALUES",
                    "각 계열에는 표시 가능한 유한 숫자 값이 하나 이상 필요합니다.",
                    **details,
                )


def _categories(frame: pd.DataFrame, request: VisualizationRequest) -> list[Any]:
    values: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for value in frame[request.x].tolist():
        if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
            raise _error("UNRENDERABLE_VALUES", "x 컬럼에는 NULL이 없어야 합니다.")
        key = _identity(value)
        if key not in seen:
            seen.add(key)
            values.append(value)
    if request.kind == "line":
        try:
            values.sort(key=_time_key)
        except (TypeError, ValueError, OverflowError) as exc:
            raise _error(
                "INVALID_COLUMN_ROLE",
                "line 차트의 x 값은 날짜 또는 연월로 해석할 수 있어야 합니다.",
                column=request.x,
            ) from exc
    return [_json_value(value) for value in values]


def _build_spec(frame: pd.DataFrame, request: VisualizationRequest) -> NormalizedVisualizationSpec:
    group_values = _group_values(frame, request.group_by)
    labels = _group_labels(frame, request.group_by, group_values)
    series: list[NormalizedSeries] = []
    for group_value in group_values:
        for y_name in request.y:
            if request.group_by is None:
                label = y_name
            else:
                group_label = labels[_identity(group_value)]
                label = group_label if len(request.y) == 1 else f"{group_label} · {y_name}"
            series.append(
                NormalizedSeries(
                    key=f"series_{len(series)}",
                    label=label,
                    y=y_name,
                    group_value=group_value,
                )
            )
    if len(series) > MAX_SERIES:
        raise _error(
            "DISPLAY_LIMIT_EXCEEDED",
            "표시 범위를 기간·라인 등 더 좁은 grain으로 다시 집계해 주세요.",
            limit_type="series",
            limit=MAX_SERIES,
            actual=len(series),
        )
    return NormalizedVisualizationSpec(
        kind=request.kind,  # type: ignore[arg-type]
        x=request.x,
        y=request.y,
        group_by=request.group_by,
        series=tuple(series),
        x_label=request.x,
        y_label=request.y[0] if len(request.y) == 1 else None,
    )


def _load_frame(store: ResultStore, result_id: str) -> pd.DataFrame:
    try:
        return store.load(result_id)
    except Exception as exc:
        raise _error(
            "RESULT_UNAVAILABLE", "저장된 조회 결과 데이터를 읽을 수 없습니다."
        ) from exc


@logged_service_operation
def prepare_visualization(
    request: VisualizationRequest,
    *,
    access_scope: str | None,
    result_store: ResultStore | None = None,
    visualization_store: VisualizationStore | None = None,
) -> VisualizationMeta:
    """입력과 실제 parquet을 검증하고 새 시각화 명세를 저장한다."""

    results = result_store or get_result_store()
    visualizations = visualization_store or get_visualization_store()
    meta = _get_result_meta(results, request.result_id)
    scope = _check_scope(meta.access_scope, access_scope)
    _validate_request(request)
    frame = _load_frame(results, request.result_id)
    if frame.empty:
        raise _error("EMPTY_RESULT", "빈 조회 결과는 차트로 표시할 수 없습니다.")

    requested_columns = [request.x, *request.y]
    if request.group_by is not None:
        requested_columns.append(request.group_by)
    missing = [name for name in requested_columns if name not in frame.columns]
    if missing:
        raise _error(
            "COLUMN_NOT_FOUND",
            "조회 결과에 없는 컬럼이 지정되었습니다.",
            columns=missing,
        )

    _validate_numeric_series(frame, request.y, request.group_by)
    categories = _categories(frame, request)
    grain = [request.x] if request.group_by is None else [request.x, request.group_by]
    if frame.duplicated(subset=grain, keep=False).any():
        raise _error(
            "DUPLICATE_GRAIN",
            "차트 grain이 중복됩니다. x와 group_by 단위로 다시 집계해 주세요.",
            columns=grain,
        )

    if len(categories) > MAX_POINTS:
        raise _error(
            "DISPLAY_LIMIT_EXCEEDED",
            "표시 범위를 기간·라인 등 더 좁은 grain으로 다시 집계해 주세요.",
            limit_type="points",
            limit=MAX_POINTS,
            actual=len(categories),
        )
    spec = _build_spec(frame, request)
    warnings = (SOURCE_TRUNCATED_WARNING,) if meta.source_truncated else ()
    return visualizations.save(
        result_id=meta.result_id,
        spec=spec,
        warnings=warnings,
        access_scope=scope,
        expires_at=meta.expires_at,
    )


def _render_chart(frame: pd.DataFrame, spec: NormalizedVisualizationSpec) -> dict[str, Any]:
    request = VisualizationRequest(
        result_id="",
        kind=spec.kind,
        x=spec.x,
        y=spec.y,
        group_by=spec.group_by,
    )
    categories = _categories(frame, request)
    rows: dict[tuple[str, str], dict[str, Any]] = {
        _identity(category): {
            spec.x: category,
            **{series.key: None for series in spec.series},
        }
        for category in categories
    }
    series_by_identity = {
        (_identity(series.group_value), series.y): series for series in spec.series
    }
    for _, source_row in frame.iterrows():
        x_value = _json_value(source_row[spec.x])
        output = rows[_identity(x_value)]
        group_value = _json_value(source_row[spec.group_by]) if spec.group_by else None
        for y_name in spec.y:
            series = series_by_identity[(_identity(group_value), y_name)]
            output[series.key] = _json_value(source_row[y_name])

    return {
        "type": spec.kind,
        "x": spec.x,
        "series": [
            {"key": series.key, "label": series.label} for series in spec.series
        ],
        "categories": categories,
        "data": list(rows.values()),
        "title": spec.title,
        "x_label": spec.x_label,
        "y_label": spec.y_label,
        "unit": spec.unit,
    }


@logged_service_operation
def read_visualization(
    visualization_id: str,
    *,
    access_scope: str | None,
    result_store: ResultStore | None = None,
    visualization_store: VisualizationStore | None = None,
) -> dict[str, Any]:
    """저장 명세와 현재 원본 수명을 확인하고 API용 ChartSpec을 구성한다."""

    results = result_store or get_result_store()
    visualizations = visualization_store or get_visualization_store()
    meta = visualizations.get(visualization_id)
    if meta is None:
        raise _error("RESULT_NOT_FOUND", "시각화를 찾을 수 없습니다.")
    _check_scope(meta.access_scope, access_scope)
    if meta.expires_at <= datetime.now(timezone.utc):
        raise _error("RESULT_EXPIRED", "시각화 원본이 만료되었습니다. 새로 조회해 주세요.")
    try:
        result_meta = results.get_meta(meta.result_id)
    except Exception as exc:
        raise _error("RESULT_UNAVAILABLE", "시각화 원본을 읽을 수 없습니다.") from exc
    if result_meta is None:
        raise _error("RESULT_UNAVAILABLE", "시각화 원본이 삭제되었습니다. 새로 조회해 주세요.")
    if result_meta.expires_at <= datetime.now(timezone.utc):
        raise _error("RESULT_EXPIRED", "시각화 원본이 만료되었습니다. 새로 조회해 주세요.")
    _check_scope(result_meta.access_scope, access_scope)
    frame = _load_frame(results, meta.result_id)
    try:
        chart = _render_chart(frame, meta.spec)
    except Exception as exc:
        raise _error("RESULT_UNAVAILABLE", "시각화 원본을 구성할 수 없습니다.") from exc
    return {
        "visualization_id": meta.visualization_id,
        "result_id": meta.result_id,
        "schema_version": meta.schema_version,
        "expires_at": meta.expires_at.isoformat(),
        "chart": chart,
        "warnings": [
            {"code": warning.code, "message": warning.message}
            for warning in meta.warnings
        ],
    }
