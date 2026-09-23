"""저장 없는 Result preview·table·chart 조회와 chart projection 검증."""

import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from services.results import store as result_store
from services.results.chart import project_chart
from services.results.errors import QueryResultError
from services.results.query import (
    build_preview,
    read_chart,
    read_preview,
    read_table,
)
from services.results.store import LocalParquetResultStore, ResultColumn

SCOPE = "scope-a"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    results = LocalParquetResultStore(tmp_path / "results")
    monkeypatch.setattr(result_store, "_store", results)
    return results


def _save(store, columns, rows, *, scope=SCOPE, truncated=False):
    return store.save(
        columns,
        rows,
        source="execute_sql",
        conversation_id=None,
        source_truncated=truncated,
        access_scope=scope,
    )


def _columns(*specs):
    return [ResultColumn(name, dtype, role) for name, dtype, role in specs]


def _frame_project(frame, **kwargs):
    columns = [
        ResultColumn(str(name), str(frame[name].dtype), _role(str(name), frame[name]))
        for name in frame.columns
    ]
    return project_chart(frame, columns, **kwargs)


def _role(name, series):
    from services.results.store import _infer_role

    return _infer_role(name, str(series.dtype))


def _error(code, **kwargs):
    with pytest.raises(QueryResultError) as caught:
        _frame_project(**kwargs)
    assert caught.value.code == code
    return caught.value


MONTHLY = pd.DataFrame(
    {
        "work_month": ["2026-01", "2026-02", "2026-03"],
        "line": ["A", "A", "A"],
        "qty": [10, 20, 30],
    }
)


# ---------------------------------------------------------------- projection


def test_line_chart_sorts_time_and_reports_axes() -> None:
    frame = MONTHLY.iloc[[2, 0, 1]].reset_index(drop=True)

    chart, warnings = _frame_project(
        frame=frame, chart_type="line", x_column="work_month", y_column="qty", title=" 추이 "
    )

    assert chart["type"] == "line"
    assert chart["categories"] == ["2026-01", "2026-02", "2026-03"]
    assert chart["series"] == [{"key": "series_0", "label": "qty"}]
    assert chart["data"][0] == {"work_month": "2026-01", "series_0": 10}
    assert chart["title"] == "추이"
    assert (chart["x_label"], chart["y_label"], chart["unit"]) == ("work_month", "qty", None)
    assert warnings == []


@pytest.mark.parametrize("chart_type", ["bar", "line", "area"])
def test_all_chart_types_are_supported(chart_type) -> None:
    chart, _ = _frame_project(
        frame=MONTHLY, chart_type=chart_type, x_column="work_month", y_column="qty"
    )

    assert chart["type"] == chart_type


@pytest.mark.parametrize(
    "aggregation,expected",
    [("sum", 30), ("avg", 15), ("min", 10), ("max", 20), ("count", 2)],
)
def test_aggregation_collapses_duplicate_grain(aggregation, expected) -> None:
    frame = pd.DataFrame({"line": ["A", "A", "B"], "qty": [10, 20, 5]})

    chart, _ = _frame_project(
        frame=frame, chart_type="bar", x_column="line", y_column="qty", aggregation=aggregation
    )

    assert chart["data"][0]["series_0"] == expected
    assert chart["categories"] == ["A", "B"]


def test_duplicate_grain_without_aggregation_requires_aggregation() -> None:
    frame = pd.DataFrame({"line": ["A", "A"], "qty": [1, 2]})

    error = _error(
        "AGGREGATION_REQUIRED",
        frame=frame,
        chart_type="bar",
        x_column="line",
        y_column="qty",
    )

    assert error.details == {"columns": ["line"]}


def test_group_series_use_label_column_and_first_appearance_order() -> None:
    frame = pd.DataFrame(
        {
            "month": ["2026-01", "2026-01", "2026-02", "2026-02"],
            "line_cd": ["L2", "L1", "L2", "L1"],
            "line_nm": ["둘째", "첫째", "둘째", "첫째"],
            "qty": [1, 2, 3, 4],
        }
    )

    chart, _ = _frame_project(
        frame=frame,
        chart_type="line",
        x_column="month",
        y_column="qty",
        group_by_column="line_cd",
    )

    assert [series["label"] for series in chart["series"]] == ["둘째", "첫째"]
    assert chart["data"][1] == {"month": "2026-02", "series_0": 3, "series_1": 4}


def test_series_over_limit_keeps_top_eight_by_absolute_total_with_warning() -> None:
    groups = [f"G{i:02d}" for i in range(10)]
    frame = pd.DataFrame(
        {"month": ["2026-01"] * 10, "grp": groups, "qty": list(range(10, 0, -1))}
    )

    chart, warnings = _frame_project(
        frame=frame,
        chart_type="bar",
        x_column="month",
        y_column="qty",
        group_by_column="grp",
    )

    assert [series["label"] for series in chart["series"]] == groups[:8]
    assert [warning["code"] for warning in warnings] == ["SERIES_LIMITED"]


def test_bar_categories_over_limit_keep_top_five_hundred() -> None:
    frame = pd.DataFrame({"name": [f"n{i}" for i in range(600)], "qty": list(range(600))})

    chart, warnings = _frame_project(
        frame=frame, chart_type="bar", x_column="name", y_column="qty"
    )

    assert len(chart["categories"]) == 500
    assert "n599" in chart["categories"] and "n0" not in chart["categories"]
    assert [warning["code"] for warning in warnings] == ["CATEGORIES_LIMITED"]


def test_daily_series_over_limit_is_rebucketed_by_month_with_aggregation() -> None:
    days = pd.date_range("2024-01-01", periods=600, freq="D")
    frame = pd.DataFrame({"day": days.strftime("%Y-%m-%d"), "qty": [1] * 600})

    chart, warnings = _frame_project(
        frame=frame, chart_type="line", x_column="day", y_column="qty", aggregation="sum"
    )

    assert len(chart["categories"]) <= 500
    assert warnings[0]["code"] == "TIME_BUCKETED"
    assert sum(row["series_0"] for row in chart["data"]) == 600
    assert chart["categories"] == sorted(chart["categories"])


def test_daily_series_over_limit_without_aggregation_is_rejected() -> None:
    days = pd.date_range("2024-01-01", periods=600, freq="D")
    frame = pd.DataFrame({"day": days.strftime("%Y-%m-%d"), "qty": [1] * 600})

    _error(
        "AGGREGATION_REQUIRED", frame=frame, chart_type="line", x_column="day", y_column="qty"
    )


def test_source_truncated_adds_warning() -> None:
    _, warnings = _frame_project(
        frame=MONTHLY,
        chart_type="bar",
        x_column="work_month",
        y_column="qty",
        source_truncated=True,
    )

    assert warnings[0]["code"] == "SOURCE_TRUNCATED"


@pytest.mark.parametrize(
    "code,kwargs",
    [
        ("INVALID_REQUEST", {"chart_type": "pie", "x_column": "work_month", "y_column": "qty"}),
        ("INVALID_REQUEST", {"chart_type": "bar", "x_column": "work_month", "y_column": "qty", "aggregation": "median"}),
        ("INVALID_REQUEST", {"chart_type": "bar", "x_column": "qty", "y_column": "qty"}),
        ("COLUMN_NOT_FOUND", {"chart_type": "bar", "x_column": "nope", "y_column": "qty"}),
        ("INVALID_COLUMN_ROLE", {"chart_type": "bar", "x_column": "work_month", "y_column": "line"}),
        ("INVALID_COLUMN_ROLE", {"chart_type": "bar", "x_column": "qty", "y_column": "qty2"}),
        ("INVALID_COLUMN_ROLE", {"chart_type": "line", "x_column": "line", "y_column": "qty"}),
    ],
)
def test_invalid_specs_are_rejected_with_safe_codes(code, kwargs) -> None:
    frame = MONTHLY.assign(qty2=[1, 2, 3])

    _error(code, frame=frame, **kwargs)


def test_empty_null_and_non_finite_values_are_rejected() -> None:
    _error(
        "EMPTY_RESULT",
        frame=MONTHLY.iloc[0:0],
        chart_type="bar",
        x_column="work_month",
        y_column="qty",
    )
    _error(
        "UNRENDERABLE_VALUES",
        frame=pd.DataFrame({"x": ["a", None], "y": [1.0, 2.0]}),
        chart_type="bar",
        x_column="x",
        y_column="y",
    )
    _error(
        "UNRENDERABLE_VALUES",
        frame=pd.DataFrame({"x": ["a", "b"], "y": [1.0, math.inf]}),
        chart_type="bar",
        x_column="x",
        y_column="y",
    )
    _error(
        "UNRENDERABLE_VALUES",
        frame=pd.DataFrame({"x": ["a", "b"], "y": [math.nan, math.nan]}),
        chart_type="bar",
        x_column="x",
        y_column="y",
    )


def test_count_aggregation_accepts_non_numeric_y() -> None:
    frame = pd.DataFrame({"line": ["A", "A", "B"], "product": ["x", "y", "z"]})

    chart, _ = _frame_project(
        frame=frame,
        chart_type="bar",
        x_column="line",
        y_column="product",
        aggregation="count",
    )

    assert [row["series_0"] for row in chart["data"]] == [2, 1]


# ------------------------------------------------------------------- service


def test_preview_is_bounded_and_has_no_full_rows(store) -> None:
    rows = [[f"2026-{month:02d}", "AB"[month % 2], month * 10] for month in range(1, 13)]
    meta = _save(store, ["work_month", "line", "qty"], rows, truncated=True)

    preview = read_preview(meta.result_id, access_scope=SCOPE)

    assert preview["row_count"] == 12 and preview["source_truncated"] is True
    assert len(preview["sample_rows"]) == 5
    assert preview["sample_rows"][0] == {"work_month": "2026-01", "line": "B", "qty": 10}
    assert preview["statistics"]["qty"] == {
        "min": 10, "max": 120, "avg": 65.0, "sum": 780, "null_count": 0,
    }
    assert preview["distinct_counts"] == {"work_month": 12, "line": 2}
    assert {group["value"]: group["count"] for group in preview["top_groups"]["line"]} == {"A": 6, "B": 6}
    assert "rows" not in preview and "table" not in preview
    assert [c["name"] for c in preview["columns"]] == ["work_month", "line", "qty"]


def test_preview_groups_are_capped_at_ten(store) -> None:
    meta = _save(store, ["name"], [[f"n{i}"] for i in range(25)])

    preview = read_preview(meta.result_id, access_scope=SCOPE)

    assert len(preview["top_groups"]["name"]) == 10


def test_table_pages_columns_and_limits(store) -> None:
    meta = _save(store, ["a", "b"], [[i, f"v{i}"] for i in range(120)])

    first = read_table(meta.result_id, access_scope=SCOPE)
    last = read_table(meta.result_id, page=3, page_size=50, access_scope=SCOPE)
    selected = read_table(
        meta.result_id, page=1, page_size=2, columns=["b"], access_scope=SCOPE
    )

    assert (first["page"], first["page_size"], len(first["rows"])) == (1, 10, 10)
    assert len(last["rows"]) == 20 and last["rows"][0] == [100, "v100"]
    assert first["row_count"] == first["filtered_row_count"] == 120
    assert [(c["name"], c["role"]) for c in selected["columns"]] == [("b", "category")]
    assert selected["rows"] == [["v0"], ["v1"]]
    assert all(len(row) == len(first["columns"]) for row in first["rows"])


def test_table_searches_and_sorts_the_full_stored_result_before_paging(store) -> None:
    meta = _save(
        store,
        ["part", "lot_count"],
        [["part_1", 10], ["part_2", 30], ["other", 99], ["part_3", 20]],
    )

    result = read_table(
        meta.result_id,
        page=1,
        page_size=2,
        search="PART_",
        sort_column="lot_count",
        sort_direction="desc",
        access_scope=SCOPE,
    )

    assert result["row_count"] == 4
    assert result["filtered_row_count"] == 3
    assert result["rows"] == [["part_2", 30], ["part_3", 20]]


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"page": "0"}, "INVALID_REQUEST"),
        ({"page": "x"}, "INVALID_REQUEST"),
        ({"page_size": "101"}, "INVALID_REQUEST"),
        ({"page_size": "0"}, "INVALID_REQUEST"),
        ({"columns": ["a", "a"]}, "INVALID_REQUEST"),
        ({"columns": ["zzz"]}, "COLUMN_NOT_FOUND"),
        ({"search": "x" * 201}, "INVALID_REQUEST"),
        ({"sort_column": "a"}, "INVALID_REQUEST"),
        ({"sort_direction": "asc"}, "INVALID_REQUEST"),
        ({"sort_column": "zzz", "sort_direction": "asc"}, "COLUMN_NOT_FOUND"),
        ({"sort_column": "a", "sort_direction": "sideways"}, "INVALID_REQUEST"),
        ({"sort_column": "a", "sort_direction": []}, "INVALID_REQUEST"),
    ],
)
def test_table_rejects_invalid_requests(store, kwargs, code) -> None:
    meta = _save(store, ["a"], [[1]])

    with pytest.raises(QueryResultError) as caught:
        read_table(meta.result_id, access_scope=SCOPE, **kwargs)

    assert caught.value.code == code


def test_missing_expired_and_foreign_results_share_one_not_found(store) -> None:
    from datetime import datetime, timedelta, timezone
    import json

    meta = _save(store, ["a"], [[1]])
    expired = _save(store, ["a"], [[1]])
    sidecar = store._meta_path(expired.result_id)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    errors = []
    for result_id, scope in [
        (meta.result_id, "other"),
        (meta.result_id, None),
        ("f" * 32, SCOPE),
        ("not-an-id", SCOPE),
        (expired.result_id, SCOPE),
    ]:
        with pytest.raises(QueryResultError) as caught:
            read_preview(result_id, access_scope=scope)
        errors.append((caught.value.code, caught.value.message, caught.value.details))

    assert len(set(errors)) == 1 and errors[0][0] == "RESULT_NOT_FOUND"


def test_read_chart_wraps_projection_with_result_metadata(store) -> None:
    meta = _save(store, ["m", "q"], [["2026-01", 1], ["2026-02", 2]], truncated=True)

    payload = read_chart(
        meta.result_id, chart_type="area", x_column="m", y_column="q", access_scope=SCOPE
    )

    assert payload["status"] == "ok" and payload["result_id"] == meta.result_id
    assert payload["chart"]["type"] == "area"
    assert payload["warnings"][0]["code"] == "SOURCE_TRUNCATED"


def test_build_preview_never_mutates_or_returns_frame(store) -> None:
    meta = _save(store, ["a"], [[1], [2]])
    frame = store.load(meta.result_id)

    preview = build_preview(meta, frame)

    assert preview["sample_rows"] == [{"a": 1}, {"a": 2}]


# ----------------------------------------------------------------------- API


def _client(scope="scope-a"):
    client = TestClient(app)
    if scope:
        client.cookies.set("pp_session_scope", scope)
    return client


def test_query_result_api_round_trip_and_headers(store) -> None:
    meta = _save(store, ["m", "q"], [["2026-01", 1], ["2026-02", 2]])
    client = _client()

    preview = client.get(f"/api/query-results/{meta.result_id}/preview")
    table = client.get(
        f"/api/query-results/{meta.result_id}/table"
        "?page=1&page_size=1&columns=q&search=2&sort_column=q&sort_direction=desc"
    )
    chart = client.get(
        f"/api/query-results/{meta.result_id}/chart"
        "?chart_type=line&x_column=m&y_column=q&title=%EC%B6%94%EC%9D%B4"
    )

    assert preview.status_code == table.status_code == chart.status_code == 200
    assert preview.json()["row_count"] == 2
    assert table.json()["rows"] == [[2]] and table.json()["columns"][0]["name"] == "q"
    assert table.json()["filtered_row_count"] == 1
    assert chart.json()["chart"]["categories"] == ["2026-01", "2026-02"]
    for response in (preview, table, chart):
        assert response.headers["cache-control"].startswith("private, max-age=")
        assert response.headers["vary"] == "Cookie"


def test_query_result_api_errors_are_uniform_and_safe(store) -> None:
    meta = _save(store, ["m", "q"], [["2026-01", 1]])

    hidden = _client("scope-b").get(f"/api/query-results/{meta.result_id}/preview")
    missing = _client().get(f"/api/query-results/{'f' * 32}/preview")
    no_cookie = _client(None).get(f"/api/query-results/{meta.result_id}/table")
    bad_chart = _client().get(
        f"/api/query-results/{meta.result_id}/chart?chart_type=bar&x_column=nope&y_column=q"
    )
    bad_page = _client().get(f"/api/query-results/{meta.result_id}/table?page=abc")
    aggregation = _client().get(
        f"/api/query-results/{meta.result_id}/chart?chart_type=bar&x_column=m&y_column=q&aggregation=median"
    )

    assert hidden.status_code == missing.status_code == no_cookie.status_code == 404
    assert hidden.json() == missing.json() == no_cookie.json()
    assert hidden.json()["detail"]["code"] == "RESULT_NOT_FOUND"
    assert bad_chart.status_code == 422 and bad_chart.json()["detail"]["code"] == "COLUMN_NOT_FOUND"
    assert bad_page.status_code == 422 and bad_page.json()["detail"]["code"] == "INVALID_REQUEST"
    assert aggregation.status_code == 422
    for response in (hidden, bad_chart):
        assert str(store.directory) not in response.text
        assert meta.access_scope not in response.text
