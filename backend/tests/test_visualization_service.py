"""시각화 검증과 렌더링 데이터 구성."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from services.result_store import LocalParquetResultStore
from services.visualization_models import VisualizationRequest
from services.visualization_service import (
    VisualizationError,
    prepare_visualization,
    read_visualization,
)
from services.visualization_store import LocalVisualizationStore


@pytest.fixture()
def stores(tmp_path):
    return (
        LocalParquetResultStore(tmp_path / "results"),
        LocalVisualizationStore(tmp_path / "visualizations"),
    )


def _save(results, columns, rows, *, truncated=False, scope="scope-a"):
    return results.save(
        columns,
        rows,
        source="execute_sql",
        conversation_id=None,
        source_truncated=truncated,
        access_scope=scope,
    )


def _prepare(stores, meta, *, kind="bar", x="x", y=("value",), group_by=None):
    results, visualizations = stores
    return prepare_visualization(
        VisualizationRequest(meta.result_id, kind, x, tuple(y), group_by),
        access_scope="scope-a",
        result_store=results,
        visualization_store=visualizations,
    )


def _read(stores, visualization_id, scope="scope-a"):
    results, visualizations = stores
    return read_visualization(
        visualization_id,
        access_scope=scope,
        result_store=results,
        visualization_store=visualizations,
    )


def _assert_error(code, call) -> VisualizationError:
    with pytest.raises(VisualizationError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def test_bar_one_and_multiple_y_preserve_input_order(stores) -> None:
    results, _ = stores
    meta = _save(results, ["x", "actual", "plan"], [["B", 2, 3], ["A", 1, 4]])

    saved = _prepare(stores, meta, y=("actual", "plan"))
    payload = _read(stores, saved.visualization_id)

    assert payload["chart"]["categories"] == ["B", "A"]
    assert [series["label"] for series in payload["chart"]["series"]] == [
        "actual",
        "plan",
    ]
    assert payload["chart"]["data"][0]["series_0"] == 2


def test_line_sorts_real_time_and_year_month_values(stores) -> None:
    results, _ = stores
    meta = _save(
        results,
        ["month", "value"],
        [["2026-10", 10], ["2026-2", 2], ["202601", 1]],
    )

    saved = _prepare(stores, meta, kind="line", x="month")
    chart = _read(stores, saved.visualization_id)["chart"]

    assert chart["categories"] == ["202601", "2026-2", "2026-10"]
    assert [row["series_0"] for row in chart["data"]] == [1, 2, 10]


def test_group_by_pivots_with_stable_keys_and_duplicate_labels(stores) -> None:
    results, _ = stores
    meta = _save(
        results,
        ["month", "line_cd", "line_nm", "actual", "plan"],
        [
            ["2026-01", "A", "같은 이름", 1, 2],
            ["2026-01", "B", "같은 이름", 3, 4],
            ["2026-02", "A", "같은 이름", None, 5],
            ["2026-02", "B", "같은 이름", 6, 7],
        ],
    )

    saved = _prepare(
        stores,
        meta,
        kind="line",
        x="month",
        y=("actual", "plan"),
        group_by="line_cd",
    )
    chart = _read(stores, saved.visualization_id)["chart"]

    assert [item["key"] for item in chart["series"]] == [
        "series_0",
        "series_1",
        "series_2",
        "series_3",
    ]
    assert [item["label"] for item in chart["series"]] == [
        "같은 이름 · actual",
        "같은 이름 · plan",
        "같은 이름 · actual",
        "같은 이름 · plan",
    ]
    assert chart["data"][1]["series_0"] is None
    assert chart["data"][1]["series_2"] == 6


def test_same_result_can_have_multiple_specs(stores) -> None:
    results, _ = stores
    meta = _save(results, ["x", "value", "rate"], [["A", 1, 0.5]])

    first = _prepare(stores, meta, y=("value",))
    second = _prepare(stores, meta, y=("rate",))

    assert first.visualization_id != second.visualization_id
    assert _read(stores, first.visualization_id)["chart"]["series"][0]["label"] == "value"


@pytest.mark.parametrize(
    ("columns", "rows", "kwargs", "code"),
    [
        (["x", "value"], [["A", 1]], {"y": ("missing",)}, "COLUMN_NOT_FOUND"),
        (["x", "value"], [["A", "one"]], {}, "INVALID_COLUMN_ROLE"),
        (["x", "value"], [["A", 1]], {"group_by": "x"}, "DUPLICATE_MAPPING"),
        (["x", "value"], [["A", 1], ["A", 2]], {}, "DUPLICATE_GRAIN"),
        (["x", "value"], [["A", None]], {}, "UNRENDERABLE_VALUES"),
        (["x", "value"], [], {}, "EMPTY_RESULT"),
    ],
)
def test_validation_errors(stores, columns, rows, kwargs, code) -> None:
    results, _ = stores
    meta = _save(results, columns, rows)

    _assert_error(code, lambda: _prepare(stores, meta, **kwargs))


def test_line_rejects_non_time_x(stores) -> None:
    results, _ = stores
    meta = _save(results, ["x", "value"], [["first", 1], ["second", 2]])

    _assert_error("INVALID_COLUMN_ROLE", lambda: _prepare(stores, meta, kind="line"))


def test_display_limits_do_not_slice(stores, monkeypatch) -> None:
    from services import visualization_service

    results, _ = stores
    point_meta = _save(results, ["x", "value"], [[str(i), i] for i in range(3)])
    monkeypatch.setattr(visualization_service, "MAX_POINTS", 2)
    _assert_error("DISPLAY_LIMIT_EXCEEDED", lambda: _prepare(stores, point_meta))

    series_meta = _save(
        results,
        ["x", "group", "value"],
        [["A", "one", 1], ["A", "two", 2], ["A", "three", 3]],
    )
    monkeypatch.setattr(visualization_service, "MAX_POINTS", 500)
    monkeypatch.setattr(visualization_service, "MAX_SERIES", 2)
    _assert_error(
        "DISPLAY_LIMIT_EXCEEDED",
        lambda: _prepare(stores, series_meta, group_by="group"),
    )


def test_source_truncated_is_warning_not_display_error(stores) -> None:
    results, _ = stores
    meta = _save(results, ["x", "value"], [["A", 1]], truncated=True)

    saved = _prepare(stores, meta)
    payload = _read(stores, saved.visualization_id)

    assert [warning["code"] for warning in payload["warnings"]] == ["SOURCE_TRUNCATED"]


def test_scope_expiry_and_deleted_source_are_protected(stores) -> None:
    results, visualizations = stores
    meta = _save(results, ["x", "value"], [["A", 1]])
    _assert_error(
        "RESULT_FORBIDDEN",
        lambda: prepare_visualization(
            VisualizationRequest(meta.result_id, "bar", "x", ("value",)),
            access_scope="scope-b",
            result_store=results,
            visualization_store=visualizations,
        ),
    )
    saved = _prepare(stores, meta)
    _assert_error("RESULT_FORBIDDEN", lambda: _read(stores, saved.visualization_id, "scope-b"))

    results.delete(meta.result_id)
    _assert_error("RESULT_UNAVAILABLE", lambda: _read(stores, saved.visualization_id))


def test_expired_source_cannot_be_prepared(stores) -> None:
    results, visualizations = stores
    meta = _save(results, ["x", "value"], [["A", 1]])
    path = results.directory / f"{meta.result_id}.meta.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")

    _assert_error(
        "RESULT_EXPIRED",
        lambda: prepare_visualization(
            VisualizationRequest(meta.result_id, "bar", "x", ("value",)),
            access_scope="scope-a",
            result_store=results,
            visualization_store=visualizations,
        ),
    )


def test_saved_sidecar_has_no_numeric_data_array(stores) -> None:
    results, visualizations = stores
    meta = _save(results, ["x", "value"], [["A", 123]])
    saved = _prepare(stores, meta)
    path = visualizations.directory / f"{saved.visualization_id}.meta.json"

    assert '"data"' not in path.read_text(encoding="utf-8")
