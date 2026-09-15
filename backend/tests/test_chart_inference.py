"""차트 스펙 추론. (설계: docs/chart-visualization.md, chart 필드는 LLM 을 거치지 않는다)"""

from services.chart_inference import infer_chart, infer_chart_from_records


def test_category_and_number_infers_bar() -> None:
    chart = infer_chart(["line", "qty"], [["A", 10], ["B", 20]])

    assert chart["type"] == "bar"
    assert chart["x"] == "line"
    assert chart["series"] == [{"key": "qty", "label": "qty"}]
    assert "truncated" not in chart


def test_date_axis_infers_line() -> None:
    chart = infer_chart(["workMonth", "qty"], [["202608", 10], ["202609", 20]])

    assert chart["type"] == "line"
    assert chart["x"] == "workMonth"


def test_too_many_numeric_columns_returns_none() -> None:
    chart = infer_chart(
        ["line", "qty", "defect", "scrap"],
        [["A", 10, 1, 2]],
    )

    assert chart is None


def test_no_numeric_column_returns_none() -> None:
    chart = infer_chart(["line", "status"], [["A", "ok"]])

    assert chart is None


def test_empty_rows_returns_none() -> None:
    assert infer_chart(["line", "qty"], []) is None


def test_bar_truncates_to_top_n_and_reports_hidden_count() -> None:
    columns = ["line", "qty"]
    rows = [[f"L{i}", i] for i in range(30)]

    chart = infer_chart(columns, rows)

    assert chart["type"] == "bar"
    assert len(chart["categories"]) == 20
    assert chart["truncated"] is True
    assert chart["hiddenCount"] == 10
    # 내림차순 정렬 후 상위 20개 — 가장 큰 값(29)이 먼저 온다
    assert chart["categories"][0] == "L29"


def test_work_date_without_group_column_infers_line() -> None:
    chart = infer_chart(["work_date", "plan_qty"], [["2026-09-01", 100]])

    assert chart["type"] == "line"


def test_group_and_date_and_number_infers_grouped_line() -> None:
    """예: 실적_조회의 {line, workMonth, qty} — 라인별로 시리즈를 나눈 line 차트."""

    columns = ["line", "workMonth", "qty"]
    rows = [
        ["A", "202608", 100],
        ["B", "202608", 200],
        ["A", "202609", 110],
        ["B", "202609", 210],
    ]

    chart = infer_chart(columns, rows)

    assert chart["type"] == "line"
    assert chart["x"] == "workMonth"
    assert chart["categories"] == ["202608", "202609"]
    assert {s["key"] for s in chart["series"]} == {"A", "B"}


def test_infer_chart_from_records_adapts_dict_rows() -> None:
    records = [
        {"line": "A", "workMonth": "202608", "qty": 100},
        {"line": "B", "workMonth": "202608", "qty": 200},
    ]

    chart = infer_chart_from_records(records)

    assert chart["type"] == "line"
    assert chart["x"] == "workMonth"


def test_infer_chart_from_records_empty_returns_none() -> None:
    assert infer_chart_from_records([]) is None


def test_code_and_name_pair_keeps_name_column_only() -> None:
    """실제 LLM 이 만드는 SQL 은 `line_cd`+`line_nm` 을 함께 SELECT 하는 경우가
    흔하다(예: `SELECT m.line_cd, m.line_nm, SUM(...) FROM ... JOIN LINE_MASTER m`).
    이 둘은 같은 개체의 두 표현이지 서로 다른 그룹 축이 아니므로, 사람이 읽는
    `_nm` 만 남기고 bar 로 판정해야 한다."""

    columns = ["line_cd", "line_nm", "total_qty"]
    rows = [
        ["A", "1라인", 18427],
        ["B", "2라인", 13855],
    ]

    chart = infer_chart(columns, rows)

    assert chart["type"] == "bar"
    assert chart["x"] == "line_nm"
    assert chart["categories"] == ["1라인", "2라인"]


def test_code_without_matching_name_column_is_kept() -> None:
    """`_cd` 접미사가 있어도 짝이 되는 `_nm` 컬럼이 없으면 그대로 둔다."""

    chart = infer_chart(["material_cd", "qty"], [["M1", 10], ["M2", 20]])

    assert chart["type"] == "bar"
    assert chart["x"] == "material_cd"
